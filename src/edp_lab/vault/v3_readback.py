"""Read-only, bounded V3 Delta result evidence for the protected verifier.

The owner-controlled verifier must sign the returned evidence after comparing
the protected operation ledger and the pre-job eight-table baseline. This
module never signs, retries a write, or treats a Job result as its own proof.
"""

from __future__ import annotations

import hashlib
import json

from edp_lab.vault.v3_ddl import COLUMNS, NAMESPACE, TABLES


def _rows_digest(rows: list[dict]) -> str:
    normalized = [{name: row[name] for name, _ in COLUMNS if name != "load_dts"}
                  for row in rows]
    normalized.sort(key=lambda row: (row["hk"], row["occurrence_hk"]))
    return hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False).encode()).hexdigest()


def collect(spark, expected: dict[str, list[dict]], per_source: dict[str, int]) -> dict:
    if tuple(expected) != TABLES:
        raise ValueError("V3_READBACK_TABLE_ALLOWLIST_CHANGED")
    tables = {}
    for name in TABLES:
        full = NAMESPACE + "." + name
        detail = spark.sql("DESCRIBE DETAIL " + full).first().asDict(recursive=True)
        history = [row.asDict(recursive=True) for row in
                   spark.sql("DESCRIBE HISTORY " + full + " LIMIT 3").collect()]
        if (detail.get("format", "").lower() != "delta" or not detail.get("id")
                or not history or history[0]["version"] > 1
                or any(row["operation"] in {"DELETE", "UPDATE", "TRUNCATE"}
                       for row in history)):
            raise ValueError("V3_READBACK_DELTA_ID_OR_HISTORY_INVALID:" + name)
        columns = ",".join(name for name, _ in COLUMNS if name != "load_dts")
        persisted = [row.asDict(recursive=True) for row in
                     spark.sql("SELECT " + columns + " FROM " + full).collect()]
        count = len(persisted)
        expected_digest = _rows_digest(expected[name])
        actual_digest = _rows_digest(persisted)
        if count != len(expected[name]) or actual_digest != expected_digest:
            raise ValueError("V3_READBACK_ROW_COUNT_MISMATCH:" + name)
        tables[name] = {"uc_delta_id": detail["id"], "latest_version": history[0]["version"],
                        "operations": [{"version": row["version"],
                                        "operation": row["operation"]} for row in history],
                        "row_count": count, "exact_row_sha256": actual_digest}
    for name in ("v3_r_source_occurrence", "v3_r_load_event"):
        full = NAMESPACE + "." + name
        rows = spark.sql("SELECT source_instance_id, COUNT(*) AS n, "
                         "COUNT(DISTINCT occurrence_hk) AS unique_n FROM " + full +
                         " GROUP BY source_instance_id").collect()
        actual = {row["source_instance_id"]: int(row["n"]) for row in rows}
        if actual != per_source or any(row["n"] != row["unique_n"] for row in rows):
            raise ValueError("V3_READBACK_OCCURRENCE_COVERAGE_MISMATCH:" + name)
    if tables["v3_vault_reject_quarantine"]["row_count"] != 0:
        raise ValueError("V3_SELECTED_SOURCE_QUARANTINE_NONZERO")
    return {"schema": "EDP_C2000_VAULT_V3_READBACK_CANDIDATE_V1",
            "status": "CANDIDATE_REQUIRES_PROTECTED_LEDGER_AND_SIGNATURE",
            "source_occurrences": per_source, "tables": tables}
