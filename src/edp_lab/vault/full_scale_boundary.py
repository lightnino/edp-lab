"""Pure validation for a proposed full-scale Vault Jobs and live-freeze boundary.

These functions grant no authority and perform no Databricks calls. A protected
service must verify owner signatures, deployment hashes and live readback before
using a validated request or accepting a freeze candidate.
"""

from __future__ import annotations

import re

from edp_lab.operating.authority import Denied
from edp_lab.vault.standing_v2 import NAMESPACE

SHA = re.compile(r"[0-9a-f]{64}\Z")
SOURCE = re.compile(r"SRC[0-9]{6}\Z")
TABLE = re.compile(r"[a-z][a-z0-9_]{1,127}\Z")


def _sha(value: object) -> bool:
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def validate_batch(request: dict, authority: dict) -> None:
    """Reject a batch outside an independently supplied, signed authority.

    ``authority`` must come from owner-controlled trust, never a repo proposal.
    The check is deliberately exact; runtime selection and manifest contents
    must be hash-pinned by that authority and checked by the protected service.
    """
    required = {"schema", "cohort", "namespace", "source_ids", "source_manifest_sha256",
                "contracts", "target_tables", "runtime_sha256", "batch_id",
                "max_data_rows", "timeout_seconds", "max_retries", "mode"}
    if not isinstance(request, dict) or set(request) != required:
        raise Denied("VAULT_BATCH_FIELDS_INVALID")
    if request["schema"] != "EDP_VAULT_SPARK_BATCH_V1" or request["mode"] != "INSERT_ONLY":
        raise Denied("VAULT_BATCH_MODE_INVALID")
    if request["cohort"] != "C2000" or request["namespace"] != NAMESPACE:
        raise Denied("VAULT_BATCH_TARGET_INVALID")
    sources = request["source_ids"]
    if (not isinstance(sources, list) or not sources
            or sources != sorted(set(sources))
            or any(not isinstance(s, str) or not SOURCE.fullmatch(s) for s in sources)
            or not set(sources) <= set(authority.get("source_ids", []))):
        raise Denied("VAULT_BATCH_SOURCES_INVALID")
    tables = request["target_tables"]
    if (not isinstance(tables, list) or not tables or tables != sorted(set(tables))
            or any(not isinstance(t, str) or not TABLE.fullmatch(t) for t in tables)
            or not set(tables) <= set(authority.get("target_tables", []))):
        raise Denied("VAULT_BATCH_TABLES_INVALID")
    if (not isinstance(request["contracts"], dict) or not request["contracts"]
            or request["contracts"] != authority.get("contracts")
            or any(not _sha(v) for v in request["contracts"].values())):
        raise Denied("VAULT_BATCH_CONTRACTS_INVALID")
    if (request["source_manifest_sha256"] != authority.get("source_manifest_sha256")
            or request["runtime_sha256"] != authority.get("runtime_sha256")
            or not _sha(request["source_manifest_sha256"])
            or not _sha(request["runtime_sha256"])):
        raise Denied("VAULT_BATCH_PIN_INVALID")
    if (not isinstance(request["batch_id"], str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", request["batch_id"])):
        raise Denied("VAULT_BATCH_ID_INVALID")
    for field, limit in (("max_data_rows", "max_data_rows"),
                         ("timeout_seconds", "timeout_seconds")):
        value = request[field]
        ceiling = authority.get(limit)
        if type(value) is not int or type(ceiling) is not int or not 0 < value <= ceiling:
            raise Denied("VAULT_BATCH_LIMIT_INVALID")
    if request["max_retries"] != 0:
        raise Denied("VAULT_BATCH_RETRY_FORBIDDEN")


def validate_freeze_candidate(candidate: dict, authority: dict) -> None:
    """Check complete live-readback shape before protected signing.

    This cannot establish that values came from Databricks. A separate trusted
    verifier must perform the reads itself, then sign its own receipt.
    """
    required = {"schema", "cohort", "namespace", "source_manifest_sha256",
                "contracts", "tables", "source_coverage", "status"}
    if not isinstance(candidate, dict) or set(candidate) != required:
        raise Denied("VAULT_FREEZE_FIELDS_INVALID")
    if (candidate["schema"] != "EDP_VAULT_FREEZE_CANDIDATE_V1"
            or candidate["cohort"] != "C2000"
            or candidate["namespace"] != NAMESPACE
            or candidate["status"] != "LIVE_READBACK_COMPLETE"
            or candidate["source_manifest_sha256"] != authority.get("source_manifest_sha256")
            or candidate["contracts"] != authority.get("contracts")):
        raise Denied("VAULT_FREEZE_SCOPE_INVALID")
    tables = candidate["tables"]
    expected = set(authority.get("target_tables", []))
    if not isinstance(tables, dict) or set(tables) != expected or not expected:
        raise Denied("VAULT_FREEZE_TABLE_COVERAGE_INVALID")
    for name, table in tables.items():
        if (not TABLE.fullmatch(name) or not isinstance(table, dict)
                or set(table) != {"uc_table_id", "delta_version", "row_count",
                                  "history_sha256", "readback_sha256"}
                or not isinstance(table["uc_table_id"], str) or not table["uc_table_id"]
                or type(table["delta_version"]) is not int or table["delta_version"] < 0
                or type(table["row_count"]) is not int or table["row_count"] < 0
                or not _sha(table["history_sha256"])
                or not _sha(table["readback_sha256"])):
            raise Denied("VAULT_FREEZE_TABLE_INVALID")
    coverage = candidate["source_coverage"]
    expected_sources = set(authority.get("source_ids", []))
    if (not isinstance(coverage, dict) or set(coverage) != expected_sources
            or any(value not in {"LOADED", "PRESERVED_ONLY", "UNSUPPORTED", "FAILED"}
                   for value in coverage.values())):
        raise Denied("VAULT_FREEZE_SOURCE_COVERAGE_INVALID")
