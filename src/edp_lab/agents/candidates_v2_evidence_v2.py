"""Bounded Agent V2 evidence correction; original candidate V1 stays frozen."""
from __future__ import annotations

from edp_lab.agents.candidates_v2 import REPORT_KEYS
from edp_lab.agents.candidates_v2 import propose as propose_v1
from edp_lab.profiling.source_reader import canonical_hash

VERSION = "EDP_CANDIDATE_AGENT_V2_EVIDENCE_V2"


def propose(case: dict, witnesses: dict) -> dict:
    report = propose_v1(case, witnesses)
    left, right = case["left"], case["right"]
    close_yield = (("CLOSE" in left["field"] and "YIELD" in right["field"])
                   or ("YIELD" in left["field"] and "CLOSE" in right["field"]))
    if (case["question"] == "same_measure" and report["candidate_label"] == "NON_MATCH"
            and close_yield and left["value"] != right["value"]):
        report["conflicting_evidence"].append(
            f"Distinct source properties {left['field']}={left['value']!r} and "
            f"{right['field']}={right['value']!r}; no conversion approved")
    report["agent_version"] = VERSION
    report["result_fingerprint"] = canonical_hash(
        {key: value for key, value in report.items() if key != "result_fingerprint"})
    return report


def validate(report: dict) -> bool:
    if (set(report) != REPORT_KEYS or report["agent_version"] != VERSION
            or report["side_effects"] or report["semantic_promotions"]
            or report["promotion_eligible"]
            or canonical_hash({k: v for k, v in report.items() if k != "result_fingerprint"})
            != report["result_fingerprint"]):
        raise ValueError("INVALID_EVIDENCE_V2_CANDIDATE")
    if report["question"] == "canonical_entity" and (
            report["candidate_label"] != "UNRESOLVED" or report["state"] != "UNRESOLVED"):
        raise ValueError("UNAUTHORIZED_CANONICAL_RESOLUTION")
    return True
