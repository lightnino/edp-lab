"""Static CI checks for the retained live O_C1500_M2 freeze evidence.

These checks cannot substitute for the referenced Databricks SQL receipts.
"""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVALUATION = ROOT / "metadata/evaluations/o_c1500_m2_databricks_freeze_v2.json"
MARKER = ROOT / "metadata/freezes/O_C1500_M2_v1/databricks_result_freeze_v2.json"
VIEW_SQL = ROOT / "sql/freezes/o_c1500_m2_v1/result_view.sql"


def data(path: Path) -> dict:
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_live_evaluation_and_marker_reconcile() -> None:
    evaluation, marker = data(EVALUATION), data(MARKER)
    assert evaluation["status"] == "PASS"
    assert evaluation["scope"] == "SOURCE_PRESERVING_ADDITIVE_M2_ONLY"
    assert marker["status"] == "FROZEN_IN_DATABRICKS_SOURCE_PRESERVING"
    assert marker["runtime_evaluation_sha256"] == sha(EVALUATION)
    assert marker["databricks_view_object_id"] == evaluation["result_view"]["uc_table_id"]
    assert marker["databricks_view"] == "workspace.edp_lab.o_c1500_m2_result_frozen_v1"
    assert evaluation["result_view"]["source_sql_sha256"] == sha(VIEW_SQL)
    assert marker["view_source_sql_sha256"] == sha(VIEW_SQL)
    assert evaluation["result_view"]["queryable_marker"][
        "edp.freeze.source_sql_sha256"] == sha(VIEW_SQL)
    assert len(evaluation["runtime_receipts"]) >= 68
    assert all(r["terminal_status"] == "SUCCEEDED" and r["statement_id"]
               and r["response_sha256"] for r in evaluation["runtime_receipts"].values())


def test_pinned_physical_inputs_and_zero_copy_sql() -> None:
    evaluation = data(EVALUATION)
    sql = VIEW_SQL.read_text()
    refs = re.findall(r"workspace\.edp_lab\.([a-z0-9_]+)\s+VERSION AS OF\s+(\d+)",
                      sql, re.IGNORECASE)
    assert len(refs) == 10
    assert all(version == "0" for _, version in refs)
    assert {table for table, _ in refs} == set(evaluation["result_view"][
        "direct_pinned_physical_dependencies"])
    assert "o_c750_m2_records_historical_20261022_v1" not in sql
    assert "CREATE OR REPLACE" not in sql.upper()
    assert not re.search(r"(?im)^\s*CREATE\s+TABLE\b", sql)
    assert len(evaluation["physical_delta_pins"]) == 11
    assert all(pin["approved_read_version"] == 0 and pin["delta_id"]
               and pin["protection"] in {"ALREADY_APPEND_ONLY", "SET_APPEND_ONLY_METADATA_ONLY"}
               for pin in evaluation["physical_delta_pins"].values())


def test_approved_scope_and_population_do_not_claim_economic_pass() -> None:
    evaluation, marker = data(EVALUATION), data(MARKER)
    owner = ROOT / "metadata/evaluations/treasury_l3_owner_scope_decision_v1.json"
    scoped = ROOT / "metadata/evaluations/c1500_m2_stability_scoped_v3_owner_acceptance.json"
    assert evaluation["owner_decision_sha256"] == sha(owner)
    assert evaluation["scoped_acceptance_sha256"] == sha(scoped)
    assert len(data(owner)["approvals"]) == 50
    assert data(scoped)["scoped_results"] == {
        "B2_1_SOURCE_PRESERVING": "PASS", "C1_SOURCE_PRESERVING": "PASS"}
    population = evaluation["population"]
    assert (population["physical_sources"], population["operational_bindings"]) == (1500, 1932)
    assert (population["treasury_valid"], population["treasury_structural_missing"]) == (12793, 155)
    assert population["total_occurrences_including_framing_and_derived"] == 319151239
    assert sum(item["occurrences"] for item in population["occurrence_classes"].values()) == 319151239
    assert evaluation["limitations"]["treasury_economic_L6_B"] == "NOT_IMPLEMENTED_OUT_OF_SCOPE"
    assert marker["treasury_economic_L6_B"] == "NOT_IMPLEMENTED_OUT_OF_SCOPE"
    assert "BLOCKED" in evaluation["limitations"]["historical_day4_C3_4"]
    assert marker["backup_archive_copy_created"] is False
    assert marker["full_dataset_materialization_created"] is False
