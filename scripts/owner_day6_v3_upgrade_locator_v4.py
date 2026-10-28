"""Owner-controlled V4 locator canary; no V3 data write or prior-canary replay.

Run only from the reviewed, clean commit in the protected Owner terminal. The
two existing signatures are verified before any remote action. A missing run
ledger after reservation is an uncertain submission and stops this workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import owner_day6_v3_upgrade_13f as canary
from owner_day6_v3_authorize_locator_v4 import (
    APPROVAL,
    DEPLOYMENT,
    E2E,
    NO_EFFECT,
    REQUEST,
    STANDING,
    WHEEL_SHA,
    git,
)
from owner_day6_v3_one_shot import APP_ID, BASE, ROOT, _remote_digest, _signed_once, require
from owner_day6_v3_upgrade_edgar import OLD_E2E_SHA, STANDING_SHA, verify_canary

from edp_lab.operating.authority import canonical, file_digest, verified_document

APPROVED_COMMIT = "a2ff6b436e10708f18a58d55c681bc1b6166ae1b"
NO_EFFECT_SHA = "f51736e5bf2eabaad934ec613410b9d7a1d00e5791dbd43a4079dabbe8ff9fc1"
APPROVAL_SHA = "b0505cf64ad36cf518a98185159547e68bb16d0ec94bde9e63f5d8a063676db8"
REQUEST_SHA = "137e24ca672b68223b7609155c5c124d49393ec183eb96534589b7980bef025f"
REMOTE_DIR = "/Workspace/Shared/edp-lab/day6-c2000-v3-edgar-locator-fix-v4"
REMOTE_REQUEST = REMOTE_DIR + "/request.readonly.json"
JOB_NAME = "day6-v3-edgar-locator-v4-readonly-canary"
JOB_RESERVATION = BASE / "ledger/day6-v3-locator-canary-job-reservation-v4.json"
JOB = BASE / "ledger/day6-v3-locator-canary-job-v4.json"
RUN_RESERVATION = BASE / "ledger/day6-v3-locator-canary-run-reservation-v4.json"
RUN = BASE / "ledger/day6-v3-locator-canary-run-v4.json"
E2E_READY = BASE / "receipts/day6-v3-e2e-ready-edgar-locator-v4.signed.json"


def verify_gate() -> tuple[dict, dict]:
    """Check signed protected evidence and the original reviewed artifact pins."""
    require(os.geteuid() == 0, "V4_OWNER_ROOT_REQUIRED")
    require(file_digest(NO_EFFECT) == NO_EFFECT_SHA
            and file_digest(APPROVAL) == APPROVAL_SHA,
            "V4_PROTECTED_RECEIPT_SHA_CHANGED")
    no_effect = verified_document(ROOT, NO_EFFECT, BASE / "trust")
    approval = verified_document(ROOT, APPROVAL, BASE / "trust")
    require(no_effect.get("schema") == "EDP_DAY6_V3_CANARY_3_NO_EFFECT_V1"
            and no_effect.get("authority") == "protected-verifier-v1"
            and no_effect.get("status") == "TERMINAL_NO_REMOTE_EFFECT"
            and no_effect.get("job_id") == 389618471873606
            and no_effect.get("run_id") == 588435072660254
            and no_effect.get("task_id") == 105664983922870
            and no_effect.get("target_absent_count") == 23
            and no_effect.get("read_only_parameters_verified") is True,
            "V4_SIGNED_NO_EFFECT_SCOPE_CHANGED")
    require(approval.get("schema") == "EDP_DAY6_V3_ARTIFACT_UPGRADE_V4"
            and approval.get("authority") == "owner-v3-artifact-upgrade-v4"
            and approval.get("status") == "APPROVED"
            and approval.get("reviewed_commit") == APPROVED_COMMIT
            and approval.get("canary_3_no_effect_sha256") == NO_EFFECT_SHA
            and approval.get("request_sha256") == REQUEST_SHA
            and approval.get("wheel_sha256") == WHEEL_SHA
            and approval.get("allowed_operation") ==
            "DISTINCT_READ_ONLY_CANARY_V4_THEN_EXISTING_SCOPE_V3"
            and approval.get("canary_job_submissions_max") == 1
            and approval.get("automatic_retries_max") == 0
            and approval.get("standing_sha256") == STANDING_SHA
            and approval.get("prior_e2e_sha256") == OLD_E2E_SHA,
            "V4_SIGNED_APPROVAL_SCOPE_CHANGED")
    require(file_digest(STANDING) == STANDING_SHA
            and file_digest(E2E) == OLD_E2E_SHA,
            "V4_INSTALLED_STANDING_OR_E2E_CHANGED")
    for path in (REQUEST, DEPLOYMENT):
        require(path.read_bytes() == git("show", f"{APPROVED_COMMIT}:{path.relative_to(ROOT)}"),
                "V4_APPROVED_COMMIT_PIN_CHANGED:" + path.name)
    request = json.loads(REQUEST.read_bytes())
    deployment = json.loads(DEPLOYMENT.read_bytes())
    require(file_digest(REQUEST) == REQUEST_SHA
            and file_digest(DEPLOYMENT) == approval.get("deployment_sha256")
            and deployment["artifact"]["sha256"] == WHEEL_SHA
            and file_digest(Path(deployment["artifact"]["local_build_output_uncommitted"]))
            == WHEEL_SHA
            and deployment["artifact"]["workspace_target_proposed"] ==
            REMOTE_DIR + "/edp_lab-0.1.0-py3-none-any.whl"
            and request["target_namespace"] == approval.get("target_namespace")
            and request["selection"]["source_ids"] == approval.get("source_ids")
            and request["new_v3_table_allowlist"] == approval.get("table_allowlist"),
            "V4_APPROVED_REQUEST_OR_WHEEL_CHANGED")
    return request, deployment


def configure_canary() -> None:
    """Bind existing one-shot machinery to new V4 identities only."""
    canary.WHEEL_SHA = WHEEL_SHA
    canary.CURRENT_REQUEST_SHA256 = REQUEST_SHA
    canary.REQUEST = REQUEST
    canary.DEPLOYMENT = DEPLOYMENT
    canary.UPGRADE_APPROVAL = APPROVAL
    canary.NEW_REMOTE_DIR = REMOTE_DIR
    canary.NEW_REMOTE_REQUEST = REMOTE_REQUEST
    canary.NEW_JOB_NAME = JOB_NAME
    canary.NEW_JOB_RESERVATION = JOB_RESERVATION
    canary.NEW_JOB = JOB
    canary.NEW_RUN_RESERVATION = RUN_RESERVATION
    canary.NEW_RUN = RUN
    require("--execute" not in canary.canary_parameters()
            and "--v0a-smoke" not in canary.canary_parameters(),
            "V4_CANARY_PARAMETERS_NOT_READ_ONLY")


def run_canary(reviewed_commit: str) -> dict:
    """Called only after a separate Owner review of this continuation code."""
    from owner_day6_v3_one_shot import _owner, _targets, _workspace_access

    _owner(reviewed_commit)
    request, deployment = verify_gate()
    os.environ["EDP_DAY6_V3_SERVICE_CONTEXT"] = "1"
    _workspace_access()
    historical = verified_document(ROOT, BASE / "receipts/day6-v3-install-v1.signed.json",
                                   BASE / "trust")
    require(_targets(request) == historical.get("historical_table_ids"),
            "V4_HISTORICAL_DELTA_CHANGED")
    configure_canary()
    canary.upload_artifacts(deployment)
    require(_remote_digest(REMOTE_REQUEST) == REQUEST_SHA
            and _remote_digest(deployment["artifact"]["workspace_target_proposed"])
            == WHEEL_SHA, "V4_REMOTE_ARTIFACT_CHANGED")
    if E2E_READY.exists():
        ready = verified_document(ROOT, E2E_READY, BASE / "trust")
    else:
        job_id = canary.ensure_job(deployment)
        run_id = canary.ensure_run(job_id)
        observed = verify_canary(request, job_id, run_id, historical)
        baseline = verified_document(ROOT, E2E, BASE / "trust")
        require(baseline.get("status") == "VERIFIED"
                and baseline.get("isolated_persisted_readback") is True
                and baseline.get("smoke_terminal_state") == "SUCCESS",
                "V4_ORIGINAL_PERSISTED_SMOKE_INVALID")
        ready = {
            "schema": "EDP_VAULT_E2E_UPGRADE_V1",
            "authority": "protected-verifier-v1",
            "status": "VERIFIED",
            "approval_sha256": APPROVAL_SHA,
            "no_effect_sha256": NO_EFFECT_SHA,
            "original_e2e_sha256": OLD_E2E_SHA,
            "standing_sha256": STANDING_SHA,
            "request_sha256": REQUEST_SHA,
            "deployment_sha256": file_digest(DEPLOYMENT),
            "wheel_sha256": WHEEL_SHA,
            "installed_reviewed_commit": reviewed_commit,
            "run_as": APP_ID,
            "environment_version": "4",
            "target_namespace": request["target_namespace"],
            "canary_terminal_state": "SUCCESS",
            "read_only_new_wheel_verified": True,
            "isolated_persisted_readback_reused": True,
            "signed_readback_sha256": hashlib.sha256(canonical(observed)).hexdigest(),
            "effective_uc_access_verified": True,
            "workspace_access_verified": True,
            "canary": observed,
            "verified_at_utc": datetime.now(UTC).isoformat(),
        }
        _signed_once(ready, "verifier.pem", E2E_READY)
    require(ready.get("schema") == "EDP_VAULT_E2E_UPGRADE_V1"
            and ready.get("status") == "VERIFIED"
            and ready.get("approval_sha256") == APPROVAL_SHA
            and ready.get("no_effect_sha256") == NO_EFFECT_SHA
            and ready.get("original_e2e_sha256") == OLD_E2E_SHA
            and ready.get("standing_sha256") == STANDING_SHA
            and ready.get("request_sha256") == REQUEST_SHA
            and ready.get("deployment_sha256") == file_digest(DEPLOYMENT)
            and ready.get("wheel_sha256") == WHEEL_SHA
            and ready.get("installed_reviewed_commit") == reviewed_commit
            and ready.get("run_as") == APP_ID
            and ready.get("canary_terminal_state") == "SUCCESS"
            and ready.get("canary", {}).get("canary_24_negatives") is True,
            "V4_SIGNED_E2E_CHANGED")
    return {"status": "V4_CANARY_E2E_READY", "receipt_sha256": file_digest(E2E_READY),
            "job_id": ready["canary"]["canary_job_id"],
            "run_id": ready["canary"]["canary_run_id"], "v3_run_submitted": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("verify-gate", "run-canary"))
    parser.add_argument("--reviewed-commit")
    args = parser.parse_args()
    if args.action == "verify-gate":
        request, deployment = verify_gate()
        result = {"status": "V4_GATE_VERIFIED", "request_sha256": file_digest(REQUEST),
                  "wheel_sha256": deployment["artifact"]["sha256"],
                  "source_count": len(request["selection"]["source_ids"])}
    else:
        require(bool(args.reviewed_commit), "V4_REVIEWED_COMMIT_REQUIRED")
        result = run_canary(args.reviewed_commit)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
