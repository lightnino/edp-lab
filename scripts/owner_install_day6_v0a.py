"""One root invocation: reconcile the failed V3 run and prove the new Jobs path.

The signed standing record is installed only for the exact bounded Day 6
request. The isolated smoke uses the same wheel, run-as and serverless task
environment as V3, then a separate Owner SQL readback is signed by the
protected verifier key. Any uncertain remote operation stops without replay.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess
import tarfile
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from owner_day6_v3_one_shot import (
    APP_ID,
    BASE,
    CURRENT_REQUEST_SHA256,
    REQUEST,
    ROOT,
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
from owner_day6_v3_successor import E2E_READY, STANDING
from owner_reconcile_day6_v3_partial import RECEIPT as PARTIAL_RECEIPT
from owner_reconcile_day6_v3_partial import _original_ledger, _target_absent, reconcile
from owner_setup_day6_vault_0a import admin_cli, admin_sql

from edp_lab.operating.authority import canonical, file_digest, verified_document
from edp_lab.vault.v3_one_shot_gate import verify_saved_job

SMOKE_DIR = "/Workspace/Shared/edp-lab/day6-c2000-v3-e2e-v3"
SMOKE_REQUEST = SMOKE_DIR + "/request.smoke.json"
SMOKE_TABLE = "workspace.edp_lab_day6_vault_proto.v0a_day6_e2e_20261025"
SMOKE_JOB = BASE / "ledger/day6-v0a-e2e-job-v1.json"
SMOKE_RESERVATION = BASE / "ledger/day6-v0a-e2e-run-reservation-v1.json"
SMOKE_SUBMISSION = BASE / "ledger/day6-v0a-e2e-run-v1.json"
SERVICE_LABEL = "org.edp-lab.day6-v3-standing"


def _service(expected_commit: str) -> dict:
    socket_path = BASE / "day6-v3.sock"
    if socket_path.exists():
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(5)
            client.connect(str(socket_path))
            client.sendall(b'{"action":"status"}\n')
            client.shutdown(socket.SHUT_WR)
            response = json.loads(client.recv(8192))
        require(response.get("status") == "READY_FOR_DISTINCT_ATTEMPT",
                "V0A_PROTECTED_SERVICE_NOT_READY")
        return response
    runtime = BASE / "runtime-v3"
    require(not runtime.exists(), "V0A_RUNTIME_PARTIAL_INSTALL_RECONCILE")
    runtime.mkdir(mode=0o755)
    archive = subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
         "archive", expected_commit, "src/edp_lab", "scripts"],
        stdout=subprocess.PIPE, check=True, timeout=60)
    with tarfile.open(fileobj=BytesIO(archive.stdout), mode="r:") as tar:
        tar.extractall(runtime, filter="data")
    for path in runtime.rglob("*"):
        if path.is_file():
            path.chmod(path.stat().st_mode & ~0o022)
    commit_file = BASE / "trust/day6-v3-installed-commit.txt"
    require(not commit_file.exists(), "V0A_INSTALLED_COMMIT_ALREADY_EXISTS")
    commit_file.write_text(expected_commit + "\n")
    commit_file.chmod(0o644)
    plist = Path("/Library/LaunchDaemons") / (SERVICE_LABEL + ".plist")
    require(not plist.exists(), "V0A_V3_SERVICE_PLIST_ALREADY_EXISTS")
    args = [str(BASE / "python/bin/python3.12"), "-m", "edp_lab.vault.v3_service",
            str(ROOT), str(BASE)]
    arguments = "".join(f"<string>{escape(value)}</string>" for value in args)
    plist.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict><key>Label</key>'
        f'<string>{SERVICE_LABEL}</string><key>ProgramArguments</key><array>{arguments}</array>'
        '<key>EnvironmentVariables</key><dict><key>PYTHONPATH</key>'
        f'<string>{runtime}/src:{runtime}/scripts</string><key>PATH</key>'
        '<string>/opt/homebrew/bin:/usr/bin:/bin</string></dict>'
        '<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>'
        f'<key>StandardOutPath</key><string>{BASE}/{SERVICE_LABEL}.stdout.log</string>'
        f'<key>StandardErrorPath</key><string>{BASE}/{SERVICE_LABEL}.stderr.log</string>'
        '</dict></plist>\n')
    plist.chmod(0o644)
    subprocess.run(["/bin/launchctl", "bootstrap", "system", str(plist)],
                   check=True, capture_output=True, timeout=30)
    for _ in range(30):
        if socket_path.exists():
            return _service(expected_commit)
        time.sleep(1)
    raise RuntimeError("V0A_PROTECTED_SERVICE_DID_NOT_START")


def _standing(request: dict, deployment: dict) -> None:
    if STANDING.exists():
        proof = verified_document(ROOT, STANDING, BASE / "trust")
        require(proof.get("request_sha256") == CURRENT_REQUEST_SHA256
                and proof.get("wheel_sha256") == deployment["artifact"]["sha256"],
                "V0A_STANDING_SCOPE_CHANGED")
        return
    document = {
        "schema": "EDP_DAY6_V3_STANDING_AUTHORIZATION_V1",
        "authority": "owner-installed-day6-v0a-v1", "status": "INSTALLED",
        "request_sha256": CURRENT_REQUEST_SHA256,
        "original_request_sha256": _original_ledger()[1]["request_sha256"],
        "original_partial_receipt_sha256": file_digest(PARTIAL_RECEIPT),
        "wheel_sha256": deployment["artifact"]["sha256"],
        "job_submissions_max": 10000000, "runtime_seconds_max": 3600,
        "automatic_retries_max": 0, "run_as": APP_ID,
        "source_ids": request["selection"]["source_ids"],
        "target_namespace": request["target_namespace"],
        "table_allowlist": request["new_v3_table_allowlist"],
        "smoke_table": SMOKE_TABLE,
        "distinct_no_effect_recovery_allowed": True,
        "issued_at_utc": datetime.now(UTC).isoformat(),
    }
    _signed_once(document, "owner.pem", STANDING)


def _smoke_parameters() -> list[str]:
    return ["--request", SMOKE_REQUEST, "--request-sha256", CURRENT_REQUEST_SHA256,
            "--selection", "/Workspace/Shared/edp-lab/day6-c2000-v3/selection.json",
            "--negative-oracles",
            "/Workspace/Shared/edp-lab/day6-c2000-v3/negative-oracles.json",
            "--v0a-smoke"]


def _job(deployment: dict) -> int:
    if SMOKE_JOB.exists():
        record = json.loads(SMOKE_JOB.read_bytes())
        job_id = record["job_id"]
    else:
        jobs = admin_cli("jobs", "list")
        require(isinstance(jobs, list) and not any(
            item.get("settings", {}).get("name") == "day6-v0a-e2e-smoke"
            for item in jobs), "V0A_SMOKE_JOB_ABSENCE_UNVERIFIED")
        _workspace_absent(SMOKE_REQUEST)
        _upload(REQUEST, SMOKE_REQUEST)
        settings = _job_settings(CURRENT_REQUEST_SHA256, deployment)
        settings["name"] = "day6-v0a-e2e-smoke"
        settings["tasks"][0]["python_wheel_task"]["parameters"] = _smoke_parameters()
        created = admin_cli("jobs", "create", "--json", json.dumps(settings))
        job_id = created.get("job_id") if isinstance(created, dict) else None
        require(type(job_id) is int and job_id > 0, "V0A_SMOKE_JOB_CREATE_UNCERTAIN")
        _write_once(SMOKE_JOB, {"job_id": job_id,
                                "request_sha256": CURRENT_REQUEST_SHA256,
                                "wheel_sha256": deployment["artifact"]["sha256"]})
    saved = admin_cli("jobs", "get", str(job_id))
    require(saved.get("job_id") == job_id and saved.get("run_as_user_name") == APP_ID,
            "V0A_SMOKE_JOB_IDENTITY_CHANGED")
    verify_saved_job(saved["settings"],
                     wheel_path=deployment["artifact"]["workspace_target_proposed"],
                     run_as={"service_principal_name": APP_ID},
                     parameters=_smoke_parameters())
    return job_id


def _run(job_id: int) -> int:
    if SMOKE_SUBMISSION.exists():
        submission = json.loads(SMOKE_SUBMISSION.read_bytes())
        require(submission.get("job_id") == job_id, "V0A_SMOKE_SUBMISSION_CHANGED")
        return submission["run_id"]
    require(not SMOKE_RESERVATION.exists(), "V0A_SMOKE_UNCERTAIN_NO_REPLAY")
    _target_absent(SMOKE_TABLE)
    _write_once(SMOKE_RESERVATION, {"job_id": job_id,
                                    "standing_sha256": file_digest(STANDING),
                                    "reserved_at_utc": datetime.now(UTC).isoformat()})
    response = admin_cli("jobs", "run-now", str(job_id), "--no-wait",
                         "--idempotency-token",
                         hashlib.sha256(canonical({"job_id": job_id,
                                                   "standing": file_digest(STANDING)}))
                         .hexdigest()[:32])
    run_id = response.get("run_id") if isinstance(response, dict) else None
    require(type(run_id) is int and run_id > 0, "V0A_SMOKE_RUN_UNKNOWN_NO_REPLAY")
    _write_once(SMOKE_SUBMISSION, {"job_id": job_id, "run_id": run_id,
                                   "submitted_at_utc": datetime.now(UTC).isoformat()})
    return run_id


def _terminal(run_id: int, job_id: int) -> dict:
    deadline = time.monotonic() + 3600
    while True:
        run = admin_cli("jobs", "get-run", str(run_id))
        require(run.get("run_id") == run_id and run.get("job_id") == job_id,
                "V0A_SMOKE_RUN_ID_CHANGED")
        if run.get("status", {}).get("state") == "TERMINATED":
            require(run.get("state", {}).get("result_state") == "SUCCESS"
                    and len(run.get("tasks", [])) == 1
                    and run["tasks"][0].get("attempt_number") == 0,
                    "V0A_SMOKE_JOB_FAILED")
            return run
        require(time.monotonic() < deadline, "V0A_SMOKE_RUN_TIMEOUT_RECONCILE")
        time.sleep(10)


def _independent_readback() -> dict:
    table = admin_cli("tables", "get", SMOKE_TABLE)
    require(table.get("full_name") == SMOKE_TABLE
            and table.get("data_source_format") == "DELTA"
            and table.get("table_id"), "V0A_SMOKE_DELTA_ID_MISSING")
    rows = admin_sql("SELECT probe_id, probe_value FROM " + SMOKE_TABLE)
    require(rows.get("status", {}).get("state") == "SUCCEEDED"
            and rows.get("result", {}).get("data_array") == [["day6-v0a", "ready"]],
            "V0A_SMOKE_INDEPENDENT_ROWS_MISMATCH")
    return {"table_id": table["table_id"], "row_count": 1,
            "table_readback_sha256": hashlib.sha256(canonical(table)).hexdigest(),
            "sql_readback_sha256": hashlib.sha256(canonical(rows)).hexdigest()}


def install(expected_commit: str) -> dict:
    _owner(expected_commit)
    if not PARTIAL_RECEIPT.exists():
        reconcile(expected_commit)
    request, deployment = _pins()
    _workspace_access()
    _source_rights()
    _targets(request)
    require(_remote_digest(deployment["artifact"]["workspace_target_proposed"])
            == deployment["artifact"]["sha256"], "V0A_DEPLOYED_WHEEL_CHANGED")
    _standing(request, deployment)
    if E2E_READY.exists():
        service = _service(expected_commit)
        return {"status": "VAULT_INFRA_E2E_READY",
                "receipt_sha256": file_digest(E2E_READY), "service": service}
    job_id = _job(deployment)
    run_id = _run(job_id)
    run = _terminal(run_id, job_id)
    readback = _independent_readback()
    document = {
        "schema": "EDP_VAULT_E2E_READY_V1", "authority": "protected-verifier-v1",
        "status": "VERIFIED", "standing_sha256": file_digest(STANDING),
        "request_sha256": CURRENT_REQUEST_SHA256, "run_as": APP_ID,
        "wheel_sha256": deployment["artifact"]["sha256"],
        "environment_version": "4", "target_namespace": request["target_namespace"],
        "smoke_job_id": job_id, "smoke_run_id": run_id,
        "smoke_terminal_state": "SUCCESS", "isolated_persisted_readback": True,
        "signed_readback_sha256": hashlib.sha256(canonical(readback)).hexdigest(),
        "workspace_access_verified": True, "effective_uc_access_verified": True,
        "job_readback_sha256": hashlib.sha256(canonical(run)).hexdigest(),
        "readback": readback, "verified_at_utc": datetime.now(UTC).isoformat(),
    }
    _signed_once(document, "verifier.pem", E2E_READY)
    service = _service(expected_commit)
    return {"status": "VAULT_INFRA_E2E_READY", "job_id": job_id,
            "run_id": run_id, "receipt_sha256": file_digest(E2E_READY),
            "service": service}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    args = parser.parse_args()
    print(json.dumps(install(args.expected_commit), sort_keys=True))


if __name__ == "__main__":
    main()
