"""Owner-only, additive Day 6 V3 EDGAR artifact upgrade.

The old standing policy, original signed E2E, attempts, grants, ledger entries,
and historical Delta tables are immutable. This script is never agent-callable.
It authorizes exactly one separately pinned read-only Spark canary using the
new wheel and only then installs the reviewed successor protected code. A
reserved but unknown external mutation blocks replay until manual reconciliation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from owner_day6_v3_one_shot import (
    APP_ID,
    BASE,
    CURRENT_REQUEST_SHA256,
    DEPLOYMENT,
    ORIGINAL_ACTIVE_REQUEST_SHA256,
    ORIGINAL_ACTIVE_REQUEST,
    ORIGINAL_ACTIVE_DEPLOYMENT,
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
    _workspace_access,
    require,
)
from owner_day6_v3_successor import (
    E2E_READY,
    HISTORICAL_E2E,
    STANDING,
    UPGRADE_APPROVAL,
)
from owner_setup_day6_vault_0a import admin_cli
from edp_lab.operating.authority import canonical, file_digest, verified_document
from edp_lab.vault.v3_one_shot_gate import verify_saved_job
from edp_lab.vault.v3_service import _service_target_absent

OLD_COMMIT = "9556295e1669fd53e258dacec80698e68222d385"
OLD_E2E_SHA = "bb3f92e332d8765753a2abe605eb6b0fb90ff4ae7031f068a9eef1f2fbdd9c05"
STANDING_SHA = "ce084d5be48bfc777d82216543f12547bd57b566962dec1d235ee7df38054bc0"
NEW_WHEEL_SHA = "fd2d890f5a57f2bf3596eb2f0275860b70f2ac4549d1aae549e818e202bda546"

UPGRADE_DIR = "/Workspace/Shared/edp-lab/day6-c2000-v3-edgar-fix-v1"
CANARY_REQUEST = UPGRADE_DIR + "/request.readonly.json"
CANARY_NAME = "day6-v3-edgar-fix-v1-readonly-canary"
CANARY_JOB_RESERVATION = BASE / "ledger/day6-v3-edgarfix-canary-job-reservation-v1.json"
CANARY_JOB = BASE / "ledger/day6-v3-edgarfix-canary-job-v1.json"
CANARY_RUN_RESERVATION = BASE / "ledger/day6-v3-edgarfix-canary-run-reservation-v1.json"
CANARY_RUN = BASE / "ledger/day6-v3-edgarfix-canary-run-v1.json"
LOCAL_MODULES = (
    "scripts/owner_day6_v3_one_shot.py",
    "scripts/owner_day6_v3_successor.py",
    "src/edp_lab/vault/v3_service.py",
)
RUNTIME = BASE / "runtime-v3"
PIN = BASE / "trust/day6-v3-installed-commit.txt"
SOCKET = BASE / "day6-v3.sock"
LABEL = "system/org.edp-lab.day6-v3-standing"
ORIGINAL_NO_EFFECT = BASE / "receipts/day6-v3-attempt-1-no-effect.signed.json"
ORIGINAL_SUBMISSION = BASE / "ledger/day6-v3-distinct-1-submission.json"


def git(*args: str) -> bytes:
    return subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT), *args],
        capture_output=True, check=True, timeout=60,
    ).stdout


def socket_action(action: str) -> dict:
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(600 if action == "audit" else 30)
        client.connect(str(SOCKET))
        client.sendall((json.dumps({"action": action}) + "\n").encode())
        client.shutdown(socket.SHUT_WR)
        data = bytearray()
        while chunk := client.recv(8192):
            data.extend(chunk)
            require(len(data) <= 100_000, "UPGRADE_SOCKET_RESPONSE_TOO_LARGE")
    return json.loads(data)


def preflight(commit: str) -> tuple[dict, dict, dict]:
    _owner(commit)
    require(git("rev-parse", "HEAD").decode().strip() == commit,
            "UPGRADE_UNREVIEWED_HEAD")
    request, deployment = _pins()
    require(request["execution"]["runtime_artifact_sha256"] == NEW_WHEEL_SHA
            and deployment["artifact"]["sha256"] == NEW_WHEEL_SHA
            and deployment["artifact"]["workspace_target_proposed"]
            == UPGRADE_DIR + "/edp_lab-0.1.0-py3-none-any.whl",
            "UPGRADE_PROPOSAL_NOT_EXACT")
    for path in (REQUEST, DEPLOYMENT, ORIGINAL_ACTIVE_REQUEST,
                 ORIGINAL_ACTIVE_DEPLOYMENT):
        require(path.read_bytes() == git("show", f"{commit}:{path.relative_to(ROOT)}"),
                "UPGRADE_REVIEWED_MANIFEST_CHANGED:" + path.name)
    require(file_digest(ORIGINAL_ACTIVE_REQUEST) == ORIGINAL_ACTIVE_REQUEST_SHA256
            and file_digest(HISTORICAL_E2E) == OLD_E2E_SHA
            and file_digest(STANDING) == STANDING_SHA,
            "UPGRADE_ORIGINAL_TRUST_CHANGED")
    signed_old = verified_document(ROOT, HISTORICAL_E2E, BASE / "trust")
    standing = verified_document(ROOT, STANDING, BASE / "trust")
    no_effect = verified_document(ROOT, ORIGINAL_NO_EFFECT, BASE / "trust")
    require(signed_old.get("status") == "VERIFIED"
            and signed_old.get("wheel_sha256") ==
            json.loads(ORIGINAL_ACTIVE_DEPLOYMENT.read_bytes())["artifact"]["sha256"]
            and standing.get("status") == "INSTALLED"
            and standing.get("request_sha256") == ORIGINAL_ACTIVE_REQUEST_SHA256
            and no_effect.get("status") == "TERMINAL_NO_REMOTE_EFFECT"
            and no_effect.get("attempt_number") == 1
            and no_effect.get("submission_sha256") == file_digest(ORIGINAL_SUBMISSION),
            "UPGRADE_SIGNED_ATTEMPT_ONE_NOT_RECOVERED")
    # Historical original installation remains the same; active new request
    # is checked against its frozen source/contract/table scope by _pins.
    historical = _installed(request, deployment)
    require(historical["historical_table_ids"] == _targets(request),
            "UPGRADE_HISTORICAL_IDS_CHANGED")
    require(PIN.is_file() and PIN.stat().st_uid == 0
            and PIN.read_text().strip() in {OLD_COMMIT, commit},
            "UPGRADE_INSTALLED_COMMIT_UNEXPECTED")
    return request, deployment, historical


def ensure_approval(request: dict, deployment: dict, commit: str) -> None:
    if UPGRADE_APPROVAL.exists():
        approval = verified_document(ROOT, UPGRADE_APPROVAL, BASE / "trust")
    else:
        before = socket_action("status")
        require(before.get("status") == "READY_FOR_DISTINCT_ATTEMPT"
                and before.get("next_attempt") == 2
                and before.get("standing_sha256") == STANDING_SHA
                and before.get("e2e_sha256") == OLD_E2E_SHA
                and PIN.read_text().strip() == OLD_COMMIT,
                "UPGRADE_ORIGINAL_CHECKPOINT_CHANGED")
        approval = {
            "schema": "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1",
            "authority": "owner-v3-artifact-upgrade-v1",
            "status": "APPROVED",
            "reviewed_commit": commit,
            "request_sha256": CURRENT_REQUEST_SHA256,
            "deployment_sha256": file_digest(DEPLOYMENT),
            "wheel_sha256": NEW_WHEEL_SHA,
            "standing_sha256": STANDING_SHA,
            "original_e2e_sha256": OLD_E2E_SHA,
            "original_commit": OLD_COMMIT,
            "next_attempt": 2,
            "allowed_operation": "READ_ONLY_CANARY_THEN_EXISTING_SCOPE_V3",
            "run_as": APP_ID,
            "target_namespace": request["target_namespace"],
            "source_ids": request["selection"]["source_ids"],
            "table_allowlist": request["new_v3_table_allowlist"],
            "canary_job_submissions_max": 1,
            "automatic_retries_max": 0,
            "issued_at_utc": datetime.now(UTC).isoformat(),
        }
        _signed_once(approval, "owner.pem", UPGRADE_APPROVAL)
    require(approval.get("schema") == "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1"
            and approval.get("status") == "APPROVED"
            and approval.get("reviewed_commit") == commit
            and approval.get("request_sha256") == CURRENT_REQUEST_SHA256
            and approval.get("deployment_sha256") == file_digest(DEPLOYMENT)
            and approval.get("wheel_sha256") == NEW_WHEEL_SHA
            and approval.get("original_e2e_sha256") == OLD_E2E_SHA
            and approval.get("standing_sha256") == STANDING_SHA
            and approval.get("next_attempt") == 2
            and approval.get("canary_job_submissions_max") == 1,
            "UPGRADE_OWNER_APPROVAL_CHANGED")


def canary_parameters() -> list[str]:
    request = json.loads(REQUEST.read_bytes())
    return ["--request", CANARY_REQUEST, "--request-sha256", file_digest(REQUEST),
            "--selection", "/Workspace/Shared/edp-lab/day6-c2000-v3/selection.json",
            "--negative-oracles",
            "/Workspace/Shared/edp-lab/day6-c2000-v3/negative-oracles.json"]


def ensure_remote(deployment: dict) -> None:
    wheel = Path(deployment["artifact"]["local_build_output_uncommitted"])
    remote = deployment["artifact"]["workspace_target_proposed"]
    require(file_digest(wheel) == NEW_WHEEL_SHA, "UPGRADE_WHEEL_LOCAL_CHANGED")
    original = json.loads(ORIGINAL_ACTIVE_DEPLOYMENT.read_bytes())
    require(_remote_digest(original["artifact"]["workspace_target_proposed"])
            == original["artifact"]["sha256"],
            "UPGRADE_ORIGINAL_REMOTE_WHEEL_CHANGED")
    admin_cli("workspace", "mkdirs", UPGRADE_DIR, allow_empty=True)
    for local, path in ((wheel, remote), (REQUEST, CANARY_REQUEST)):
        # An interrupted upload may exist; its exact bytes are adopted.
        try:
            observed = _remote_digest(path)
        except RuntimeError as error:
            if "RESOURCE_DOES_NOT_EXIST" not in str(error).upper() and (
                "PATH_NOT_FOUND" not in str(error).upper()
                and "DOES NOT EXIST" not in str(error).upper()):
                raise
            _upload(local, path)
        else:
            require(observed == file_digest(local),
                    "UPGRADE_EXISTING_WORKSPACE_ARTIFACT_CHANGED:" + path)
        require(_remote_digest(path) == file_digest(local),
                "UPGRADE_WORKSPACE_EXPORT_MISMATCH:" + path)


def ensure_canary_job(deployment: dict) -> int:
    if CANARY_JOB.exists():
        job_id = json.loads(CANARY_JOB.read_bytes())["job_id"]
    else:
        require(not CANARY_JOB_RESERVATION.exists(),
                "UPGRADE_CANARY_JOB_CREATE_UNCERTAIN_NO_REPLAY")
        jobs = admin_cli("jobs", "list")
        require(isinstance(jobs, list) and not any(
            job.get("settings", {}).get("name") == CANARY_NAME
            for job in jobs), "UPGRADE_CANARY_JOB_ALREADY_PRESENT")
        _write(CANARY_JOB_RESERVATION, {
            "request_sha256": CURRENT_REQUEST_SHA256,
            "approval_sha256": file_digest(UPGRADE_APPROVAL),
        })
        settings = _job_settings(CURRENT_REQUEST_SHA256, deployment)
        settings["name"] = CANARY_NAME
        settings["tasks"][0]["python_wheel_task"]["parameters"] = canary_parameters()
        reply = admin_cli("jobs", "create", "--json", json.dumps(settings))
        job_id = reply.get("job_id") if isinstance(reply, dict) else None
        require(type(job_id) is int and job_id > 0,
                "UPGRADE_CANARY_JOB_CREATE_UNCERTAIN_NO_REPLAY")
        _write(CANARY_JOB, {"job_id": job_id,
                            "approval_sha256": file_digest(UPGRADE_APPROVAL)})
    saved = admin_cli("jobs", "get", str(job_id))
    require(saved.get("job_id") == job_id
            and saved.get("run_as_user_name") == APP_ID,
            "UPGRADE_CANARY_JOB_RUNAS_CHANGED")
    verify_saved_job(
        saved["settings"],
        wheel_path=deployment["artifact"]["workspace_target_proposed"],
        run_as={"service_principal_name": APP_ID},
        parameters=canary_parameters(),
    )
    return job_id


def _write(path: Path, doc: dict) -> None:
    from owner_day6_v3_one_shot import _write_once
    _write_once(path, doc)


def ensure_canary_run(job_id: int) -> int:
    if CANARY_RUN.exists():
        record = json.loads(CANARY_RUN.read_bytes())
        require(record.get("job_id") == job_id
                and record.get("approval_sha256") == file_digest(UPGRADE_APPROVAL),
                "UPGRADE_CANARY_RUN_LEDGER_CHANGED")
        return record["run_id"]
    require(not CANARY_RUN_RESERVATION.exists(),
            "UPGRADE_CANARY_RUN_UNCERTAIN_NO_REPLAY")
    _write(CANARY_RUN_RESERVATION, {
        "job_id": job_id,
        "approval_sha256": file_digest(UPGRADE_APPROVAL),
        "status": "RESERVED_BEFORE_REMOTE_SUBMISSION",
    })
    idem = hashlib.sha256(canonical({
        "job_id": job_id, "approval": file_digest(UPGRADE_APPROVAL)
    })).hexdigest()[:32]
    reply = admin_cli("jobs", "run-now", str(job_id), "--no-wait",
                      "--idempotency-token", idem)
    run_id = reply.get("run_id") if isinstance(reply, dict) else None
    require(type(run_id) is int and run_id > 0,
            "UPGRADE_CANARY_RUN_ID_UNCERTAIN_NO_REPLAY")
    _write(CANARY_RUN, {"job_id": job_id, "run_id": run_id,
                        "approval_sha256": file_digest(UPGRADE_APPROVAL)})
    return run_id


def verify_canary(request: dict, job_id: int, run_id: int, historical: dict) -> dict:
    deadline = time.monotonic() + 3600
    while True:
        item = admin_cli("jobs", "get-run", str(run_id))
        require(item.get("job_id") == job_id and item.get("run_id") == run_id,
                "UPGRADE_CANARY_REMOTE_RUN_CHANGED")
        if item.get("status", {}).get("state") == "TERMINATED":
            break
        require(time.monotonic() < deadline, "UPGRADE_CANARY_TIMEOUT_RECONCILE")
        time.sleep(10)
    require(item.get("state", {}).get("result_state") == "SUCCESS"
            and len(item.get("tasks", [])) == 1
            and item["tasks"][0].get("attempt_number", 0) == 0,
            "UPGRADE_CANARY_TERMINAL_FAILURE")
    task_id = item["tasks"][0]["run_id"]
    output = admin_cli("jobs", "get-run-output", str(task_id))
    lines = [json.loads(line) for line in output.get("logs", "").splitlines()
             if line.startswith("{") and '"READ_ONLY_PREPARED"' in line]
    require(len(lines) == 1 and lines[0].get("status") == "READ_ONLY_PREPARED",
            "UPGRADE_READ_ONLY_CANARY_OUTPUT_UNAVAILABLE")
    candidate = lines[0]
    selection = json.loads((ROOT / request["selection"]["path"]).read_bytes())
    expected = {sid: sum(m["selected_data_rows"] for m in source["members"].values())
                for sid, source in selection["sources"].items()}
    counts = candidate.get("expected_table_rows")
    require(candidate.get("per_source") == expected
            and sum(expected.values()) == 2047
            and type(counts) is dict
            and set(counts) == set(request["new_v3_table_allowlist"])
            and all(type(n) is int and n >= 0 for n in counts.values())
            and len(candidate.get("isolated_negative_oracles_passed", [])) == 24,
            "UPGRADE_CANARY_SCOPE_OR_NEGATIVES_CHANGED")
    require(_targets(request) == historical["historical_table_ids"],
            "UPGRADE_CANARY_HISTORICAL_DELTA_CHANGED")
    for name in request["new_v3_table_allowlist"]:
        _service_target_absent(request["target_namespace"] + "." + name)
    return {
        "canary_job_id": job_id,
        "canary_run_id": run_id,
        "canary_task_id": task_id,
        "canary_per_source": expected,
        "canary_24_negatives": True,
        "canary_output_sha256": hashlib.sha256(canonical(output)).hexdigest(),
        "canary_run_sha256": hashlib.sha256(canonical(item)).hexdigest(),
    }


def readiness(request: dict, deployment: dict, historical: dict) -> None:
    if E2E_READY.exists():
        data = verified_document(ROOT, E2E_READY, BASE / "trust")
    else:
        ensure_remote(deployment)
        job_id = ensure_canary_job(deployment)
        run_id = ensure_canary_run(job_id)
        canary = verify_canary(request, job_id, run_id, historical)
        old = verified_document(ROOT, HISTORICAL_E2E, BASE / "trust")
        require(old.get("status") == "VERIFIED"
                and old.get("isolated_persisted_readback") is True
                and old.get("smoke_terminal_state") == "SUCCESS",
                "UPGRADE_ORIGINAL_PERSISTED_SMOKE_INVALID")
        data = {
            "schema": "EDP_VAULT_E2E_UPGRADE_V1",
            "authority": "protected-verifier-v1",
            "status": "VERIFIED",
            "approval_sha256": file_digest(UPGRADE_APPROVAL),
            "original_e2e_sha256": OLD_E2E_SHA,
            "standing_sha256": STANDING_SHA,
            "request_sha256": CURRENT_REQUEST_SHA256,
            "wheel_sha256": NEW_WHEEL_SHA,
            "environment_version": "4",
            "target_namespace": request["target_namespace"],
            "run_as": APP_ID,
            "canary_terminal_state": "SUCCESS",
            "read_only_new_wheel_verified": True,
            "isolated_persisted_readback_reused": True,
            "persisted_write_smoke_scope": "ORIGINAL_WHEEL_UNCHANGED_WRITE_MECHANISM",
            "signed_readback_sha256": hashlib.sha256(canonical(canary)).hexdigest(),
            "workspace_access_verified": True,
            "effective_uc_access_verified": True,
            "canary": canary,
            "verified_at_utc": datetime.now(UTC).isoformat(),
        }
        _signed_once(data, "verifier.pem", E2E_READY)
    require(data.get("schema") == "EDP_VAULT_E2E_UPGRADE_V1"
            and data.get("status") == "VERIFIED"
            and data.get("approval_sha256") == file_digest(UPGRADE_APPROVAL)
            and data.get("original_e2e_sha256") == OLD_E2E_SHA
            and data.get("standing_sha256") == STANDING_SHA
            and data.get("request_sha256") == CURRENT_REQUEST_SHA256
            and data.get("wheel_sha256") == NEW_WHEEL_SHA
            and data.get("canary_terminal_state") == "SUCCESS"
            and data.get("read_only_new_wheel_verified") is True,
            "UPGRADE_SIGNED_CANARY_E2E_INVALID")


def install_runtime(commit: str) -> None:
    installed = PIN.read_text().strip()
    if installed == commit:
        for name in LOCAL_MODULES:
            require((RUNTIME / name).read_bytes() == git("show", f"{commit}:{name}"),
                    "UPGRADE_INSTALLED_RUNTIME_PARTIAL")
        return
    require(installed == OLD_COMMIT, "UPGRADE_INSTALLED_COMMIT_UNEXPECTED")
    for name in LOCAL_MODULES:
        path = RUNTIME / name
        require(path.is_file() and not path.is_symlink()
                and path.stat().st_uid == 0
                and path.read_bytes() == git("show", f"{OLD_COMMIT}:{name}"),
                "UPGRADE_ORIGINAL_INSTALLED_MODULE_CHANGED:" + name)
    # Stage all updated bytes before replacing any protected runtime file.
    staged = []
    for name in LOCAL_MODULES:
        path = RUNTIME / name
        tmp = path.with_name(path.name + ".edgarfix-stage")
        require(not tmp.exists(), "UPGRADE_STAGE_ALREADY_PRESENT")
        data = git("show", f"{commit}:{name}")
        require((ROOT / name).read_bytes() == data,
                "UPGRADE_SOURCE_DIFFERS_FROM_REVIEWED_COMMIT:" + name)
        tmp.write_bytes(data)
        tmp.chmod(0o644)
        staged.append((tmp, path))
    pin_tmp = PIN.with_name(PIN.name + ".edgarfix-stage")
    require(not pin_tmp.exists(), "UPGRADE_COMMIT_STAGE_ALREADY_PRESENT")
    pin_tmp.write_text(commit + "\n")
    pin_tmp.chmod(0o644)
    for temp, dest in staged:
        temp.replace(dest)
    pin_tmp.replace(PIN)
    subprocess.run(["/bin/launchctl", "kickstart", "-k", LABEL],
                   check=True, capture_output=True, timeout=30)


def activate(commit: str) -> dict:
    require(os.geteuid() == 0, "UPGRADE_OWNER_ROOT_REQUIRED")
    request, deployment, historical = preflight(commit)
    ensure_approval(request, deployment, commit)
    # Service-context M2M is used for the canary and all remote verification;
    # it never uses an agent-owned credential, role, key or ad-hoc SQL.
    os.environ["EDP_DAY6_V3_SERVICE_CONTEXT"] = "1"
    _workspace_access()
    readiness(request, deployment, historical)
    install_runtime(commit)
    final = None
    for _ in range(30):
        try:
            final = socket_action("status")
            if (final.get("status") == "READY_FOR_DISTINCT_ATTEMPT"
                    and final.get("next_attempt") == 2
                    and final.get("e2e_sha256") == file_digest(E2E_READY)):
                break
        except (OSError, RuntimeError, ValueError):
            pass
        time.sleep(1)
    require(final is not None
            and final.get("status") == "READY_FOR_DISTINCT_ATTEMPT"
            and final.get("next_attempt") == 2
            and final.get("e2e_sha256") == file_digest(E2E_READY),
            "UPGRADE_PROTECTED_SERVICE_NOT_READY")
    audit = socket_action("audit")
    require(audit.get("status") == "V3_UNATTENDED_ADMISSION_READS_VERIFIED"
            and audit.get("attempt_number") == 2
            and audit.get("checks_passed") == audit.get("checks_total") == 13,
            "UPGRADE_PROTECTED_AUDIT_NOT_VERIFIED")
    return {
        "status": "V3_UPGRADE_READY_FOR_DISTINCT_ATTEMPT_2",
        "new_installed_commit": commit,
        "new_wheel_sha256": NEW_WHEEL_SHA,
        "e2e_sha256": file_digest(E2E_READY),
        "audit_checks_passed": audit["checks_passed"],
        "attempt_number": 2,
        "no_v3_run_submitted": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reviewed_commit")
    args = parser.parse_args()
    print(json.dumps(activate(args.reviewed_commit), sort_keys=True))


if __name__ == "__main__":
    main()
