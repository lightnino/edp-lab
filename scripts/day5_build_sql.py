"""Build exact, source-preserving N500 SQL from prepared membership without RAW reads."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "runs/day5/p6_candidate_v1"
OUTPUT = ROOT / "runs/day5/sql_v1"
WAREHOUSE = "589e80595c7c8cb8"
SCHEMA = "workspace.edp_lab"
ROSTER = f"{SCHEMA}.n500_input_roster_day5_v1"
SMOKE = f"{SCHEMA}.clean_n500_m1_smoke_day5_v1"
CLEAN = f"{SCHEMA}.clean_n500_m1_records_day5_v1"
CANDIDATE = f"{SCHEMA}.o_c2000_m2_candidate_day5_v1"
FROZEN = f"{SCHEMA}.o_c2000_m2_result_frozen_day5_v1"
OLD = f"{SCHEMA}.o_c1500_m2_result_frozen_v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def statement(name: str, sql: str) -> Path:
    path = OUTPUT / (name + ".json")
    with path.open("x") as stream:
        json.dump({"warehouse_id": WAREHOUSE, "statement": sql,
                   "wait_timeout": "30s"}, stream, sort_keys=True, indent=2)
        stream.write("\n")
    return path


def clean_sql(target: str, path: str) -> str:
    return f"""CREATE TABLE {target} USING DELTA AS
WITH files AS (
  SELECT path, length AS raw_bytes, decode(content, 'UTF-8') AS body
  FROM read_files({literal(path)}, format => 'binaryFile')
), lines AS (
  SELECT path, raw_bytes, pos + 1 AS source_line, line AS payload
  FROM files LATERAL VIEW posexplode(split(body, char(10))) exploded AS pos, line
  WHERE pos >= 7 AND line <> ''
), parsed AS (
  SELECT *, split(payload, '[|]', -1) AS fields FROM lines
)
SELECT roster.source_instance_id, roster.source_identity, roster.raw_sha256,
       roster.remote_raw_path, parsed.source_line,
       concat('line=', cast(parsed.source_line AS STRING)) AS locator,
       parsed.payload, size(parsed.fields) AS field_count,
       element_at(parsed.fields, 1) AS cik_lexical,
       element_at(parsed.fields, 2) AS company_name_lexical,
       element_at(parsed.fields, 3) AS form_type_lexical,
       element_at(parsed.fields, 4) AS date_filed_lexical,
       element_at(parsed.fields, 5) AS file_name_lexical,
       parsed.raw_bytes
FROM parsed JOIN {ROSTER} VERSION AS OF 0 roster
  ON regexp_replace(parsed.path, '^dbfs:', '') =
     regexp_replace(roster.remote_raw_path, '^dbfs:', '')"""


def result_sql(target: str) -> str:
    return f"""CREATE VIEW {target} AS
SELECT occurrence_class, source_instance_id, run_id, binding_ref, locator, payload
FROM {OLD}
UNION ALL
SELECT 'NEW_N500_SEC_RECORD' AS occurrence_class, source_instance_id,
       'day5_n500_v1' AS run_id, raw_sha256 AS binding_ref, locator, payload
FROM {CLEAN} VERSION AS OF 0"""


def main() -> None:
    candidate = json.loads((BASE / "candidate.json").read_bytes())
    rows = json.loads((BASE / "N500.bindings.json").read_bytes())
    if (candidate["status"] != "PREPARED_NOT_ADMITTED_REMOTE_READBACK_PENDING"
            or candidate["outputs_sha256"]["N500.bindings.json"]
            != sha(BASE / "N500.bindings.json")
            or len(rows) != 500 or candidate["new_count"] != 500):
        raise ValueError("P6_CANDIDATE_CHANGED")
    OUTPUT.mkdir(parents=True, exist_ok=False)
    values = ",\n".join("(" + ", ".join((literal(row["source_instance_id"]),
                                      literal(row["source_identity"]),
                                      literal(row["remote_raw_path"]),
                                      literal(row["raw_sha256"]),
                                      str(row["raw_bytes"]),
                                      str(row["data_records"]))) + ")" for row in rows)
    roster_sql = f"""CREATE TABLE {ROSTER} USING DELTA AS
SELECT * FROM VALUES
{values}
AS r(source_instance_id, source_identity, remote_raw_path,
     raw_sha256, raw_bytes, expected_records)"""
    prefix = candidate["remote_raw_prefix"].removeprefix("dbfs:")
    smoke_path = rows[0]["remote_raw_path"].removeprefix("dbfs:")
    built = [statement("roster", roster_sql),
             statement("smoke", clean_sql(SMOKE, smoke_path)),
             statement("full_clean", clean_sql(CLEAN, prefix + "/*/*")),
             statement("candidate_view", result_sql(CANDIDATE)),
             statement("result_view", result_sql(FROZEN))]
    summary = {"schema": "DAY5_SQL_BUILD_V1",
               "status": "PINNED_SQL_NOT_EXECUTED",
               "p6_candidate_sha256": sha(BASE / "candidate.json"),
               "statements": {p.stem: {"path": str(p.relative_to(ROOT)),
                                       "sha256": sha(p)} for p in built},
               "targets": {"roster": ROSTER, "smoke": SMOKE, "full_clean": CLEAN,
                           "candidate_view": CANDIDATE, "result_view": FROZEN},
               "expected_new_records": sum(row["data_records"] for row in rows),
               "expected_sources": 500,
               "source_handling": "UTF-8 LF only; first seven preamble/header/separator lines "
                                  "excluded; five pipe-delimited fields kept lexical; "
                                  "no NULL conversion, deduplication or business mapping"}
    with (OUTPUT / "build.json").open("x") as stream:
        json.dump(summary, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"status": summary["status"],
                      "expected_new_records": summary["expected_new_records"],
                      "statements": list(summary["statements"])}, sort_keys=True))


if __name__ == "__main__":
    main()
