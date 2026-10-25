"""Owner Terminal only: install, issue and submit the exact Day 6 V3 Job.

This is a fixed, one-shot extension of the installed Vault trust directory. It
does not change the V2 standing policy or expose an agent-callable service.
Each mutating action is a separate Owner invocation after review. A reserved
submission is consumed even if Databricks returns no run ID.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from owner_setup_day6_vault_0a import BASE, ROOT, admin_cli, run

from edp_lab.operating.authority import canonical, file_digest, verified_document
from edp_lab.vault.v3_one_shot_gate import verify_saved_job

REQUEST = ROOT / "metadata/operating/day6_c2000_vault_v3_bounded_request_v1.json"
DEPLOYMENT = ROOT / "metadata/operating/day6_c2000_vault_v3_deployment_v1.json"
SEMANTIC = BASE / "approvals/c2000-full-semantics-v1.signed.json"
WHEEL_DIR = "/Workspace/Shared/edp-lab/day6-c2000-v3"
GRANT_ID = "day6-c2000-v3-one-shot-20261025-v1"
INSTALL = BASE / "receipts/day6-v3-install-v1.signed.json"
GRANT = BASE / "grants/day6-v3-one-shot-v1.signed.json"
RESERVATION = BASE / "ledger/day6-v3-one-shot-v1.json"
SUBMISSION = BASE / "ledger/day6-v3-one-shot-submission-v1.json"
APP_ID = "87df13c2-1bb7-4a0b-b84a-84e01bdc1764"
SERVICE_PRINCIPAL_ID = "72304318628585"
SOURCE_TABLES = (
    "clean_c300_m1_records_main_recovery_20261021_v4_full",
    "clean_c300_m1_bindings_main_recovery_20261021_v4_full",
    "clean_c300_m1_records_num_recovery_20261021_v1_recovery",
    "clean_c300_m1_bindings_num_recovery_20261021_v1_recovery",
    "clean_n750_m1_treasury_properties_step8_v1",
)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(reason)


def _owner(expected_commit: str) -> None:
    require(os.geteuid() == 0 and ROOT == Path(
        "/Users/lightnino/Projects/edp-lab-day6-vault-prototype"),
        "OWNER_ROOT_TERMINAL_REQUIRED")
    actual = run("/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
                 "rev-parse", "HEAD").stdout.strip()
    require(actual == expected_commit, "UNREVIEWED_COMMIT")
    changed = run("/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
                  "status", "--porcelain", "--untracked-files=no").stdout.strip()
    require(not changed, "TRACKED_WORKTREE_CHANGED")
    for folder in (BASE, BASE / "private", BASE / "trust", BASE / "approvals",
                   BASE / "receipts", BASE / "grants", BASE / "ledger"):
        require(folder.is_dir() and not folder.is_symlink()
                and folder.stat().st_uid == 0
                and not folder.stat().st_mode & 0o022,
                "PROTECTED_DIRECTORY_REQUIRED:" + folder.name)
    policy = verified_document(ROOT, BASE / "trust/policy.signed.json", BASE / "trust")
    require(policy.get("schema") == "EDP_VAULT_STANDING_POLICY_V2",
            "INSTALLED_V2_TRUST_REQUIRED")
    predecessor = verified_document(ROOT, BASE / "receipts/install-v2.signed.json",
                                    BASE / "trust")
    require(predecessor.get("status") == "VAULT_0A_INSTALLED_AWAITING_ELIGIBLE_RUN"
            and str(predecessor.get("service_principal_id")) == SERVICE_PRINCIPAL_ID,
            "INSTALLED_V2_RECEIPT_CHANGED")


def _pins() -> tuple[dict, dict]:
    request = json.loads(REQUEST.read_bytes())
    deployment = json.loads(DEPLOYMENT.read_bytes())
    require(file_digest(REQUEST) == "dfe24b8e5aa15b07891892b93270aa73995f43d17a7d5f2d8c25323755cc684d",
            "REQUEST_PIN_CHANGED")
    require(file_digest(DEPLOYMENT) == request["execution"]["deployment_sha256"],
            "DEPLOYMENT_PIN_CHANGED")
    for field in ("selection", "negative_oracles", "target_ddl",
                  "semantic_approval_request", "resource_proposal"):
        pin = request[field]
        require(file_digest(ROOT / pin["path"]) == pin["sha256"],
                "V3_PIN_CHANGED:" + field)
    wheel = Path(deployment["artifact"]["local_build_output_uncommitted"])
    require(file_digest(wheel) == request["execution"]["runtime_artifact_sha256"],
            "LOCAL_WHEEL_CHANGED")
    semantic = verified_document(ROOT, SEMANTIC, BASE / "trust")
    unsigned = json.loads((ROOT / request["semantic_approval_request"]["path"]).read_bytes())
    require(semantic == unsigned["document"], "SIGNED_SEMANTIC_SCOPE_CHANGED")
    require(request["execution"]["job_submissions_max"] == 1
            and request["execution"]["automatic_retries_max"] == 0
            and len(request["new_v3_table_allowlist"]) == 23,
            "V3_BOUNDS_CHANGED")
    return request, deployment


def _write_once(path: Path, value: dict) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())


def _signed_once(document: dict, key_name: str, path: Path) -> None:
    key = BASE / "private" / key_name
    require(key.is_file() and not key.is_symlink() and key.stat().st_uid == 0
            and not key.stat().st_mode & 0o077, "PROTECTED_SIGNING_KEY_REQUIRED")
    with tempfile.TemporaryDirectory(dir=BASE / "private") as folder:
        payload, signature = (Path(folder) / name for name in ("payload", "signature"))
        payload.write_bytes(canonical(document))
        subprocess.run(["/opt/homebrew/bin/openssl", "pkeyutl", "-sign",
                        "-inkey", str(key), "-rawin", "-in", str(payload),
                        "-out", str(signature)], check=True, capture_output=True, timeout=30)
        envelope = {"document": document,
                    "signature_base64": base64.b64encode(signature.read_bytes()).decode()}
    _write_once(path, envelope)
    require(verified_document(ROOT, path, BASE / "trust") == document,
            "SIGNED_READBACK_CHANGED")


def _job_parameters(request_sha: str, deployment: dict) -> list[str]:
    path = WHEEL_DIR
    return ["--request", path + "/request.granted.json",
            "--request-sha256", request_sha,
            "--selection", path + "/selection.json",
            "--negative-oracles", path + "/negative-oracles.json", "--execute"]


def _job_settings(request_sha: str, deployment: dict) -> dict:
    wheel = deployment["artifact"]["workspace_target_proposed"]
    return {"name": "day6-c2000-v3-one-shot", "max_concurrent_runs": 1,
            "queue": {"enabled": False}, "timeout_seconds": 3600,
            "run_as": {"service_principal_name": APP_ID},
            "tasks": [{"task_key": "day6_v3_one_shot", "timeout_seconds": 3600,
                       "max_retries": 0, "retry_on_timeout": False,
                       "disable_auto_optimization": True,
                       "environment_key": "v3_fixed_runtime",
                       "python_wheel_task": {"package_name": "edp-lab",
                                             "entry_point": "edp-day6-v3",
                                             "parameters": _job_parameters(request_sha, deployment)}}],
            "environments": [{"environment_key": "v3_fixed_runtime",
                              "spec": {"dependencies": [wheel]}}]}


def _source_rights() -> None:
    for securable, name, rights in (
        ("catalog", "workspace", {"USE_CATALOG"}),
        ("schema", "workspace.edp_lab", {"USE_SCHEMA"}),
        ("schema", "workspace.edp_lab_day6_vault_proto", {"USE_SCHEMA", "CREATE_TABLE"}),
        *(("table", "workspace.edp_lab." + name, {"SELECT"}) for name in SOURCE_TABLES),
    ):
        require(rights <= _effective_rights(securable, name),
                "V3_RUN_AS_PRIVILEGES_MISSING:" + name)


def _effective_rights(securable: str, name: str) -> set[str]:
    grants = admin_cli("grants", "get-effective", securable, name,
                       "--principal", APP_ID)
    return {item["privilege"] for assignment in grants.get("privilege_assignments", [])
            for item in assignment.get("privileges", [])}


def _ensure_rights(securable: str, name: str, rights: list[str]) -> None:
    missing = sorted(set(rights) - _effective_rights(securable, name))
    if missing:
        admin_cli("grants", "update", securable, name,
                  "--json", json.dumps({"changes": [{"principal": APP_ID,
                                                        "add": missing}]}),
                  allow_empty=True)
        require(set(missing) <= _effective_rights(securable, name),
                "V3_GRANT_UPDATE_UNVERIFIED:" + name)


def _targets(request: dict) -> dict:
    tables = admin_cli("tables", "list", "workspace", "edp_lab_day6_vault_proto")
    require(isinstance(tables, list), "V3_TARGET_LIST_UNVERIFIED")
    existing = {item["name"]: item for item in tables}
    require(set(existing) == set(request["existing_tables_read_only"]),
            "V3_TARGET_OR_HISTORICAL_TABLE_SET_CHANGED")
    return {name: existing[name]["table_id"] for name in sorted(existing)}


def _upload(path: Path, remote: str) -> None:
    if path.is_relative_to(BASE):
        admin_cli("workspace", "import", remote, "--content",
                  base64.b64encode(path.read_bytes()).decode(), "--format", "AUTO",
                  allow_empty=True)
    else:
        admin_cli("workspace", "import", remote, "--file", str(path), "--format", "AUTO",
                  allow_empty=True)
    require(_remote_digest(remote) == file_digest(path),
            "UPLOADED_WORKSPACE_BYTES_UNVERIFIED:" + remote)


def _remote_digest(remote: str) -> str:
    exported = admin_cli("workspace", "export", remote, "--format", "AUTO")
    return hashlib.sha256(base64.b64decode(exported["content"], validate=True)).hexdigest()


def _workspace_absent(remote: str) -> None:
    result = subprocess.run(
        ["/usr/bin/sudo", "-n", "-u", "lightnino", "-H",
         "/opt/homebrew/bin/databricks", "workspace", "get-status", remote,
         "-p", "edp-lab", "-o", "json"],
        capture_output=True, text=True, check=False, timeout=30)
    message = result.stderr.upper()
    missing_path = f"PATH ({remote.upper()}) DOESN'T EXIST."
    require(result.returncode != 0 and (
        any(code in message for code in
            ("PATH_NOT_FOUND", "RESOURCE_DOES_NOT_EXIST", "DOES NOT EXIST"))
        or message.strip() in (missing_path, "ERROR: " + missing_path)),
            "V3_REMOTE_FILE_ABSENCE_UNVERIFIED:" + remote)


def _workspace_directory() -> None:
    status = admin_cli("workspace", "get-status", WHEEL_DIR)
    require(status.get("path") == WHEEL_DIR and status.get("object_type") == "DIRECTORY"
            and status.get("object_id"), "V3_WORKSPACE_DIRECTORY_UNVERIFIED")


def _finish_install(expected_commit: str, request: dict, deployment: dict,
                    baseline: dict, derived_sha: str) -> dict:
    wheel = Path(deployment["artifact"]["local_build_output_uncommitted"])
    created = admin_cli("jobs", "create", "--json",
                        json.dumps(_job_settings(derived_sha, deployment)))
    job_id = created.get("job_id") if isinstance(created, dict) else None
    require(type(job_id) is int and job_id > 0, "V3_JOB_CREATE_UNCERTAIN_STOP")
    saved = admin_cli("jobs", "get", str(job_id))
    verify_saved_job(saved["settings"],
                     wheel_path=deployment["artifact"]["workspace_target_proposed"],
                     run_as={"service_principal_name": APP_ID},
                     parameters=_job_parameters(derived_sha, deployment))
    require(_targets(request) == baseline, "V3_HISTORICAL_BASELINE_CHANGED")
    document = {"schema": "EDP_DAY6_V3_INSTALL_RECEIPT_V1",
                "authority": "protected-verifier-v1", "status": "INSTALLED_NOT_GRANTED",
                "commit": expected_commit, "job_id": job_id,
                "request_sha256": file_digest(REQUEST),
                "derived_request_sha256": derived_sha,
                "deployment_sha256": file_digest(DEPLOYMENT),
                "wheel_sha256": file_digest(wheel),
                "semantic_receipt_sha256": file_digest(SEMANTIC),
                "run_as": APP_ID, "historical_table_ids": baseline,
                "installed_at_utc": datetime.now(UTC).isoformat()}
    _signed_once(document, "verifier.pem", INSTALL)
    return {"status": "V3_INSTALLED_NOT_GRANTED", "job_id": job_id,
            "install_receipt_sha256": file_digest(INSTALL)}


def install(expected_commit: str) -> dict:
    _owner(expected_commit)
    request, deployment = _pins()
    require(not INSTALL.exists() and not GRANT.exists() and not RESERVATION.exists(),
            "V3_INSTALL_OR_GRANT_ALREADY_EXISTS")
    principal = admin_cli("current-user", "me")
    require(principal.get("userName") == "chengzhu13@gmail.com"
            and "admins" in {group.get("display") for group in principal.get("groups", [])},
            "OWNER_ADMIN_SESSION_REQUIRED")
    sp = admin_cli("service-principals", "get", SERVICE_PRINCIPAL_ID)
    require(sp.get("applicationId") == APP_ID and sp.get("active") is True,
            "EXISTING_PROTECTED_PRINCIPAL_CHANGED")
    baseline = _targets(request)
    require(admin_cli("jobs", "list") == [], "V3_JOB_LIST_CHANGED")
    for remote in (deployment["artifact"]["workspace_target_proposed"],
                   WHEEL_DIR + "/selection.json",
                   WHEEL_DIR + "/negative-oracles.json",
                   WHEEL_DIR + "/request.granted.json"):
        _workspace_absent(remote)
    admin_cli("workspace", "mkdirs", WHEEL_DIR, allow_empty=True)
    _workspace_directory()
    wheel = Path(deployment["artifact"]["local_build_output_uncommitted"])
    _upload(wheel, deployment["artifact"]["workspace_target_proposed"])
    for kind, source in (("selection", ROOT / request["selection"]["path"]),
                         ("negative-oracles", ROOT / request["negative_oracles"]["path"])):
        _upload(source, WHEEL_DIR + "/" + kind + ".json")
    # A fixed grant ID is inserted into a derived runtime request; the original
    # reviewed request bytes and its SHA remain unchanged.
    derived = json.loads(REQUEST.read_bytes())
    derived["execution"]["protected_grant_id"] = GRANT_ID
    derived_path = BASE / "private/day6-v3-request.granted.json"
    _write_once(derived_path, derived)
    _upload(derived_path, WHEEL_DIR + "/request.granted.json")
    derived_sha = file_digest(derived_path)
    # Only these missing V3 privileges are installed. V2 policy and eight old
    # tables are never updated. Verify the uploaded bytes before adding rights.
    for securable, name, rights in (
        ("schema", "workspace.edp_lab", ["USE_SCHEMA"]),
        ("schema", "workspace.edp_lab_day6_vault_proto", ["CREATE_TABLE"]),
        *(("table", "workspace.edp_lab." + name, ["SELECT"])
          for name in SOURCE_TABLES),
    ):
        _ensure_rights(securable, name, rights)
    _source_rights()
    return _finish_install(expected_commit, request, deployment, baseline, derived_sha)


def resume_install(expected_commit: str) -> dict:
    """Owner-only recovery from files and grants installed, before Job creation."""
    _owner(expected_commit)
    request, deployment = _pins()
    require(not any(path.exists() for path in (INSTALL, GRANT, RESERVATION, SUBMISSION)),
            "V3_LATER_CHECKPOINT_ALREADY_EXISTS")
    derived = BASE / "private/day6-v3-request.granted.json"
    require(derived.is_file() and not derived.is_symlink()
            and derived.stat().st_uid == 0 and not derived.stat().st_mode & 0o077,
            "V3_PROTECTED_DERIVED_REQUEST_REQUIRED")
    expected = json.loads(REQUEST.read_bytes())
    expected["execution"]["protected_grant_id"] = GRANT_ID
    require(derived.read_bytes() == canonical(expected),
            "V3_DERIVED_REQUEST_CHANGED")
    derived_sha = file_digest(derived)
    principal = admin_cli("current-user", "me")
    require(principal.get("userName") == "chengzhu13@gmail.com"
            and "admins" in {group.get("display") for group in principal.get("groups", [])},
            "OWNER_ADMIN_SESSION_REQUIRED")
    sp = admin_cli("service-principals", "get", SERVICE_PRINCIPAL_ID)
    require(sp.get("applicationId") == APP_ID and sp.get("active") is True,
            "EXISTING_PROTECTED_PRINCIPAL_CHANGED")
    baseline = _targets(request)
    require(admin_cli("jobs", "list") == [], "V3_JOB_LIST_CHANGED")
    _workspace_directory()
    for remote, local in (
        (deployment["artifact"]["workspace_target_proposed"],
         Path(deployment["artifact"]["local_build_output_uncommitted"])),
        (WHEEL_DIR + "/selection.json", ROOT / request["selection"]["path"]),
        (WHEEL_DIR + "/negative-oracles.json", ROOT / request["negative_oracles"]["path"]),
        (WHEEL_DIR + "/request.granted.json", derived),
    ):
        require(_remote_digest(remote) == file_digest(local),
                "V3_REMOTE_ARTIFACT_CHANGED:" + remote)
    _source_rights()
    return _finish_install(expected_commit, request, deployment, baseline, derived_sha)


def _installed(request: dict, deployment: dict) -> dict:
    proof = verified_document(ROOT, INSTALL, BASE / "trust")
    require(proof.get("schema") == "EDP_DAY6_V3_INSTALL_RECEIPT_V1"
            and proof.get("status") == "INSTALLED_NOT_GRANTED"
            and proof.get("request_sha256") == file_digest(REQUEST)
            and proof.get("deployment_sha256") == file_digest(DEPLOYMENT)
            and proof.get("semantic_receipt_sha256") == file_digest(SEMANTIC)
            and proof.get("run_as") == APP_ID,
            "V3_INSTALL_RECEIPT_CHANGED")
    derived = BASE / "private/day6-v3-request.granted.json"
    require(file_digest(derived) == proof["derived_request_sha256"],
            "V3_DERIVED_REQUEST_CHANGED")
    for remote, expected in (
        (deployment["artifact"]["workspace_target_proposed"], proof["wheel_sha256"]),
        (WHEEL_DIR + "/selection.json", request["selection"]["sha256"]),
        (WHEEL_DIR + "/negative-oracles.json", request["negative_oracles"]["sha256"]),
        (WHEEL_DIR + "/request.granted.json", proof["derived_request_sha256"]),
    ):
        require(_remote_digest(remote) == expected, "V3_REMOTE_ARTIFACT_CHANGED:" + remote)
    _source_rights()
    saved = admin_cli("jobs", "get", str(proof["job_id"]))
    verify_saved_job(saved["settings"],
                     wheel_path=deployment["artifact"]["workspace_target_proposed"],
                     run_as={"service_principal_name": APP_ID},
                     parameters=_job_parameters(proof["derived_request_sha256"], deployment))
    require(_targets(request) == proof["historical_table_ids"],
            "V3_TARGET_OR_HISTORICAL_BASELINE_CHANGED")
    return proof


def issue(expected_commit: str) -> dict:
    _owner(expected_commit)
    request, deployment = _pins()
    require(not GRANT.exists() and not RESERVATION.exists(), "V3_ONE_SHOT_ALREADY_ISSUED")
    proof = _installed(request, deployment)
    require(proof["commit"] == expected_commit, "V3_INSTALL_COMMIT_CHANGED")
    issued = datetime.now(UTC)
    document = {"schema": "EDP_DAY6_V3_ONE_SHOT_GRANT_V1",
                "authority": "owner-v3-one-shot-v1", "grant_id": GRANT_ID,
                "status": "ISSUED_NOT_SUBMITTED", "job_id": proof["job_id"],
                "install_receipt_sha256": file_digest(INSTALL),
                "request_sha256": file_digest(REQUEST),
                "derived_request_sha256": proof["derived_request_sha256"],
                "semantic_receipt_sha256": file_digest(SEMANTIC),
                "selection_sha256": request["selection"]["sha256"],
                "negative_oracles_sha256": request["negative_oracles"]["sha256"],
                "ddl_sha256": request["target_ddl"]["sha256"],
                "wheel_sha256": deployment["artifact"]["sha256"],
                "run_as": APP_ID, "tables": request["new_v3_table_allowlist"],
                "job_submissions_max": 1, "runtime_seconds_max": 3600,
                "automatic_retries_max": 0,
                "issued_at_utc": issued.isoformat(),
                "expires_at_utc": (issued + timedelta(hours=1)).isoformat()}
    _signed_once(document, "owner.pem", GRANT)
    return {"status": "V3_GRANT_ISSUED_NOT_SUBMITTED",
            "grant_sha256": file_digest(GRANT), "job_id": proof["job_id"]}


def execute(expected_commit: str) -> dict:
    _owner(expected_commit)
    request, deployment = _pins()
    proof = _installed(request, deployment)
    require(proof["commit"] == expected_commit, "V3_INSTALL_COMMIT_CHANGED")
    grant = verified_document(ROOT, GRANT, BASE / "trust")
    require(grant.get("schema") == "EDP_DAY6_V3_ONE_SHOT_GRANT_V1"
            and grant.get("grant_id") == GRANT_ID
            and grant.get("status") == "ISSUED_NOT_SUBMITTED"
            and grant.get("job_id") == proof["job_id"]
            and grant.get("install_receipt_sha256") == file_digest(INSTALL)
            and grant.get("request_sha256") == file_digest(REQUEST)
            and grant.get("derived_request_sha256") == proof["derived_request_sha256"]
            and grant.get("semantic_receipt_sha256") == file_digest(SEMANTIC)
            and grant.get("selection_sha256") == request["selection"]["sha256"]
            and grant.get("negative_oracles_sha256") == request["negative_oracles"]["sha256"]
            and grant.get("ddl_sha256") == request["target_ddl"]["sha256"]
            and grant.get("wheel_sha256") == deployment["artifact"]["sha256"]
            and grant.get("run_as") == APP_ID
            and grant.get("tables") == request["new_v3_table_allowlist"]
            and grant.get("job_submissions_max") == 1
            and grant.get("runtime_seconds_max") == 3600
            and grant.get("automatic_retries_max") == 0,
            "V3_EXACT_GRANT_CHANGED")
    require(datetime.fromisoformat(grant["issued_at_utc"]) <= datetime.now(UTC)
            < datetime.fromisoformat(grant["expires_at_utc"]),
            "V3_ONE_SHOT_GRANT_EXPIRED")
    require(not RESERVATION.exists() and not SUBMISSION.exists(),
            "V3_SUBMISSION_ALREADY_RESERVED")
    # The durable reservation precedes the only Jobs call. Any error after it
    # is uncertain and must be reconciled against the original Job and Delta.
    _write_once(RESERVATION, {"schema": "EDP_DAY6_V3_ONE_SHOT_LEDGER_V1",
                              "status": "UNCERTAIN_REQUIRES_READBACK",
                              "grant_sha256": file_digest(GRANT),
                              "request_sha256": proof["derived_request_sha256"],
                              "job_id": proof["job_id"],
                              "reserved_at_utc": datetime.now(UTC).isoformat()})
    try:
        response = admin_cli("jobs", "run-now", str(proof["job_id"]), "--no-wait",
                             "--idempotency-token", hashlib.sha256(
                                 canonical(grant)).hexdigest()[:32])
        run_id = response.get("run_id")
        require(type(run_id) is int and run_id > 0, "V3_RUN_ID_UNKNOWN")
        _write_once(SUBMISSION, {"status": "SUBMITTED_REQUIRES_READBACK",
                                 "run_id": run_id, "job_id": proof["job_id"],
                                 "grant_sha256": file_digest(GRANT),
                                 "submitted_at_utc": datetime.now(UTC).isoformat()})
    except (OSError, ValueError, TypeError, KeyError, RuntimeError,
            subprocess.CalledProcessError):
        return {"status": "UNCERTAIN_REQUIRES_READBACK",
                "reservation_path": str(RESERVATION), "job_id": proof["job_id"]}
    return {"status": "SUBMITTED_REQUIRES_INDEPENDENT_SIGNED_READBACK",
            "run_id": run_id, "job_id": proof["job_id"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("install", "resume-install", "issue", "execute"))
    parser.add_argument("expected_commit")
    args = parser.parse_args()
    result = {"install": install, "resume-install": resume_install,
              "issue": issue, "execute": execute}[args.action](
        args.expected_commit)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
