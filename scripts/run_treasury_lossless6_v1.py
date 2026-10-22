"""Execute the four permanent, read-only Treasury Lossless 6 SQL controls."""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "metadata/evaluations/fixtures/treasury_lossless6_expected_v1.json"
SQL_ROOT = ROOT / "sql/reconciliation/treasury_lossless6_v1"
OUT = ROOT / "runs/treasury-lossless6/v1"
WAREHOUSE = "589e80595c7c8cb8"
NAMES = ("TRY_001", "TRY_002", "TRY_003", "TRY_004")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_bytes())


def quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def render(name: str, fixture: dict) -> str:
    sql = (SQL_ROOT / f"{name}.sql").read_text()
    if name == "TRY_001":
        pins = []
        allowlist = []
        for row in fixture["sources"]:
            pins.append("(" + ",".join((quoted(row["source_instance_id"]),
                        quoted(row["source_identity"]), quoted(row["raw_sha256"]),
                        str(row["entries"]), str(row["evaluations"]), str(row["valid"]),
                        str(row["missing"]))) + ")")
            allowlist.extend("(" + quoted(row["source_instance_id"]) + "," + quoted(q) + ")"
                             for q in row["qnames"])
        sql = sql.replace("{{PINS}}", ",".join(pins)).replace("{{ALLOWLIST}}", ",".join(allowlist))
    elif name == "TRY_004":
        prefix = (ROOT / "sql/stability/c1500_m2_v1/fin_candidate_prefix.sql").read_text()
        sql = sql.replace("{{FIN_CANDIDATE_PREFIX}}", prefix.rstrip().removesuffix(","))
    assert "{{" not in sql and "}}" not in sql
    return sql


def cli(*args: str) -> dict:
    process = subprocess.run(["databricks", *args, "-p", "edp-lab", "-o", "json"],
                             capture_output=True, text=True, check=False, timeout=1800)
    if process.returncode:
        raise RuntimeError(process.stderr.strip())
    return json.loads(process.stdout)


def save_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert read(path) == value, f"Evidence changed: {path}"
        return
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def execute(name: str, statement: str) -> dict:
    if (OUT / f"{name}-result.json").exists():
        previous = read(OUT / f"{name}-result.json")
        assert previous["status"]["state"] == "SUCCEEDED", name
        assert read(OUT / f"{name}-request.json")["statement"] == statement
        return previous
    request = {"warehouse_id": WAREHOUSE, "statement": statement,
               "wait_timeout": "50s", "on_wait_timeout": "CONTINUE", "disposition": "INLINE"}
    save_new(OUT / f"{name}-request.json", request)
    result = cli("api", "post", "/api/2.0/sql/statements", "--json",
                 "@" + str(OUT / f"{name}-request.json"))
    save_new(OUT / f"{name}-submitted.json", result)
    while result.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        time.sleep(5)
        result = cli("api", "get", "/api/2.0/sql/statements/" + result["statement_id"])
    save_new(OUT / f"{name}-result.json", result)
    if result["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(f"{name}: {result['status']}")
    return result


def verify_inputs(fixture: dict, step9: dict) -> None:
    assert len(fixture["sources"]) == 5
    assert fixture["totals"] == {"sources": 5, "entries": 1743, "source_specific_qnames": 50,
                                 "evaluations": 12948, "valid": 12793, "missing": 155}
    bindings = {r["source_instance_id"]: r for r in read(ROOT / fixture["source_binding_file"])}
    for row in fixture["sources"]:
        binding = bindings[row["source_instance_id"]]
        for key in ("source_identity", "raw_sha256", "raw_path"):
            assert row[key] == binding[key]
        assert len(row["qnames"]) == len(set(row["qnames"]))
        assert row["entries"] * len(row["qnames"]) == row["evaluations"]
        assert row["valid"] + row["missing"] == row["evaluations"]
    for key, relative in step9["evidence_locations"].items():
        if key in ("candidate_sql", "fin_projection_sql", "n750_raw_completion",
                   "n750_clean_completion", "n750_delta_readback", "n750_queryable",
                   "n750_live_verify", "combined_multiset_request", "combined_multiset_result",
                   "fin_001_result", "fin_002_result", "fin_witnesses_result",
                   "fin_typed_raw_witnesses_result"):
            assert sha(ROOT / relative) == step9["evidence_sha256"][key], key
    assert len(step9["combined_candidate"]["bidirectional_full_schema_differences"]) == 8
    assert all(x["differences"] == 0 for x in step9["combined_candidate"][
        "bidirectional_full_schema_differences"])
    assert step9["fin"] == {"FIN_001": "2/2 PASS", "FIN_002": "1/1 PASS",
                            "wrong_equity_difference": "1232700000.0000",
                            "lineage_witnesses": 13, "exact_fixture_differences": 0}


def evaluate(name: str, rows: list[list[str]], fixture: dict) -> dict:
    assert rows and all(row[0] == name + "_V1" for row in rows)
    if name == "TRY_001":
        expected = {r["source_instance_id"]: r for r in fixture["sources"]}
        assert {r[1] for r in rows} == set(expected)
        problems = []
        for r in rows:
            e = expected[r[1]]
            pairs = ((2, 3, e["entries"]), (4, 5, len(e["qnames"])),
                     (6, 7, e["evaluations"]), (8, 9, e["valid"]),
                     (10, 11, e["missing"]))
            if any(int(r[a]) != value or int(r[b]) != value for a, b, value in pairs):
                problems.append(r[1] + ":count")
            if int(r[12]) or int(r[13]):
                problems.append(r[1] + ":coverage_or_pin")
        return {"status": "PASS" if not problems else "FAIL", "discrepancies": problems,
                "actual_rows": rows}
    assert len(rows) == 1
    row = rows[0]
    if name == "TRY_002":
        problems = [] if int(row[1]) == 12793 and int(row[2]) == 12793 and all(
            int(v) == 0 for v in row[3:]) else ["numeric_or_lineage_discrepancy"]
    elif name == "TRY_003":
        expected = (12948, 12948, 12793, 12793, 155, 155, 0, 0, 0, 0, 249, 0)
        problems = [] if tuple(map(int, row[1:])) == expected else ["absence_or_multiplicity_discrepancy"]
    else:
        # TRY_004 live query proves source isolation; immutable Step 9 FIN/witness/
        # multiset receipts were verified above under their exact SHA fingerprints.
        problems = [] if len(row) == 6 and tuple(map(int, row[1:])) == (
            34564, 0, 0, 12793, 5) else [
                "combined_fin_noninterference_discrepancy"]
    return {"status": "PASS" if not problems else "FAIL", "discrepancies": problems,
            "actual_rows": rows}


def main() -> None:
    fixture = read(FIXTURE)
    step9 = read(ROOT / "metadata/evaluations/c1500_m2_stability_v1.json")
    verify_inputs(fixture, step9)
    summary = {"schema": "TREASURY_LOSSLESS6_RUNTIME_V1", "fixture_sha256": sha(FIXTURE),
               "step9_sha256": sha(ROOT / "metadata/evaluations/c1500_m2_stability_v1.json"),
               "input_table_pins": step9["output_pins"]["n750_tables"],
               "historical_table_pin": {k: step9["output_pins"][k] for k in (
                   "historical_m2_table", "historical_m2_delta_id", "historical_m2_uc_id",
                   "historical_m2_version")}, "controls": {}}
    for name in NAMES:
        label = "TRY_004_corrected" if name == "TRY_004" else name
        result = execute(label, render(name, fixture))
        assessed = evaluate(name, result["result"]["data_array"], fixture)
        summary["controls"][name + "_V1"] = {**assessed,
            "statement_id": result["statement_id"], "sql_template_sha256": sha(SQL_ROOT / f"{name}.sql"),
            "sql_request_sha256": sha(OUT / f"{label}-request.json"),
            "response_sha256": sha(OUT / f"{label}-result.json"),
            "request_ref": str((OUT / f"{label}-request.json").relative_to(ROOT)),
            "response_ref": str((OUT / f"{label}-result.json").relative_to(ROOT))}
        print(json.dumps({"control": name, "status": assessed["status"],
                          "statement_id": result["statement_id"], "rows": assessed["actual_rows"]}), flush=True)
    summary["status"] = "PASS" if all(x["status"] == "PASS" for x in summary["controls"].values()) else "FAIL"
    save_new(OUT / "runtime-summary.json", summary)
    print(json.dumps({"status": summary["status"], "sha256": sha(OUT / "runtime-summary.json")}))


if __name__ == "__main__":
    main()
