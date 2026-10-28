"""Owner-only signed no-effect disposition and exact V4 locator upgrade approval.

This performs read-only remote checks, then writes two additive protected signed
documents. It does not upload a wheel, create/run a Job, or alter any old pin.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

from owner_day6_v3_one_shot import APP_ID, BASE, ROOT, _remote_digest, _signed_once, require
from owner_day6_v3_upgrade_13f import EXPECTED_OLD_JOB, EXPECTED_OLD_RUN, EXPECTED_OLD_TASK
from owner_day6_v3_upgrade_coverpage import (
    JOB as V3_JOB_LEDGER,
)
from owner_day6_v3_upgrade_coverpage import (
    JOB_NAME as V3_JOB_NAME,
)
from owner_day6_v3_upgrade_coverpage import (
    JOB_RESERVATION as V3_JOB_RESERVATION,
)
from owner_day6_v3_upgrade_coverpage import (
    REMOTE_REQUEST as V3_REMOTE_REQUEST,
)
from owner_day6_v3_upgrade_coverpage import (
    RUN as V3_RUN_LEDGER,
)
from owner_day6_v3_upgrade_coverpage import (
    RUN_RESERVATION as V3_RUN_RESERVATION,
)
from owner_day6_v3_upgrade_coverpage import (
    V1_NO_EFFECT,
    V2_APPROVAL,
    V2_DEPLOYMENT_SHA,
    V2_JOB_ID,
    V2_NO_EFFECT,
    V2_REQUEST_SHA,
    V2_RUN_ID,
    V2_TASK_ID,
    V2_WHEEL_SHA,
)
from owner_day6_v3_upgrade_edgar import OLD_COMMIT, OLD_E2E_SHA, STANDING_SHA, socket_action
from owner_setup_day6_vault_0a import admin_cli

from edp_lab.operating.authority import canonical, file_digest, verified_document
from edp_lab.vault.v3_one_shot_gate import verify_saved_job

REQUEST = ROOT / "metadata/operating/day6_c2000_vault_v3_bounded_request_locator_fix_v1.json"
DEPLOYMENT = ROOT / "metadata/operating/day6_c2000_vault_v3_deployment_v6.json"
PRIOR_REQUEST = ROOT / "metadata/operating/day6_c2000_vault_v3_bounded_request_coverpage_quote_fix_v1.json"
PRIOR_DEPLOYMENT = ROOT / "metadata/operating/day6_c2000_vault_v3_deployment_v5.json"
NO_EFFECT = BASE / "receipts/day6-v3-canary-3-no-effect.signed.json"
APPROVAL = BASE / "approvals/day6-v3-edgar-locator-upgrade-v4.signed.json"
INSTALL = BASE / "receipts/day6-v3-install-v1.signed.json"
STANDING = BASE / "trust/day6-v3-standing-v1.signed.json"
E2E = BASE / "receipts/day6-v3-e2e-ready-v1.signed.json"
FAILED_CANARY_E2E = BASE / "receipts/day6-v3-e2e-ready-coverpage-fix-v3.signed.json"
V3_APPROVAL = BASE / "approvals/day6-v3-coverpage-fix-upgrade-v3.signed.json"
INSTALLED_COMMIT = BASE / "trust/day6-v3-installed-commit.txt"
V3_REQUEST_SHA = "f28f5495387d53a29e19885b458c1bc684c791fc6c4aa6a5a0beb6aa1bd58c6b"
V3_WHEEL_SHA = "240cfcd2661087d73a1beb56dc9ddb2b1ef880a267b6ee3c616914192be8984b"
WHEEL_SHA = "0b26e3319bd453fc1a460d09d81326ee12abc22422cb41d268d5068f4cbcd88e"
JOB_ID = 389618471873606
RUN_ID = 588435072660254
TASK_ID = 105664983922870
EXPECTED_HISTORICAL_VERSION = "0"


def git(*args: str) -> bytes:
    return subprocess.run(["/usr/bin/git", "-c", f"safe.directory={ROOT}",
                           "-C", str(ROOT), *args], check=True,
                          capture_output=True, timeout=60).stdout


def _function(source: bytes, name: str) -> str:
    node = next(item for item in ast.parse(source).body
                if isinstance(item, ast.FunctionDef) and item.name == name)
    return ast.dump(node, include_attributes=False)


def _protected_ledger(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_uid == 0 and not path.stat().st_mode & 0o077,
            "V4_PROTECTED_LEDGER_INVALID:" + path.name)
    value = json.loads(path.read_bytes())
    require(type(value) is dict, "V4_PROTECTED_LEDGER_INVALID:" + path.name)
    return value


def _prior_trust() -> dict:
    """The failed v3 canary has no E2E receipt; retain the real baseline chain."""
    standing = verified_document(ROOT, STANDING, BASE / "trust")
    baseline = verified_document(ROOT, E2E, BASE / "trust")
    install = verified_document(ROOT, INSTALL, BASE / "trust")
    first = verified_document(ROOT, V1_NO_EFFECT, BASE / "trust")
    second = verified_document(ROOT, V2_NO_EFFECT, BASE / "trust")
    v2_approval = verified_document(ROOT, V2_APPROVAL, BASE / "trust")
    v3_approval = verified_document(ROOT, V3_APPROVAL, BASE / "trust")
    require(not FAILED_CANARY_E2E.exists()
            and file_digest(STANDING) == STANDING_SHA
            and file_digest(E2E) == OLD_E2E_SHA
            and standing.get("status") == "INSTALLED"
            and baseline.get("schema") == "EDP_VAULT_E2E_READY_V1"
            and baseline.get("status") == "VERIFIED"
            and baseline.get("standing_sha256") == STANDING_SHA
            and baseline.get("run_as") == APP_ID
            and baseline.get("isolated_persisted_readback") is True
            and install.get("schema") == "EDP_DAY6_V3_INSTALL_RECEIPT_V1"
            and install.get("status") == "INSTALLED_NOT_GRANTED"
            and install.get("run_as") == APP_ID
            and len(install.get("historical_table_ids", {})) == 8
            and first.get("schema") == "EDP_DAY6_V3_UPGRADE_CANARY_NO_EFFECT_V1"
            and first.get("status") == "TERMINAL_NO_REMOTE_EFFECT"
            and first.get("job_id") == EXPECTED_OLD_JOB
            and first.get("run_id") == EXPECTED_OLD_RUN
            and first.get("task_run_id") == EXPECTED_OLD_TASK
            and second.get("schema") == "EDP_DAY6_V3_UPGRADE_CANARY_NO_EFFECT_V1"
            and second.get("status") == "TERMINAL_NO_REMOTE_EFFECT"
            and second.get("job_id") == V2_JOB_ID
            and second.get("run_id") == V2_RUN_ID
            and second.get("task_run_id") == V2_TASK_ID
            and second.get("old_approval_sha256") == file_digest(V2_APPROVAL)
            and second.get("old_wheel_sha256") == V2_WHEEL_SHA
            and second.get("prior_canary_no_effect_sha256") == file_digest(V1_NO_EFFECT)
            and v2_approval.get("schema") == "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1"
            and v2_approval.get("status") == "APPROVED"
            and v2_approval.get("request_sha256") == V2_REQUEST_SHA
            and v2_approval.get("deployment_sha256") == V2_DEPLOYMENT_SHA
            and v2_approval.get("wheel_sha256") == V2_WHEEL_SHA
            and v2_approval.get("failed_canary_no_effect_sha256") == file_digest(V1_NO_EFFECT)
            and v3_approval.get("schema") == "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1"
            and v3_approval.get("status") == "APPROVED"
            and v3_approval.get("request_sha256") == V3_REQUEST_SHA
            and v3_approval.get("deployment_sha256") == file_digest(PRIOR_DEPLOYMENT)
            and v3_approval.get("wheel_sha256") == V3_WHEEL_SHA
            and v3_approval.get("standing_sha256") == STANDING_SHA
            and v3_approval.get("original_e2e_sha256") == OLD_E2E_SHA
            and v3_approval.get("failed_canary_no_effect_sha256") == file_digest(V2_NO_EFFECT)
            and v3_approval.get("previous_upgrade_approval_sha256") == file_digest(V2_APPROVAL)
            and v3_approval.get("first_canary_no_effect_sha256") == file_digest(V1_NO_EFFECT),
            "V4_PRIOR_SIGNED_CHAIN_INVALID")
    require(INSTALLED_COMMIT.is_file() and not INSTALLED_COMMIT.is_symlink()
            and INSTALLED_COMMIT.stat().st_uid == 0
            and not INSTALLED_COMMIT.stat().st_mode & 0o022
            and INSTALLED_COMMIT.read_text().strip() == OLD_COMMIT,
            "V4_INSTALLED_COMMIT_UNPROTECTED")
    current = socket_action("status")
    require(current.get("status") == "READY_FOR_DISTINCT_ATTEMPT"
            and current.get("next_attempt") == 2
            and current.get("standing_sha256") == STANDING_SHA
            and current.get("e2e_sha256") == OLD_E2E_SHA,
            "V4_PROTECTED_CHECKPOINT_CHANGED")
    return install


def preflight(commit: str) -> tuple[dict, dict]:
    require(os.geteuid() == 0, "V4_OWNER_ROOT_REQUIRED")
    require(git("rev-parse", "HEAD").decode().strip() == commit
            and not git("status", "--porcelain", "--untracked-files=no").strip(),
            "V4_REVIEWED_COMMIT_OR_TREE_CHANGED")
    for path in (REQUEST, DEPLOYMENT, PRIOR_REQUEST, PRIOR_DEPLOYMENT):
        require(path.read_bytes() == git("show", f"{commit}:{path.relative_to(ROOT)}"),
                "V4_REVIEWED_PIN_CHANGED:" + path.name)
    request = json.loads(REQUEST.read_bytes())
    deployment = json.loads(DEPLOYMENT.read_bytes())
    prior = json.loads(PRIOR_REQUEST.read_bytes())
    require({k: v for k, v in request.items() if k != "execution"} ==
            {k: v for k, v in prior.items() if k != "execution"},
            "V4_SOURCE_OR_SEMANTIC_SCOPE_CHANGED")
    altered = {k for k in request["execution"]
               if request["execution"][k] != prior["execution"][k]}
    require(altered == {"runtime_artifact_sha256", "deployment_sha256"}
            and request["execution"]["runtime_artifact_sha256"] == WHEEL_SHA
            and request["execution"]["deployment_sha256"] == file_digest(DEPLOYMENT),
            "V4_REQUEST_SCOPE_CHANGED")
    artifact = deployment["artifact"]
    wheel = Path(artifact["local_build_output_uncommitted"])
    require(artifact["sha256"] == file_digest(wheel) == WHEEL_SHA
            and artifact["workspace_target_proposed"] ==
            "/Workspace/Shared/edp-lab/day6-c2000-v3-edgar-locator-fix-v4/edp_lab-0.1.0-py3-none-any.whl",
            "V4_WHEEL_OR_PATH_CHANGED")
    with ZipFile(wheel) as archive, ZipFile(Path(json.loads(PRIOR_DEPLOYMENT.read_bytes())
                                           ["artifact"]["local_build_output_uncommitted"])) as old:
        for name in ("v3_keys.py", "v3_mapping.py", "v3_input.py",
                     "v3_spark_runtime.py", "v3_ddl.py", "v3_oracles.py",
                     "v3_readback.py"):
            member = "edp_lab/vault/" + name
            require(archive.read(member) == git("show", f"{commit}:src/edp_lab/vault/{name}"),
                    "V4_WHEEL_SOURCE_MISMATCH:" + name)
        for name in ("v3_ddl.py", "v3_oracles.py", "v3_readback.py"):
            require(archive.read("edp_lab/vault/" + name) ==
                    old.read("edp_lab/vault/" + name),
                    "V4_WRITE_OR_VERIFIER_CHANGED:" + name)
        require(_function(archive.read("edp_lab/vault/v3_spark_runtime.py"), "_write_once") ==
                _function(old.read("edp_lab/vault/v3_spark_runtime.py"), "_write_once"),
                "V4_PERSISTED_WRITE_PATH_CHANGED")
    require(file_digest(PRIOR_REQUEST) == V3_REQUEST_SHA
            and json.loads(PRIOR_DEPLOYMENT.read_bytes())["artifact"]["sha256"] ==
            V3_WHEEL_SHA, "V4_PRIOR_CANARY_PIN_CHANGED")
    _prior_trust()
    return request, deployment


def reconcile(request: dict) -> dict:
    approval_sha = file_digest(V3_APPROVAL)
    job_reservation = _protected_ledger(V3_JOB_RESERVATION)
    job_ledger = _protected_ledger(V3_JOB_LEDGER)
    run_reservation = _protected_ledger(V3_RUN_RESERVATION)
    run_ledger = _protected_ledger(V3_RUN_LEDGER)
    require(job_reservation == {
                "approval_sha256": approval_sha,
                "request_sha256": V3_REQUEST_SHA,
                "status": "RESERVED_BEFORE_CREATE",
            } and job_ledger == {
                "job_id": JOB_ID, "approval_sha256": approval_sha,
            } and run_reservation == {
                "job_id": JOB_ID,
                "status": "RESERVED_BEFORE_REMOTE_SUBMISSION",
                "approval_sha256": approval_sha,
            } and run_ledger == {
                "job_id": JOB_ID, "run_id": RUN_ID,
                "approval_sha256": approval_sha,
            }, "V4_CANARY_3_LEDGER_CHANGED")
    old_deployment = json.loads(PRIOR_DEPLOYMENT.read_bytes())
    old_wheel = old_deployment["artifact"]["workspace_target_proposed"]
    require(_remote_digest(old_wheel) == V3_WHEEL_SHA
            and _remote_digest(V3_REMOTE_REQUEST) == V3_REQUEST_SHA,
            "V4_CANARY_3_REMOTE_ARTIFACT_CHANGED")
    job = admin_cli("jobs", "get", str(JOB_ID))
    run = admin_cli("jobs", "get-run", str(RUN_ID))
    parameters = [
        "--request", V3_REMOTE_REQUEST,
        "--request-sha256", V3_REQUEST_SHA,
        "--selection", "/Workspace/Shared/edp-lab/day6-c2000-v3/selection.json",
        "--negative-oracles",
        "/Workspace/Shared/edp-lab/day6-c2000-v3/negative-oracles.json",
    ]
    require(job.get("job_id") == JOB_ID
            and job.get("run_as_user_name") == APP_ID
            and job.get("settings", {}).get("name") == V3_JOB_NAME
            and run.get("job_id") == JOB_ID
            and run.get("run_id") == RUN_ID
            and run.get("creator_user_name") == APP_ID
            and run.get("run_name") == V3_JOB_NAME
            and run.get("state", {}).get("result_state") == "FAILED"
            and run.get("status", {}).get("state") == "TERMINATED"
            and len(run.get("tasks", [])) == 1
            and run["tasks"][0].get("run_id") == TASK_ID
            and run["tasks"][0].get("task_key") == "day6_v3_one_shot"
            and run["tasks"][0].get("attempt_number") == 0
            and run["tasks"][0].get("environment_key") == "v3_fixed_runtime",
            "V4_CANARY_3_NOT_TERMINAL_FAILED")
    verify_saved_job(
        job["settings"], wheel_path=old_wheel,
        run_as={"service_principal_name": APP_ID}, parameters=parameters,
    )
    params = run["tasks"][0]["python_wheel_task"]["parameters"]
    require(params == parameters, "V4_CANARY_3_RUN_PARAMETERS_CHANGED")
    output = admin_cli("jobs", "get-run-output", str(TASK_ID))
    task_metadata = output.get("metadata") or {}
    require(task_metadata.get("job_id") == JOB_ID
            and task_metadata.get("run_id") == TASK_ID
            and task_metadata.get("creator_user_name") == APP_ID
            and task_metadata.get("python_wheel_task", {}).get("parameters") == parameters,
            "V4_CANARY_3_TASK_OUTPUT_IDENTITY_CHANGED")
    require(output.get("error") == "ValueError: INVALID_OCCURRENCE_LOCATOR"
            and "_prepare_rows" in output.get("error_trace", "")
            and "_write_once" not in output.get("error_trace", ""),
            "V4_CANARY_3_FAILURE_CLASS_CHANGED")
    listed = admin_cli("tables", "list", "workspace", "edp_lab_day6_vault_proto")
    require(isinstance(listed, list), "V4_REMOTE_TABLE_LIST_UNVERIFIED")
    by_name = {item["name"]: item for item in listed}
    historical = _prior_trust()["historical_table_ids"]
    allowed = set(historical) | {"v0a_day6_e2e_20261025"}
    require(set(by_name) == allowed
            and not set(request["new_v3_table_allowlist"]) & set(by_name),
            "V4_CANARY_3_TARGET_OR_HISTORICAL_SET_CHANGED")
    for name, table_id in historical.items():
        item = by_name[name]
        require(item.get("table_id") == table_id
                and item.get("data_source_format") == "DELTA"
                and item.get("properties", {}).get("delta.lastUpdateVersion") ==
                EXPECTED_HISTORICAL_VERSION,
                "V4_HISTORICAL_DELTA_CHANGED:" + name)
    return {"schema": "EDP_DAY6_V3_CANARY_3_NO_EFFECT_V1",
            "authority": "protected-verifier-v1",
            "status": "TERMINAL_NO_REMOTE_EFFECT",
            "job_id": JOB_ID, "run_id": RUN_ID, "task_id": TASK_ID,
            "read_only_parameters_verified": True,
            "failure_code": "INVALID_OCCURRENCE_LOCATOR",
            "prior_e2e_sha256": OLD_E2E_SHA,
            "prior_v1_no_effect_sha256": file_digest(V1_NO_EFFECT),
            "prior_v2_no_effect_sha256": file_digest(V2_NO_EFFECT),
            "v3_approval_sha256": approval_sha,
            "v3_request_sha256": V3_REQUEST_SHA,
            "v3_wheel_sha256": V3_WHEEL_SHA,
            "v3_job_reservation_sha256": file_digest(V3_JOB_RESERVATION),
            "v3_job_ledger_sha256": file_digest(V3_JOB_LEDGER),
            "v3_run_reservation_sha256": file_digest(V3_RUN_RESERVATION),
            "v3_run_ledger_sha256": file_digest(V3_RUN_LEDGER),
            "target_absent_count": 23,
            "historical_table_ids": historical,
            "historical_delta_versions": {name: EXPECTED_HISTORICAL_VERSION
                                          for name in historical},
            "job_sha256": hashlib.sha256(canonical(job)).hexdigest(),
            "run_sha256": hashlib.sha256(canonical(run)).hexdigest(),
            "task_output_sha256": hashlib.sha256(canonical(output)).hexdigest(),
            "verified_at_utc": datetime.now(UTC).isoformat()}


def authorize(commit: str) -> dict:
    request, deployment = preflight(commit)
    proof = reconcile(request)
    if NO_EFFECT.exists():
        saved = verified_document(ROOT, NO_EFFECT, BASE / "trust")
        require(all(saved.get(k) == v for k, v in proof.items()
                    if k != "verified_at_utc"), "V4_SIGNED_NO_EFFECT_CHANGED")
    else:
        _signed_once(proof, "verifier.pem", NO_EFFECT)
    approval = {"schema": "EDP_DAY6_V3_ARTIFACT_UPGRADE_V4",
                "authority": "owner-v3-artifact-upgrade-v4",
                "status": "APPROVED",
                "reviewed_commit": commit,
                "request_sha256": file_digest(REQUEST),
                "deployment_sha256": file_digest(DEPLOYMENT),
                "wheel_sha256": WHEEL_SHA,
                "wheel_workspace_path": deployment["artifact"]["workspace_target_proposed"],
                "canary_3_no_effect_sha256": file_digest(NO_EFFECT),
                "standing_sha256": file_digest(STANDING),
                "prior_e2e_sha256": file_digest(E2E),
                "prior_v1_no_effect_sha256": file_digest(V1_NO_EFFECT),
                "prior_v2_no_effect_sha256": file_digest(V2_NO_EFFECT),
                "prior_v3_approval_sha256": file_digest(V3_APPROVAL),
                "allowed_operation": "DISTINCT_READ_ONLY_CANARY_V4_THEN_EXISTING_SCOPE_V3",
                "canary_job_submissions_max": 1,
                "automatic_retries_max": 0,
                "target_namespace": request["target_namespace"],
                "source_ids": request["selection"]["source_ids"],
                "table_allowlist": request["new_v3_table_allowlist"],
                "issued_at_utc": datetime.now(UTC).isoformat()}
    if APPROVAL.exists():
        saved = verified_document(ROOT, APPROVAL, BASE / "trust")
        require(all(saved.get(k) == v for k, v in approval.items()
                    if k != "issued_at_utc"), "V4_SIGNED_APPROVAL_CHANGED")
    else:
        _signed_once(approval, "owner.pem", APPROVAL)
    return {"status": "V4_APPROVED_NOT_DEPLOYED",
            "no_effect_sha256": file_digest(NO_EFFECT),
            "approval_sha256": file_digest(APPROVAL),
            "request_sha256": file_digest(REQUEST),
            "wheel_sha256": WHEEL_SHA,
            "remote_job_submissions": 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reviewed_commit")
    args = parser.parse_args()
    print(json.dumps(authorize(args.reviewed_commit), sort_keys=True))


if __name__ == "__main__":
    main()
