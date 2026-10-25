"""Owner-only: distinct V3 13F successor after terminal failed EDGAR canary.

Never edits the first signed upgrade, the failed canary Job/run, the historical
standing/E2E, the original V3 attempt, or the frozen C2000 source population.
Owner consent is represented only by a new signed, bounded v2 approval.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

from owner_day6_v3_one_shot import (
    APP_ID,
    BASE,
    CURRENT_REQUEST_SHA256,
    DEPLOYMENT,
    ORIGINAL_ACTIVE_REQUEST,
    REQUEST,
    ROOT,
    _installed,
    _job_settings,
    _owner,
    _pins,
    _remote_digest,
    _signed_once,
    _targets,
    _upload,
    _workspace_absent,
    _workspace_access,
    _write_once,
    require,
)
from owner_day6_v3_successor import (
    E2E_READY,
    HISTORICAL_E2E,
    STANDING,
    UPGRADE_APPROVAL,
)
from owner_day6_v3_upgrade_edgar import (
    OLD_COMMIT,
    OLD_E2E_SHA,
    STANDING_SHA,
    git,
    install_runtime,
    socket_action,
    verify_canary,
)
from owner_setup_day6_vault_0a import admin_cli

from edp_lab.operating.authority import canonical, file_digest, verified_document
from edp_lab.vault.v3_one_shot_gate import verify_saved_job
from edp_lab.vault.v3_service import _service_target_absent

WHEEL_COMMIT = "cafcd0ec7d5543672c0fc252669b24430333b85b"
WHEEL_SHA = "dee430dce58f687c116caf80f824b3647ae6d5493fbbbc1baff3782136637a2a"
OLD_WHEEL_SHA = "fd2d890f5a57f2bf3596eb2f0275860b70f2ac4549d1aae549e818e202bda546"
OLD_REQUEST_SHA = "2d1e8baca8b754abbdbeeb4338ad2df9c3a95e196fe4c930983f918db5499cc2"
OLD_DEPLOYMENT_SHA = "82b7fc51a716b7b1179195d1fda6de3a8b720187b0b606dbe17f5fa81e5ba155"
OLD_REQUEST = ROOT / "metadata/operating/day6_c2000_vault_v3_bounded_request_edgar_fix_v1.json"
OLD_DEPLOYMENT = ROOT / "metadata/operating/day6_c2000_vault_v3_deployment_v3.json"
OLD_APPROVAL = BASE / "approvals/day6-v3-edgar-fix-upgrade-v1.signed.json"
OLD_REPAIR = BASE / "approvals/day6-v3-edgarfix-installer-repair-v1.signed.json"
OLD_CANARY_JOB = BASE / "ledger/day6-v3-edgarfix-canary-job-v1.json"
OLD_CANARY_RUN = BASE / "ledger/day6-v3-edgarfix-canary-run-v1.json"
OLD_CANARY_NO_EFFECT = (
    BASE / "receipts/day6-v3-edgarfix-canary-1-no-effect.signed.json"
)
EXPECTED_OLD_JOB = 790551653088925
EXPECTED_OLD_RUN = 1057011099528821
EXPECTED_OLD_TASK = 749464491620163
NEW_REMOTE_DIR = "/Workspace/Shared/edp-lab/day6-c2000-v3-13f-fix-v1"
NEW_REMOTE_REQUEST = NEW_REMOTE_DIR + "/request.readonly.json"
NEW_JOB_NAME = "day6-v3-13f-fix-v2-readonly-canary"
NEW_JOB_RESERVATION = BASE / "ledger/day6-v3-13f-canary-job-reservation-v2.json"
NEW_JOB = BASE / "ledger/day6-v3-13f-canary-job-v2.json"
NEW_RUN_RESERVATION = BASE / "ledger/day6-v3-13f-canary-run-reservation-v2.json"
NEW_RUN = BASE / "ledger/day6-v3-13f-canary-run-v2.json"


def reviewed_wheel(deployment: dict) -> None:
    wheel = Path(deployment["artifact"]["local_build_output_uncommitted"])
    require(file_digest(wheel) == WHEEL_SHA, "V3_13F_WHEEL_SHA_CHANGED")
    with ZipFile(wheel) as archive:
        for filename in ("v3_spark_runtime.py", "v3_input.py"):
            name = "src/edp_lab/vault/" + filename
            require(archive.read("edp_lab/vault/" + filename) ==
                    git("show", f"{WHEEL_COMMIT}:{name}"),
                    "V3_13F_WHEEL_SOURCE_MISMATCH:" + filename)
        for filename in ("v3_mapping.py", "v3_ddl.py", "v3_oracles.py",
                         "v3_readback.py"):
            name = "src/edp_lab/vault/" + filename
            require(archive.read("edp_lab/vault/" + filename) ==
                    git("show", f"{OLD_COMMIT}:{name}"),
                    "V3_13F_WRITE_OR_VALIDATOR_CHANGED:" + filename)

        original = git("show", f"{OLD_COMMIT}:src/edp_lab/vault/v3_spark_runtime.py")
        updated = archive.read("edp_lab/vault/v3_spark_runtime.py")

        def node_bytes(name: str, source: bytes) -> str:
            node = next(
                (item for item in ast.parse(source).body
                 if isinstance(item, ast.FunctionDef) and item.name == name),
                None,
            )
            require(node is not None, "V3_13F_EXPECTED_FUNCTION_MISSING:" + name)
            return ast.dump(node, include_attributes=False)

        for name in ("_write_once", "v0a_smoke"):
            require(node_bytes(name, original) == node_bytes(name, updated),
                    "V3_13F_PERSISTED_WRITE_PATH_CHANGED:" + name)


def preflight(commit: str) -> tuple[dict, dict, dict]:
    _owner(commit)
    require(git("rev-parse", "HEAD").decode().strip() == commit,
            "V3_13F_UNREVIEWED_HEAD")
    request, deployment = _pins()
    require(file_digest(OLD_REQUEST) == OLD_REQUEST_SHA
            and file_digest(OLD_DEPLOYMENT) == OLD_DEPLOYMENT_SHA,
            "V3_13F_PREVIOUS_MANIFEST_CHANGED")
    require(file_digest(STANDING) == STANDING_SHA
            and file_digest(HISTORICAL_E2E) == OLD_E2E_SHA,
            "V3_13F_ORIGINAL_E2E_CHANGED")
    require(request["execution"]["runtime_artifact_sha256"] == WHEEL_SHA
            and deployment["artifact"]["sha256"] == WHEEL_SHA
            and deployment["artifact"]["workspace_target_proposed"]
            == NEW_REMOTE_DIR + "/edp_lab-0.1.0-py3-none-any.whl",
            "V3_13F_ACTIVE_WHEEL_NOT_PINNED")
    original = json.loads(OLD_REQUEST.read_bytes())
    require(
        all(request[k] == original[k] for k in original if k != "execution")
        and all(request["execution"][k] == original["execution"][k]
                for k in original["execution"]
                if k not in {"runtime_artifact_sha256", "deployment_sha256"}),
        "V3_13F_SCOPE_OR_SEMANTICS_CHANGED",
    )
    for path in (REQUEST, DEPLOYMENT, OLD_REQUEST, OLD_DEPLOYMENT,
                 ORIGINAL_ACTIVE_REQUEST):
        require(path.read_bytes() == git("show", f"{commit}:{path.relative_to(ROOT)}"),
                "V3_13F_REVIEWED_MANIFEST_MISMATCH:" + path.name)
    reviewed_wheel(deployment)
    proof = _installed(request, deployment)
    require(proof["historical_table_ids"] == _targets(request),
            "V3_13F_HISTORICAL_DELTA_ID_CHANGED")
    return request, deployment, proof


def predecessor_no_effect(request: dict, historical: dict) -> dict:
    """Bound to the previously failed Job/run/task; never replay it."""
    old_approval = verified_document(ROOT, OLD_APPROVAL, BASE / "trust")
    require(old_approval.get("status") == "APPROVED"
            and old_approval.get("request_sha256") == OLD_REQUEST_SHA
            and old_approval.get("deployment_sha256") == OLD_DEPLOYMENT_SHA
            and old_approval.get("wheel_sha256") == OLD_WHEEL_SHA
            and old_approval.get("standing_sha256") == STANDING_SHA
            and old_approval.get("original_e2e_sha256") == OLD_E2E_SHA,
            "V3_13F_PREVIOUS_OWNER_APPROVAL_MISMATCH")
    require(_remote_digest(json.loads(OLD_DEPLOYMENT.read_bytes())
                           ["artifact"]["workspace_target_proposed"])
            == OLD_WHEEL_SHA, "V3_13F_OLD_REMOTE_WHEEL_CHANGED")
    # Repair addendum is signed in the previous owner-controlled installer.
    prior_repair = verified_document(ROOT, OLD_REPAIR, BASE / "trust")
    require(prior_repair.get("original_approval_sha256") == file_digest(OLD_APPROVAL)
            and prior_repair.get("status") == "APPROVED"
            and prior_repair.get("wheel_sha256") == OLD_WHEEL_SHA,
            "V3_13F_PREVIOUS_INSTALLER_REPAIR_MISMATCH")
    job_record = json.loads(OLD_CANARY_JOB.read_bytes())
    run_record = json.loads(OLD_CANARY_RUN.read_bytes())
    require(job_record["job_id"] == EXPECTED_OLD_JOB
            and run_record["job_id"] == EXPECTED_OLD_JOB
            and run_record["run_id"] == EXPECTED_OLD_RUN
            and run_record["approval_sha256"] == file_digest(OLD_APPROVAL),
            "V3_13F_PREVIOUS_CANARY_LEDGER_CHANGED")
    saved = admin_cli("jobs", "get", str(EXPECTED_OLD_JOB))
    task = saved["settings"]["tasks"][0]
    parameters = task["python_wheel_task"]["parameters"]
    require(
        saved.get("run_as_user_name") == APP_ID
        and saved["settings"]["run_as"]["service_principal_name"] == APP_ID
        and saved["settings"]["max_concurrent_runs"] == 1
        and task["max_retries"] == 0
        and parameters == [
            "--request", "/Workspace/Shared/edp-lab/day6-c2000-v3-edgar-fix-v1/request.readonly.json",
            "--request-sha256", OLD_REQUEST_SHA,
            "--selection", "/Workspace/Shared/edp-lab/day6-c2000-v3/selection.json",
            "--negative-oracles",
            "/Workspace/Shared/edp-lab/day6-c2000-v3/negative-oracles.json",
        ],
        "V3_13F_PREVIOUS_CANARY_JOB_UNEXPECTED",
    )
    remote = admin_cli("jobs", "get-run", str(EXPECTED_OLD_RUN))
    require(remote.get("job_id") == EXPECTED_OLD_JOB
            and remote.get("run_id") == EXPECTED_OLD_RUN
            and remote.get("state", {}).get("result_state") == "FAILED"
            and remote.get("status", {}).get("state") == "TERMINATED"
            and len(remote.get("tasks", [])) == 1
            and remote["tasks"][0]["run_id"] == EXPECTED_OLD_TASK,
            "V3_13F_PREVIOUS_CANARY_NOT_TERMINAL")
    output = admin_cli("jobs", "get-run-output", str(EXPECTED_OLD_TASK))
    require("V3_C300_BINDING_COVERAGE_CHANGED" in str(output.get("error", "")),
            "V3_13F_PREVIOUS_CANARY_FAILURE_CAUSE_CHANGED")
    require(_targets(request) == historical["historical_table_ids"],
            "V3_13F_PREVIOUS_CANARY_HISTORICAL_CHANGED")
    for name in request["new_v3_table_allowlist"]:
        _service_target_absent(request["target_namespace"] + "." + name)
    if OLD_CANARY_NO_EFFECT.exists():
        receipt = verified_document(ROOT, OLD_CANARY_NO_EFFECT, BASE / "trust")
    else:
        receipt = {
            "schema": "EDP_DAY6_V3_UPGRADE_CANARY_NO_EFFECT_V1",
            "authority": "protected-verifier-v1",
            "status": "TERMINAL_NO_REMOTE_EFFECT",
            "job_id": EXPECTED_OLD_JOB,
            "run_id": EXPECTED_OLD_RUN,
            "task_run_id": EXPECTED_OLD_TASK,
            "old_approval_sha256": file_digest(OLD_APPROVAL),
            "old_wheel_sha256": OLD_WHEEL_SHA,
            "run_sha256": hashlib.sha256(canonical(remote)).hexdigest(),
            "task_output_sha256": hashlib.sha256(canonical(output)).hexdigest(),
            "absent_targets": request["new_v3_table_allowlist"],
            "historical_table_ids": historical["historical_table_ids"],
            "verified_at_utc": datetime.now(UTC).isoformat(),
        }
        _signed_once(receipt, "verifier.pem", OLD_CANARY_NO_EFFECT)
    require(receipt.get("schema") == "EDP_DAY6_V3_UPGRADE_CANARY_NO_EFFECT_V1"
            and receipt.get("status") == "TERMINAL_NO_REMOTE_EFFECT"
            and receipt.get("job_id") == EXPECTED_OLD_JOB
            and receipt.get("run_id") == EXPECTED_OLD_RUN
            and receipt.get("task_run_id") == EXPECTED_OLD_TASK
            and receipt.get("old_approval_sha256") == file_digest(OLD_APPROVAL)
            and receipt.get("old_wheel_sha256") == OLD_WHEEL_SHA
            and receipt.get("absent_targets") == request["new_v3_table_allowlist"]
            and receipt.get("historical_table_ids") == historical["historical_table_ids"]
            and receipt.get("run_sha256") == hashlib.sha256(canonical(remote)).hexdigest()
            and receipt.get("task_output_sha256") == hashlib.sha256(canonical(output)).hexdigest(),
            "V3_13F_SIGNED_NO_EFFECT_CHANGED")
    return receipt


def owner_approval(commit: str, request: dict, deployment: dict) -> None:
    if UPGRADE_APPROVAL.exists():
        approved = verified_document(ROOT, UPGRADE_APPROVAL, BASE / "trust")
    else:
        before = socket_action("status")
        require(before.get("status") == "READY_FOR_DISTINCT_ATTEMPT"
                and before.get("next_attempt") == 2
                and before.get("e2e_sha256") == OLD_E2E_SHA
                and before.get("standing_sha256") == STANDING_SHA,
                "V3_13F_PRE_UPGRADE_CHECKPOINT_CHANGED")
        approved = {
            "schema": "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1",
            "status": "APPROVED",
            "authority": "owner-v3-artifact-upgrade-v2",
            "reviewed_commit": commit,
            "request_sha256": CURRENT_REQUEST_SHA256,
            "deployment_sha256": file_digest(DEPLOYMENT),
            "wheel_sha256": WHEEL_SHA,
            "wheel_source_commit": WHEEL_COMMIT,
            "original_e2e_sha256": OLD_E2E_SHA,
            "standing_sha256": STANDING_SHA,
            "failed_canary_no_effect_sha256": file_digest(OLD_CANARY_NO_EFFECT),
            "previous_upgrade_approval_sha256": file_digest(OLD_APPROVAL),
            "previous_upgrade_repair_sha256": file_digest(OLD_REPAIR),
            "next_attempt": 2,
            "source_ids": request["selection"]["source_ids"],
            "table_allowlist": request["new_v3_table_allowlist"],
            "target_namespace": request["target_namespace"],
            "run_as": APP_ID,
            "canary_job_submissions_max": 1,
            "automatic_retries_max": 0,
            "approved_at_utc": datetime.now(UTC).isoformat(),
        }
        _signed_once(approved, "owner.pem", UPGRADE_APPROVAL)
    require(approved.get("schema") == "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1"
            and approved.get("status") == "APPROVED"
            and approved.get("reviewed_commit") == commit
            and approved.get("request_sha256") == CURRENT_REQUEST_SHA256
            and approved.get("deployment_sha256") == file_digest(DEPLOYMENT)
            and approved.get("wheel_sha256") == WHEEL_SHA
            and approved.get("failed_canary_no_effect_sha256")
            == file_digest(OLD_CANARY_NO_EFFECT)
            and approved.get("previous_upgrade_approval_sha256") ==
            file_digest(OLD_APPROVAL)
            and approved.get("previous_upgrade_repair_sha256") ==
            file_digest(OLD_REPAIR)
            and approved.get("original_e2e_sha256") == OLD_E2E_SHA
            and approved.get("standing_sha256") == STANDING_SHA
            and approved.get("run_as") == APP_ID
            and approved.get("next_attempt") == 2,
            "V3_13F_OWNER_APPROVAL_CHANGED")


def upload_artifacts(deployment: dict) -> None:
    wheel = Path(deployment["artifact"]["local_build_output_uncommitted"])
    remote = deployment["artifact"]["workspace_target_proposed"]
    require(file_digest(wheel) == WHEEL_SHA, "V3_13F_WHEEL_LOCAL_CHANGED")
    admin_cli("workspace", "mkdirs", NEW_REMOTE_DIR, allow_empty=True)
    for local, workspace in ((wheel, remote), (REQUEST, NEW_REMOTE_REQUEST)):
        try:
            observed = _remote_digest(workspace)
        except RuntimeError:
            _workspace_absent(workspace)
            _upload(local, workspace)
        else:
            require(observed == file_digest(local),
                    "V3_13F_REMOTE_EXISTS_DIFFERENT_BYTES:" + workspace)
        require(_remote_digest(workspace) == file_digest(local),
                "V3_13F_REMOTE_UPLOAD_BYTES_CHANGED:" + workspace)


def canary_parameters() -> list[str]:
    return ["--request", NEW_REMOTE_REQUEST,
            "--request-sha256", CURRENT_REQUEST_SHA256,
            "--selection", "/Workspace/Shared/edp-lab/day6-c2000-v3/selection.json",
            "--negative-oracles",
            "/Workspace/Shared/edp-lab/day6-c2000-v3/negative-oracles.json"]


def ensure_job(deployment: dict) -> int:
    if NEW_JOB.exists():
        ledger = json.loads(NEW_JOB.read_bytes())
        require(ledger["approval_sha256"] == file_digest(UPGRADE_APPROVAL),
                "V3_13F_EXISTING_JOB_LEDGER_CHANGED")
        job_id = ledger["job_id"]
    else:
        require(not NEW_JOB_RESERVATION.exists(),
                "V3_13F_UNCERTAIN_JOB_CREATE_DO_NOT_REPLAY")
        jobs = admin_cli("jobs", "list")
        require(isinstance(jobs, list) and not any(
            entry.get("settings", {}).get("name") == NEW_JOB_NAME
            for entry in jobs), "V3_13F_CANARY_JOB_ALREADY_EXISTS")
        settings = _job_settings(CURRENT_REQUEST_SHA256, deployment)
        settings["name"] = NEW_JOB_NAME
        settings["tasks"][0]["python_wheel_task"]["parameters"] = canary_parameters()
        _write_once(NEW_JOB_RESERVATION, {
            "approval_sha256": file_digest(UPGRADE_APPROVAL),
            "request_sha256": CURRENT_REQUEST_SHA256,
            "status": "RESERVED_BEFORE_CREATE",
        })
        result = admin_cli("jobs", "create", "--json", json.dumps(settings))
        job_id = result.get("job_id") if isinstance(result, dict) else None
        require(type(job_id) is int and job_id > 0,
                "V3_13F_JOB_ID_UNCERTAIN_NO_REPLAY")
        _write_once(NEW_JOB, {"job_id": job_id,
                              "approval_sha256": file_digest(UPGRADE_APPROVAL)})
    saved = admin_cli("jobs", "get", str(job_id))
    require(saved.get("job_id") == job_id
            and saved.get("run_as_user_name") == APP_ID,
            "V3_13F_CANARY_JOB_RUNAS_CHANGED")
    verify_saved_job(saved["settings"],
                     wheel_path=deployment["artifact"]["workspace_target_proposed"],
                     run_as={"service_principal_name": APP_ID},
                     parameters=canary_parameters())
    return job_id


def ensure_run(job_id: int) -> int:
    if NEW_RUN.exists():
        ledger = json.loads(NEW_RUN.read_bytes())
        require(ledger.get("job_id") == job_id
                and ledger.get("approval_sha256") == file_digest(UPGRADE_APPROVAL),
                "V3_13F_CANARY_RUN_LEDGER_CHANGED")
        return ledger["run_id"]
    require(not NEW_RUN_RESERVATION.exists(),
            "V3_13F_UNCERTAIN_RUN_SUBMISSION_DO_NOT_REPLAY")
    _write_once(NEW_RUN_RESERVATION, {
        "job_id": job_id,
        "status": "RESERVED_BEFORE_REMOTE_SUBMISSION",
        "approval_sha256": file_digest(UPGRADE_APPROVAL),
    })
    token = hashlib.sha256(canonical({
        "job_id": job_id, "approval_sha256": file_digest(UPGRADE_APPROVAL),
        "request_sha256": CURRENT_REQUEST_SHA256,
    })).hexdigest()[:32]
    record = admin_cli("jobs", "run-now", str(job_id), "--no-wait",
                       "--idempotency-token", token)
    run_id = record.get("run_id") if isinstance(record, dict) else None
    require(type(run_id) is int and run_id > 0,
            "V3_13F_RUN_ID_UNCERTAIN_NO_REPLAY")
    _write_once(NEW_RUN, {"job_id": job_id, "run_id": run_id,
                          "approval_sha256": file_digest(UPGRADE_APPROVAL)})
    return run_id


def readiness(commit: str, request: dict, deployment: dict, historical: dict) -> None:
    if E2E_READY.exists():
        ready = verified_document(ROOT, E2E_READY, BASE / "trust")
    else:
        require(_remote_digest(deployment["artifact"]["workspace_target_proposed"])
                == WHEEL_SHA
                and _remote_digest(NEW_REMOTE_REQUEST) == file_digest(REQUEST),
                "V3_13F_SERVICE_WHEEL_OR_REQUEST_UNVERIFIED")
        job_id = ensure_job(deployment)
        run_id = ensure_run(job_id)
        canary = verify_canary(request, job_id, run_id, historical)
        persisted = verified_document(ROOT, HISTORICAL_E2E, BASE / "trust")
        require(persisted.get("status") == "VERIFIED"
                and persisted.get("isolated_persisted_readback") is True
                and persisted.get("smoke_terminal_state") == "SUCCESS",
                "V3_13F_OLD_PERSISTED_E2E_CHANGED")
        ready = {
            "schema": "EDP_VAULT_E2E_UPGRADE_V1",
            "authority": "protected-verifier-v1",
            "status": "VERIFIED",
            "approval_sha256": file_digest(UPGRADE_APPROVAL),
            "original_e2e_sha256": OLD_E2E_SHA,
            "standing_sha256": STANDING_SHA,
            "failed_canary_no_effect_sha256": file_digest(OLD_CANARY_NO_EFFECT),
            "request_sha256": CURRENT_REQUEST_SHA256,
            "wheel_sha256": WHEEL_SHA,
            "installed_reviewed_commit": commit,
            "run_as": APP_ID,
            "environment_version": "4",
            "target_namespace": request["target_namespace"],
            "canary_terminal_state": "SUCCESS",
            "read_only_new_wheel_verified": True,
            "isolated_persisted_readback_reused": True,
            "signed_readback_sha256": hashlib.sha256(canonical(canary)).hexdigest(),
            "effective_uc_access_verified": True,
            "workspace_access_verified": True,
            "canary": canary,
            "verified_at_utc": datetime.now(UTC).isoformat(),
        }
        _signed_once(ready, "verifier.pem", E2E_READY)
    require(ready.get("schema") == "EDP_VAULT_E2E_UPGRADE_V1"
            and ready.get("status") == "VERIFIED"
            and ready.get("approval_sha256") == file_digest(UPGRADE_APPROVAL)
            and ready.get("failed_canary_no_effect_sha256") ==
            file_digest(OLD_CANARY_NO_EFFECT)
            and ready.get("original_e2e_sha256") == OLD_E2E_SHA
            and ready.get("standing_sha256") == STANDING_SHA
            and ready.get("request_sha256") == CURRENT_REQUEST_SHA256
            and ready.get("wheel_sha256") == WHEEL_SHA
            and ready.get("installed_reviewed_commit") == commit
            and ready.get("canary_terminal_state") == "SUCCESS"
            and ready.get("read_only_new_wheel_verified") is True,
            "V3_13F_SIGNED_E2E_CHANGED")


def activate(commit: str) -> dict:
    require(os.geteuid() == 0, "V3_13F_OWNER_ROOT_REQUIRED")
    request, deployment, historical = preflight(commit)
    os.environ["EDP_DAY6_V3_SERVICE_CONTEXT"] = "1"
    _workspace_access()
    predecessor_no_effect(request, historical)
    owner_approval(commit, request, deployment)
    upload_artifacts(deployment)
    readiness(commit, request, deployment, historical)
    install_runtime(commit)
    for _ in range(30):
        try:
            report = socket_action("status")
            if (report.get("status") == "READY_FOR_DISTINCT_ATTEMPT"
                    and report.get("next_attempt") == 2
                    and report.get("e2e_sha256") == file_digest(E2E_READY)):
                break
        except (OSError, RuntimeError, ValueError):
            pass
        time.sleep(1)
    else:
        raise RuntimeError("V3_13F_PROTECTED_SERVICE_NOT_READY")
    audit = socket_action("audit")
    require(audit.get("status") == "V3_UNATTENDED_ADMISSION_READS_VERIFIED"
            and audit.get("attempt_number") == 2
            and audit.get("checks_passed") == audit.get("checks_total") == 13,
            "V3_13F_PROTECTED_AUDIT_NOT_READY")
    return {
        "status": "V3_UPGRADE_READY_FOR_DISTINCT_ATTEMPT_2",
        "reviewed_commit": commit,
        "wheel_sha256": WHEEL_SHA,
        "e2e_sha256": file_digest(E2E_READY),
        "checks_passed": audit["checks_passed"],
        "v3_run_submitted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reviewed_commit")
    args = parser.parse_args()
    print(json.dumps(activate(args.reviewed_commit), sort_keys=True))


if __name__ == "__main__":
    main()
