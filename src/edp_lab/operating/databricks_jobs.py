"""Signed, exact-payload Databricks Jobs adapter with live deployment preflight.

Reuses Day 3 fixed notebook / runtime hash and idempotent Jobs-submit design.
The separately protected broker must hold credentials, owner trust and ledger.
Successful CLI submission is NEVER successful processing or signed readback.
"""

import base64
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    authorize,
    canonical,
    digest,
    file_digest,
    load_grant,
    protected_trust_dir,
)
from edp_lab.operating.boundaries import _reserve

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_NAME = re.compile(r"[a-zA-Z][a-zA-Z0-9_.-]{1,127}\Z")


def _tracked(root: Path, relative: str) -> Path:
    if not isinstance(relative, str):
        raise Denied("INVALID_DEPLOYMENT_PATH")
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise Denied("FILE_OUTSIDE_REPO")
    return path


def _cli(*args: str, timeout: int) -> bytes:
    """Use the protected executor's preconfigured Databricks profile."""
    profile = os.environ.get("EDP_DATABRICKS_PROFILE")
    if profile is not None and not _NAME.fullmatch(profile):
        raise Denied("INVALID_DATABRICKS_PROFILE")
    argv = ["databricks", *args]
    if profile:
        argv.extend(["--profile", profile])
    process = subprocess.run(argv, capture_output=True, check=False, timeout=timeout)
    if process.returncode:
        raise Denied("DATABRICKS_REMOTE_VERIFICATION_OR_SUBMISSION_FAILED")
    return process.stdout


def _validate_job(payload: dict, deployment: dict, grant: dict) -> None:
    if (not isinstance(payload, dict) or set(payload) != {
            "run_name", "timeout_seconds", "idempotency_token", "tasks"}):
        raise Denied("JOB_SUBMISSION_FIELDS_NOT_ALLOWED")
    if (not isinstance(payload["run_name"], str)
            or not _NAME.fullmatch(payload["run_name"])
            or not isinstance(payload["idempotency_token"], str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", payload["idempotency_token"])):
        raise Denied("JOB_IDENTITY_INVALID")
    total = payload["timeout_seconds"]
    if not isinstance(total, int) or isinstance(total, bool) or not 0 < total <= grant["limits"]["runtime_seconds"]:
        raise Denied("JOB_TIMEOUT_OUT_OF_SCOPE")
    tasks = payload["tasks"]
    if not isinstance(tasks, list) or len(tasks) != 1:
        raise Denied("JOB_TASK_COUNT_OUT_OF_SCOPE")
    task = tasks[0]
    if not isinstance(task, dict) or set(task) != {
            "task_key", "timeout_seconds", "max_retries", "notebook_task"}:
        raise Denied("JOB_TASK_FIELDS_NOT_ALLOWED")
    if (not isinstance(task["task_key"], str)
            or not _NAME.fullmatch(task["task_key"])
            or type(task["timeout_seconds"]) is not int
            or not 0 < task["timeout_seconds"] <= total
            or task["max_retries"] != 0):
        raise Denied("JOB_TASK_LIMITS_INVALID")
    notebook = task["notebook_task"]
    if (not isinstance(notebook, dict) or set(notebook) != {
            "notebook_path", "source", "base_parameters"}
            or notebook["source"] != "WORKSPACE"
            or notebook["notebook_path"] != deployment["notebook_path"]):
        raise Denied("JOB_NOTEBOOK_OUT_OF_SCOPE")
    params = notebook["base_parameters"]
    # Phase may be smoke, full, publish, query as in existing Day 3 runtime.
    # Any other runtime must be separately reviewed and version pinned.
    if (not isinstance(params, dict) or set(params) != {"phase"}
            or not isinstance(params["phase"], str)
            or not re.fullmatch(r"[a-z][a-z0-9_-]{1,39}", params["phase"])):
        raise Denied("JOB_PARAMETERS_OUT_OF_SCOPE")


def _validate_deployment(root: Path, deployment: dict, request: dict,
                         submission_sha: str, grant: dict) -> None:
    if not isinstance(deployment, dict) or set(deployment) != {
            "schema", "notebook_path", "notebook_sha256", "files", "submission_sha256"}:
        raise Denied("DEPLOYMENT_MANIFEST_INVALID")
    if deployment["schema"] != "EDP_DATABRICKS_DEPLOYMENT_V1":
        raise Denied("DEPLOYMENT_MANIFEST_INVALID")
    if (deployment["submission_sha256"] != submission_sha
            or not _SHA.fullmatch(str(deployment["notebook_sha256"]))):
        raise Denied("DEPLOYMENT_PIN_MISMATCH")
    notebook = deployment["notebook_path"]
    if notebook != request["databricks_path"] or notebook not in grant["databricks_paths"]:
        raise Denied("DEPLOYMENT_NOTEBOOK_OUT_OF_SCOPE")
    files = deployment["files"]
    if not isinstance(files, list) or not files or len(files) > 16:
        raise Denied("DEPLOYMENT_FILES_REQUIRED")
    seen = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"uri", "sha256"}:
            raise Denied("DEPLOYMENT_FILE_INVALID")
        uri, sha = item["uri"], item["sha256"]
        if (not isinstance(uri, str) or not uri.startswith("dbfs:/Volumes/")
                or uri not in grant["databricks_paths"] or uri in seen
                or not isinstance(sha, str) or not _SHA.fullmatch(sha)):
            raise Denied("DEPLOYMENT_FILE_OUT_OF_SCOPE")
        seen.add(uri)
    if not root.is_dir():
        raise Denied("ROOT_NOT_FOUND")


def _remote_preflight(deployment: dict, grant: dict) -> None:
    """Re-read deployed Notebook and source artifacts before every Jobs submit."""
    timeout = min(grant["limits"]["runtime_seconds"], 1800)
    try:
        output = json.loads(_cli("workspace", "export", deployment["notebook_path"],
                                 "-o", "json", timeout=timeout))
    except ValueError as exc:
        raise Denied("REMOTE_NOTEBOOK_INVALID") from exc
    if not isinstance(output.get("content"), str):
        raise Denied("REMOTE_NOTEBOOK_MISSING")
    try:
        raw = base64.b64decode(output["content"], validate=True)
    except (ValueError, TypeError) as exc:
        raise Denied("REMOTE_NOTEBOOK_INVALID") from exc
    if hashlib.sha256(raw).hexdigest() != deployment["notebook_sha256"]:
        raise Denied("REMOTE_NOTEBOOK_HASH_CHANGED")
    for item in deployment["files"]:
        raw = _cli("fs", "cat", item["uri"], timeout=timeout)
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise Denied("REMOTE_DEPLOYMENT_HASH_CHANGED")


def databricks_job_submit(root: Path, grant: dict, request: dict, ledger: Path,
                          *, execute: bool = False) -> dict:
    """Submit one exact pinned Jobs task after live deployment hash readback."""
    if request["operation"] != "databricks_job_submit":
        raise Denied("WRONG_BOUNDARY")
    root = root.resolve()
    if ledger.resolve().is_relative_to(root):
        raise Denied("LEDGER_MUST_BE_OUTSIDE_WORKTREE")
    if execute:
        fresh = load_grant(root, Path(request["grant_path"]), protected_trust_dir(root))
        if fresh != grant:
            raise Denied("GRANT_CHANGED_AT_WRITE_BOUNDARY")
    authorize(grant, request, root=root)
    submission_path = _tracked(root, request["submission_path"])
    deployment_path = _tracked(root, request["deployment_path"])
    submission_pin = grant["contracts"].get(request["submission_contract"])
    deployment_pin = grant["contracts"].get(request["deployment_contract"])
    if not submission_pin or not deployment_pin:
        raise Denied("JOB_CONTRACT_NOT_PINNED")
    if (file_digest(submission_path) != submission_pin["sha256"]
            or file_digest(deployment_path) != deployment_pin["sha256"]):
        raise Denied("JOB_OR_DEPLOYMENT_CONTRACT_CHANGED")
    payload = json.loads(submission_path.read_bytes())
    deployment = json.loads(deployment_path.read_bytes())
    _validate_deployment(root, deployment, request, file_digest(submission_path), grant)
    _validate_job(payload, deployment, grant)
    if not execute:
        return {"status": "AUTHORIZED_DRY_RUN_REMOTE_UNVERIFIED"}
    _remote_preflight(deployment, grant)
    # Changes in owner grant, revocation and local payload between preflight
    # and submission must abort before reserving an external side effect.
    fresh = load_grant(root, Path(request["grant_path"]), protected_trust_dir(root))
    if fresh != grant:
        raise Denied("GRANT_CHANGED_BEFORE_SUBMIT")
    authorize(fresh, request, root=root)
    if (file_digest(submission_path) != submission_pin["sha256"]
            or file_digest(deployment_path) != deployment_pin["sha256"]):
        raise Denied("DEPLOYMENT_CHANGED_BEFORE_SUBMIT")
    record = _reserve(ledger, request["operation_id"], request)
    try:
        result = _cli("jobs", "submit", "--json", "@" + str(submission_path),
                      "--no-wait", "-o", "json", timeout=grant["limits"]["runtime_seconds"])
        response = json.loads(result)
        run_id = response.get("run_id")
        if type(run_id) is not int or run_id <= 0:
            raise Denied("JOB_RUN_ID_MISSING_AFTER_SUBMISSION")
        outcome = {"status": "SUBMITTED_REQUIRES_READBACK",
                   "run_id": run_id, "idempotency_token": payload["idempotency_token"],
                   "request_sha256": digest(canonical(request))}
    except (OSError, ValueError, Denied, subprocess.TimeoutExpired):
        outcome = {"status": "UNCERTAIN_REQUIRES_READBACK",
                   "request_sha256": digest(canonical(request))}
    record.write_text(json.dumps(outcome, sort_keys=True) + "\n")
    return outcome


def inspect_submitted_job(root: Path, grant: dict, request: dict,
                          ledger: Path) -> dict:
    """Independent read-only Databricks Jobs terminal check.

    Returns UNSIGNED receipt content. Only a separately protected verifier may
    sign it with the owner-trusted key after completing its own checks.
    """
    if request.get("operation") != "databricks_job_submit":
        raise Denied("WRONG_BOUNDARY")
    authorize(grant, request, root=root.resolve())
    record_path = ledger / (request["operation_id"] + ".json")
    if ledger.resolve().is_relative_to(root.resolve()):
        raise Denied("LEDGER_MUST_BE_OUTSIDE_WORKTREE")
    record = json.loads(record_path.read_bytes())
    if record.get("status") != "SUBMITTED_REQUIRES_READBACK":
        raise Denied("JOB_NOT_SUBMITTED_OR_UNCERTAIN")
    run_id = record.get("run_id")
    if type(run_id) is not int or run_id <= 0:
        raise Denied("JOB_RUN_ID_NOT_PINNED")
    expected = digest(canonical(request))
    if record.get("request_sha256") != expected:
        raise Denied("JOB_REQUEST_LEDGER_MISMATCH")
    payload_path = _tracked(root.resolve(), request["submission_path"])
    if file_digest(payload_path) != grant["contracts"][request["submission_contract"]]["sha256"]:
        raise Denied("JOB_SUBMISSION_CHANGED")
    submission = json.loads(payload_path.read_bytes())
    raw = _cli("jobs", "get-run", str(run_id), "-o", "json",
               timeout=min(grant["limits"]["runtime_seconds"], 1800))
    try:
        live = json.loads(raw)
    except ValueError as exc:
        raise Denied("JOB_READBACK_INVALID") from exc
    state = live.get("state", {})
    if live.get("run_id") != run_id:
        raise Denied("JOB_RUN_ID_CHANGED")
    tasks = live.get("tasks", [])
    expected_task = submission["tasks"][0]
    if (not isinstance(tasks, list) or len(tasks) != 1
            or tasks[0].get("task_key") != expected_task["task_key"]
            or tasks[0].get("notebook_task", {}).get("notebook_path") !=
            expected_task["notebook_task"]["notebook_path"]):
        raise Denied("JOB_REMOTE_TASK_CHANGED")
    if state.get("life_cycle_state") != "TERMINATED":
        raise Denied("JOB_NOT_TERMINAL")
    if state.get("result_state") != "SUCCESS":
        raise Denied("JOB_TERMINAL_FAILURE")
    return {
        "schema": "EDP_EXTERNAL_OPERATION_RECEIPT_V1",
        "operation_id": request["operation_id"],
        "request_sha256": expected,
        "status": "VERIFIED",
        "live_readback": True,
        "external_service": "DATABRICKS_JOBS",
        "terminal_state": "SUCCESS",
        "job_run_id": run_id,
        "remote_response_sha256": digest(raw),
        "signature_status": "UNSIGNED_REQUIRES_PROTECTED_VERIFIER",
    }
