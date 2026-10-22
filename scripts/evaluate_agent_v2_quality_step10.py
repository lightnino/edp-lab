"""Reproduce and measure the unchanged 23-case Agent V2 benchmark."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path

import evaluate_agent_v2

from edp_lab.agents.candidates_v2 import score
from edp_lab.agents.candidates_v2_evidence_v2 import VERSION, propose, validate
from edp_lab.profiling.source_reader import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "metadata/evaluations/agent_v2"
OUTPUT = BASE / "quality_regression_step10_v1.json"
LABELS = ("MATCH", "NON_MATCH", "UNRESOLVED")
DIMENSIONS = ("STTM", "CROSSWALK", "ER")


def read(path: Path) -> dict:
    return json.loads(path.read_bytes())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matrix(cases: list[dict], label_key: str) -> dict:
    cells = {actual: {predicted: 0 for predicted in LABELS} for actual in LABELS}
    errors = {"false_match_ids": [], "false_non_match_ids": [],
              "premature_resolution_ids": [], "incorrectly_unresolved_ids": []}
    for case in cases:
        actual, predicted = case["ground_truth_label"], case[label_key]
        cells[actual][predicted] += 1
        if actual == "NON_MATCH" and predicted == "MATCH":
            errors["false_match_ids"].append(case["case_id"])
        if actual == "MATCH" and predicted == "NON_MATCH":
            errors["false_non_match_ids"].append(case["case_id"])
        if actual == "UNRESOLVED" and predicted != "UNRESOLVED":
            errors["premature_resolution_ids"].append(case["case_id"])
        if actual != "UNRESOLVED" and predicted == "UNRESOLVED":
            errors["incorrectly_unresolved_ids"].append(case["case_id"])
    return {"labels": list(LABELS), "rows_actual_columns_predicted": cells,
            "correct": sum(cells[k][k] for k in LABELS), "total": len(cases),
            "accuracy": sum(cells[k][k] for k in LABELS) / len(cases), **errors}


def main() -> None:
    with contextlib.redirect_stdout(io.StringIO()) as capture:
        evaluate_agent_v2.main()
    reproduction = json.loads(capture.getvalue())
    assert reproduction["status"] == "REPRODUCED" and reproduction["cases"] == 23
    inputs, truth, frozen, prior, review = (read(BASE / f"{name}.json") for name in (
        "inputs_v1", "ground_truth_v1", "proposals_v1", "evaluation_v1", "human_review_v1"))
    assert sha(BASE / "ground_truth_v1.json") == "9ba83190b260b1bb5ac7feb0043fa7591b9da846f49a40be0d7fe6c4428477fd"
    assert sha(BASE / "inputs_v1.json") == truth["inputs_sha256"]
    assert sha(BASE / "proposals_v1.json") == prior["proposals_sha256"]
    assert frozen["agent_code_sha256"] == sha(ROOT / "src/edp_lab/agents/candidates_v2.py")
    source = {case["id"]: case for case in inputs["cases"]}
    labels = {case["id"]: case for case in truth["cases"]}
    old = {case["case_id"]: case for case in frozen["proposals"]}
    assert len(source) == len(labels) == len(old) == 23
    assert set(source) == set(labels) == set(old)
    assert score(frozen["proposals"], truth["cases"]) == prior["metrics"]
    corrected = {case["id"]: propose(case, inputs["witnesses"]) for case in inputs["cases"]}
    assert all(validate(report) for report in corrected.values())
    case_rows = []
    evidence_gaps = []
    unsupported = []
    changed = []
    for case_id, case in source.items():
        proposal, after, expected = old[case_id], corrected[case_id], labels[case_id]
        assert proposal["candidate_label"] == after["candidate_label"]
        assert proposal["state"] == after["state"]
        before_comparable = {k: v for k, v in proposal.items() if k not in (
            "agent_version", "result_fingerprint")}
        after_comparable = {k: v for k, v in after.items() if k not in (
            "agent_version", "result_fingerprint")}
        if before_comparable != after_comparable:
            changed.append(case_id)
        evidence = proposal["supporting_evidence"]
        if len(evidence) != 2 or any(not e["source"].get("raw_sha256") or not e["locator"]
                                      for e in evidence):
            evidence_gaps.append({"case_id": case_id, "type": "source_or_locator_missing"})
        if not proposal["required_transformation"] or set(proposal["compatibility"]) != {
            "unit", "grain", "time"}:
            evidence_gaps.append({"case_id": case_id, "type": "transform_or_compatibility_missing"})
        if (proposal["candidate_label"] == "NON_MATCH" and "unequal observed values" in proposal["reason"]
                and not proposal["conflicting_evidence"]):
            evidence_gaps.append({"case_id": case_id, "type": "explicit_conflict_evidence_missing"})
        if (proposal["human_review_required"] and (not proposal["review_question"]
                or len(proposal["alternatives"]) < 2)):
            evidence_gaps.append({"case_id": case_id, "type": "review_question_or_alternatives_missing"})
        if (proposal["promotion_eligible"] or proposal["semantic_promotions"] or proposal["side_effects"]
                or (case["question"] == "canonical_entity" and proposal["candidate_label"] != "UNRESOLVED")
                or (proposal["state"] == "VALIDATED" and case["question"] not in (
                    "typed_projection", "same_native_identifier"))):
            unsupported.append(case_id)
        case_rows.append({"case_id": case_id, "dimension": case["dimension"],
            "question": case["question"], "ground_truth_label": expected["expected_label"],
            "ground_truth_reason": expected["reason"], "ground_truth_evidence_refs": expected["evidence_refs"],
            "candidate_label": proposal["candidate_label"], "name_only_baseline_label": proposal[
                "name_only_baseline_label"], "proposal_state": proposal["state"],
            "reason": proposal["reason"], "source_witnesses_and_locators": evidence,
            "supporting_evidence": evidence, "conflicting_evidence": proposal["conflicting_evidence"],
            "compatibility": proposal["compatibility"], "required_transformation": proposal[
                "required_transformation"], "human_review_required": proposal["human_review_required"],
            "review_question": proposal["review_question"], "alternatives": proposal["alternatives"],
            "promotion_eligible": proposal["promotion_eligible"],
            "input_fingerprint": proposal["input_fingerprint"],
            "proposal_fingerprint": proposal["result_fingerprint"],
            "corrected_proposal_fingerprint": after["result_fingerprint"],
            "label_correct": proposal["candidate_label"] == expected["expected_label"]})
    assert changed == ["S09"]
    assert evidence_gaps == [{"case_id": "S09", "type": "explicit_conflict_evidence_missing"}]
    assert not unsupported
    assert corrected["S09"]["conflicting_evidence"] and not old["S09"]["conflicting_evidence"]
    assert all(case["label_correct"] for case in case_rows)
    assert [c["case_id"] for c in case_rows if c["ground_truth_label"] == "UNRESOLVED"] == [
        "S08", "S11", "E05", "E06", "E11", "E12"]
    assert review["requests_sent"] == 3 and review["actual_responses_observed"] == 0
    assert not review["semantic_approvals"]
    review_ids = [case["case_id"] for case in case_rows if case["human_review_required"]]
    assert review_ids == ["S05", "S06", "S08", "S11", "E05", "E06", "E11", "E12"]
    matrices = {"overall": matrix(case_rows, "candidate_label")}
    matrices.update({dimension: matrix([case for case in case_rows if case["dimension"] == dimension],
                                "candidate_label") for dimension in DIMENSIONS})
    corrected_rows = [{**case, "candidate_label": corrected[case["case_id"]]["candidate_label"]}
                      for case in case_rows]
    result = {"schema": "AGENT_V2_QUALITY_REGRESSION_STEP10_V1", "status": "AGENT_QUALITY_MEASURED",
        "benchmark_scope": "Curated engineering benchmark fixed before implementation; no blinded human adjudication or production accuracy estimate",
        "ground_truth_commit": frozen["ground_truth_commit"],
        "ground_truth_sha256": sha(BASE / "ground_truth_v1.json"),
        "inputs_sha256": sha(BASE / "inputs_v1.json"),
        "frozen_proposals_sha256": sha(BASE / "proposals_v1.json"),
        "frozen_candidate_code_sha256": frozen["agent_code_sha256"],
        "frozen_result_fingerprint": frozen["result_fingerprint"],
        "reproduction": reproduction, "population": {"STTM": 11, "CROSSWALK": 4, "ER": 8,
            "total": 23, "MATCH": 7, "NON_MATCH": 10, "UNRESOLVED": 6},
        "matrices": matrices, "name_only_heuristic": matrix(case_rows, "name_only_baseline_label"),
        "ambiguity_recognition": {"expected_ids": ["S08", "S11", "E05", "E06", "E11", "E12"],
            "correctly_unresolved": 6, "premature_resolutions": 0, "excessive_abstentions": 0},
        "numeric_confidence": "NUMERIC_CONFIDENCE_NOT_EMITTED",
        "unsupported_authority_assertion_ids": unsupported,
        "original_evidence_gaps": evidence_gaps,
        "review": {"proposal_count": len(review_ids), "proposal_ids": review_ids,
            "missing_question_or_alternatives": 0, "consequential_requests_sent": 3,
            "request_ids": [r["case_id"] for r in review["requests"]],
            "responses_observed": 0, "semantic_approvals": 0,
            "active_review_seconds": "UNMEASURED", "decision_log_status": "UNRESOLVED"},
        "earlier_agent_comparison": "NEW_CAPABILITY / NO_COMPARABLE_BASELINE",
        "earlier_agent_reason": "Agent V1 emitted bounded key/FD observations and contextual attachments, not the same 23 STTM/Crosswalk/ER decisions",
        "observed_failure": {"case_ids": ["S09"], "type": "structured_conflict_evidence_missing",
            "impact": "Correct NON_MATCH label lacked explicit CLOSE/YIELD value conflict in the structured evidence list"},
        "focused_correction": {"version": VERSION,
            "code_sha256": sha(ROOT / "src/edp_lab/agents/candidates_v2_evidence_v2.py"),
            "changed_case_ids": changed,
            "before_matrix": matrices["overall"],
            "after_matrix": matrix(corrected_rows, "candidate_label"),
            "after_evidence_gap_ids": [],
            "after_result_fingerprint": canonical_hash([corrected[c["id"]] for c in inputs["cases"]]),
            "new_conflict_evidence": corrected["S09"]["conflicting_evidence"]},
        "remaining_risks": ["Canonical security/manager and temporal identity remain unresolved",
            "No out-of-sample or independently human-adjudicated canonical positive cases"],
        "case_details": case_rows, "no_production_side_effects": True,
        "semantic_approval": "NONE"}
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "cases": 23, "correct": 23,
                      "observed_evidence_gap": "S09", "corrected_cases": changed,
                      "output_sha256": sha(OUTPUT)}))


if __name__ == "__main__":
    main()
