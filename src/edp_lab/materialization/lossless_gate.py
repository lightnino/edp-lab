"""Deterministic per-binding CLEAN gate; consumer SQL cannot bypass membership."""
from __future__ import annotations

import re

VERSION = "C300_M1_LOSSLESS_GATE_V1"
REQUIRED = ("1", "2", "3", "4", "5", "6")


def decide(tests, processing_status):
    if processing_status == "BLOCKED":
        return "BLOCKED"
    if processing_status != "COMPLETE":
        return "FAIL" if processing_status == "FAILED" else "NOT_IMPLEMENTED"
    statuses = [tests.get(k, {}).get("status", "NOT_IMPLEMENTED") for k in REQUIRED]
    if "FAIL" in statuses:
        return "FAIL"
    if any(s.startswith("BLOCKED") for s in statuses):
        return "BLOCKED"
    if any(s != "PASS" for s in statuses[:5]):
        return "NOT_IMPLEMENTED"
    # NOT_APPLICABLE is permitted only for this reviewed measure boundary.
    sixth = tests["6"]
    if (sixth["status"] != "NOT_APPLICABLE"
            or sixth.get("boundary") != "M1_LEXICAL_V1" or not sixth.get("inventory_ref")):
        return "BLOCKED"
    return "PASS"


def view_sql(suffix, records_table, bindings_table, versions, gate):
    if not re.fullmatch(r"[A-Za-z0-9_]+", suffix):
        raise ValueError("UNSAFE_RUN_SUFFIX")
    if gate.get("version") != VERSION or not gate.get("evidence_sha256"):
        raise ValueError("UNSEALED_GATE")
    passed = sorted(r["binding_sha256"] for r in gate["bindings"] if r["gate_status"] == "PASS")
    if any(not re.fullmatch(r"[0-9a-f]{64}", sha) for sha in passed):
        raise ValueError("INVALID_BINDING_HASH")
    predicate = "r.binding_sha256 IN (" + ",".join(f"'{sha}'" for sha in passed) + ")" if passed else "false"
    base = f"""FROM {records_table} VERSION AS OF {int(versions[records_table])} r
      JOIN {bindings_table} VERSION AS OF {int(versions[bindings_table])} b
      ON r.run_id=b.run_id AND r.binding_sha256=b.binding_sha256"""
    where = f"r.record_kind='DATA' AND b.processing_status='COMPLETE' AND {predicate}"
    return {
        f"q_c300_m1_records_{suffix}": f"SELECT r.* {base} WHERE {where}",
        f"q_c300_m1_fields_{suffix}": f"""SELECT r.run_id,r.source_instance_id,r.binding_sha256,r.source_line,
          r.byte_offset,r.byte_length,f.*,b.raw_path,b.volume_path,b.raw_sha256,b.archive_member,
          b.member_sha256,b.parser_profile_id,b.parser_version,b.model_version,b.rule_version
          {base} LATERAL VIEW explode(r.fields) x AS f WHERE {where}""",
        f"q_c300_m1_coverage_{suffix}": f"SELECT * FROM {bindings_table} VERSION AS OF {int(versions[bindings_table])}"}
