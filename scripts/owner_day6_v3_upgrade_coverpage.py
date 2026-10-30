"""Owner terminal: distinct V3-only COVERPAGE quote-repair canary v3.

Canary v1 and v2 are immutable failed attempts. Only Owner may approve a
different reviewed wheel, after exact terminal no-effect verification.
All v3 actions have new signed receipt/Job/run identities. No real V3 run.
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

import owner_day6_v3_upgrade_13f as predecessor
from owner_day6_v3_one_shot import (
    APP_ID,
    BASE,
    CURRENT_REQUEST_SHA256,
    DEPLOYMENT,
    ORIGINAL_ACTIVE_REQUEST,
    REQUEST,
    ROOT,
    _installed,
    _owner,
    _pins,
    _remote_digest,
    _signed_once,
    _targets,
    _workspace_access,
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
)
from owner_setup_day6_vault_0a import admin_cli

from edp_lab.operating.authority import canonical, file_digest, verified_document
from edp_lab.vault.v3_one_shot_gate import verify_saved_job
from edp_lab.vault.v3_service import _service_target_absent

WHEEL_SOURCE_COMMIT = "bf079cba4b1ba1ef14a704fa1162d157630735ff"
WHEEL_SHA = "240cfcd2661087d73a1beb56dc9ddb2b1ef880a267b6ee3c616914192be8984b"
V2_WHEEL_SHA = "dee430dce58f687c116caf80f824b3647ae6d5493fbbbc1baff3782136637a2a"
V2_REQUEST = ROOT / "metadata/operating/day6_c2000_vault_v3_bounded_request_13f_fix_v1.json"
V2_DEPLOYMENT = ROOT / "metadata/operating/day6_c2000_vault_v3_deployment_v4.json"
V2_REQUEST_SHA = "7e6597c06499671cced90fa3afac96efd97547cd85a674a145023c52bc6cdce1"
V2_DEPLOYMENT_SHA = "e6bfcd5acbd8ce9844835509a89ed14e6d07907a9848f480aeefc75a394ecf82"
V2_APPROVAL = BASE / "approvals/day6-v3-13f-fix-upgrade-v2.signed.json"
V1_NO_EFFECT = BASE / "receipts/day6-v3-edgarfix-canary-1-no-effect.signed.json"
V2_NO_EFFECT = BASE / "receipts/day6-v3-13f-canary-2-no-effect.signed.json"
V2_JOB_LEDGER = BASE / "ledger/day6-v3-13f-canary-job-v2.json"
V2_RUN_LEDGER = BASE / "ledger/day6-v3-13f-canary-run-v2.json"
V2_JOB_ID = 552562574530819
V2_RUN_ID = 321745477125884
V2_TASK_ID = 299105441863960
REMOTE_DIR = "/Workspace/Shared/edp-lab/day6-c2000-v3-coverpage-quote-fix-v3"
REMOTE_REQUEST = REMOTE_DIR + "/request.readonly.json"
JOB_NAME = "day6-v3-coverpage-quote-v3-readonly-canary"
JOB = BASE / "ledger/day6-v3-coverpage-canary-job-v3.json"
JOB_RESERVATION = BASE / "ledger/day6-v3-coverpage-canary-job-reservation-v3.json"
RUN = BASE / "ledger/day6-v3-coverpage-canary-run-v3.json"
RUN_RESERVATION = BASE / "ledger/day6-v3-coverpage-canary-run-reservation-v3.json"


def wheel_provenance(deployment: dict) -> None:
    wheel = Path(deployment["artifact"]["local_build_output_uncommitted"])
    require(file_digest(wheel) == WHEEL_SHA, "V3_COVERPAGE_WHEEL_SHA_CHANGED")
    with ZipFile(wheel) as archive:
        for name in ("v3_spark_runtime.py", "v3_input.py"):
            wheel_bytes = archive.read("edp_lab/vault/" + name)
            expected = git("show", f"{WHEEL_SOURCE_COMMIT}:src/edp_lab/vault/{name}")
            require(wheel_bytes == expected, "V3_COVERPAGE_WHEEL_SOURCE_CHANGED:" + name)
        for name in ("v3_ddl.py", "v3_mapping.py", "v3_oracles.py", "v3_readback.py"):
            old = git("show", f"{OLD_COMMIT}:src/edp_lab/vault/{name}")
            require(archive.read("edp_lab/vault/" + name) == old,
                    "V3_COVERPAGE_WRITE_OR_VERIFIER_CHANGED:" + name)

        old = git("show", f"{OLD_COMMIT}:src/edp_lab/vault/v3_spark_runtime.py")
        new = archive.read("edp_lab/vault/v3_spark_runtime.py")

        def signature(source: bytes, name: str) -> str:
            fn = next((n for n in ast.parse(source).body
                       if isinstance(n, ast.FunctionDef) and n.name == name), None)
            require(fn is not None, "V3_COVERPAGE_FUNCTION_MISSING:" + name)
            return ast.dump(fn, include_attributes=False)

        for name in ("_write_once", "v0a_smoke"):
            require(signature(old, name) == signature(new, name),
                    "V3_COVERPAGE_PERSISTED_WRITE_PATH_CHANGED:" + name)


def preflight(commit: str) -> tuple[dict, dict, dict]:
    _owner(commit)
    require(git("rev-parse", "HEAD").decode().strip() == commit,
            "V3_COVERPAGE_UNREVIEWED_HEAD")
    require(file_digest(V2_REQUEST) == V2_REQUEST_SHA
            and file_digest(V2_DEPLOYMENT) == V2_DEPLOYMENT_SHA
            and file_digest(STANDING) == STANDING_SHA
            and file_digest(HISTORICAL_E2E) == OLD_E2E_SHA,
            "V3_COVERPAGE_PREVIOUS_FROZEN_ARTIFACT_CHANGED")
    request, deployment = _pins()
    require(deployment["artifact"]["sha256"] == WHEEL_SHA
            and request["execution"]["runtime_artifact_sha256"] == WHEEL_SHA
            and deployment["artifact"]["workspace_target_proposed"] ==
            REMOTE_DIR + "/edp_lab-0.1.0-py3-none-any.whl",
            "V3_COVERPAGE_DEPLOYED_WHEEL_NOT_PINNED")
    prior = json.loads(V2_REQUEST.read_bytes())
    require(
        all(request[key] == prior[key] for key in prior if key != "execution")
        and all(request["execution"][key] == prior["execution"][key]
                for key in prior["execution"]
                if key not in {"runtime_artifact_sha256", "deployment_sha256"}),
        "V3_COVERPAGE_SCOPE_EXPANSION",
    )
    for path in (REQUEST, DEPLOYMENT, V2_REQUEST, V2_DEPLOYMENT,
                 ORIGINAL_ACTIVE_REQUEST):
        require(path.read_bytes() == git("show", f"{commit}:{path.relative_to(ROOT)}"),
                "V3_COVERPAGE_REVIEWED_FILE_CHANGED:" + path.name)
    wheel_provenance(deployment)
    historical = _installed(request, deployment)
    require(_targets(request) == historical["historical_table_ids"],
            "V3_COVERPAGE_HISTORICAL_TABLE_CHANGED")
    return request, deployment, historical


def predecessor_no_effect(request: dict, historical: dict) -> dict:
    """Sign immutable terminal-no-effect proof for v2, not a retry."""
    v1 = verified_document(ROOT, V1_NO_EFFECT, BASE / "trust")
    require(v1.get("schema") == "EDP_DAY6_V3_UPGRADE_CANARY_NO_EFFECT_V1"
            and v1.get("status") == "TERMINAL_NO_REMOTE_EFFECT"
            and v1.get("run_id") == predecessor.EXPECTED_OLD_RUN,
            "V3_COVERPAGE_FIRST_CANARY_NO_EFFECT_REQUIRED")
    approved = verified_document(ROOT, V2_APPROVAL, BASE / "trust")
    require(approved.get("schema") == "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1"
            and approved.get("status") == "APPROVED"
            and approved.get("request_sha256") == V2_REQUEST_SHA
            and approved.get("deployment_sha256") == V2_DEPLOYMENT_SHA
            and approved.get("wheel_sha256") == V2_WHEEL_SHA
            and approved.get("wheel_source_commit") ==
            "cafcd0ec7d5543672c0fc252669b24430333b85b"
            and approved.get("failed_canary_no_effect_sha256") == file_digest(V1_NO_EFFECT)
            and approved.get("standing_sha256") == STANDING_SHA,
            "V3_COVERPAGE_SECOND_APPROVAL_CHANGED")
    job_ledger = json.loads(V2_JOB_LEDGER.read_bytes())
    run_ledger = json.loads(V2_RUN_LEDGER.read_bytes())
    require(job_ledger.get("job_id") == V2_JOB_ID
            and job_ledger.get("approval_sha256") == file_digest(V2_APPROVAL)
            and run_ledger.get("job_id") == V2_JOB_ID
            and run_ledger.get("run_id") == V2_RUN_ID
            and run_ledger.get("approval_sha256") == file_digest(V2_APPROVAL),
            "V3_COVERPAGE_SECOND_CANARY_LEDGER_CHANGED")
    remote_job = admin_cli("jobs", "get", str(V2_JOB_ID))
    require(remote_job.get("run_as_user_name") == APP_ID
            and remote_job.get("job_id") == V2_JOB_ID,
            "V3_COVERPAGE_SECOND_JOB_IDENTITY_CHANGED")
    old_request = json.loads(V2_REQUEST.read_bytes())
    old_deployment = json.loads(V2_DEPLOYMENT.read_bytes())
    verify_saved_job(
        remote_job["settings"],
        wheel_path=old_deployment["artifact"]["workspace_target_proposed"],
        run_as={"service_principal_name": APP_ID},
        parameters=[
            "--request",
            "/Workspace/Shared/edp-lab/day6-c2000-v3-13f-fix-v1/request.readonly.json",
            "--request-sha256", V2_REQUEST_SHA,
            "--selection", "/Workspace/Shared/edp-lab/day6-c2000-v3/selection.json",
            "--negative-oracles",
            "/Workspace/Shared/edp-lab/day6-c2000-v3/negative-oracles.json",
        ],
    )
    require(old_request["selection"] == request["selection"]
            and old_request["new_v3_table_allowlist"] ==
            request["new_v3_table_allowlist"], "V3_COVERPAGE_SECOND_CANARY_SCOPE_CHANGED")
    observed = admin_cli("jobs", "get-run", str(V2_RUN_ID))
    require(observed.get("job_id") == V2_JOB_ID
            and observed.get("run_id") == V2_RUN_ID
            and observed.get("status", {}).get("state") == "TERMINATED"
            and observed.get("state", {}).get("result_state") == "FAILED"
            and len(observed.get("tasks", [])) == 1
            and observed["tasks"][0].get("run_id") == V2_TASK_ID,
            "V3_COVERPAGE_SECOND_CANARY_NOT_TERMINAL")
    output = admin_cli("jobs", "get-run-output", str(V2_TASK_ID))
    require("V3_C300_SELECTED_LEXICAL_CHANGED" in str(output.get("error", "")),
            "V3_COVERPAGE_SECOND_CANARY_FAILURE_REASON_CHANGED")
    require(_remote_digest(old_deployment["artifact"]["workspace_target_proposed"])
            == V2_WHEEL_SHA and _targets(request) ==
            historical["historical_table_ids"],
            "V3_COVERPAGE_SECOND_CANARY_HISTORICAL_CHANGED")
    for name in request["new_v3_table_allowlist"]:
        _service_target_absent(request["target_namespace"] + "." + name)
    if V2_NO_EFFECT.exists():
        proof = verified_document(ROOT, V2_NO_EFFECT, BASE / "trust")
    else:
        proof = {
            "schema": "EDP_DAY6_V3_UPGRADE_CANARY_NO_EFFECT_V1",
            "authority": "protected-verifier-v1",
            "status": "TERMINAL_NO_REMOTE_EFFECT",
            "job_id": V2_JOB_ID, "run_id": V2_RUN_ID, "task_run_id": V2_TASK_ID,
            "old_approval_sha256": file_digest(V2_APPROVAL),
            "old_wheel_sha256": V2_WHEEL_SHA,
            "prior_canary_no_effect_sha256": file_digest(V1_NO_EFFECT),
            "run_sha256": hashlib.sha256(canonical(observed)).hexdigest(),
            "task_output_sha256": hashlib.sha256(canonical(output)).hexdigest(),
            "absent_targets": request["new_v3_table_allowlist"],
            "historical_table_ids": historical["historical_table_ids"],
            "verified_at_utc": datetime.now(UTC).isoformat(),
        }
        _signed_once(proof, "verifier.pem", V2_NO_EFFECT)
    require(proof.get("schema") == "EDP_DAY6_V3_UPGRADE_CANARY_NO_EFFECT_V1"
            and proof.get("status") == "TERMINAL_NO_REMOTE_EFFECT"
            and proof.get("job_id") == V2_JOB_ID and proof.get("run_id") == V2_RUN_ID
            and proof.get("task_run_id") == V2_TASK_ID
            and proof.get("old_approval_sha256") == file_digest(V2_APPROVAL)
            and proof.get("old_wheel_sha256") == V2_WHEEL_SHA
            and proof.get("prior_canary_no_effect_sha256") == file_digest(V1_NO_EFFECT)
            and proof.get("absent_targets") == request["new_v3_table_allowlist"]
            and proof.get("historical_table_ids") == historical["historical_table_ids"]
            and proof.get("run_sha256") == hashlib.sha256(canonical(observed)).hexdigest()
            and proof.get("task_output_sha256") == hashlib.sha256(canonical(output)).hexdigest(),
            "V3_COVERPAGE_SIGNED_SECOND_NO_EFFECT_CHANGED")
    return proof


def approval(commit: str, request: dict, deployment: dict) -> dict:
    if UPGRADE_APPROVAL.exists():
        document = verified_document(ROOT, UPGRADE_APPROVAL, BASE / "trust")
    else:
        document = {
            "schema": "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1",
            "authority": "owner-v3-artifact-upgrade-v3",
            "status": "APPROVED",
            "reviewed_commit": commit,
            "request_sha256": CURRENT_REQUEST_SHA256,
            "deployment_sha256": file_digest(DEPLOYMENT),
            "wheel_sha256": WHEEL_SHA,
            "wheel_source_commit": WHEEL_SOURCE_COMMIT,
            "original_e2e_sha256": OLD_E2E_SHA,
            "standing_sha256": STANDING_SHA,
            "failed_canary_no_effect_sha256": file_digest(V2_NO_EFFECT),
            "previous_upgrade_approval_sha256": file_digest(V2_APPROVAL),
            "first_canary_no_effect_sha256": file_digest(V1_NO_EFFECT),
            "next_attempt": 2,
            "source_ids": request["selection"]["source_ids"],
            "table_allowlist": request["new_v3_table_allowlist"],
            "target_namespace": request["target_namespace"],
            "run_as": APP_ID,
            "canary_job_submissions_max": 1,
            "automatic_retries_max": 0,
            "approved_at_utc": datetime.now(UTC).isoformat(),
        }
        _signed_once(document, "owner.pem", UPGRADE_APPROVAL)
    require(document.get("schema") == "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1"
            and document.get("status") == "APPROVED"
            and document.get("reviewed_commit") == commit
            and document.get("request_sha256") == CURRENT_REQUEST_SHA256
            and document.get("deployment_sha256") == file_digest(DEPLOYMENT)
            and document.get("wheel_sha256") == WHEEL_SHA
            and document.get("wheel_source_commit") == WHEEL_SOURCE_COMMIT
            and document.get("failed_canary_no_effect_sha256") == file_digest(V2_NO_EFFECT)
            and document.get("previous_upgrade_approval_sha256") == file_digest(V2_APPROVAL)
            and document.get("first_canary_no_effect_sha256") == file_digest(V1_NO_EFFECT)
            and document.get("standing_sha256") == STANDING_SHA
            and document.get("next_attempt") == 2
            and document.get("run_as") == APP_ID
            and document.get("automatic_retries_max") == 0
            and document.get("canary_job_submissions_max") == 1,
            "V3_COVERPAGE_OWNER_APPROVAL_CHANGED")
    return document


def configure_distinct_canary() -> None:
    """Reuse reviewed fail-closed machinery under only new v3 identifiers."""
    predecessor.WHEEL_SHA = WHEEL_SHA
    predecessor.CURRENT_REQUEST_SHA256 = CURRENT_REQUEST_SHA256
    predecessor.REQUEST = REQUEST
    predecessor.DEPLOYMENT = DEPLOYMENT
    predecessor.UPGRADE_APPROVAL = UPGRADE_APPROVAL
    predecessor.E2E_READY = E2E_READY
    predecessor.OLD_CANARY_NO_EFFECT = V2_NO_EFFECT
    predecessor.NEW_REMOTE_DIR = REMOTE_DIR
    predecessor.NEW_REMOTE_REQUEST = REMOTE_REQUEST
    predecessor.NEW_JOB_NAME = JOB_NAME
    predecessor.NEW_JOB_RESERVATION = JOB_RESERVATION
    predecessor.NEW_JOB = JOB
    predecessor.NEW_RUN_RESERVATION = RUN_RESERVATION
    predecessor.NEW_RUN = RUN


def execute(commit: str) -> dict:
    require(os.geteuid() == 0, "V3_COVERPAGE_ROOT_TERMINAL_REQUIRED")
    request, deployment, historical = preflight(commit)
    os.environ["EDP_DAY6_V3_SERVICE_CONTEXT"] = "1"
    _workspace_access()
    predecessor_no_effect(request, historical)
    approval(commit, request, deployment)
    configure_distinct_canary()
    predecessor.upload_artifacts(deployment)
    predecessor.readiness(commit, request, deployment, historical)
    # No V3 data writes: service install follows successful independent canary.
    install_runtime(commit)
    for _ in range(30):
        try:
            report = socket_action("status")
            if (report.get("status") == "READY_FOR_DISTINCT_ATTEMPT"
                    and report.get("next_attempt") == 2
                    and report.get("e2e_sha256") == file_digest(E2E_READY)):
                break
        except (RuntimeError, OSError, ValueError):
            pass
        time.sleep(1)
    else:
        raise RuntimeError("V3_COVERPAGE_PROTECTED_RUNTIME_NOT_READY")
    audit = socket_action("audit")
    require(audit.get("status") == "V3_UNATTENDED_ADMISSION_READS_VERIFIED"
            and audit.get("attempt_number") == 2
            and audit.get("checks_passed") == audit.get("checks_total") == 13,
            "V3_COVERPAGE_PROTECTED_AUDIT_NOT_READY")
    return {
        "status": "V3_UPGRADE_READY_FOR_DISTINCT_ATTEMPT_2",
        "reviewed_commit": commit,
        "wheel_sha256": WHEEL_SHA,
        "e2e_sha256": file_digest(E2E_READY),
        "audit_checks_passed": audit["checks_passed"],
        "v3_run_submitted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reviewed_commit")
    args = parser.parse_args()
    print(json.dumps(execute(args.reviewed_commit), sort_keys=True))


if __name__ == "__main__":
    main()
