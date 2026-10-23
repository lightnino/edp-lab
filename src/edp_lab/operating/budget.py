"""Project C3.4 timing comparison. Never grants an execution budget.

Consumes the separately versioned EDP Lab pilot reference; the first-valid-frozen-
cohort rule remains the generic policy in docs/workflows.
"""

import json
import math
import re
from pathlib import Path

from edp_lab.operating.authority import Denied, digest, verified_document


def load_policy(path: Path) -> dict:
    value = json.loads(path.read_text())
    if (value.get("schema") != "EDP_LAB_AUTONOMOUS_PILOT_C3_4_BUDGET_V1"
            or value.get("version") != 1):
        raise Denied("INVALID_C3_4_POLICY")
    phases = value.get("phase_limits", [])
    ids = [phase.get("id") for phase in phases]
    if not ids or len(ids) != len(set(ids)):
        raise Denied("INVALID_C3_4_PHASES")
    for phase in phases:
        base = phase.get("baseline_observed_seconds")
        if not isinstance(base, (float, int)) or isinstance(base, bool) or not math.isfinite(base) or base <= 0:
            raise Denied("INVALID_C3_4_BASELINE")
        if (not math.isclose(phase["warning_above_seconds"], base * 5, abs_tol=0.001)
                or not math.isclose(phase["block_above_seconds"], base * 10, abs_tol=0.001)):
            raise Denied("C3_4_THRESHOLDS_CHANGED")
    thresholds = value["thresholds"]
    if (thresholds.get("pass_at_or_below_multiplier") != 5
            or thresholds.get("nonblocking_warning_above_multiplier", 5) != 5
            or thresholds.get("pass_with_warning_at_or_below_multiplier") != 10
            or thresholds.get("block_above_multiplier") != 10):
        raise Denied("INVALID_C3_4_POLICY")
    return value


def compare_phase(policy: dict, phase_id: str, observed_seconds: float) -> dict:
    """Inclusive 5x/10x limits: equal to 5 = PASS; equal to 10 = PASS_WARNING."""
    if (not isinstance(observed_seconds, (int, float)) or isinstance(observed_seconds, bool)
            or not math.isfinite(observed_seconds) or observed_seconds < 0):
        raise Denied("C3_4_TIMING_INVALID")
    phase = next((p for p in policy["phase_limits"] if p["id"] == phase_id), None)
    if phase is None:
        return {"status": "BASELINE_OR_MEASUREMENT_UNRESOLVED", "phase_id": phase_id}
    ratio = observed_seconds / phase["baseline_observed_seconds"]
    if ratio > 10:
        status = "C3_4_BLOCKED_NEEDS_HUMAN_APPROVAL"
    elif ratio > 5:
        status = "PASS_WITH_PERFORMANCE_WARNING"
    else:
        status = "PASS"
    return {"phase_id": phase_id, "status": status, "ratio": ratio,
            "observed_seconds": observed_seconds, "baseline_seconds": phase["baseline_observed_seconds"],
            "warning_above_seconds": phase["warning_above_seconds"],
            "block_above_seconds": phase["block_above_seconds"],
            "timing_method": phase["metric"]}


def verify_phase_receipt(root: Path, policy_file: Path, receipt_file: Path, *,
                         cohort: str, output: str, phase_id: str, trust_dir: Path) -> dict:
    """Only a separately signed measurement may count as an observed live C3.4 result."""
    policy = load_policy(policy_file)
    evidence = verified_document(root, receipt_file, trust_dir)
    if (evidence.get("schema") != "EDP_PHASE_TIMING_RECEIPT_V1"
            or evidence.get("cohort") != cohort or evidence.get("output") != output
            or evidence.get("phase_id") != phase_id
            or evidence.get("policy_sha256") != digest(policy_file.read_bytes())
            or evidence.get("observed_live") is not True
            or not isinstance(evidence.get("measurement_receipt_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", evidence["measurement_receipt_sha256"])):
        raise Denied("C3_4_RECEIPT_SCOPE_INVALID")
    row = next((p for p in policy["phase_limits"] if p["id"] == phase_id), None)
    if row is None or evidence.get("timing_method") != row["metric"]:
        raise Denied("C3_4_PHASE_NOT_COMPARABLE")
    if evidence.get("phase_comparable") is not True:
        raise Denied("C3_4_PHASE_NOT_COMPARABLE")
    return compare_phase(policy, phase_id, evidence.get("elapsed_seconds"))
