"""Owner Terminal only: distinct V3 one-shot after signed original PARTIAL.

The original Job, grant, request, reservation and submission remain immutable.
This creates a separate exact Job/grant and permits one new submission only
after Owner authorization and current protected readback. It never replays the
original Job or changes approved semantic/data artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta

from owner_day6_v3_one_shot import (
    APP_ID,
    BASE,
    CURRENT_REQUEST_SHA256,
    GRANT,
    INSTALL,
    ORIGINAL_ACTIVE_REQUEST_SHA256,
    REQUEST,
    ROOT,
    SERVICE_PRINCIPAL_ID,
    _installed,
    _job_settings,
    _owner,
    _pins,
    _remote_digest,
    _signed_once,
    _source_rights,
    _targets,
    _upload,
    _workspace_absent,
    _workspace_access,
    _write_once,
    require,
)
from owner_reconcile_day6_v3_partial import (
    JOB_ID as ORIGINAL_JOB_ID,
)
from owner_reconcile_day6_v3_partial import (
    RECEIPT as PARTIAL_RECEIPT,
)
from owner_reconcile_day6_v3_partial import (
    RUN_ID as ORIGINAL_RUN_ID,
)
from owner_reconcile_day6_v3_partial import (
    _original_ledger,
)
from owner_setup_day6_vault_0a import admin_cli

from edp_lab.operating.authority import canonical, file_digest, verified_document
from edp_lab.vault.v3_one_shot_gate import verify_saved_job

GRANT_ID = "day6-c2000-v3-distinct-20261025-v1"
REMOTE_DIR = "/Workspace/Shared/edp-lab/day6-c2000-v3-distinct"
REMOTE_REQUEST = REMOTE_DIR + "/request.granted.json"
DERIVED = BASE / "private/day6-v3-distinct-request.granted.json"
SUCCESSOR_INSTALL = BASE / "receipts/day6-v3-distinct-install-v1.signed.json"
SUCCESSOR_GRANT = BASE / "grants/day6-v3-distinct-one-shot-v1.signed.json"
RESERVATION = BASE / "ledger/day6-v3-distinct-one-shot-v1.json"
SUBMISSION = BASE / "ledger/day6-v3-distinct-one-shot-submission-v1.json"
STANDING = BASE / "trust/day6-v3-standing-v1.signed.json"
# Upgrade receipt is additive; original readiness and signed attempt history stay intact.
E2E_READY = BASE / "receipts/day6-v3-e2e-ready-coverpage-fix-v3.signed.json"
HISTORICAL_E2E = BASE / "receipts/day6-v3-e2e-ready-v1.signed.json"
UPGRADE_APPROVAL = BASE / "approvals/day6-v3-coverpage-fix-upgrade-v3.signed.json"


def configure_attempt(number: int) -> None:
    """Select a separate protected identity; the service controls the number."""
    global GRANT_ID, REMOTE_DIR, REMOTE_REQUEST, DERIVED
    global SUCCESSOR_INSTALL, SUCCESSOR_GRANT, RESERVATION, SUBMISSION
    require(type(number) is int and 1 <= number <= 10000000,
            "V3_ATTEMPT_NUMBER_OUT_OF_SCOPE")
    GRANT_ID = f"day6-c2000-v3-distinct-20261025-v{number}"
    REMOTE_DIR = f"/Workspace/Shared/edp-lab/day6-c2000-v3-distinct-{number}"
    REMOTE_REQUEST = REMOTE_DIR + "/request.granted.json"
    DERIVED = BASE / f"private/day6-v3-distinct-{number}-request.granted.json"
    SUCCESSOR_INSTALL = BASE / f"receipts/day6-v3-distinct-{number}-install.signed.json"
    SUCCESSOR_GRANT = BASE / f"grants/day6-v3-distinct-{number}-grant.signed.json"
    RESERVATION = BASE / f"ledger/day6-v3-distinct-{number}-reservation.json"
    SUBMISSION = BASE / f"ledger/day6-v3-distinct-{number}-submission.json"


def _admission(request: dict, deployment: dict) -> None:
    """Require installed standing scope and an independently signed live smoke."""
    standing = verified_document(ROOT, STANDING, BASE / "trust")
    ready = verified_document(ROOT, E2E_READY, BASE / "trust")
    approval = verified_document(ROOT, UPGRADE_APPROVAL, BASE / "trust")
    require(standing.get("schema") == "EDP_DAY6_V3_STANDING_AUTHORIZATION_V1"
            and standing.get("status") == "INSTALLED"
            and standing.get("request_sha256") == ORIGINAL_ACTIVE_REQUEST_SHA256
            and standing.get("job_submissions_max") == 10000000
            and standing.get("runtime_seconds_max") == 3600
            and standing.get("run_as") == APP_ID
            and standing.get("target_namespace") == request["target_namespace"]
            and standing.get("source_ids") == request["selection"]["source_ids"]
            and standing.get("table_allowlist") == request["new_v3_table_allowlist"]
            and standing.get("distinct_no_effect_recovery_allowed") is True,
            "V3_INSTALLED_STANDING_AUTHORITY_REQUIRED")
    require(approval.get("schema") == "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1"
            and approval.get("status") == "APPROVED"
            and approval.get("request_sha256") == CURRENT_REQUEST_SHA256
            and approval.get("wheel_sha256") == deployment["artifact"]["sha256"]
            and approval.get("original_e2e_sha256") == file_digest(HISTORICAL_E2E)
            and approval.get("standing_sha256") == file_digest(STANDING)
            and approval.get("failed_canary_no_effect_sha256") ==
            file_digest(BASE / "receipts/day6-v3-13f-canary-2-no-effect.signed.json"),

            "V3_UPGRADE_OWNER_APPROVAL_REQUIRED")
    require(ready.get("schema") == "EDP_VAULT_E2E_UPGRADE_V1"
            and ready.get("status") == "VERIFIED"
            and ready.get("approval_sha256") == file_digest(UPGRADE_APPROVAL)
            and ready.get("original_e2e_sha256") == file_digest(HISTORICAL_E2E)
            and ready.get("standing_sha256") == file_digest(STANDING)
            and ready.get("request_sha256") == CURRENT_REQUEST_SHA256
            and ready.get("run_as") == APP_ID
            and ready.get("wheel_sha256") == deployment["artifact"]["sha256"]
            and ready.get("environment_version") == "4"
            and ready.get("target_namespace") == request["target_namespace"]
            and ready.get("canary_terminal_state") == "SUCCESS"
            and ready.get("isolated_persisted_readback_reused") is True
            and ready.get("read_only_new_wheel_verified") is True
            and ready.get("signed_readback_sha256")
            and ready.get("workspace_access_verified") is True
            and ready.get("effective_uc_access_verified") is True,
            "V3_SIGNED_E2E_READINESS_REQUIRED")


def _partial() -> dict:
    _original_ledger()
    proof = verified_document(ROOT, PARTIAL_RECEIPT, BASE / "trust")
    require(proof.get("schema") == "EDP_DAY6_V3_ONE_SHOT_PARTIAL_FAILURE_RECEIPT_V1"
            and proof.get("status") == "PARTIAL_RECONCILE_AND_STOP"
            and proof.get("original_job_id") == ORIGINAL_JOB_ID
            and proof.get("original_run_id") == ORIGINAL_RUN_ID
            and proof.get("v3_pass") is False
            and proof.get("submission_allowance_remaining") == 0
            and proof.get("grant_sha256") == file_digest(GRANT)
            and proof.get("install_receipt_sha256") == file_digest(INSTALL),
            "V3_ORIGINAL_SIGNED_PARTIAL_REQUIRED")
    return proof


def _parameters(derived_sha: str) -> list[str]:
    return ["--request", REMOTE_REQUEST, "--request-sha256", derived_sha,
            "--selection", "/Workspace/Shared/edp-lab/day6-c2000-v3/selection.json",
            "--negative-oracles",
            "/Workspace/Shared/edp-lab/day6-c2000-v3/negative-oracles.json",
            "--execute"]


def _settings(derived_sha: str, deployment: dict) -> dict:
    saved = _job_settings(derived_sha, deployment)
    saved["name"] = "day6-c2000-v3-" + GRANT_ID
    saved["tasks"][0]["python_wheel_task"]["parameters"] = _parameters(derived_sha)
    return saved


def _readback_job(job_id: int, derived_sha: str, deployment: dict) -> None:
    saved = admin_cli("jobs", "get", str(job_id))
    require(saved.get("job_id") == job_id and saved.get("run_as_user_name") == APP_ID,
            "V3_DISTINCT_JOB_IDENTITY_CHANGED")
    verify_saved_job(saved["settings"],
                     wheel_path=deployment["artifact"]["workspace_target_proposed"],
                     run_as={"service_principal_name": APP_ID},
                     parameters=_parameters(derived_sha))


def entitle(expected_commit: str) -> dict:
    """Owner-authorized addition of only the missing Jobs Workspace entitlement."""
    _owner(expected_commit)
    _partial()
    identity = admin_cli("service-principals", "get", SERVICE_PRINCIPAL_ID)
    require(identity.get("applicationId") == APP_ID and identity.get("active") is True,
            "V3_RUN_AS_PRINCIPAL_CHANGED")
    assignment = admin_cli("workspace-iam-v2", "get-workspace-assignment-proxy",
                           SERVICE_PRINCIPAL_ID)
    access = admin_cli("workspace-iam-v2", "get-workspace-access-detail-local",
                       SERVICE_PRINCIPAL_ID)
    require(str(assignment.get("principal_id")) == SERVICE_PRINCIPAL_ID
            and assignment.get("principal_type") == "SERVICE_PRINCIPAL"
            and access.get("status") == "ACTIVE"
            and access.get("access_type") == "DIRECT",
            "V3_RUN_AS_WORKSPACE_ASSIGNMENT_CHANGED")
    effective = assignment.get("effective_entitlements")
    direct = assignment.get("entitlements")
    require(isinstance(effective, list) and isinstance(direct, list),
            "V3_RUN_AS_ENTITLEMENTS_UNVERIFIED")
    if "WORKSPACE_ACCESS" not in effective:
        require(set(effective) == {"DATABRICKS_SQL_ACCESS"}
                and set(direct) == {"DATABRICKS_SQL_ACCESS"},
                "V3_RUN_AS_ENTITLEMENT_SCOPE_CHANGED")
        admin_cli("workspace-iam-v2", "update-workspace-assignment-proxy",
                  SERVICE_PRINCIPAL_ID, "entitlements",
                  "--json", json.dumps({
                      "principal_id": int(SERVICE_PRINCIPAL_ID),
                      "entitlements": ["DATABRICKS_SQL_ACCESS", "WORKSPACE_ACCESS"]}),
                  allow_empty=True)
    _workspace_access()
    observed = admin_cli("workspace-iam-v2", "get-workspace-assignment-proxy",
                         SERVICE_PRINCIPAL_ID)
    require("WORKSPACE_ACCESS" in observed.get("effective_entitlements", []),
            "V3_RUN_AS_WORKSPACE_ACCESS_NOT_INSTALLED")
    return {"status": "V3_RUN_AS_WORKSPACE_ACCESS_READY",
            "principal_id": SERVICE_PRINCIPAL_ID,
            "effective_entitlements": sorted(observed["effective_entitlements"])}


def authorize(expected_commit: str) -> dict:
    """Owner approval boundary: install a distinct Job and signed one-shot grant."""
    _owner(expected_commit)
    request, deployment = _pins()
    partial = _partial()
    _admission(request, deployment)
    original = _installed(request, deployment)
    require(original["job_id"] == ORIGINAL_JOB_ID,
            "V3_ORIGINAL_INSTALLED_JOB_CHANGED")
    _workspace_access()
    _source_rights()
    require(_remote_digest(deployment["artifact"]["workspace_target_proposed"])
            == deployment["artifact"]["sha256"], "V3_DEPLOYED_WHEEL_CHANGED")
    baseline = _targets(request)
    require(baseline == original["historical_table_ids"],
            "V3_HISTORICAL_BASELINE_CHANGED")
    require(not any(path.exists() for path in
                    (DERIVED, SUCCESSOR_INSTALL, SUCCESSOR_GRANT, RESERVATION, SUBMISSION)),
            "V3_DISTINCT_OPERATION_ALREADY_STARTED")
    _workspace_absent(REMOTE_REQUEST)
    derived = json.loads(REQUEST.read_bytes())
    derived["execution"]["protected_grant_id"] = GRANT_ID
    _write_once(DERIVED, derived)
    admin_cli("workspace", "mkdirs", REMOTE_DIR, allow_empty=True)
    _upload(DERIVED, REMOTE_REQUEST)
    derived_sha = file_digest(DERIVED)
    created = admin_cli("jobs", "create", "--json",
                        json.dumps(_settings(derived_sha, deployment)))
    job_id = created.get("job_id") if isinstance(created, dict) else None
    require(type(job_id) is int and job_id > 0 and job_id != ORIGINAL_JOB_ID,
            "V3_DISTINCT_JOB_CREATE_UNCERTAIN_STOP")
    _readback_job(job_id, derived_sha, deployment)
    require(_targets(request) == baseline, "V3_DISTINCT_TARGET_SET_CHANGED")
    install = {"schema": "EDP_DAY6_V3_DISTINCT_INSTALL_RECEIPT_V1",
               "authority": "protected-verifier-v1", "status": "INSTALLED_NOT_SUBMITTED",
               "job_id": job_id, "original_job_id": ORIGINAL_JOB_ID,
               "original_partial_receipt_sha256": file_digest(PARTIAL_RECEIPT),
               "original_grant_sha256": file_digest(GRANT),
               "reviewed_commit": expected_commit,
               "request_sha256": file_digest(REQUEST),
               "derived_request_sha256": derived_sha,
               "wheel_sha256": deployment["artifact"]["sha256"],
               "run_as": APP_ID, "historical_table_ids": baseline,
               "installed_at_utc": datetime.now(UTC).isoformat()}
    _signed_once(install, "verifier.pem", SUCCESSOR_INSTALL)
    now = datetime.now(UTC)
    grant = {"schema": "EDP_DAY6_V3_DISTINCT_ONE_SHOT_GRANT_V1",
             "authority": "owner-v3-one-shot-v1", "status": "ISSUED_NOT_SUBMITTED",
             "grant_id": GRANT_ID, "job_id": job_id,
             "install_receipt_sha256": file_digest(SUCCESSOR_INSTALL),
             "original_partial_receipt_sha256": file_digest(PARTIAL_RECEIPT),
             "original_job_id": ORIGINAL_JOB_ID,
             "original_run_id": ORIGINAL_RUN_ID,
             "original_grant_sha256": file_digest(GRANT),
             "request_sha256": file_digest(REQUEST),
             "derived_request_sha256": derived_sha,
             "selection_sha256": request["selection"]["sha256"],
             "negative_oracles_sha256": request["negative_oracles"]["sha256"],
             "ddl_sha256": request["target_ddl"]["sha256"],
             "wheel_sha256": deployment["artifact"]["sha256"],
             "run_as": APP_ID, "tables": request["new_v3_table_allowlist"],
             "job_submissions_max": 1, "runtime_seconds_max": 3600,
             "automatic_retries_max": 0,
             "issued_at_utc": now.isoformat(),
             "expires_at_utc": (now + timedelta(hours=1)).isoformat()}
    _signed_once(grant, "owner.pem", SUCCESSOR_GRANT)
    return {"status": "V3_DISTINCT_GRANT_ISSUED_NOT_SUBMITTED",
            "job_id": job_id, "grant_sha256": file_digest(SUCCESSOR_GRANT),
            "original_partial_receipt_sha256": file_digest(PARTIAL_RECEIPT),
            "original_terminal_result": partial["terminal_result"]}


def execute(expected_commit: str) -> dict:
    """Submit exactly once under the separately signed distinct grant."""
    _owner(expected_commit)
    request, deployment = _pins()
    _partial()
    _admission(request, deployment)
    original = _installed(request, deployment)
    install = verified_document(ROOT, SUCCESSOR_INSTALL, BASE / "trust")
    grant = verified_document(ROOT, SUCCESSOR_GRANT, BASE / "trust")
    require(original["job_id"] == ORIGINAL_JOB_ID
            and install.get("schema") == "EDP_DAY6_V3_DISTINCT_INSTALL_RECEIPT_V1"
            and install.get("reviewed_commit") == expected_commit
            and install.get("original_partial_receipt_sha256") == file_digest(PARTIAL_RECEIPT)
            and install.get("request_sha256") == file_digest(REQUEST)
            and install.get("derived_request_sha256") == file_digest(DERIVED)
            and install.get("run_as") == APP_ID
            and install.get("historical_table_ids") == original["historical_table_ids"]
            and grant.get("schema") == "EDP_DAY6_V3_DISTINCT_ONE_SHOT_GRANT_V1"
            and grant.get("grant_id") == GRANT_ID
            and grant.get("status") == "ISSUED_NOT_SUBMITTED"
            and grant.get("job_id") == install.get("job_id")
            and grant.get("install_receipt_sha256") == file_digest(SUCCESSOR_INSTALL)
            and grant.get("original_partial_receipt_sha256") == file_digest(PARTIAL_RECEIPT)
            and grant.get("original_job_id") == ORIGINAL_JOB_ID
            and grant.get("original_run_id") == ORIGINAL_RUN_ID
            and grant.get("original_grant_sha256") == file_digest(GRANT)
            and grant.get("request_sha256") == file_digest(REQUEST)
            and grant.get("derived_request_sha256") == file_digest(DERIVED)
            and grant.get("selection_sha256") == request["selection"]["sha256"]
            and grant.get("negative_oracles_sha256") == request["negative_oracles"]["sha256"]
            and grant.get("ddl_sha256") == request["target_ddl"]["sha256"]
            and grant.get("wheel_sha256") == deployment["artifact"]["sha256"]
            and grant.get("run_as") == APP_ID
            and grant.get("tables") == request["new_v3_table_allowlist"]
            and grant.get("job_submissions_max") == 1
            and grant.get("automatic_retries_max") == 0,
            "V3_DISTINCT_EXACT_GRANT_CHANGED")
    require(datetime.fromisoformat(grant["issued_at_utc"]) <= datetime.now(UTC)
            < datetime.fromisoformat(grant["expires_at_utc"]),
            "V3_DISTINCT_GRANT_EXPIRED")
    _workspace_access()
    _source_rights()
    require(_remote_digest(REMOTE_REQUEST) == file_digest(DERIVED),
            "V3_DISTINCT_DEPLOYED_REQUEST_CHANGED")
    _readback_job(install["job_id"], file_digest(DERIVED), deployment)
    require(_targets(request) == original["historical_table_ids"],
            "V3_DISTINCT_TARGET_SET_CHANGED")
    require(not RESERVATION.exists() and not SUBMISSION.exists(),
            "V3_DISTINCT_SUBMISSION_ALREADY_RESERVED")
    _write_once(RESERVATION, {
        "schema": "EDP_DAY6_V3_DISTINCT_ONE_SHOT_LEDGER_V1",
        "status": "UNCERTAIN_REQUIRES_READBACK",
        "grant_sha256": file_digest(SUCCESSOR_GRANT),
        "request_sha256": file_digest(DERIVED),
        "original_partial_receipt_sha256": file_digest(PARTIAL_RECEIPT),
        "job_id": install["job_id"],
        "reserved_at_utc": datetime.now(UTC).isoformat(),
    })
    try:
        response = admin_cli("jobs", "run-now", str(install["job_id"]),
                             "--no-wait", "--idempotency-token",
                             hashlib.sha256(canonical(grant)).hexdigest()[:32])
        run_id = response.get("run_id")
        require(type(run_id) is int and run_id > 0,
                "V3_DISTINCT_RUN_ID_UNKNOWN")
        _write_once(SUBMISSION, {
            "status": "SUBMITTED_REQUIRES_READBACK", "run_id": run_id,
            "job_id": install["job_id"],
            "grant_sha256": file_digest(SUCCESSOR_GRANT),
            "submitted_at_utc": datetime.now(UTC).isoformat(),
        })
    except (OSError, ValueError, TypeError, KeyError, RuntimeError,
            subprocess.CalledProcessError):
        return {"status": "UNCERTAIN_REQUIRES_READBACK",
                "job_id": install["job_id"],
                "reservation_path": str(RESERVATION)}
    return {"status": "SUBMITTED_REQUIRES_INDEPENDENT_SIGNED_READBACK",
            "job_id": install["job_id"], "run_id": run_id}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("entitle", "authorize", "execute"))
    parser.add_argument("expected_commit")
    args = parser.parse_args()
    print(json.dumps({"entitle": entitle, "authorize": authorize,
                      "execute": execute}[args.action](
        args.expected_commit), sort_keys=True))


if __name__ == "__main__":
    main()
