"""Validate retained live Databricks receipts for the zero-copy O_C1500_M2 view.

This does not submit SQL. Runtime receipts are kept outside Git; the compact
versioned evaluation written here is their reproducible index and assessment.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/c1500-m2-databricks-freeze/v1"
OUT = ROOT / "metadata/evaluations/o_c1500_m2_databricks_freeze_v2.json"
VIEW = "workspace.edp_lab.o_c1500_m2_result_frozen_v1"
CLASSES = {
    "OLD_C750_RECORD": (316063821, 750),
    "NEW_N750_SEC_RECORD": (3052854, 745),
    "NEW_N750_XML_PROPERTY": (21616, 5),
    "NEW_N750_M2_EVALUATION": (12948, 5),
}


def read(path: Path) -> dict:
    return json.loads(path.read_bytes())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt(label: str) -> dict:
    request = RUN / f"{label}-request.json"
    result = RUN / f"{label}-result.json"
    assert request.is_file() and result.is_file(), label
    data = read(result)
    assert data["status"]["state"] == "SUCCEEDED", label
    return {"request_ref": str(request.relative_to(ROOT)), "request_sha256": sha(request),
            "response_ref": str(result.relative_to(ROOT)), "response_sha256": sha(result),
            "statement_id": data["statement_id"], "terminal_status": "SUCCEEDED"}


def rows(label: str) -> list[list[str]]:
    return read(RUN / f"{label}-result.json").get("result", {}).get("data_array", [])


def row_dict(label: str) -> dict:
    result = read(RUN / f"{label}-result.json")
    columns = [x["name"] for x in result["manifest"]["schema"]["columns"]]
    return dict(zip(columns, result["result"]["data_array"][0], strict=True))


def versioned_refs(sql: str) -> set[str]:
    matches = re.findall(r"workspace\.edp_lab\.([a-z0-9_]+)\s+VERSION AS OF\s+(\d+)",
                         sql, re.IGNORECASE)
    assert matches and all(version == "0" for _, version in matches)
    return {name for name, _ in matches}


def main() -> None:
    prior = read(ROOT / "metadata/evaluations/c1500_m2_stability_v1.json")
    pins = prior["output_pins"]
    owner_path = ROOT / "metadata/evaluations/treasury_l3_owner_scope_decision_v1.json"
    scoped_path = ROOT / "metadata/evaluations/c1500_m2_stability_scoped_v3_owner_acceptance.json"
    owner, scoped = read(owner_path), read(scoped_path)
    assert len(owner["approvals"]) == 50
    assert all(a["l3_disposition"] == "PRESERVED_NOT_MODELED" and a[
        "owner_decision"] == "APPROVED_SOURCE_PRESERVING_ONLY" for a in owner["approvals"])
    assert scoped["scoped_results"] == {"B2_1_SOURCE_PRESERVING": "PASS",
                                         "C1_SOURCE_PRESERVING": "PASS"}

    expected = dict(pins["historical_m1_delta_ids"])
    expected[pins["historical_m2_table"]] = pins["historical_m2_delta_id"]
    expected.update({v["name"]: v["delta_id"] for v in pins["n750_tables"].values()})
    assert len(expected) == 11
    delta = {}
    for table, identity in expected.items():
        key = table.rsplit(".", 1)[-1]
        detail = row_dict("detail-" + key)
        history = row_dict("history-" + key)
        assert detail["id"] == identity and detail["format"] == "delta"
        assert rows("v0-readable-" + key) == [["1"]]
        initial_version = int(history["version"])
        is_protected = json.loads(detail["properties"]).get("delta.appendOnly") == "true"
        if table in pins["historical_m1_delta_ids"]:
            assert initial_version == 1 and is_protected
            final_version = 1
            mutation = "ALREADY_APPEND_ONLY"
        else:
            assert (initial_version == 1 if table == pins[
                "historical_m2_table"] else initial_version == 0)
            assert not is_protected
            post = row_dict("post-detail-" + key)
            post_history = row_dict("post-history-" + key)
            final_version = int(post_history["version"])
            assert post["id"] == identity and post_history["operation"] == "SET TBLPROPERTIES"
            assert json.loads(post["properties"])["delta.appendOnly"] == "true"
            assert final_version == initial_version + 1
            assert rows("post-v0-" + key) == [["1"]]
            mutation = "SET_APPEND_ONLY_METADATA_ONLY"
        delta[table] = {"delta_id": identity, "approved_read_version": 0,
                        "latest_version_before": initial_version,
                        "latest_version_after": final_version, "protection": mutation}

    historical = rows("historical-view-definition")[0][0]
    historical_refs = versioned_refs(historical)
    assert historical_refs == {t.rsplit(".", 1)[-1] for t in pins[
        "historical_m1_delta_ids"]} | {pins["historical_m2_table"].rsplit(".", 1)[-1]}
    source_sql = ROOT / "sql/freezes/o_c1500_m2_v1/result_view.sql"
    source_text = source_sql.read_text()
    assert source_text.startswith("-- O_C1500_M2 source-preserving occurrence-level result")
    assert "CREATE OR REPLACE" not in source_text.upper()
    assert not re.search(r"(?im)^\s*CREATE\s+TABLE\b", source_text)
    result_refs = versioned_refs(source_text)
    assert result_refs == {t.rsplit(".", 1)[-1] for t in expected if "coverage" not in t}
    assert "o_c750_m2_records_historical_20261022_v1" not in source_text
    live_definition = rows("result-view-definition-post-marker")[0][0]
    assert versioned_refs(live_definition) == result_refs
    assert "o_c750_m2_records_historical_20261022_v1" not in live_definition
    assert read(RUN / "create-result-view-request.json")["statement"] == source_text

    candidate_sql = (ROOT / "sql/stability/c1500_m2_v1/combined_candidate.sql").read_text()
    old_branch = candidate_sql.split("WITH combined AS (", 1)[1].rsplit(
        "\n)\nSELECT occurrence_class", 1)[0].replace(
            "FROM workspace.edp_lab.o_c750_m2_records_historical_20261022_v1 o",
            "FROM old_records o")
    new_branch = source_text.split("), combined AS (", 1)[1].rsplit(
        "\n)\nSELECT occurrence_class", 1)[0]
    assert re.sub(r"\s+", "", old_branch) == re.sub(r"\s+", "", new_branch)

    counts = {r[0]: r for r in rows("result-view-counts")}
    assert set(counts) == set(CLASSES) | {"ALL"}
    for name, (expected_count, expected_sources) in CLASSES.items():
        row = counts[name]
        assert (int(row[1]), int(row[2]), int(row[4])) == (
            expected_count, expected_sources, 0)
    assert [int(x) for x in counts["ALL"][1:]] == [319151239, 1500, 1182, 0]
    assert int(counts["OLD_C750_RECORD"][3]) == 1182
    assert rows("n750-coverage") == [["750", "750"]]
    assert rows("treasury-outcomes") == [["MISSING", "155"], ["VALID", "12793"]]
    assert rows("result-view-sample-post-marker")[0][0] == "OLD_C750_RECORD"
    for name in ("new_n750_sec_record", "new_n750_xml_property", "new_n750_m2_evaluation"):
        sample = rows("sample-" + name)
        assert len(sample) == 1 and int(sample[0][-1]) > 0

    props = dict(rows("result-view-properties"))
    uc_path = RUN / "view-uc-get-post-marker.json"
    uc = read(uc_path)
    assert uc["full_name"] == VIEW and uc["table_type"] == "VIEW"
    assert uc["table_id"] == "43e16098-b123-4689-83d5-4d942bbe4dfc"
    deps = {x["table"]["table_full_name"].rsplit(".", 1)[-1] for x in uc[
        "view_dependencies"]["dependencies"]}
    assert deps == result_refs
    assert props["edp.freeze.status"] == "SOURCE_PRESERVING_VERIFIED"
    assert props["edp.freeze.scope"] == "SOURCE_PRESERVING_ADDITIVE_M2_ONLY"
    assert props["edp.freeze.version"] == "O_C1500_M2_DATABRICKS_V2"
    assert props["edp.freeze.source_sql_sha256"] == sha(source_sql)
    assert props["edp.freeze.owner_scope_decision_sha256"] == sha(owner_path)
    assert props["edp.freeze.scoped_acceptance_sha256"] == sha(scoped_path)
    assert props["edp.freeze.physical_sources"] == "1500"
    assert props["edp.freeze.operational_bindings"] == "1932"
    assert props["edp.freeze.economic_l6_b"] == "NOT_IMPLEMENTED"
    assert props["edp.freeze.day4_c3_4"] == "HISTORICAL_BLOCKED_OWNER_EXCEPTION"

    multiset = read(ROOT / prior["evidence_locations"]["combined_multiset_result"])
    for key in ("candidate_sql", "combined_multiset_result", "fin_001_result",
                "fin_002_result", "fin_witnesses_result", "fin_typed_raw_witnesses_result"):
        assert sha(ROOT / prior["evidence_locations"][key]) == prior["evidence_sha256"][key]
    assert len(multiset["result"]["data_array"]) == 8
    assert all(int(row[2]) == 0 for row in multiset["result"]["data_array"])
    assert prior["fin"]["FIN_001"] == "2/2 PASS"
    assert prior["fin"]["FIN_002"] == "1/1 PASS"
    assert prior["fin"]["lineage_witnesses"] == 13

    index = {p.name.removesuffix("-result.json"): receipt(p.name.removesuffix(
        "-result.json")) for p in sorted(RUN.glob("*-result.json"))}
    evidence = {
        "schema": "O_C1500_M2_DATABRICKS_RESULT_FREEZE_V2",
        "status": "PASS",
        "scope": "SOURCE_PRESERVING_ADDITIVE_M2_ONLY",
        "prior_git_only_freeze": "metadata/freezes/O_C1500_M2_v1/freeze.json",
        "owner_decision_sha256": sha(owner_path),
        "scoped_acceptance_sha256": sha(scoped_path),
        "historical_view_live_definition_sha256": hashlib.sha256(historical.encode()).hexdigest(),
        "historical_view_pinned_physical_refs": sorted(historical_refs),
        "result_view": {"full_name": VIEW, "uc_table_id": uc["table_id"],
                        "object_type": "VIEW", "source_sql_ref": str(source_sql.relative_to(ROOT)),
                        "source_sql_sha256": sha(source_sql),
                        "show_create_post_marker_sha256": hashlib.sha256(
                            live_definition.encode()).hexdigest(),
                        "uc_get_response_sha256": sha(uc_path),
                        "direct_pinned_physical_dependencies": sorted(result_refs),
                        "queryable_marker": props},
        "physical_delta_pins": delta,
        "population": {"physical_sources": 1500, "old_bindings": 1182,
                       "new_bindings": 750, "operational_bindings": 1932,
                       "total_occurrences_including_framing_and_derived": 319151239,
                       "source_data_records": 319111460,
                       "occurrence_classes": {name: {"occurrences": value[0],
                                                    "physical_sources": value[1]}
                                              for name, value in CLASSES.items()},
                       "incomplete_lineage_envelopes": 0,
                       "treasury_valid": 12793, "treasury_structural_missing": 155},
        "reused_unchanged_evidence": {"step9_full_schema_multiset_directions": 8,
                                      "step9_full_schema_differences": 0,
                                      "FIN_001": "2/2 PASS", "FIN_002": "1/1 PASS",
                                      "historical_lineage_witnesses": 13,
                                      "candidate_branch_sql_equivalent_after_inline": True},
        "runtime_receipts": index,
        "limitations": {"treasury_economic_L6_B": "NOT_IMPLEMENTED_OUT_OF_SCOPE",
                        "historical_day4_C3_4": "BLOCKED_OWNER_EXCEPTION_NOT_TECHNICAL_PASS",
                        "retention": "VERSION_0_CURRENTLY_READABLE_NO_INDEFINITE_RETENTION_CLAIM",
                        "no_backup_archive_or_full_data_copy": True},
    }
    OUT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": evidence["status"], "view": VIEW,
                      "uc_table_id": uc["table_id"], "receipt_count": len(index),
                      "evaluation_sha256": sha(OUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
