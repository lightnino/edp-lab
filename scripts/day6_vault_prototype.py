"""Bounded read-only C1500 Vault input selection and guarded deployment preflight.

The selected lexical rows remain in ignored ``runs/day6-vault-prototype``.
No warehouse write is issued by this script without a separately verified
controlled-write path; its current commands are deliberately read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from day6_vault_readonly_sql import WAREHOUSE, cli, source_sql, verify_baseline

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/day6-vault-prototype"
IDS = ("SRC000005", "SRC000054", "SRC000064")
HEADER = ("adsh", "tag", "version", "ddate", "qtrs", "uom", "segments",
          "coreg", "value", "footnote")
WITNESS = {"SRC000005": (89863, 651978),
           "SRC000054": (337467,),
           "SRC000064": (3723826, 3723836, 3723930, 3723931)}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sample_sql() -> str:
    """All repeated full-context groups plus deterministic normal witnesses.

    This reads only the three approved pinned NUM bindings; it may scan their
    rows to find all collision groups, but returns at most 1000 DATA rows.
    """
    source = source_sql()
    keys = ",".join(f"r.fields[{i}].lexical_value" for i in range(8))
    witness = " OR ".join(
        f"(source_instance_id='{sid}' AND source_line IN ({','.join(map(str, lines))}))"
        for sid, lines in WITNESS.items())
    return f"""WITH source AS ({source}), ranked AS (
 SELECT r.*, COUNT(*) OVER (PARTITION BY r.source_instance_id,{keys}) AS slot_n,
 ROW_NUMBER() OVER (PARTITION BY r.source_instance_id ORDER BY r.byte_offset) AS source_rank
 FROM source r
), chosen AS (
 SELECT * FROM ranked WHERE slot_n>1 OR source_rank<=8 OR {witness}
)
SELECT source_instance_id,run_id,binding_sha256,source_line,byte_offset,byte_length,
 raw_sha256,member_sha256,archive_member,to_json(fields) AS fields_json,slot_n,source_rank
FROM chosen ORDER BY source_instance_id,byte_offset LIMIT 1000"""


def submit_read(name: str, sql: str) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    request = {"warehouse_id": WAREHOUSE, "statement": sql,
               "wait_timeout": "50s", "on_wait_timeout": "CONTINUE",
               "disposition": "INLINE"}
    request_sha = sha(json.dumps(request, sort_keys=True).encode())
    path = OUT / f"{name}-{request_sha[:12]}.json"
    if path.exists():
        return json.loads(path.read_text())
    submitted = cli("api", "post", "/api/2.0/sql/statements", "--json", json.dumps(request))
    result = submitted
    while result.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        time.sleep(5)
        result = cli("api", "get", "/api/2.0/sql/statements/" + result["statement_id"])
    packet = {"request_sha256": request_sha, "request": request,
              "submitted": submitted, "result": result}
    path.write_text(json.dumps(packet, sort_keys=True, indent=2) + "\n")
    return packet


def source_roster() -> dict:
    roster = json.loads((ROOT / "metadata/freezes/C1500_v1/C1500.bindings.json").read_text())
    return {r["source_instance_id"]: r for r in roster if r["source_instance_id"] in IDS}


def manifest(packet: dict) -> dict:
    if packet["result"].get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError("SAMPLE_SQL_FAILED")
    result = packet["result"]["result"]
    if packet["result"].get("manifest", {}).get("truncated"):
        raise RuntimeError("SAMPLE_RESULT_TRUNCATED")
    roster = source_roster()
    rows = []
    seen = set()
    for values in result.get("data_array", []):
        sid, run, binding, line, offset, length, raw_sha, member_sha, member, fields, slot_n, rank = values
        if sid not in roster or raw_sha != roster[sid]["raw_sha256"]:
            raise RuntimeError("SOURCE_ROSTER_MISMATCH")
        key = (sid, int(offset), int(length))
        if key in seen:
            raise RuntimeError("DUPLICATE_LOCATOR")
        seen.add(key)
        fields = json.loads(fields)
        if len(fields) != len(HEADER):
            raise RuntimeError("FIELD_WIDTH_MISMATCH")
        rows.append({"source_instance_id": sid, "run_id": run,
                     "binding_sha256": binding, "source_line": int(line),
                     "byte_offset": int(offset), "byte_length": int(length),
                     "raw_path": roster[sid]["raw_path"], "raw_sha256": raw_sha,
                     "archive_member": member, "member_sha256": member_sha,
                     "m1_fields": fields, "slot_population_size": int(slot_n),
                     "source_rank": int(rank)})
    if len(rows) >= 1000 or not rows:
        raise RuntimeError("SAMPLE_CAP_OR_EMPTY")
    for sid, lines in WITNESS.items():
        if not set(lines) <= {r["source_line"] for r in rows if r["source_instance_id"] == sid}:
            raise RuntimeError("MISSING_WITNESS")
    encoded = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return {"schema": "DAY6_VAULT_PROTOTYPE_SAMPLE_V1", "selection_sql_sha256": sha(sample_sql().encode()),
            "rows_sha256": sha(encoded), "selected_data_occurrences": len(rows),
            "warehouse_statement_id": packet["result"]["statement_id"], "rows": rows}


def permission_sql() -> tuple[str, ...]:
    return ("SELECT current_user(), current_catalog(), current_schema()",
            "SHOW GRANTS ON CATALOG workspace",
            "SHOW SCHEMAS IN workspace LIKE 'edp_lab_day6_vault_proto'",
            "DESCRIBE DETAIL workspace.edp_lab.clean_c300_m1_records_main_recovery_20261021_v4_full",
            "DESCRIBE DETAIL workspace.edp_lab.clean_c300_m1_records_num_recovery_20261021_v1_recovery",
            ("SELECT source_instance_id,run_id,parser_profile_id,parser_version,model_version,rule_version "
            "FROM workspace.edp_lab.clean_c300_m1_bindings_main_recovery_20261021_v4_full VERSION AS OF 0 "
            "WHERE source_instance_id='SRC000005' AND archive_member='num.txt' "
            "UNION ALL SELECT source_instance_id,run_id,parser_profile_id,parser_version,model_version,rule_version "
            "FROM workspace.edp_lab.clean_c300_m1_bindings_num_recovery_20261021_v1_recovery VERSION AS OF 0 "
            "WHERE source_instance_id IN ('SRC000054','SRC000064') AND archive_member='num.txt'"))


def build_local() -> dict:
    """Project the saved read-only sample with the exact live binding versions."""
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))
    from edp_lab.vault.prototype import project, validate_batch

    sample = json.loads((OUT / "sample-manifest.json").read_text())
    packet = submit_read("preflight-6", permission_sql()[5])
    versions = {sid: {"run_id": run, "parser_profile_id": profile,
                      "parser_version": parser, "model_version": model,
                      "rule_version": rule}
                for sid, run, profile, parser, model, rule in
                packet["result"]["result"]["data_array"]}
    approved = {}
    for sid in IDS:
        matching = [r for r in sample["rows"] if r["source_instance_id"] == sid]
        first = matching[0]
        approved[sid] = {**versions[sid], **{name: first[name] for name in
                                       ("raw_sha256", "member_sha256", "binding_sha256")}}
    projected = [project(row, approved) for row in sample["rows"]]
    validate_batch(projected)
    path = OUT / "projected-manifest.json"
    path.write_text(json.dumps({"approved_bindings": approved, "rows": projected},
                               sort_keys=True, ensure_ascii=False, indent=2) + "\n")
    from collections import Counter

    slot_counts = Counter(r["fact_slot_hk"] for r in projected)
    summary = {"schema": "DAY6_VAULT_PROTOTYPE_LOCAL_PROJECTION_V1",
               "sample_rows_sha256": sample["rows_sha256"],
               "projected_file_sha256": sha(path.read_bytes()),
               "occurrences": len(projected),
               "filings": len({r["filing_hk"] for r in projected}),
               "concepts": len({r["concept_hk"] for r in projected}),
               "fact_slots": len(slot_counts),
               "assertions": len({r["assertion_hk"] for r in projected}),
               "collision_slots": sum(n > 1 for n in slot_counts.values()),
               "collision_assertions": sum(n for n in slot_counts.values() if n > 1),
               "m2_outcomes": dict(Counter(r["m2_outcome"] for r in projected)),
               "status": "LOCAL_PROJECTION_ONLY_NO_DELTA_WRITE"}
    (OUT / "local-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("render", "sample", "preflight", "build-local"))
    args = parser.parse_args()
    verify_baseline()
    if args.command == "render":
        print(sample_sql())
        print("\n-- Access and source-version inspection:\n" + "\n".join(permission_sql()))
    elif args.command == "sample":
        packet = submit_read("sample", sample_sql())
        sample = manifest(packet)
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / "sample-manifest.json"
        path.write_text(json.dumps(sample, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        print(json.dumps({key: value for key, value in sample.items() if key != "rows"}, sort_keys=True))
    elif args.command == "preflight":
        for n, sql in enumerate(permission_sql(), 1):
            packet = submit_read(f"preflight-{n}", sql)
            result = packet["result"]
            print(json.dumps({"query": n, "statement_id": result.get("statement_id"),
                              "status": result.get("status"), "result": result.get("result")},
                             sort_keys=True))
    else:
        print(json.dumps(build_local(), sort_keys=True))


if __name__ == "__main__":
    main()
