"""Read-only dispatch over trusted, already verified SourceTable bindings.

Requests are data, never authority. The host supplies both bindings and grants.
No source loading, filesystem writes, network access, or Agent runtime is involved.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Literal

from edp_lab.profiling import tools
from edp_lab.profiling.source_reader import SourceTable, canonical_hash

VERSION = "DETERMINISTIC_TOOL_V1"
ToolName = Literal[
    "profile_table", "profile_column", "find_duplicates", "candidate_key_scan", "schema_fingerprint"
]
Status = Literal["SUCCESS", "PARTIAL", "FAILED", "BLOCKED"]


@dataclass(frozen=True)
class SourceRef:
    binding: str
    source_identity_fingerprint: str
    configuration_fingerprint: str


@dataclass(frozen=True)
class Authorization:
    principal: str
    permission: Literal["READ_PROFILE"] = "READ_PROFILE"


@dataclass(frozen=True)
class ExecutionScope:
    population: Literal["FULL_LOGICAL_TABLE_DATA_OCCURRENCES"] = (
        "FULL_LOGICAL_TABLE_DATA_OCCURRENCES"
    )
    read_only: bool = True
    max_rows: int = 500_000
    max_cells: int = 10_000_000


@dataclass(frozen=True)
class EmptyParameters:
    pass


@dataclass(frozen=True)
class ColumnParameters:
    column: str
    top_limit: int = 10
    sample_size: int = 5
    sample_seed: int = 0


@dataclass(frozen=True)
class DuplicateParameters:
    columns: tuple[str, ...] | None = None
    group_limit: int = 20
    witness_limit: int = 3


@dataclass(frozen=True)
class CandidateKeyParameters:
    composites: tuple[tuple[str, ...], ...] = ()
    search_columns: tuple[str, ...] | None = None
    max_width: int = 1
    max_combinations: int = 256


Parameters = EmptyParameters | ColumnParameters | DuplicateParameters | CandidateKeyParameters
PARAMETERS = {
    "profile_table": EmptyParameters, "profile_column": ColumnParameters,
    "find_duplicates": DuplicateParameters, "candidate_key_scan": CandidateKeyParameters,
    "schema_fingerprint": EmptyParameters,
}


@dataclass(frozen=True)
class ToolRequest:
    tool: ToolName
    source: SourceRef
    authorization: Authorization
    parameters: Parameters = field(default_factory=EmptyParameters)
    scope: ExecutionScope = field(default_factory=ExecutionScope)
    tool_version: str = VERSION


@dataclass(frozen=True)
class ToolResponse:
    status: Status
    result: dict | None
    input_refs: dict
    evidence_refs: dict
    metrics: dict
    warnings: list[str]
    errors: list[str]
    unresolved_questions: list[str]
    run_id: str
    tool_version: str
    result_fingerprint: str
    approval_required: bool
    side_effects: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


def _strings(value):
    return isinstance(value, (tuple, list)) and all(type(v) is str and v for v in value)


def _validate(request):
    if request.tool_version != VERSION or request.tool not in PARAMETERS:
        raise ValueError("UNSUPPORTED_TOOL_OR_VERSION")
    if type(request.parameters) is not PARAMETERS[request.tool]:
        raise ValueError("PARAMETER_CONTRACT_MISMATCH")
    if not all(type(v) is str and v for v in asdict(request.source).values()):
        raise ValueError("INVALID_SOURCE_REFERENCE")
    if type(request.authorization.principal) is not str or not request.authorization.principal:
        raise ValueError("INVALID_PRINCIPAL")
    scope = request.scope
    if scope.population != ExecutionScope().population or scope.read_only is not True:
        raise ValueError("UNSUPPORTED_EXECUTION_SCOPE")
    for name in ("max_rows", "max_cells"):
        if type(getattr(scope, name)) is not int or getattr(scope, name) < 1:
            raise ValueError("INVALID_RESOURCE_LIMIT")
    for name, value in asdict(request.parameters).items():
        if name == "column":
            if type(value) is not str or not value:
                raise ValueError("INVALID_COLUMN")
        elif name in ("columns", "search_columns"):
            if value is not None and not _strings(value):
                raise ValueError("INVALID_COLUMNS")
        elif name == "composites":
            if not isinstance(value, (tuple, list)) or not all(_strings(v) for v in value):
                raise ValueError("INVALID_COMPOSITES")
        elif type(value) is not int:
            raise ValueError("INVALID_INTEGER_PARAMETER")
        elif name != "sample_seed" and not 0 <= value <= 4096:
            raise ValueError("PARAMETER_LIMIT_EXCEEDED")


def _request(value: ToolRequest | Mapping) -> ToolRequest:
    if isinstance(value, ToolRequest):
        # Reconstruct nested contracts too: Python annotations alone do not validate input.
        value = asdict(value)
    if not isinstance(value, Mapping):
        raise TypeError("REQUEST_MUST_BE_OBJECT")
    data = dict(value)
    tool = data.get("tool")
    if not isinstance(tool, str) or tool not in PARAMETERS:
        raise ValueError("UNKNOWN_TOOL")
    data["source"] = SourceRef(**data["source"])
    data["authorization"] = Authorization(**data["authorization"])
    data["scope"] = ExecutionScope(**data.get("scope", {}))
    data["parameters"] = PARAMETERS[tool](**data.get("parameters", {}))
    request = ToolRequest(**data)
    _validate(request)
    return request


def _unresolved(value):
    reasons = set()
    if isinstance(value, dict):
        if value.get("computation_mode") == "NOT_COMPUTED":
            reasons.add(value.get("reason", "NOT_COMPUTED"))
        for child in value.values():
            reasons.update(_unresolved(child))
    elif isinstance(value, list):
        for child in value:
            reasons.update(_unresolved(child))
    return reasons


class ProfilingAdapters:
    """Host-owned source registry and principal-to-binding grants.

    Deep copies isolate execution from caller mutation. Limits govern profiling of
    materialized tables, not the separate reader's memory or ingestion cost.
    """

    def __init__(self, sources: Mapping[str, SourceTable], grants: Mapping[str, set[str]]):
        self._sources = deepcopy(dict(sources))
        self._grants = {principal: frozenset(names) for principal, names in grants.items()}

    def source_ref(self, binding: str) -> SourceRef:
        table = self._sources[binding]
        return SourceRef(binding, canonical_hash(table.source), canonical_hash(table.config))

    def invoke(self, value: ToolRequest | Mapping) -> ToolResponse:
        result = None
        inputs = {}
        errors, warnings, questions = [], [], []
        status: Status = "FAILED"
        approval = False
        identity = {"tool_version": VERSION, "request": "MALFORMED"}
        try:
            request = _request(value)
            identity["request"] = asdict(request)
            inputs = asdict(request.source)
            binding = request.source.binding
            if (request.authorization.permission != "READ_PROFILE" or
                    binding not in self._grants.get(request.authorization.principal, ())):
                status, approval = "BLOCKED", True
                errors.append("AUTHORIZATION_DENIED")
            elif binding not in self._sources:
                errors.append("SOURCE_UNAVAILABLE")
            else:
                table = self._sources[binding]
                identity["provenance"] = table.provenance
                if request.source != self.source_ref(binding):
                    status = "BLOCKED"
                    errors.append("SOURCE_OR_CONFIGURATION_MISMATCH")
                elif (len(table.rows) > request.scope.max_rows or
                      len(table.rows) * len(table.columns) > request.scope.max_cells):
                    status = "BLOCKED"
                    errors.append("RESOURCE_LIMIT_EXCEEDED")
                else:
                    result = deepcopy(getattr(tools, request.tool)(
                        table, **asdict(request.parameters)))
                    errors.extend(result["errors"])
                    questions = sorted(_unresolved(result))
                    status = ("PARTIAL" if table.rows else "FAILED") if errors else (
                        "PARTIAL" if questions else "SUCCESS")
                    if questions:
                        warnings.append("Some requested metrics remain NOT_COMPUTED")
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            errors.append(f"INVALID_REQUEST: {exc}")
        evidence = {} if result is None else {
            "source": result["source"], "config": result["config"],
            "provenance": result["provenance"], "profiling_run_id": result["run_id"],
            "profiling_result_sha256": result["result_sha256"],
        }
        metrics = {} if result is None else {
            "rows_scanned": result["rows_scanned"], "population": result["population"]}
        payload = {"status": status, "result": result, "input_refs": inputs, "evidence_refs": evidence,
                       "metrics": metrics, "warnings": warnings, "errors": errors,
                       "unresolved_questions": questions, "run_id": canonical_hash(identity),
                       "tool_version": VERSION, "approval_required": approval, "side_effects": ()}
        return ToolResponse(**payload, result_fingerprint=canonical_hash(payload))

    def profile_table(self, request: ToolRequest | Mapping) -> ToolResponse:
        return self._call("profile_table", request)

    def profile_column(self, request: ToolRequest | Mapping) -> ToolResponse:
        return self._call("profile_column", request)

    def find_duplicates(self, request: ToolRequest | Mapping) -> ToolResponse:
        return self._call("find_duplicates", request)

    def candidate_key_scan(self, request: ToolRequest | Mapping) -> ToolResponse:
        return self._call("candidate_key_scan", request)

    def schema_fingerprint(self, request: ToolRequest | Mapping) -> ToolResponse:
        return self._call("schema_fingerprint", request)

    def _call(self, name, value):
        try:
            request = _request(value)
            if request.tool != name:
                raise ValueError("TOOL_NAME_MISMATCH")
        except (ValueError, TypeError, KeyError, AttributeError):
            return self.invoke({"tool": name, "parameters": {"invalid": True}})
        return self.invoke(request)
