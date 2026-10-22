"""Fail-closed checks for owner-scoped Day 4 freeze and truthful exception reporting."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def packet(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def test_original_candidate_pins_unchanged() -> None:
    original = packet("metadata/evaluations/o_c1500_m2_freeze_assessment_v1.json")
    assert original["status"] == "CANDIDATE"
    assert original["result_frozen"] is False
    for path, digest in original["file_pins_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


def test_fifty_dispositions_are_approved_without_data_fabrication() -> None:
    d = packet("metadata/evaluations/treasury_l3_owner_scope_decision_v1.json")
    s = packet("metadata/evaluations/c1500_m2_stability_scoped_v3_owner_acceptance.json")
    assert d["decision_status"] == "APPROVED_SOURCE_PRESERVING_ONLY"
    assert d["approved_disposition"] == "PRESERVED_NOT_MODELED"
    assert len(d["approvals"]) == 50
    assert len({(x["source_instance_id"], x["property_qname"]) for x in d["approvals"]}) == 50
    assert all(x["owner_decision"] == "APPROVED_SOURCE_PRESERVING_ONLY" for x in d["approvals"])
    assert s["scoped_results"] == {
        "B2_1_SOURCE_PRESERVING": "PASS",
        "C1_SOURCE_PRESERVING": "PASS",
    }
    scope = s["source_scope"]
    assert (scope["treasury_m2_evaluations"], scope["treasury_valid"], scope["treasury_missing"]) == (12948, 12793, 155)
    assert s["preserved_limits"]["B2_1_FULL_ECONOMIC"] == "NOT_IMPLEMENTED"


def test_permanent_budget_matches_exact_measured_phase_envelope() -> None:
    old = packet("metadata/evaluations/operational_budget_v1.json")
    approved = packet("metadata/authorizations/day4_c3_4_budget_approval_v1.json")
    assert old["status"] == "PROPOSED_PENDING_APPLICABILITY_APPROVAL"
    assert approved["status"] == "APPROVED"
    assert approved["multiplier"] == 10
    assert "UNTIL_EXPLICITLY_SUPERSEDED" in approved["validity"]
    assert approved["retrospective_test_outcome"].startswith("NOT_TESTED")
    for phase, values in old["phases"].items():
        assert abs(approved["phase_limits_seconds"][phase] - 10 * values["observed_seconds"]) < 1e-6
    assert abs(approved["phase_limits_seconds"]["sql_phase_total_nonoverlap"] - 10 * old["sql_phase_total"]["observed_seconds"]) < 1e-6
    assert approved["applicability_day5_n500"] == "CONDITIONAL_ON_DOCUMENTED_COMPARABILITY; NOT_AUTOMATIC"


def test_freeze_is_explicit_and_non_semantic_and_does_not_fake_runtime() -> None:
    a = packet("metadata/freezes/O_C1500_M2_v1/authorization.json")
    f = packet("metadata/freezes/O_C1500_M2_v1/freeze.json")
    r = packet("metadata/freezes/O_C1500_M2_v1/references.json")
    v2 = packet("metadata/evaluations/o_c1500_m2_freeze_assessment_v2.json")
    assert "HUMAN_OVERRIDE" in a["decision"]
    assert f["result_frozen"] is True
    assert f["status"] == "FROZEN_BY_EXPLICIT_HUMAN_OVERRIDE"
    assert f["freeze_type"] == "GIT_EVIDENCE_AND_APPROVAL_MARKER_ONLY"
    assert f["runtime"]["new_live_readback"] == "NOT_RUN"
    assert f["runtime"]["delta_table_property_protection"] == "NOT_RUN"
    assert f["runtime"]["durable_archive"] == "NOT_CREATED"
    assert f["non_implemented"]["Treasury_L6_B"] == "NOT_IMPLEMENTED"
    assert r["source_roster_sha256"] == packet("metadata/evaluations/o_c1500_m2_freeze_assessment_v1.json")["population"]["bindings_sha256"]
    assert r["combined_candidate_sql_sha256"] == packet("metadata/evaluations/o_c1500_m2_freeze_assessment_v1.json")["validated_candidate_sql_sha256"]
    assert v2["technical_acceptance"]["C3_4"] == "NOT_RETROACTIVELY_PROVEN_OWNER_OVERRIDE"
    assert "TREASURY_L6_B_NOT_IMPLEMENTED" in v2["exceptions"]


def test_exit_v2_cannot_rewrite_historical_partial() -> None:
    historic = packet("metadata/evaluations/day4_exit_v1.json")
    closeout = packet("metadata/evaluations/day4_exit_v2.json")
    assert historic["status"] == "PARTIAL"
    assert historic["result_frozen"] is False
    assert closeout["status"] == "COMPLETE_BY_HUMAN_OVERRIDE_WITH_EXCEPTIONS"
    assert closeout["result_frozen"] is True
    assert closeout["treasury_economic_integration"] == "NOT_IMPLEMENTED"
    assert closeout["c3_4_historical_technical_result"].startswith("BLOCKED_IN_ORIGINAL_V1")
    assert closeout["integration"]["merger_proof"].startswith("GITHUB_MERGE_EVENT_REQUIRED")
