"""Compile checked Step 9 receipts into versioned, tracked evaluation evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/c1500-m2-stability/v1"
BASELINE = ROOT / "metadata/baselines/O_C750_M2_v1.json"
OUTPUT = ROOT / "metadata/evaluations/c1500_m2_stability_v1.json"


def read(path: Path) -> dict:
    return json.loads(path.read_bytes())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sql_rows(label: str) -> list[list[str]]:
    result = read(RUN / f"{label}-result.json")
    assert result["status"]["state"] == "SUCCEEDED", label
    return result["result"]["data_array"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("historical_archive", type=Path)
    parser.add_argument("historical_verification", type=Path)
    args = parser.parse_args()
    baseline = read(BASELINE)
    old_m1 = read(ROOT / "metadata/freezes/O_C750_M1_v1/references.json")
    assert sha(ROOT / baseline["input_freeze"]) == baseline["input_freeze_sha256"]
    assert sha(args.historical_archive) == baseline["evidence"]["sha256"]
    assert sha(args.historical_verification) == baseline["evidence"]["verification_sha256"]
    historical = read(args.historical_verification)
    local = read(RUN / "local-oracle.json")
    feed = read(RUN / "treasury-feed-metadata.json")
    step8 = read(ROOT / "runs/n750/step8-v1/validation.json")
    assert local["status"] == feed["status"] == "PASS"
    assert step8["status"] == "STEP8_COMPLETE_WITH_ECONOMIC_BOUNDARY"
    assert local["population"]["combined_sources"] == 1500
    assert local["population"]["combined_execution_bindings"] == 1932
    assert local["oracle"]["outcomes"] == {"VALID": 12793, "MISSING": 155}
    assert local["oracle"]["mismatches"] == 0
    counts = {row[0]: {"occurrences": int(row[1]), "sources": int(row[2]),
                       "incomplete_envelopes": int(row[3])}
              for row in sql_rows("combined-counts")}
    expected_counts = {
        "OLD_C750_RECORD": (316063821, 750),
        "NEW_N750_SEC_RECORD": (3052854, 745),
        "NEW_N750_XML_PROPERTY": (21616, 5),
        "NEW_N750_M2_EVALUATION": (12948, 5),
    }
    assert {k: (v["occurrences"], v["sources"]) for k, v in counts.items()} == expected_counts
    assert all(v["incomplete_envelopes"] == 0 for v in counts.values())
    comparisons = {(r[0], r[1]): int(r[2]) for r in sql_rows(
        "combined-full-schema-multiset-null-v2")}
    assert len(comparisons) == 8 and set(comparisons) == {
        (scope, direction) for scope in expected_counts
        for direction in ("candidate_minus_pinned", "pinned_minus_candidate")}
    assert set(comparisons.values()) == {0}
    fixture = list(csv.DictReader((ROOT / "sql/reconciliation/fin_eval_v1/observed_expected_results.csv").open()))
    fin1 = sql_rows("fin-001-combined")
    fin2 = sql_rows("fin-002-combined")
    assert len(fin1) == 2 and len(fin2) == 1
    for actual, expected in zip(fin1, fixture[:2], strict=True):
        assert actual == [expected[c] for c in (
            "ddate", "assets", "liabilities", "equity_used", "reported_total")
                          ] + ["0.0000", "0.0000", "PASS"]
    assert fin2[0] == ["0.0000", fixture[2]["wrong_equity_difference"],
                       fixture[2]["implied_nci"], "PASS"]
    witnesses = sql_rows("fin-witnesses")
    frozen = sorted(historical["fin"]["lineage_witnesses"], key=lambda r: r["source_line"])
    cols = ("source_line", "byte_offset", "byte_length", "run_id", "model_version",
            "rule_version", "lexical_value", "value_decimal", "m2_model_version",
            "conversion_rule_version")
    assert len(witnesses) == len(frozen) == 13
    assert all(a == [str(o[c]) for c in cols]
               for a, o in zip(witnesses, frozen, strict=True))
    raw_witnesses = sql_rows("fin-typed-raw-witnesses")
    raw_cols = ("source_line", "source_instance_id", "run_id", "binding_sha256",
                "raw_sha256", "archive_member", "member_sha256", "byte_offset",
                "byte_length", "model_version", "rule_version", "lexical_value",
                "value_decimal", "m2_model_version", "conversion_rule_version")
    assert len(raw_witnesses) == 13
    assert all(a == [str(o[c]) for c in raw_cols]
               for a, o in zip(raw_witnesses, frozen, strict=True))
    detail = sql_rows("historical-typed-detail")[0]
    assert detail[1] == baseline["output"]["delta_id"]
    assert json.loads(detail[11])["io.unitycatalog.tableId"] == baseline["output"]["uc_table_id"]
    assert int(sql_rows("historical-typed-history")[0][0]) == 0
    for label, name in (("historical-view-definition", "C750_records_view"),
                        ("historical-c300-view-definition", "C300_logical_subset_view")):
        definition = sql_rows(label)[0][0]
        assert hashlib.sha256(definition.encode()).hexdigest() == baseline["output"][
            "definition_sha256"][baseline["output"][name]]
    assert len(feed["sources"]) == 5
    step8_sql_results = list((ROOT / "runs/n750/step8-v1/publication").glob("*-result.json"))
    assert len(step8_sql_results) == 80
    assert all(read(path).get("status", {}).get("state") == "SUCCEEDED"
               for path in step8_sql_results)
    statuses = {
        "A1": "PASS", "A2": "PASS", "A3": "PASS", "A4": "PASS",
        "B2.1": "BLOCKED", "B2.2": "PASS", "B2.3": "PASS", "B2.4": "PASS",
        "C1": "BLOCKED", "C2.1": "PASS", "C2.2": "PASS", "C2.3": "PASS",
        "C2.4": "PASS", "C3.1": "PASS", "C3.2": "PASS", "C3.3": "PASS",
        "C3.4": "BLOCKED",
    }
    evidence_files = {
        "historical_archive": args.historical_archive,
        "historical_verification": args.historical_verification,
        "historical_m1_references": ROOT / "metadata/freezes/O_C750_M1_v1/references.json",
        "historical_m2_baseline": BASELINE,
        "local_oracle": RUN / "local-oracle.json",
        "treasury_feed_metadata": RUN / "treasury-feed-metadata.json",
        "combined_counts_request": RUN / "combined-counts-request.json",
        "combined_counts_result": RUN / "combined-counts-result.json",
        "combined_multiset_request": RUN / "combined-full-schema-multiset-null-v2-request.json",
        "combined_multiset_result": RUN / "combined-full-schema-multiset-null-v2-result.json",
        "fin_001_result": RUN / "fin-001-combined-result.json",
        "fin_002_result": RUN / "fin-002-combined-result.json",
        "fin_witnesses_result": RUN / "fin-witnesses-result.json",
        "fin_typed_raw_witnesses_result": RUN / "fin-typed-raw-witnesses-result.json",
        "historical_typed_detail_result": RUN / "historical-typed-detail-result.json",
        "historical_typed_history_result": RUN / "historical-typed-history-result.json",
        "historical_c750_view_result": RUN / "historical-view-definition-result.json",
        "historical_c300_view_result": RUN / "historical-c300-view-definition-result.json",
        "n750_raw_completion": ROOT / "runs/n750/step8-v1/raw/completion.json",
        "n750_clean_completion": ROOT / "runs/n750/step8-v1/clean/completion.json",
        "n750_delta_readback": ROOT / "runs/n750/step8-v1/publication/delta-readback.json",
        "n750_queryable": ROOT / "runs/n750/step8-v1/publication/queryable.json",
        "n750_live_verify": ROOT / "runs/n750/step8-v1/live-verify-v1.json",
        "candidate_sql": ROOT / "sql/stability/c1500_m2_v1/combined_candidate.sql",
        "fin_projection_sql": ROOT / "sql/stability/c1500_m2_v1/fin_candidate_prefix.sql",
    }
    result = {
        "schema": "C1500_M2_STABILITY_EVALUATION_V1",
        "status": "STABILITY_EVALUATED",
        "full_acceptance": "BLOCKED",
        "validated_scope": "C1500 source-preserving M1 lexical and approved additive M2 typed projections at exact pinned outputs",
        "model_versions": {"lexical": "M1_LEXICAL_V1",
                           "typed": "M2_ADDITIVE_TYPED_NUMERIC_V1",
                           "decimal_rule": "EXACT_DECIMAL_38_4_V1",
                           "historical_source_rule": "FSDS_NUM_VALUE_SCOPE_V1",
                           "treasury_source_rule": "TREASURY_RATE_QNAME_SCOPE_V1"},
        "start_merge_sha": "2177f32a0434d2b75fa69a9eafbb2b601676fac7",
        "authority": ["docs/evaluation_contract.md", "metadata/evaluations/stability_m1_v1.json",
                      "metadata/evaluations/lossless6_fin_suite_v2.json"],
        "population": local["population"],
        "output_pins": {"historical_m2_table": baseline["output"]["table"],
                        "historical_m2_delta_id": baseline["output"]["delta_id"],
                        "historical_m2_uc_id": baseline["output"]["uc_table_id"],
                        "historical_m2_version": 0,
                        "historical_m1_input_versions": baseline["input_snapshots"],
                        "historical_m1_delta_ids": {
                            row["table"]: row["delta_id"] for row in old_m1["clean_snapshots"]},
                        "n750_tables": step8["output_tables"]},
        "combined_candidate": {"statement_id": read(RUN / "combined-counts-result.json")["statement_id"],
                               "counts": counts, "multiset_statement_id": read(
                                   RUN / "combined-full-schema-multiset-null-v2-result.json")["statement_id"],
                               "bidirectional_full_schema_differences": [
                                   {"scope": scope, "direction": direction, "differences": n}
                                   for (scope, direction), n in sorted(comparisons.items())]},
        "decimal": local["oracle"],
        "fin": {"FIN_001": "2/2 PASS", "FIN_002": "1/1 PASS",
                "wrong_equity_difference": "1232700000.0000",
                "lineage_witnesses": 13, "exact_fixture_differences": 0},
        "lossless": {"old_1_to_5": "PASS", "old_mandatory_fin_6": "PASS",
                     "new_1_to_5": "PASS", "new_treasury_economic_6": "NOT_IMPLEMENTED",
                     "combined_1_to_5": "PASS", "combined_mandatory_fin_6": "PASS",
                     "combined_treasury_economic_6": "NOT_IMPLEMENTED"},
        "statuses": statuses,
        "treasury_economic_reconciliation": "NOT_IMPLEMENTED",
        "operational": {"remote_seconds": 675.667, "clean_seconds": 45.890,
                        "remote_sources_per_second": 750 / 675.667,
                        "remote_verified_bytes_per_second": 269323425 / 675.667,
                        "clean_sources_per_second": 750 / 45.890,
                        "clean_sec_data_records_per_second": 3047639 / 45.890,
                        "clean_source_fields_per_second": (15238195 + 21616) / 45.890,
                        "step8_clean_run_id": "n750_step8_v1",
                        "historical_m2_build_run_id": baseline["runtime"]["build_run"],
                        "historical_m2_verify_run_id": baseline["runtime"]["verify_run"],
                        "historical_m2_failed_preflight_run_id": baseline["runtime"]["failed_preflight_run"],
                        "warehouse_id": "589e80595c7c8cb8",
                        "publication_intervals_seconds": {"create": 55.145, "delta_validate": 91.842,
                                                          "views": 27.862, "coverage_lineage": 43.465},
                        "remote_reused": 450, "remote_uploaded": 300, "remote_verified": 750,
                        "step8_sql_succeeded_receipts": len(step8_sql_results),
                        "step8_indexed_failed_sql_results": 0,
                        "step8_observed_failed_job_recovery": "NOT_APPLICABLE",
                        "provider_internal_retry_attempts": "UNAVAILABLE",
                        "prior_approved_runtime_budget": "UNAVAILABLE",
                        "cpu_memory_dbu_cost": "UNAVAILABLE",
                        "owner_processing_grant_artifacts": 1,
                        "human_review_event_count_duration": "UNAVAILABLE"},
        "difference_classification": {"UNCHANGED": "historical M1 and source/run/locator fields",
                                      "EXPECTED_ADDITIVE": "approved typed Decimal and outcome/version columns",
                                      "UNEXPLAINED_REGRESSION": 0,
                                      "UNRESOLVED": "Treasury economic semantics, source NULL meaning and wider financial relationships"},
        "unresolved": ["Treasury observation grain", "Treasury explicit units and time basis",
                       "rate/yield meaning and exact reconciliation equation",
                       "enterprise entity identity and cross-source equivalence",
                       "prospective operational performance budget"],
        "evidence_sha256": {key: sha(path) for key, path in evidence_files.items()},
        "evidence_locations": {
            key: (baseline["evidence"]["uri"] if key == "historical_archive"
                  else baseline["evidence"]["verification_member"] if key == "historical_verification"
                  else str(path.relative_to(ROOT)) if path.is_relative_to(ROOT)
                  else str(path))
            for key, path in evidence_files.items()},
        "no_new_tables_or_historical_replay": True,
        "stop_before_step_10": True,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "full_acceptance": result["full_acceptance"],
                      "output": str(OUTPUT), "sha256": sha(OUTPUT)}))


if __name__ == "__main__":
    main()
