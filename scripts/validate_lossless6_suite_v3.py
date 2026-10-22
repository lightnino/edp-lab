"""Fail-closed cumulative Lossless 6 gate; CI is static, runtime checks live receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import run_treasury_lossless6_v1 as treasury

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "metadata/evaluations/lossless6_suite_v3.json"
CONTROLS = ("FIN_001_V1", "FIN_002_V1", "TRY_001_V1", "TRY_002_V1",
            "TRY_003_V1", "TRY_004_V1")


def read(path: Path) -> dict:
    return json.loads(path.read_bytes())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_registration(suite: dict) -> None:
    assert suite["schema"] == "LOSSLESS6_SUITE_V3"
    assert tuple(suite["mandatory_controls"]) == CONTROLS
    for relative, expected in suite["registered_sha256"].items():
        assert sha(ROOT / relative) == expected, relative
    assert suite["economic_integration"]["current_status"] == "NOT_IMPLEMENTED"
    assert suite["fin_suite_ref"] == "metadata/evaluations/lossless6_fin_suite_v2.json"
    assert suite["treasury_suite_ref"] == "metadata/evaluations/treasury_lossless6_v1.json"


def check_packet(packet: dict, suite: dict, *, live_get=None) -> dict:
    """Return a disposition; only live checks can accept newly executed evidence."""
    errors = []
    base = {x["source_instance_id"]: x for x in read(ROOT / suite["retained_roster_ref"])}
    rows = packet["sources"] if "sources" in packet else read(ROOT / packet["sources_ref"])
    actual = {x["source_instance_id"]: x for x in rows}
    if len(actual) != len(rows) or not set(base) <= set(actual):
        errors.append("retained_source_membership")
    for sid, old in base.items():
        if actual.get(sid) != old:
            errors.append("changed_retained_source_pin:" + sid)
    if packet.get("model_pins") != suite["model_pins"]:
        errors.append("changed_model_pin")
    if packet.get("historical_output_pins") != suite["historical_output_pins"]:
        errors.append("changed_historical_output_pin")
    if packet.get("registered_sha256") != suite["registered_sha256"]:
        errors.append("changed_fixture_or_sql_fingerprint")
    new = set(actual) - set(base)
    classified = packet.get("new_source_classifications", {})
    if set(classified) != new:
        errors.append("new_source_applicability_incomplete")
    for sid in new:
        declaration = classified.get(sid, {})
        path = actual[sid].get("raw_path", "")
        if declaration.get("source_kind") not in {"TREASURY_XML", "OTHER"} or not declaration.get(
            "classification_evidence_sha256"):
            errors.append("new_source_classification_missing:" + sid)
        if "treasury" in path.lower() and declaration.get("source_kind") != "TREASURY_XML":
            errors.append("treasury_source_misclassified:" + sid)
        if declaration.get("source_kind") == "TREASURY_XML" and not declaration.get(
            "independent_fixture_ref"):
            errors.append("new_treasury_fixture_missing:" + sid)
    results = packet.get("control_results", {})
    if set(results) != set(CONTROLS):
        errors.append("mandatory_result_missing")
    for control in CONTROLS:
        result = results.get(control, {})
        if result.get("status") != "PASS" or result.get("evidence_mode") not in {"REUSED", "FRESH"}:
            errors.append("control_not_passed:" + control)
            continue
        ref = result.get("response_ref")
        if not ref or not (ROOT / ref).is_file():
            errors.append("receipt_missing:" + control)
            continue
        receipt = read(ROOT / ref)
        if sha(ROOT / ref) != result.get("response_sha256") or receipt.get("status", {}).get(
            "state") != "SUCCEEDED" or receipt.get("statement_id") != result.get("statement_id"):
            errors.append("receipt_invalid:" + control)
        if control.startswith("TRY_"):
            request_ref = result.get("request_ref")
            if not request_ref or not (ROOT / request_ref).is_file() or sha(
                ROOT / request_ref) != result.get("request_sha256") or read(
                ROOT / request_ref).get("statement") != treasury.render(
                control.removesuffix("_V1"), read(treasury.FIXTURE)):
                errors.append("try_sql_request_invalid:" + control)
            try:
                assessed = treasury.evaluate(control.removesuffix("_V1"), receipt.get(
                    "result", {}).get("data_array", []), read(treasury.FIXTURE))["status"]
            except (AssertionError, ValueError, TypeError):
                assessed = "FAIL"
            if assessed != "PASS":
                errors.append("try_result_invalid:" + control)
        if result["evidence_mode"] == "REUSED":
            if result.get("reuse_scope_sha256") != suite["retained_scope_sha256"]:
                errors.append("reuse_scope_changed:" + control)
            if result.get("response_sha256") != suite["approved_reused_receipts"].get(control):
                errors.append("unapproved_reuse:" + control)
        elif live_get is None:
            errors.append("fresh_live_verification_pending:" + control)
        elif live_get(result["statement_id"]) != receipt:
            errors.append("live_receipt_mismatch:" + control)
    treasury_new = {sid for sid in new if classified.get(sid, {}).get("source_kind") == "TREASURY_XML"}
    extra_controls = packet.get("new_treasury_controls", {})
    if set(extra_controls) != treasury_new:
        errors.append("new_treasury_controls_missing_or_extra")
    for sid in treasury_new:
        declared = classified[sid]
        fixture_ref = declared.get("independent_fixture_ref")
        fixture_path = ROOT / fixture_ref if fixture_ref else None
        if not fixture_path or not fixture_path.is_file() or sha(fixture_path) != declared.get(
            "independent_fixture_sha256"):
            errors.append("new_treasury_fixture_invalid:" + sid)
            continue
        fixture = read(fixture_path)
        if fixture.get("source_instance_id") != sid or not fixture.get("qnames") or not fixture.get(
            "expected_by_control"):
            errors.append("new_treasury_fixture_incomplete:" + sid)
            continue
        scoped = extra_controls.get(sid, {})
        if set(scoped) != set(CONTROLS[2:]):
            errors.append("new_treasury_control_missing:" + sid)
        for control in CONTROLS[2:]:
            evidence = scoped.get(control, {})
            request_ref = evidence.get("request_ref")
            response_ref = evidence.get("response_ref")
            sql_ref = evidence.get("sql_ref")
            if any(not ref or not (ROOT / ref).is_file() for ref in (
                request_ref, response_ref, sql_ref)):
                errors.append("new_treasury_evidence_missing:" + sid + ":" + control)
                continue
            request = read(ROOT / request_ref)
            response = read(ROOT / response_ref)
            rows = response.get("result", {}).get("data_array", [])
            if (evidence.get("status") != "PASS" or sha(ROOT / request_ref) != evidence.get(
                "request_sha256") or sha(ROOT / response_ref) != evidence.get("response_sha256")
                or sha(ROOT / sql_ref) != evidence.get("sql_sha256")
                or request.get("statement") != (ROOT / sql_ref).read_text()
                or response.get("status", {}).get("state") != "SUCCEEDED"
                or response.get("statement_id") != evidence.get("statement_id")
                or len(rows) != 1 or len(rows[0]) != 5 or rows[0][:2] != [control, sid]
                or json.loads(rows[0][2]) != fixture["expected_by_control"].get(control)
                or json.loads(rows[0][3]) != fixture["expected_by_control"].get(control)
                or int(rows[0][4]) != 0 or live_get is None
                or live_get(evidence["statement_id"]) != response):
                errors.append("new_treasury_evidence_invalid:" + sid + ":" + control)
    candidate = packet.get("combined_candidate", {})
    if candidate.get("status") != "PASS" or candidate.get("full_schema_differences") != 0 or candidate.get(
        "fin_noninterference") != "PASS":
        errors.append("combined_candidate_not_validated")
    if new and candidate.get("evidence_mode") != "FRESH":
        errors.append("expanded_candidate_requires_fresh_execution")
    if candidate.get("evidence_mode") == "REUSED":
        if new or candidate.get("sql_sha256") != suite["registered_sha256"][
            "sql/stability/c1500_m2_v1/combined_candidate.sql"] or candidate.get(
            "response_sha256") != suite["approved_combined_response_sha256"]:
            errors.append("combined_reuse_invalid")
        elif candidate.get("response_ref"):
            rows = read(ROOT / candidate["response_ref"]).get("result", {}).get("data_array", [])
            if len(rows) != 8 or any(len(row) != 3 or int(row[2]) != 0 for row in rows):
                errors.append("combined_reused_multiset_invalid")
    elif candidate.get("evidence_mode") == "FRESH":
        ref = candidate.get("response_ref")
        request_ref = candidate.get("request_ref")
        if not request_ref or not (ROOT / request_ref).is_file() or sha(ROOT / request_ref) != candidate.get(
            "request_sha256") or ("EXCEPT ALL" not in read(ROOT / request_ref).get("statement", "")
            or "UNION ALL" not in read(ROOT / request_ref).get("statement", "")):
            errors.append("combined_request_invalid")
        if not ref or not (ROOT / ref).is_file():
            errors.append("combined_receipt_missing")
        elif sha(ROOT / ref) != candidate.get("response_sha256") or read(ROOT / ref).get(
            "status", {}).get("state") != "SUCCEEDED":
            errors.append("combined_receipt_invalid")
        else:
            response = read(ROOT / ref)
            rows = response.get("result", {}).get("data_array", [])
            expected_classes = set(candidate.get("expected_occurrence_classes", []))
            expected_pairs = {(scope, direction) for scope in expected_classes for direction in (
                "candidate_minus_pinned", "pinned_minus_candidate")}
            if (response.get("statement_id") != candidate.get("statement_id")
                or not expected_classes or {(r[0], r[1]) for r in rows} != expected_pairs
                or any(len(r) != 3 or int(r[2]) != 0 for r in rows)):
                errors.append("combined_fresh_multiset_invalid")
            if live_get is None or live_get(candidate.get("statement_id")) != response:
                errors.append("combined_live_verification_pending_or_mismatch")
    else:
        errors.append("combined_evidence_mode_missing")
    if packet.get("claims_economic_integration"):
        economic = packet.get("economic_controls", {})
        if economic.get("status") != "PASS" or not economic.get("approved_grain_units_equation"):
            errors.append("economic_controls_required")
    if packet.get("source_preserving_status") == "PASS" and errors:
        errors.append("fabricated_scoped_acceptance")
    return {"status": "PASS" if not errors else "BLOCKED", "errors": sorted(set(errors)),
            "required_controls": list(CONTROLS), "new_sources": len(new),
            "economic_integration": "CONDITIONAL_REQUIRED" if packet.get(
                "claims_economic_integration") else "NOT_IMPLEMENTED"}


def check_prospective_budget(measurement: dict, budget: dict) -> dict:
    """Apply C3.4 only after an applicable approval predating the measured run."""
    problems = []
    if budget.get("status") != "APPROVED" or not budget.get("approved_effective_date"):
        problems.append("budget_not_effective")
    if measurement.get("workload_applicability_approval") != budget.get(
        "approved_scope_id") or not budget.get("approved_scope_id"):
        problems.append("workload_not_approved_comparable")
    if measurement.get("method") != budget.get("measurement_method"):
        problems.append("timing_method_changed")
    if measurement.get("run_started_at", "") < budget.get("approved_effective_date", "~"):
        problems.append("budget_not_prospective")
    for name, limit in budget["phases"].items():
        value = measurement.get("phases", {}).get(name)
        if value is None:
            problems.append("phase_unavailable:" + name)
        elif value > limit["prospective_max_seconds"]:
            problems.append("phase_exceeded:" + name)
    return {"status": "PASS" if not problems else "BLOCKED", "errors": problems}


def databricks_get(statement_id: str) -> dict:
    result = subprocess.run(["databricks", "api", "get", "/api/2.0/sql/statements/" + statement_id,
                             "-p", "edp-lab", "-o", "json"], capture_output=True,
                            text=True, check=True, timeout=1800)
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    suite = read(SUITE)
    check_registration(suite)
    outcome = check_packet(read(args.packet), suite, live_get=databricks_get if args.live else None)
    print(json.dumps(outcome, sort_keys=True))
    if outcome["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
