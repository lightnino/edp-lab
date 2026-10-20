"""EDP_ANALYST_AGENT_V0: deterministic, read-only orchestration of typed tools.

No SDK, network, autonomous semantic decisions, file writes or source loading.
The host owns source bindings and authenticated principal grants.
"""
from __future__ import annotations

from dataclasses import asdict

from edp_lab.profiling.source_reader import canonical_hash
from edp_lab.tool_adapters import (
    Authorization,
    CandidateKeyParameters,
    ColumnParameters,
    DuplicateParameters,
    EmptyParameters,
    ProfilingAdapters,
    ToolRequest,
)

VERSION = "EDP_ANALYST_AGENT_V0"
REPORT_VERSION = "SOURCE_OBSERVATION_REPORT_V1"
STATES = ("OBSERVED", "PROPOSED", "VALIDATED", "REJECTED", "UNRESOLVED")


def plan(host: ProfilingAdapters, binding: str, principal: str, columns: tuple[str, ...]):
    """Fixed mechanical plan; names remain exact source text, never business keys."""
    params = [("profile_table", EmptyParameters()),
              ("schema_fingerprint", EmptyParameters()),
              ("find_duplicates", DuplicateParameters()),
              ("candidate_key_scan", CandidateKeyParameters(
                  search_columns=columns[:3], max_width=2))]
    params.extend(("profile_column", ColumnParameters(name)) for name in columns)
    return [ToolRequest(name, host.source_ref(binding), Authorization(principal), parameters)
            for name, parameters in params]


def observe(host: ProfilingAdapters, binding: str, principal: str, columns: tuple[str, ...]):
    """All five functions are reused through adapters, including each column."""
    requests = plan(host, binding, principal, columns)
    trace = []
    for sequence, request in enumerate(requests):
        response = host.invoke(request).to_dict()
        trace.append({"sequence": sequence, "request": asdict(request), "response": response})
    errors = [e for step in trace for e in step["response"]["errors"]]
    statuses = {step["response"]["status"] for step in trace}
    status = ("BLOCKED" if "BLOCKED" in statuses else "FAILED" if errors else "PASS")
    unresolved = sorted({q for step in trace
                         for q in step["response"]["unresolved_questions"]})
    findings = [{"state": "OBSERVED", "claim": "Literal mechanical tool outputs",
                 "evidence_refs": [s["response"]["result_fingerprint"] for s in trace]},
                {"state": "UNRESOLVED", "claim":
                 "No business key, equivalence, deduplication or source NULL semantics approved",
                 "evidence_refs": []}]
    report = {"schema_version": REPORT_VERSION, "agent_version": VERSION,
              "binding": binding, "source_ref": asdict(host.source_ref(binding)),
              "execution_status": status, "tool_statuses": sorted(statuses),
              "population": "FULL_LOGICAL_TABLE_DATA_OCCURRENCES",
              "trace": trace, "findings": findings, "errors": errors,
              "unresolved_questions": unresolved, "side_effects": [],
              "semantic_promotions": [],
              "run_id": canonical_hash({"agent": VERSION,
                                        "tool_runs": [s["response"]["run_id"] for s in trace]})}
    report["result_fingerprint"] = canonical_hash(report)
    return report


def validate_report(report):
    expected = {"schema_version", "agent_version", "binding", "source_ref", "execution_status",
                "tool_statuses", "population", "trace", "findings", "errors",
                "unresolved_questions", "side_effects", "semantic_promotions", "run_id",
                "result_fingerprint"}
    if (set(report) != expected or report["schema_version"] != REPORT_VERSION
            or report["agent_version"] != VERSION
            or report["execution_status"] not in {"PASS", "FAILED", "BLOCKED"}
            or report["population"] != "FULL_LOGICAL_TABLE_DATA_OCCURRENCES"
            or report["side_effects"] or report["semantic_promotions"]
            or any(f["state"] not in STATES for f in report["findings"])):
        raise ValueError("INVALID_OBSERVATION_REPORT")
    payload = {k: v for k, v in report.items() if k != "result_fingerprint"}
    if canonical_hash(payload) != report["result_fingerprint"]:
        raise ValueError("REPORT_FINGERPRINT_MISMATCH")
    for sequence, step in enumerate(report["trace"]):
        response = step["response"]
        if step["sequence"] != sequence or canonical_hash({
                k: v for k, v in response.items() if k != "result_fingerprint"
        }) != response["result_fingerprint"]:
            raise ValueError("TRACE_FINGERPRINT_MISMATCH")
    return True
