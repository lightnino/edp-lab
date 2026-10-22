"""Stage N750 Step 8 CLEAN Parquet, publish versioned Delta and pinned views.

Each phase is explicit and resumable. Existing remote files/tables/views are
never overwritten. All SQL requests/responses are retained under ignored runs/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.ingestion.n750_step8_authorization import authorize

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/n750/step8-v1"
CLEAN = OUT / "clean"
PUB = OUT / "publication"
BASE = "dbfs:/Volumes/workspace/edp_lab/raw/n750-step8-clean-v1-5ae18d7d2ee7"
SQL_BASE = BASE.removeprefix("dbfs:")
WAREHOUSE = "589e80595c7c8cb8"
TABLES = {
    "sec": "workspace.edp_lab.clean_n750_m1_sec_records_step8_v1",
    "xml": "workspace.edp_lab.clean_n750_m1_treasury_properties_step8_v1",
    "m2": "workspace.edp_lab.clean_n750_m2_treasury_rates_step8_v1",
    "coverage": "workspace.edp_lab.clean_n750_source_coverage_step8_v1",
}
FILES = {"sec": "sec-m1-records.parquet", "xml": "treasury-m1-properties.parquet",
         "m2": "treasury-m2-projections.parquet", "coverage": "source-coverage.parquet"}
VIEWS = {
    "sec": "workspace.edp_lab.q_n750_m1_sec_records_step8_v1",
    "xml": "workspace.edp_lab.q_n750_m1_treasury_properties_step8_v1",
    "m2": "workspace.edp_lab.q_n750_m2_treasury_rates_step8_v1",
    "coverage": "workspace.edp_lab.q_n750_source_coverage_step8_v1",
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as f:
        json.dump(value, f, indent=2, sort_keys=True, default=str)
        f.write("\n")


def cli(*args):
    result = subprocess.run(["databricks", *args, "-p", "edp-lab", "-o", "json"],
                            check=False, capture_output=True, text=True, timeout=1800)
    if result.returncode:
        raise RuntimeError(f"Databricks {args[:2]} failed: {result.stderr.strip()}")
    return result.stdout


def sql(label, statement):
    request = {"warehouse_id": WAREHOUSE, "statement": statement,
               "wait_timeout": "50s", "on_wait_timeout": "CONTINUE",
               "disposition": "INLINE"}
    save(PUB / (label + "-request.json"), request)
    response = json.loads(cli("api", "post", "/api/2.0/sql/statements",
                              "--json", "@" + str(PUB / (label + "-request.json"))))
    save(PUB / (label + "-submitted.json"), response)
    while response.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        time.sleep(5)
        response = json.loads(cli("api", "get", "/api/2.0/sql/statements/" + response["statement_id"]))
    save(PUB / (label + "-result.json"), response)
    if response.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError(f"SQL {label} failed: {response.get('status')}")
    return response


def rows(response):
    return response.get("result", {}).get("data_array", [])


def count(label, statement):
    values = rows(sql(label, statement))
    assert len(values) == 1 and len(values[0]) == 1, (label, values)
    return int(values[0][0])


def authorize_inputs():
    bindings = json.loads((ROOT / "metadata/admissions/N750_v1/bindings.json").read_bytes())
    grant = authorize(ROOT, "processing", [x["source_instance_id"] for x in bindings])
    complete = json.loads((CLEAN / "completion.json").read_bytes())
    assert complete["status"] == "PASS" and complete["sources_complete"] == 750
    assert complete["owner_grant_sha256"] == grant["owner_grant_sha256"]
    for key, name in FILES.items():
        assert sha(CLEAN / name) == complete["parquet_sha256"][key]
    return complete


def stage(complete):
    PUB.mkdir(parents=True, exist_ok=True)
    parent = json.loads(cli("fs", "ls", "dbfs:/Volumes/workspace/edp_lab/raw"))
    assert BASE.rsplit("/", 1)[-1] not in {x["name"] for x in parent}, "DESTINATION_EXISTS"
    cli("fs", "mkdir", BASE)
    assert json.loads(cli("fs", "ls", BASE)) == []
    for key, name in FILES.items():
        cli("fs", "cp", str(CLEAN / name), BASE + "/" + name)
        with tempfile.TemporaryDirectory(prefix="n750-clean-readback-") as temp:
            target = Path(temp) / name
            cli("fs", "cp", BASE + "/" + name, str(target))
            assert sha(target) == complete["parquet_sha256"][key]
    inventory = json.loads(cli("fs", "ls", BASE))
    assert {x["name"] for x in inventory} == set(FILES.values())
    save(PUB / "stage.json", {"status": "PASS", "destination": BASE,
         "files_sha256": complete["parquet_sha256"],
         "inventory": inventory, "verified_at_utc": datetime.now(UTC).isoformat()})


def verify_stage(complete):
    stage_record = json.loads((PUB / "stage.json").read_bytes())
    assert stage_record["status"] == "PASS" and stage_record["destination"] == BASE
    assert stage_record["files_sha256"] == complete["parquet_sha256"]
    actual = json.loads(cli("fs", "ls", BASE))
    assert actual == stage_record["inventory"]


def publish_tables(complete):
    verify_stage(complete)
    for key, name in FILES.items():
        table = TABLES[key]
        short = table.rsplit(".", 1)[-1]
        assert rows(sql("absence-" + key,
                        f"SHOW TABLES IN workspace.edp_lab LIKE '{short}'")) == []
        sql("create-" + key, f"CREATE TABLE {table} USING DELTA AS SELECT * FROM "
            f"read_files('{SQL_BASE}/{name}', format => 'parquet')")
    save(PUB / "tables-created.json", {"status": "CREATED_PENDING_INDEPENDENT_VALIDATION",
         "tables": TABLES, "created_at_utc": datetime.now(UTC).isoformat()})


def verify_tables(complete):
    assert (PUB / "tables-created.json").exists()
    expected = {"sec": complete["records_data"] + 745 * 7,
                "xml": complete["xml_properties_present"],
                "m2": complete["m2_evaluations"], "coverage": 750}
    evidence = {}
    for key, name in FILES.items():
        table = TABLES[key]
        observed = count("count-" + key, f"SELECT COUNT(*) FROM {table} VERSION AS OF 0")
        assert observed == expected[key], (key, observed, expected[key])
        source = f"read_files('{SQL_BASE}/{name}', format => 'parquet')"
        left = count("except-stage-" + key,
                     f"SELECT COUNT(*) FROM (SELECT * FROM {source} EXCEPT ALL "
                     f"SELECT * FROM {table} VERSION AS OF 0) x")
        right = count("except-delta-" + key,
                      f"SELECT COUNT(*) FROM (SELECT * FROM {table} VERSION AS OF 0 EXCEPT ALL "
                      f"SELECT * FROM {source}) x")
        assert left == right == 0, (key, left, right)
        history = rows(sql("history-" + key, f"DESCRIBE HISTORY {table} LIMIT 1"))
        detail = rows(sql("detail-" + key, f"DESCRIBE DETAIL {table}"))
        evidence[key] = {"table": table, "version": 0, "rows": observed,
                         "except_stage": left, "except_delta": right,
                         "history_row": history[0], "detail_row": detail[0]}
    assert count("sec-data-count", f"SELECT COUNT(*) FROM {TABLES['sec']} VERSION AS OF 0 "
                 "WHERE record_kind='DATA'") == complete["records_data"]
    assert count("sec-field-count", f"SELECT SUM(size(fields)) FROM {TABLES['sec']} VERSION AS OF 0 "
                 "WHERE record_kind='DATA'") == complete["fields_data"]
    assert count("m2-present-count", f"SELECT COUNT(*) FROM {TABLES['m2']} VERSION AS OF 0 "
                 "WHERE present=true") == complete["m2_present"]
    assert count("m2-missing-count", f"SELECT COUNT(*) FROM {TABLES['m2']} VERSION AS OF 0 "
                 "WHERE present=false AND conversion_outcome='MISSING' AND lexical_value IS NULL "
                 "AND value_decimal IS NULL") == complete["m2_missing"]
    assert count("m2-invalid-projection", f"SELECT COUNT(*) FROM {TABLES['m2']} VERSION AS OF 0 "
                 "WHERE (conversion_outcome='VALID' AND (value_decimal IS NULL OR "
                 "value_decimal <> CAST(lexical_value AS DECIMAL(38,4)))) OR "
                 "(conversion_outcome<>'VALID' AND value_decimal IS NOT NULL)") == 0
    save(PUB / "delta-readback.json", {"status": "PASS", "tables": evidence,
         "source_complete": 750, "sec_data": complete["records_data"],
         "xml_properties": complete["xml_properties_present"],
         "m2_evaluations": complete["m2_evaluations"],
         "verified_at_utc": datetime.now(UTC).isoformat()})


def publish_views(complete):
    verified = json.loads((PUB / "delta-readback.json").read_bytes())
    assert verified["status"] == "PASS" and set(verified["tables"]) == set(TABLES)
    for key, view in VIEWS.items():
        short = view.rsplit(".", 1)[-1]
        assert rows(sql("view-absence-" + key,
                        f"SHOW TABLES IN workspace.edp_lab LIKE '{short}'")) == []
        predicate = " WHERE record_kind='DATA'" if key == "sec" else ""
        sql("view-create-" + key, f"CREATE VIEW {view} AS SELECT * FROM "
            f"{TABLES[key]} VERSION AS OF 0{predicate}")
    expected = {"sec": complete["records_data"], "xml": complete["xml_properties_present"],
                "m2": complete["m2_evaluations"], "coverage": 750}
    counts = {key: count("view-count-" + key, f"SELECT COUNT(*) FROM {view}")
              for key, view in VIEWS.items()}
    assert counts == expected
    save(PUB / "queryable.json", {"status": "PASS", "views": VIEWS,
         "pinned_delta_versions": {table: 0 for table in TABLES.values()},
         "counts": counts, "verified_at_utc": datetime.now(UTC).isoformat(),
         "lossless_6_economic_reconciliation": "NOT_IMPLEMENTED_NO_APPROVED_RELATIONSHIP_GRAIN_UNITS"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("stage", "tables", "verify", "views"))
    args = parser.parse_args()
    complete = authorize_inputs()
    if args.action == "stage":
        stage(complete)
    elif args.action == "tables":
        publish_tables(complete)
    elif args.action == "verify":
        verify_tables(complete)
    else:
        publish_views(complete)
    print(f"N750 Step 8 {args.action} PASS", flush=True)


if __name__ == "__main__":
    main()
