"""Executable minimum C2/C3 contract checks and source-aware mutation witnesses.

These tests protect the evaluator; they do NOT certify a live C750 Databricks result.
"""

import json
from pathlib import Path

from edp_lab.evaluation.stability_m1_v1 import (
    SourceOccurrence,
    check_disjoint_source_ids,
    multiset_differences,
    old_projection_differences,
)

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "metadata/evaluations/stability_m1_v1.json"


def occ(source: str, locator: str, value: str) -> SourceOccurrence:
    return SourceOccurrence(source, source + "-binding", source + "-run", locator, value)


def test_permanent_c2_c3_coverage_and_fin_compatibility():
    suite = json.loads(CONTRACT.read_text())
    fin = json.loads((ROOT / "metadata/evaluations/lossless6_fin_suite_v2.json").read_text())
    authority = (ROOT / "docs/evaluation_contract.md").read_text()

    assert suite["schema"] == "STABILITY_M1_V1"
    assert suite["persistent"] is True
    assert suite["model"] == fin["model"] == "M1_LEXICAL_V1"
    assert suite["fin_suite"] == "metadata/evaluations/lossless6_fin_suite_v2.json"
    assert [x["id"] for x in suite["tests"]] == [
        "C2.1", "C2.2", "C2.3", "C2.4",
        "C3.1", "C3.2", "C3.3", "C3.4",
    ]
    assert all(t["required"] for t in suite["tests"])
    assert "### 5.1 Permanent M1 source-preserving C2/C3 minimum" in authority
    assert "FIN_001" in suite["tests"][3]["requires"][0]
    assert "configured job timeout" in suite["operational_threshold_policy"]
    assert "not" in suite["enterprise_scope"].lower() or "No" in suite["enterprise_scope"]
    assert "No changes to frozen Day2" in suite["historical_integrity"]


def test_c2_live_shaped_fixture_passes_exact_multiset_and_old_projection():
    old = [occ("SRC_OLD", "0", "XYZ"), occ("SRC_OLD", "1", "XYZ")]
    new = [occ("SRC_NEW", "0", "XYZ"), occ("SRC_NEW", "1", "NEW")]
    combined = [old[1], new[0], old[0], new[1]]
    assert multiset_differences(old, new, combined) == ({}, {})
    assert old_projection_differences(old, combined) == ({}, {})
    assert check_disjoint_source_ids({"SRC_OLD"}, {"SRC_NEW"}) == set()


def test_c2_detects_false_merge_on_equal_looking_values_from_two_sources():
    old = [occ("SRC_OLD", "7", "ABC")]
    new = [occ("SRC_NEW", "8", "ABC")]
    incorrect = [old[0]]  # Incorrect DISTINCT/join collapsed independent new occurrence.
    missing, extra = multiset_differences(old, new, incorrect)
    assert missing == {new[0]: 1}
    assert extra == {}


def test_c2_detects_intra_source_duplicate_collapse_and_join_fanout():
    old = [occ("SRC_OLD", "7", "ABC"), occ("SRC_OLD", "8", "ABC")]
    new = [occ("SRC_NEW", "9", "ABC")]
    collapsed = [old[0], new[0]]
    missing, extra = multiset_differences(old, new, collapsed)
    assert missing == {old[1]: 1}
    assert extra == {}

    fanned_out = old + new + [new[0]]
    missing, extra = multiset_differences(old, new, fanned_out)
    assert missing == {}
    assert extra == {new[0]: 1}


def test_c2_detects_changed_historical_locator_and_identity_collision():
    old = [occ("SRC_OLD", "7", "VALUE")]
    changed = [occ("SRC_OLD", "9", "VALUE")]
    missing, extra = old_projection_differences(old, changed)
    assert missing == {old[0]: 1}
    assert extra == {changed[0]: 1}
    assert check_disjoint_source_ids({"SRC_OLD"}, {"SRC_OLD"}) == {"SRC_OLD"}


def test_c3_requires_recorded_owner_budget_before_operational_pass():
    suite = json.loads(CONTRACT.read_text())
    c3 = suite["tests"][-1]
    assert c3["id"] == "C3.4"
    assert c3["required"]
    assert any("owner-accepted" in x for x in c3["requires"])
    assert "do not choose retroactive" in suite["operational_threshold_policy"]

from edp_lab.evaluation.stability_m1_v1 import operational_acceptance_failures


def operational_sample(**updates):
    """Synthetic receipts: not a statement that a Databricks run has passed."""
    values = {
        "expected_bindings": 2,
        "completed_binding_ids": ["N1", "N2"],
        "reprocessed_completed_bindings": 0,
        "historical_replays": 0,
        "publication_exact_readback": True,
        "stage_wall_seconds": {
            "processing": 5.0,
            "clean_publication": 2.0,
            "queryable_validation": 10.0,
        },
        "approved_stage_budgets_seconds": {
            "processing": 10.0,
            "clean_publication": 10.0,
            "queryable_validation": 20.0,
        },
    }
    values.update(updates)
    return operational_acceptance_failures(**values)


def test_c3_accepts_complete_idempotent_in_budget_synthetic_receipts():
    assert operational_sample() == []


def test_c3_rejects_missing_or_duplicated_binding_and_unwanted_replay():
    failures = operational_sample(
        completed_binding_ids=["N1", "N1"],
        historical_replays=1,
        reprocessed_completed_bindings=1,
        publication_exact_readback=False,
    )
    assert any("C3.1" in f for f in failures)
    assert any("C3.2" in f for f in failures)
    assert any("C3.3" in f for f in failures)


def test_c3_does_not_invent_budgets_and_rejects_out_of_budget():
    assert any("no prior configured" in x for x in operational_sample(
        approved_stage_budgets_seconds=None
    ))
    assert any("queryable_validation" in x for x in operational_sample(
        approved_stage_budgets_seconds={
            "processing": 10.0,
            "clean_publication": 10.0,
            "queryable_validation": 2.0,
        }
    ))
