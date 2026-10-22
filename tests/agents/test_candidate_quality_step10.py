"""Step 10 exact benchmark, evidence correction, and authority negatives."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from edp_lab.agents.candidates_v2 import propose as propose_original
from edp_lab.agents.candidates_v2_evidence_v2 import propose, validate
from edp_lab.profiling.source_reader import canonical_hash

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "metadata/evaluations/agent_v2"
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "evaluate_agent_v2_quality_step10", ROOT / "scripts/evaluate_agent_v2_quality_step10.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def artifacts():
    inputs = json.loads((BASE / "inputs_v1.json").read_text())
    truth = json.loads((BASE / "ground_truth_v1.json").read_text())
    return inputs, truth


def test_same_frozen_23_cases_and_only_s09_evidence_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(MODULE, "OUTPUT", tmp_path / "quality.json")
    MODULE.main()
    result = json.loads(MODULE.OUTPUT.read_text())
    assert result["status"] == "AGENT_QUALITY_MEASURED"
    assert result["population"] == {"STTM": 11, "CROSSWALK": 4, "ER": 8,
                                     "total": 23, "MATCH": 7, "NON_MATCH": 10, "UNRESOLVED": 6}
    assert result["matrices"]["overall"]["correct"] == 23
    assert result["name_only_heuristic"]["correct"] == 8
    assert result["original_evidence_gaps"] == [
        {"case_id": "S09", "type": "explicit_conflict_evidence_missing"}]
    assert result["focused_correction"]["changed_case_ids"] == ["S09"]
    assert result["focused_correction"]["after_matrix"] == result["matrices"]["overall"]
    assert result["review"]["proposal_count"] == 8
    assert result["review"]["responses_observed"] == 0
    assert result["numeric_confidence"] == "NUMERIC_CONFIDENCE_NOT_EMITTED"


def test_evidence_correction_does_not_change_labels_or_promote():
    inputs, truth = artifacts()
    expected = {x["id"]: x["expected_label"] for x in truth["cases"]}
    for case in inputs["cases"]:
        before = propose_original(case, inputs["witnesses"])
        after = propose(case, inputs["witnesses"])
        assert after["candidate_label"] == before["candidate_label"] == expected[case["id"]]
        assert after["state"] == before["state"]
        assert not after["semantic_promotions"] and not after["promotion_eligible"]
        assert validate(after)
        if case["id"] == "S09":
            assert not before["conflicting_evidence"]
            assert "4.26" in after["conflicting_evidence"][0]
            assert "4.33" in after["conflicting_evidence"][0]
        else:
            assert after["conflicting_evidence"] == before["conflicting_evidence"]


def test_label_leakage_forged_approval_and_canonical_promotion_rejected():
    inputs, _ = artifacts()
    case = next(x for x in inputs["cases"] if x["id"] == "E05")
    leaked = copy.deepcopy(case)
    leaked["expected_label"] = "MATCH"
    with pytest.raises(ValueError, match="INVALID_CASE_OR_LABEL_LEAK"):
        propose(leaked, inputs["witnesses"])
    report = propose(case, inputs["witnesses"])
    report["candidate_label"] = "MATCH"
    report["state"] = "VALIDATED"
    report["promotion_eligible"] = True
    report["result_fingerprint"] = canonical_hash(
        {k: v for k, v in report.items() if k != "result_fingerprint"})
    with pytest.raises(ValueError):
        validate(report)
