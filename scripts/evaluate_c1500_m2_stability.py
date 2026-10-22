"""Read-only, version-pinned C1500 M2 Stability probes.

The CLI requests and complete responses live in ignored runs/; this module never
creates or changes a Databricks relation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/c1500-m2-stability/v1"
WAREHOUSE = "589e80595c7c8cb8"


def save_new(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError(f"Existing evidence differs: {path}")
        return
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def cli(*args: str) -> dict:
    result = subprocess.run(
        ["databricks", *args, "-p", "edp-lab", "-o", "json"],
        capture_output=True, text=True, check=False, timeout=1800,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout)


def query(label: str, statement: str) -> dict:
    request = {"warehouse_id": WAREHOUSE, "statement": statement,
               "wait_timeout": "50s", "on_wait_timeout": "CONTINUE",
               "disposition": "INLINE"}
    save_new(OUT / f"{label}-request.json", request)
    response = cli("api", "post", "/api/2.0/sql/statements",
                   "--json", "@" + str(OUT / f"{label}-request.json"))
    save_new(OUT / f"{label}-submitted.json", response)
    while response.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        time.sleep(5)
        response = cli("api", "get", "/api/2.0/sql/statements/" + response["statement_id"])
    save_new(OUT / f"{label}-result.json", response)
    if response.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError(f"{label}: {response.get('status')}")
    return response


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    parser.add_argument("statement")
    args = parser.parse_args()
    if args.statement == "COMBINED_MULTISET":
        candidate = (ROOT / "sql/stability/c1500_m2_v1/combined_candidate.sql").read_text()
        candidate = candidate[:candidate.index("\nSELECT occurrence_class, count(*)")]
        sources = {
            "OLD_C750_RECORD": "workspace.edp_lab.o_c750_m2_records_historical_20261022_v1",
            "NEW_N750_SEC_RECORD": "workspace.edp_lab.clean_n750_m1_sec_records_step8_v1 VERSION AS OF 0",
            "NEW_N750_XML_PROPERTY": "workspace.edp_lab.clean_n750_m1_treasury_properties_step8_v1 VERSION AS OF 0",
            "NEW_N750_M2_EVALUATION": "workspace.edp_lab.clean_n750_m2_treasury_rates_step8_v1 VERSION AS OF 0",
        }
        checks = []
        for scope, source in sources.items():
            actual = f"SELECT payload FROM combined WHERE occurrence_class='{scope}'"
            pinned = ("SELECT to_json(struct(p.*), map('ignoreNullFields', 'false')) "
                      f"AS payload FROM {source} p")
            for direction, left, right in (("candidate_minus_pinned", actual, pinned),
                                           ("pinned_minus_candidate", pinned, actual)):
                checks.append(f"SELECT '{scope}' AS scope, '{direction}' AS direction, "
                              f"count(*) AS differences FROM ({left} EXCEPT ALL {right}) d")
        statement = candidate + "\n" + "\nUNION ALL\n".join(checks)
    elif args.statement in {"FIN_001", "FIN_002"}:
        prefix = (ROOT / "sql/stability/c1500_m2_v1/fin_candidate_prefix.sql").read_text()
        fixture = (ROOT / "sql/reconciliation/fin_eval_v1" / (args.statement + ".sql")).read_text()
        fixture = fixture[fixture.index("WITH facts AS ("):]
        fixture = fixture.replace("WITH facts AS (", "facts AS (", 1)
        fixture = fixture.replace(
            "workspace.edp_lab.q_c300_m1_records_reconciled_recovery_20261021_v2_full",
            "combined_fin")
        fixture = fixture.replace("TRY_CAST(fields[8].lexical_value AS DECIMAL(38,4)) AS amount",
                                  "value_decimal AS amount")
        statement = prefix + fixture
    else:
        statement = Path(args.statement[1:]).read_text() if args.statement.startswith("@") else args.statement
    response = query(args.label, statement)
    print(json.dumps({"label": args.label, "statement_id": response.get("statement_id"),
                      "rows": response.get("result", {}).get("data_array", []),
                      "request_sha256": sha(OUT / f"{args.label}-request.json"),
                      "result_sha256": sha(OUT / f"{args.label}-result.json")}))


if __name__ == "__main__":
    main()
