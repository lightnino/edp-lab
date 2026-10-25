"""Owner Terminal only: sign the original Day 6 V3 failure after read-only reconciliation.

This entry point has no Databricks mutation, grant, Job submission or replay.
It preserves the original one-shot ledger and signs a separate PARTIAL receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from owner_day6_v3_one_shot import (
    APP_ID,
    BASE,
    GRANT,
    GRANT_ID,
    INSTALL,
    ORIGINAL_REQUEST_SHA256,
    REQUEST,
    RESERVATION,
    ROOT,
    SERVICE_PRINCIPAL_ID,
    SUBMISSION,
    _owner,
    _signed_once,
    require,
)
from owner_setup_day6_vault_0a import admin_cli

from edp_lab.operating.authority import canonical, file_digest, verified_document

JOB_ID = 1067818802179598
RUN_ID = 665044227934897
TASK_RUN_ID = 844558996680731
RECEIPT = BASE / "receipts/day6-v3-one-shot-partial-v1.signed.json"
EXPECTED_HISTORICAL_ROWS = {
    "h_filing": 20, "h_concept": 24, "l_fact_slot": 76,
    "r_source_occurrence": 127, "s_fact_assertion": 127,
    "s_num_m2_value": 127, "r_load_event": 127,
    "vault_reject_quarantine": 6,
}


def _protected_json(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_uid == 0 and not path.stat().st_mode & 0o077,
            "V3_PROTECTED_RECORD_REQUIRED:" + path.name)
    return json.loads(path.read_bytes())


def _original_ledger() -> tuple[dict, dict, dict, dict]:
    request = json.loads(REQUEST.read_bytes())
    install = verified_document(ROOT, INSTALL, BASE / "trust")
    grant = verified_document(ROOT, GRANT, BASE / "trust")
    reservation = _protected_json(RESERVATION)
    submission = _protected_json(SUBMISSION)
    require(install.get("schema") == "EDP_DAY6_V3_INSTALL_RECEIPT_V1"
            and install.get("job_id") == JOB_ID
            and install.get("run_as") == APP_ID
            and install.get("request_sha256") == ORIGINAL_REQUEST_SHA256,
            "V3_ORIGINAL_INSTALL_MISMATCH")
    require(grant.get("schema") == "EDP_DAY6_V3_ONE_SHOT_GRANT_V1"
            and grant.get("grant_id") == GRANT_ID
            and grant.get("job_id") == JOB_ID
            and grant.get("run_as") == APP_ID
            and grant.get("request_sha256") == ORIGINAL_REQUEST_SHA256
            and grant.get("derived_request_sha256") == install.get("derived_request_sha256")
            and grant.get("install_receipt_sha256") == file_digest(INSTALL)
            and grant.get("selection_sha256") == request["selection"]["sha256"]
            and grant.get("negative_oracles_sha256") == request["negative_oracles"]["sha256"]
            and grant.get("ddl_sha256") == request["target_ddl"]["sha256"]
            and grant.get("tables") == request["new_v3_table_allowlist"]
            and grant.get("job_submissions_max") == 1
            and grant.get("automatic_retries_max") == 0,
            "V3_ORIGINAL_GRANT_MISMATCH")
    require(reservation.get("schema") == "EDP_DAY6_V3_ONE_SHOT_LEDGER_V1"
            and reservation.get("status") == "UNCERTAIN_REQUIRES_READBACK"
            and reservation.get("grant_sha256") == file_digest(GRANT)
            and reservation.get("request_sha256") == grant["derived_request_sha256"]
            and reservation.get("job_id") == JOB_ID,
            "V3_ORIGINAL_RESERVATION_MISMATCH")
    require(submission.get("status") == "SUBMITTED_REQUIRES_READBACK"
            and submission.get("grant_sha256") == file_digest(GRANT)
            and submission.get("job_id") == JOB_ID
            and submission.get("run_id") == RUN_ID,
            "V3_ORIGINAL_SUBMISSION_MISMATCH")
    return request, install, grant, reservation


def _terminal_failure() -> tuple[dict, dict, dict]:
    saved = admin_cli("jobs", "get", str(JOB_ID))
    run = admin_cli("jobs", "get-run", str(RUN_ID))
    output = admin_cli("jobs", "get-run-output", str(TASK_RUN_ID))
    tasks = run.get("tasks")
    saved_tasks = saved.get("settings", {}).get("tasks")
    require(saved.get("job_id") == JOB_ID
            and saved.get("run_as_user_name") == APP_ID
            and saved.get("settings", {}).get("run_as") == {
                "service_principal_name": APP_ID}
            and saved.get("settings", {}).get("queue", {}).get("enabled") is False
            and isinstance(saved_tasks, list) and len(saved_tasks) == 1
            and saved_tasks[0].get("max_retries") == 0
            and saved_tasks[0].get("retry_on_timeout") is False
            and saved_tasks[0].get("disable_auto_optimization") is True
            and run.get("job_id") == JOB_ID
            and run.get("run_id") == RUN_ID
            and run.get("job_run_id") == RUN_ID
            and not run.get("repair_history")
            and run.get("state", {}).get("result_state") == "FAILED"
            and run.get("status", {}).get("state") == "TERMINATED"
            and run.get("status", {}).get("termination_details", {}).get("code")
            == "UNAUTHORIZED_ERROR"
            and isinstance(tasks, list) and len(tasks) == 1
            and tasks[0].get("run_id") == TASK_RUN_ID
            and tasks[0].get("task_key") == "day6_v3_one_shot"
            and tasks[0].get("attempt_number") == 0
            and tasks[0].get("execution_duration") == 0
            and tasks[0].get("state", {}).get("result_state") == "FAILED"
            and "does not have access to Databricks Workspace" in
            run.get("state", {}).get("state_message", "")
            and "does not have access to Databricks Workspace" in
            output.get("error", ""),
            "V3_ORIGINAL_TERMINAL_FAILURE_MISMATCH")
    return saved, run, output


def _target_absent(full_name: str) -> None:
    result = subprocess.run(
        ["/usr/bin/sudo", "-n", "-u", "lightnino", "-H",
         "/opt/homebrew/bin/databricks", "tables", "get", full_name,
         "-p", "edp-lab", "-o", "json"],
        capture_output=True, text=True, check=False, timeout=30)
    require(result.returncode != 0 and result.stderr.strip() ==
            f"Error: Table '{full_name}' does not exist.",
            "V3_TARGET_ABSENCE_UNVERIFIED:" + full_name)


def _remote_tables(request: dict, baseline: dict) -> dict:
    namespace = request["target_namespace"]
    names = request["new_v3_table_allowlist"]
    historical = request["existing_tables_read_only"]
    require(len(names) == 23 and set(historical) == set(EXPECTED_HISTORICAL_ROWS)
            and set(baseline) == set(historical), "V3_TARGET_SCOPE_CHANGED")
    listed = admin_cli("tables", "list", "workspace", "edp_lab_day6_vault_proto")
    require(isinstance(listed, list) and {entry.get("name") for entry in listed}
            == set(historical), "V3_REMOTE_TABLE_SET_CHANGED")
    for name in names:
        _target_absent(namespace + "." + name)
    observed = {}
    for name in historical:
        item = admin_cli("tables", "get", namespace + "." + name,
                         "--include-delta-metadata")
        props = item.get("properties") or {}
        require(item.get("table_id") == baseline[name]
                and item.get("data_source_format") == "DELTA"
                and props.get("delta.lastUpdateVersion") == "0"
                and props.get("spark.sql.statistics.numRows")
                == str(EXPECTED_HISTORICAL_ROWS[name]),
                "V3_HISTORICAL_TABLE_METADATA_CHANGED:" + name)
        observed[name] = {"table_id": item["table_id"],
                          "version_property": "0",
                          "metadata_row_count": EXPECTED_HISTORICAL_ROWS[name]}
    return observed


def reconcile(expected_commit: str) -> dict:
    _owner(expected_commit)
    require(not RECEIPT.exists(), "V3_PARTIAL_RECEIPT_ALREADY_EXISTS")
    request, install, grant, _reservation = _original_ledger()
    saved, run, output = _terminal_failure()
    historical = _remote_tables(request, install["historical_table_ids"])
    assignment = admin_cli("workspace-iam-v2", "get-workspace-assignment-proxy",
                           SERVICE_PRINCIPAL_ID)
    effective = assignment.get("effective_entitlements")
    require(str(assignment.get("principal_id")) == SERVICE_PRINCIPAL_ID
            and assignment.get("principal_type") == "SERVICE_PRINCIPAL"
            and isinstance(effective, list),
            "V3_RUN_AS_IDENTITY_READBACK_MISMATCH")
    document = {
        "schema": "EDP_DAY6_V3_ONE_SHOT_PARTIAL_FAILURE_RECEIPT_V1",
        "authority": "protected-verifier-v1", "status": "PARTIAL_RECONCILE_AND_STOP",
        "original_job_id": JOB_ID, "original_run_id": RUN_ID,
        "original_task_run_id": TASK_RUN_ID,
        "terminal_result": "FAILED", "termination_code": "UNAUTHORIZED_ERROR",
        "task_attempts": 1, "task_execution_duration_ms": 0,
        "run_as": APP_ID,
        "current_effective_entitlements": sorted(effective),
        "request_sha256": ORIGINAL_REQUEST_SHA256,
        "install_receipt_sha256": file_digest(INSTALL),
        "grant_id": grant["grant_id"], "grant_sha256": file_digest(GRANT),
        "reservation_sha256": file_digest(RESERVATION),
        "submission_sha256": file_digest(SUBMISSION),
        "saved_job_readback_sha256": hashlib.sha256(canonical(saved)).hexdigest(),
        "terminal_run_readback_sha256": hashlib.sha256(canonical(run)).hexdigest(),
        "task_output_readback_sha256": hashlib.sha256(canonical(output)).hexdigest(),
        "absent_v3_tables": sorted(request["new_v3_table_allowlist"]),
        "historical_table_metadata": historical,
        "historical_exact_row_digest_and_delta_history": "NOT_FRESHLY_VERIFIED",
        "v3_pass": False, "submission_allowance_remaining": 0,
        "new_write_authority": False,
        "verified_at_utc": datetime.now(UTC).isoformat(),
    }
    _signed_once(document, "verifier.pem", RECEIPT)
    return {"status": document["status"], "job_id": JOB_ID, "run_id": RUN_ID,
            "receipt_path": str(RECEIPT), "receipt_sha256": file_digest(RECEIPT)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    args = parser.parse_args()
    print(json.dumps(reconcile(args.expected_commit), sort_keys=True))


if __name__ == "__main__":
    main()
