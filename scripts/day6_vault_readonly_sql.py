"""Read-only, pinned FSDS NUM evidence queries for the Day 6 proposal.

The script prints SQL by default. ``--execute`` uses the configured Databricks
SQL warehouse and writes only local, ignored evidence under runs/day6-vault/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = "589e80595c7c8cb8"
SOURCE_IDS = ("SRC000005", "SRC000054", "SRC000064")
TABLES = (
    ("clean_c300_m1_records_main_recovery_20261021_v4_full",
     "clean_c300_m1_bindings_main_recovery_20261021_v4_full"),
    ("clean_c300_m1_records_num_recovery_20261021_v1_recovery",
     "clean_c300_m1_bindings_num_recovery_20261021_v1_recovery"),
)


def verify_baseline() -> None:
    freeze = json.loads((ROOT / "metadata/freezes/C1500_v1/freeze.json").read_text())
    roster_path = ROOT / "metadata/freezes/C1500_v1/C1500.bindings.json"
    assert hashlib.sha256(roster_path.read_bytes()).hexdigest() == freeze[
        "files_sha256"]["C1500.bindings.json"]
    roster = json.loads(roster_path.read_text())
    fsds = [row for row in roster if "/sec_fsds/" in row["raw_path"]]
    assert len(fsds) == 60
    assert set(SOURCE_IDS) <= {row["source_instance_id"] for row in fsds}
    result = json.loads((ROOT / "metadata/freezes/O_C1500_M2_v1/"
                         "databricks_result_freeze_v2.json").read_text())
    assert result["status"] == "FROZEN_IN_DATABRICKS_SOURCE_PRESERVING"
    assert result["pinned_read_version"] == 0


def source_sql() -> str:
    arms = []
    ids = ",".join(f"'{item}'" for item in SOURCE_IDS)
    for records, bindings in TABLES:
        arms.append(f"""SELECT r.source_instance_id, r.run_id, r.binding_sha256,
  r.source_line, r.byte_offset, r.byte_length, r.fields,
  b.raw_sha256, b.member_sha256, b.archive_member
FROM workspace.edp_lab.{records} VERSION AS OF 0 r
JOIN workspace.edp_lab.{bindings} VERSION AS OF 0 b
  ON r.run_id=b.run_id AND r.binding_sha256=b.binding_sha256
WHERE r.record_kind='DATA' AND b.processing_status='COMPLETE'
  AND b.archive_member='num.txt' AND r.source_instance_id IN ({ids})""")
    return " UNION ALL ".join(arms)


def sql() -> dict[str, str]:
    base = source_sql()
    fields = """fields[0].lexical_value AS adsh, fields[1].lexical_value AS tag,
fields[2].lexical_value AS version, fields[3].lexical_value AS ddate,
fields[4].lexical_value AS qtrs, fields[5].lexical_value AS uom,
fields[6].lexical_value AS segments, fields[7].lexical_value AS coreg,
fields[8].lexical_value AS value, fields[9].lexical_value AS footnote"""
    prefix = f"WITH source AS ({base}), num AS (SELECT source_instance_id,run_id,binding_sha256,source_line,byte_offset,byte_length,raw_sha256,member_sha256,archive_member,{fields} FROM source)"
    context = "adsh,tag,version,ddate,qtrs,uom,segments,coreg"
    return {
        "bindings": " UNION ALL ".join(
            f"SELECT source_instance_id,run_id,binding_sha256,raw_sha256,member_sha256,"
            f"archive_member,processing_status,records_total,records_data,fields_data "
            f"FROM workspace.edp_lab.{binding} VERSION AS OF 0 "
            f"WHERE source_instance_id IN (" + ",".join(f"'{sid}'" for sid in SOURCE_IDS) +
            ") AND archive_member='num.txt'" for _, binding in TABLES),
        "coverage": prefix + """ SELECT source_instance_id, COUNT(*) rows,
COUNT(DISTINCT adsh) distinct_adsh, COUNT(DISTINCT named_struct('tag',tag,'version',version)) distinct_concepts,
SUM(CASE WHEN adsh='' THEN 1 ELSE 0 END) blank_adsh,
SUM(CASE WHEN tag='' THEN 1 ELSE 0 END) blank_tag,
SUM(CASE WHEN version='' THEN 1 ELSE 0 END) blank_version,
SUM(CASE WHEN segments='' THEN 1 ELSE 0 END) blank_segments,
SUM(CASE WHEN coreg='' THEN 1 ELSE 0 END) blank_coreg,
SUM(CASE WHEN value='' THEN 1 ELSE 0 END) blank_value,
SUM(CASE WHEN footnote='' THEN 1 ELSE 0 END) blank_footnote,
COUNT(DISTINCT named_struct('adsh',adsh,'tag',tag,'version',version,'ddate',ddate,'qtrs',qtrs,'uom',uom,'segments',segments,'coreg',coreg)) distinct_context
FROM num GROUP BY source_instance_id ORDER BY source_instance_id""",
        "collisions": prefix + f""" SELECT {context},COUNT(*) occurrences,
COUNT(DISTINCT value) distinct_values,COUNT(DISTINCT footnote) distinct_footnotes,
MIN(named_struct('source_instance_id',source_instance_id,'source_line',source_line,'byte_offset',byte_offset)) first_locator,
MAX(named_struct('source_instance_id',source_instance_id,'source_line',source_line,'byte_offset',byte_offset)) last_locator
FROM num GROUP BY {context} HAVING COUNT(*)>1
ORDER BY occurrences DESC LIMIT 20""",
        "special_collisions": prefix + f""" SELECT source_instance_id,{context},COUNT(*) occurrences,
COLLECT_LIST(named_struct('line',source_line,'offset',byte_offset,'value',value,'footnote',footnote)) observations
FROM num GROUP BY source_instance_id,{context}
HAVING COUNT(*)>1 AND (source_instance_id='SRC000005' OR COUNT(DISTINCT footnote)>1)
ORDER BY source_instance_id LIMIT 10""",
        "m1_witness": prefix + """ SELECT source_instance_id,run_id,binding_sha256,source_line,
byte_offset,byte_length,adsh,tag,version,ddate,qtrs,uom,segments,coreg,value,footnote
FROM num WHERE source_instance_id='SRC000054' AND source_line=337467""",
        "cross_delivery": prefix + """ SELECT adsh,COUNT(DISTINCT source_instance_id) deliveries,
COUNT(*) occurrences,MIN(source_instance_id) first_source,MAX(source_instance_id) last_source
FROM num GROUP BY adsh HAVING COUNT(DISTINCT source_instance_id)>1
ORDER BY deliveries DESC,occurrences DESC LIMIT 20""",
        "tag_collisions": prefix + """ SELECT tag,COUNT(DISTINCT version) versions,
MIN(version) first_version,MAX(version) last_version,COUNT(*) occurrences
FROM num GROUP BY tag HAVING COUNT(DISTINCT version)>1
ORDER BY versions DESC,occurrences DESC LIMIT 20""",
        "concept_summary": prefix + """ SELECT COUNT(DISTINCT tag) distinct_tags,
COUNT(DISTINCT named_struct('tag',tag,'version',version)) distinct_tag_version_pairs,
SUM(CASE WHEN tag='' THEN 1 ELSE 0 END) blank_tag,
SUM(CASE WHEN version='' THEN 1 ELSE 0 END) blank_version
FROM num""",
        "locator": prefix + """ SELECT COUNT(*) rows,
COUNT(DISTINCT named_struct('source_instance_id',source_instance_id,'binding_sha256',binding_sha256,'source_line',source_line)) distinct_locator,
COUNT(DISTINCT named_struct('source_instance_id',source_instance_id,'binding_sha256',binding_sha256,'byte_offset',byte_offset,'byte_length',byte_length)) distinct_intervals,
COUNT(DISTINCT run_id) runs,COUNT(DISTINCT binding_sha256) bindings
FROM num""",
        "grain_summary": prefix + """ , groups AS (
SELECT adsh,tag,version,ddate,qtrs,uom,segments,coreg,
 COUNT(*) n, COUNT(DISTINCT named_struct('value',value,'footnote',footnote)) payloads,
 COUNT(DISTINCT value) values, COUNT(DISTINCT footnote) footnotes
FROM num GROUP BY adsh,tag,version,ddate,qtrs,uom,segments,coreg
), coarse AS (
SELECT adsh,tag,version,ddate,qtrs,uom,coreg, COUNT(*) n,
 COUNT(DISTINCT segments) segment_variants
FROM num GROUP BY adsh,tag,version,ddate,qtrs,uom,coreg
), tags AS (
SELECT tag,COUNT(DISTINCT version) versions FROM num GROUP BY tag
)
SELECT (SELECT COUNT(*) FROM groups WHERE n>1) context_collision_groups,
 (SELECT SUM(n) FROM groups WHERE n>1) context_collision_rows,
 (SELECT COUNT(*) FROM groups WHERE n>1 AND payloads>1) differing_payload_groups,
 (SELECT COUNT(*) FROM groups WHERE n>1 AND payloads=1) identical_payload_groups,
 (SELECT COUNT(*) FROM groups WHERE n>1 AND values>1) differing_value_groups,
 (SELECT COUNT(*) FROM groups WHERE n>1 AND footnotes>1) differing_footnote_groups,
 (SELECT COUNT(*) FROM coarse WHERE n>1) coarse_collision_groups,
 (SELECT COUNT(*) FROM coarse WHERE segment_variants>1) segment_sensitive_groups,
 (SELECT COUNT(*) FROM tags) distinct_tags,
 (SELECT COUNT(*) FROM tags WHERE versions>1) multi_version_tags""",
    }


def cli(*args: str) -> dict:
    result = subprocess.run(["databricks", *args, "-p", "edp-lab", "-o", "json"],
                            capture_output=True, text=True, check=False, timeout=180)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout)


def execute(name: str, statement: str) -> None:
    out = ROOT / "runs/day6-vault"
    out.mkdir(parents=True, exist_ok=True)
    request = {"warehouse_id": WAREHOUSE, "statement": statement,
               "wait_timeout": "50s", "on_wait_timeout": "CONTINUE", "disposition": "INLINE"}
    digest = hashlib.sha256(statement.encode()).hexdigest()
    path = out / f"{name}-{digest[:12]}.json"
    if path.exists():
        print(name, path, "already recorded")
        return
    submitted = cli("api", "post", "/api/2.0/sql/statements", "--json", json.dumps(request))
    result = submitted
    while result.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        time.sleep(5)
        result = cli("api", "get", "/api/2.0/sql/statements/" + result["statement_id"])
    path.write_text(json.dumps({"request": request, "submitted": submitted, "result": result},
                               indent=2, sort_keys=True) + "\n")
    print(name, digest, result["statement_id"], result["status"], path)


def write_request(name: str, statement: str) -> None:
    out = ROOT / "runs/day6-vault"
    out.mkdir(parents=True, exist_ok=True)
    request = {"warehouse_id": WAREHOUSE, "statement": statement,
               "wait_timeout": "50s", "on_wait_timeout": "CONTINUE", "disposition": "INLINE"}
    path = out / f"{name}-request.json"
    path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n")
    print(name, hashlib.sha256(statement.encode()).hexdigest(), path)


def main() -> None:
    verify_baseline()
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--write-requests", action="store_true")
    parser.add_argument("--query", choices=tuple(sql()))
    args = parser.parse_args()
    for name, statement in sql().items():
        if args.query and name != args.query:
            continue
        if args.execute:
            execute(name, statement)
        elif args.write_requests:
            write_request(name, statement)
        else:
            print(f"-- {name}\n{statement}\n")


if __name__ == "__main__":
    main()
