"""Day 7 V4: complete existing Broker U10 verification, without prior-stage replay.

The V3 Owner one-table SELECT and original canary Job succeeded. The broker
LaunchDaemon started, but the caller's legacy 64-hex identity validator
rejected canonical SRC000002 *before connecting to the daemon*.

--check-only: root/remote read-only checks and live Broker health, no writes.
Normal mode: bounded, one-use, root-owned broker client module upgrade,
independently verified live SRC000002 U10, and final signed deployment receipt.
No credential creation, UC GRANT, Jobs submit, RAW upload, or cohort processing.
"""

from __future__ import annotations

import argparse
import grp
import importlib
import json
import os
import socket
import stat
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/Users/lightnino/Projects/edp-lab-day7-universe")
sys.path.insert(0, str(ROOT / "scripts"))

import owner_install_day7 as owner
import owner_recover_day7_canary_select_v3 as v3

OLD_COMMIT = "6b6e18fb1bb4adc709271ffb3a6af94342287f12"
SP_ID = "78491734320299"
CANARY_RUN_ID = "771002586635696"
BROKER_REL = "src/edp_lab/operating/policy_broker.py"
BROKER_INSTALLED = owner.BASE / "runtime" / BROKER_REL
BROKER_REVIEWED = ROOT / BROKER_REL
RECOVERY_INTENT = owner.BASE / "ledger/day7-broker-u10-identity-v4-intent.json"
BROKER_BACKUP = owner.BASE / "ledger/day7-broker-pre-v4.py"
BROKER_TEMP = BROKER_INSTALLED.with_name("policy_broker.py.day7-v4-new")
ALLOWED_DIFF = {
    BROKER_REL,
    "scripts/owner_recover_day7_broker_v4.py",
    "tests/operating/test_day7_broker_v4.py",
}


def need(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def git(*args: str) -> str:
    return subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={ROOT}",
         "-C", str(ROOT), *args], capture_output=True, text=True,
        check=True, timeout=60,
    ).stdout.strip()


def protected(path: Path, *, mode: int | None = None) -> None:
    need(path.is_file() and not path.is_symlink()
         and path.stat().st_uid == 0
         and not path.stat().st_mode & 0o022,
         "DAY7_V4_ROOT_FILE_CHANGED:" + path.name)
    if mode is not None:
        need(stat.S_IMODE(path.stat().st_mode) == mode,
             "DAY7_V4_ROOT_MODE_CHANGED:" + path.name)


def broker_health() -> None:
    """Prove the deployed server is reachable; invalid action cannot mutate."""
    sock = owner.BASE / "broker.sock"
    need(sock.is_socket() and not sock.is_symlink()
         and sock.stat().st_uid == 0
         and sock.stat().st_gid == grp.getgrnam("staff").gr_gid
         and stat.S_IMODE(sock.stat().st_mode) == 0o660,
         "DAY7_V4_BROKER_SOCKET_CHANGED")
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(10)
        client.connect(str(sock))
        client.sendall(b'{"action":"health"}\n')
        client.shutdown(socket.SHUT_WR)
        response = json.loads(client.recv(8192))
    need(response == {
        "status": "DENIED", "reason": "UNKNOWN_BROKER_ACTION"},
        "DAY7_V4_BROKER_HEALTH_NOT_VERIFIED")


def broker_existing_u10_wire(referenced: dict) -> None:
    """Read-only wire check bypasses broken OLD client, not Broker authority.

    A signed U10 receipt already exists and was independently verified before
    this call, so the protected server will check/reuse it, not issue a new one.
    """
    path = owner.BASE / "receipts/day7-u10-SRC000002.json"
    protected(path)
    original_digest = owner.file_digest(path)
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(180)
        client.connect(str(owner.BASE / "broker.sock"))
        client.sendall(b'{"action":"resolve_handoff","identity":"SRC000002"}\n')
        client.shutdown(socket.SHUT_WR)
        response = json.loads(client.recv(8192))
    need(response.get("status") == "VERIFIED",
         "DAY7_V4_EXISTING_BROKER_WIRE_U10_NOT_VERIFIED:"
         + str(response.get("reason", "UNKNOWN"))[:120])
    result = response.get("result", {})
    need(isinstance(result, dict)
         and result.get("physical_identity") == "SRC000002"
         and result.get("receipt_sha256") == referenced["receipt_sha256"]
         and result.get("raw_sha256") == referenced["raw_sha256"]
         and result.get("raw_bytes") == referenced["raw_bytes"]
         and owner.file_digest(path) == original_digest,
         "DAY7_V4_EXISTING_BROKER_WIRE_U10_NOT_PINNED")


def owner_table_read() -> None:
    """Only a SELECT, not any GRANT or CREATE."""
    query = ("SELECT universe_sha256, owner_decision_sha256 FROM "
             + owner.CANARY_TABLE)
    data = owner.admin_sql(query)
    need(data.get("result", {}).get("data_array")
         == [[owner.MANIFEST_SHA, owner.DECISION_SHA]],
         "DAY7_V4_OWNER_INDEPENDENT_READBACK_CHANGED")


def check(expected_commit: str) -> tuple[dict, tuple[dict, dict, dict], dict]:
    need(os.geteuid() == 0, "DAY7_V4_OWNER_ROOT_REQUIRED")
    need(len(expected_commit) == 40
         and git("rev-parse", "HEAD") == expected_commit
         and not git("status", "--porcelain"),
         "DAY7_V4_GIT_CHECKOUT_NOT_PINNED_OR_CLEAN")
    changed = set(git("diff", "--name-only", OLD_COMMIT, expected_commit).splitlines())
    need(changed == ALLOWED_DIFF,
         "DAY7_V4_CHANGE_SCOPE_NOT_EXACTLY_BROKER_CLIENT_AND_SUCCESSOR")
    need(owner.BASE.is_dir() and not owner.BASE.is_symlink()
         and owner.BASE.stat().st_uid == 0
         and stat.S_IMODE(owner.BASE.stat().st_mode) == 0o710,
         "DAY7_V4_PROTECTED_BASE_CHANGED")
    need(not RECOVERY_INTENT.exists() and not RECOVERY_INTENT.is_symlink()
         and not BROKER_BACKUP.exists() and not BROKER_BACKUP.is_symlink()
         and not BROKER_TEMP.exists() and not BROKER_TEMP.is_symlink(),
         "DAY7_V4_RECOVERY_ALREADY_ATTEMPTED")
    protected(owner.JOURNAL, mode=0o600)
    protected(v3.GRANT_INTENT, mode=0o600)
    protected(owner.BASE / "private/service-identity.json", mode=0o600)
    protected(owner.BASE / "private/databrickscfg", mode=0o600)
    protected(BROKER_INSTALLED)
    protected(owner.PLIST, mode=0o644)

    previous = owner._read_json(owner.JOURNAL)
    need({k: v for k, v in previous.items() if k != "completed"}
         == owner._install_intent(OLD_COMMIT),
         "DAY7_V4_PREVIOUS_JOURNAL_COMMIT_MISMATCH")
    stages = previous.get("completed", {})
    required = {
        "protected_files", "service_identity", "workspace_assignment",
        "service_auth", "permissions", "publication",
        "secret_duration_v2_recovery", "job_canary",
    }
    need(isinstance(stages, dict) and required <= set(stages)
         and not ({"broker", "deployment"} & set(stages)),
         "DAY7_V4_PREVIOUS_COMPLETION_STAGES_CHANGED")
    need(stages["job_canary"] == {
        "run_id": CANARY_RUN_ID,
        "table_id": stages["job_canary"].get("table_id"),
        "readback": "OWNER_SQL_EXACT_ONE_ROW",
    } and isinstance(stages["job_canary"]["table_id"], str)
         and stages["job_canary"]["table_id"],
         "DAY7_V4_CANARY_ACCEPTANCE_LEDGER_INVALID")
    intent = owner._read_json(v3.GRANT_INTENT)
    need(intent == {
        "schema": "EDP_DAY7_CANARY_OWNER_READBACK_V3_INTENT",
        "old_commit": v3.OLD_COMMIT, "successor_commit": OLD_COMMIT,
        "table": owner.CANARY_TABLE, "owner": v3.OWNER,
        "privilege": "SELECT", "existing_run_id": CANARY_RUN_ID,
    }, "DAY7_V4_PRIOR_TABLE_GRANT_INTENT_CHANGED")
    need(owner.file_digest(owner.POLICY) == owner.POLICY_SHA
         and owner.file_digest(owner.SOURCE_INDEX) == owner.SOURCE_INDEX_SHA
         and owner.file_digest(
             ROOT / "metadata/source_universes/approved/manifest.json")
         == owner.MANIFEST_SHA,
         "DAY7_V4_UNIVERSE_PINS_CHANGED")

    # Only this one broker-client module is allowed to change. The old
    # protected installation must match exact old git bytes before replacing.
    old_blob = subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={ROOT}",
         "-C", str(ROOT), "show", OLD_COMMIT + ":" + BROKER_REL],
        capture_output=True, check=True, timeout=30,
    ).stdout
    need(BROKER_INSTALLED.read_bytes() == old_blob,
         "DAY7_V4_PROTECTED_BROKER_MODULE_DRIFT")
    new_blob = BROKER_REVIEWED.read_bytes()
    need(new_blob != old_blob and
         b're.fullmatch(r"SRC[0-9]{6}", physical_identity)' in new_blob,
         "DAY7_V4_PATCHED_BROKER_CLIENT_NOT_REVIEWED")
    compile(new_blob, str(BROKER_INSTALLED), "exec")

    identity = owner._read_json(owner.BASE / "private/service-identity.json")
    need(str(identity.get("service_principal_id")) == SP_ID
         and isinstance(identity.get("application_id"), str)
         and bool(identity["application_id"]),
         "DAY7_V4_EXISTING_SERVICE_IDENTITY_CHANGED")
    principal = owner.admin("current-user", "me")
    need(principal.get("userName") == v3.OWNER,
         "DAY7_V4_OWNER_IDENTITY_CHANGED")
    svc = owner.service("current-user", "me")
    need(str(svc.get("id")) == SP_ID and svc.get("active", True),
         "DAY7_V4_M2M_IDENTITY_CHANGED")
    registered = owner.admin("service-principals", "get", SP_ID)
    need(registered.get("applicationId") == identity["application_id"]
         and registered.get("displayName") == owner.SP_NAME,
         "DAY7_V4_SP_IDENTITY_DRIFT")
    table = owner.service("tables", "get", owner.CANARY_TABLE)
    need(table.get("full_name") == owner.CANARY_TABLE
         and table.get("table_id") == stages["job_canary"]["table_id"],
         "DAY7_V4_CANARY_TABLE_ID_DRIFT")
    run = owner.service("jobs", "get-run", CANARY_RUN_ID)
    need(str(run.get("run_id")) == CANARY_RUN_ID
         and run.get("state", {}).get("life_cycle_state") == "TERMINATED"
         and run.get("state", {}).get("result_state") == "SUCCESS"
         and len(run.get("tasks", [])) == 1,
         "DAY7_V4_PREVIOUS_CANARY_NOT_SUCCESSFUL")
    task_id = str(run["tasks"][0]["run_id"])
    outcome = owner.service("jobs", "get-run-output", task_id)
    need(outcome.get("notebook_output", {}).get("result")
         == "DAY7_PROTECTED_CANARY_PASS",
         "DAY7_V4_ORIGINAL_NOTEBOOK_RESULT_CHANGED")
    receipts = v3.signed_receipts()
    need(stages["publication"] == {
        "universe_receipt_sha256": receipts[0]["receipt_sha256"],
        "prior_receipt_sha256": receipts[1]["receipt_sha256"],
        "u10_canary_sha256": receipts[2]["receipt_sha256"],
    }, "DAY7_V4_PUBLISHED_RECEIPTS_DRIFT")
    need(not (owner.BASE / "receipts/day7-deployment.json").exists(),
         "DAY7_V4_DEPLOYMENT_ALREADY_SIGNED")
    broker_health()
    # Test the actual old live daemon without its broken SRC client-side
    # regex before any protected module upgrade or LaunchDaemon restart.
    broker_existing_u10_wire(receipts[2])
    listing = owner.run("/bin/launchctl", "print", "system/" + owner.LABEL)
    need(owner.LABEL in listing,
         "DAY7_V4_LAUNCHDAEMON_NOT_REGISTERED")
    owner_table_read()
    job = {
        "job_run_id": CANARY_RUN_ID, "task_run_id": task_id,
        "table": owner.CANARY_TABLE, "table_id": table["table_id"],
        "notebook_sha256": owner.file_digest(owner.CANARY_SOURCE),
        "result": "DAY7_PROTECTED_CANARY_PASS",
        "independent_readback": "OWNER_SQL_EXACT_ONE_ROW",
    }
    return previous, receipts, job


def _protected_atomic_replace(source: bytes, target: Path) -> None:
    """Single exact pinned executable replacement after immutable evidence."""
    existing = target.read_bytes()
    # Versioned immutable backup remains private even after a crash.
    fd = os.open(BROKER_BACKUP, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(existing)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(BROKER_TEMP, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(source)
        stream.flush()
        os.fsync(stream.fileno())
    BROKER_TEMP.chmod(stat.S_IMODE(target.stat().st_mode))
    os.replace(BROKER_TEMP, target)
    need(target.read_bytes() == source and target.stat().st_uid == 0,
         "DAY7_V4_BROKER_UPGRADE_READBACK_FAILED")


def _live_u10(referenced: dict) -> None:
    sys.path.insert(0, str(ROOT / "src"))
    import edp_lab.operating.policy_broker as broker

    importlib.invalidate_caches()
    need(Path(broker.__file__).resolve() == BROKER_REVIEWED.resolve(),
         "DAY7_V4_BROKER_CLIENT_MODULE_NOT_FROM_REVIEWED_REPO")
    receipt = None
    for i in range(30):
        try:
            broker_health()
            receipt = broker.resolve_handoff(
                owner.BASE / "broker.sock", "SRC000002")
            break
        except (ConnectionError, FileNotFoundError, TimeoutError):
            if i == 29:
                raise RuntimeError("DAY7_V4_BROKER_NOT_REACHABLE_AFTER_RESTART") from None
            time.sleep(2)
    need(isinstance(receipt, dict)
         and receipt.get("physical_identity") == "SRC000002"
         and receipt.get("receipt_sha256") == referenced["receipt_sha256"]
         and receipt.get("raw_sha256") == referenced["raw_sha256"]
         and receipt.get("raw_bytes") == referenced["raw_bytes"],
         "DAY7_V4_BROKER_LIVE_U10_SIGNED_RESULT_NOT_EQUAL")


def execute(expected_commit: str) -> dict:
    journal, (universe, prior, u10), job = check(expected_commit)
    new_bytes = BROKER_REVIEWED.read_bytes()
    old_digest = owner.file_digest(BROKER_INSTALLED)
    new_digest = owner.file_digest(BROKER_REVIEWED)
    # Durable one-use upgrade intent BEFORE modifying root executable or
    # restarting the protected LaunchDaemon. On any uncertain state, STOP.
    owner._save_json(RECOVERY_INTENT, {
        "schema": "EDP_DAY7_BROKER_U10_CLIENT_V4_RECOVERY_INTENT_V1",
        "old_deployment_commit": OLD_COMMIT,
        "successor_commit": expected_commit,
        "old_runtime_module_sha256": old_digest,
        "new_runtime_module_sha256": new_digest,
        "physical_identity": "SRC000002",
        "original_canary_run_id": CANARY_RUN_ID,
        "grant_or_job_resubmission": False,
    })
    _protected_atomic_replace(new_bytes, BROKER_INSTALLED)
    # LaunchDaemon owns root-only verifier and M2M config. Restart ONLY this
    # Day 7 service, not Day 5 or Day 6 agents.
    owner.run("/bin/launchctl", "kickstart", "-k", "system/" + owner.LABEL)
    _live_u10(u10)
    journal["reviewed_commit"] = expected_commit
    owner._save_json(owner.JOURNAL, journal)
    owner._mark("broker", {
        "launchd_label": owner.LABEL, "live_m2m_u10": True})

    from edp_lab.operating.authority import verified_document
    from edp_lab.operating.protected_verifier import _sign

    identity = owner._read_json(owner.BASE / "private/service-identity.json")
    receipt = {
        "schema": "EDP_DAY7_DEPLOYMENT_RECEIPT_V1",
        "authority": "protected-verifier-v1",
        "status": "RUNNER_DEPLOYED_AND_VERIFIED",
        "commit": expected_commit,
        "policy_sha256": owner.file_digest(
            owner.BASE / "trust/policy.signed.json"),
        "source_evidence_index_sha256": owner.SOURCE_INDEX_SHA,
        "service_principal_id": SP_ID,
        "service_application_id": identity["application_id"],
        "service_auth": "OAUTH_M2M",
        "service_workspace_access": "OWNER_VERIFIED_AND_M2M_PROBED",
        "raw_write_volume_privilege": False,
        "prior_modify_privilege": False,
        "universe": universe,
        "prior": prior,
        "u10_canary": u10,
        "job_canary": job,
    }
    output = owner.BASE / "receipts/day7-deployment.json"
    need(not output.exists(), "DAY7_V4_DEPLOYMENT_RECEIPT_PREEXISTS")
    _sign(receipt, owner.DAY5 / "private/verifier.pem", output)
    need(verified_document(ROOT, output, owner.BASE / "trust") == receipt,
         "DAY7_V4_DEPLOYMENT_RECEIPT_NOT_VERIFIED")
    owner._mark("deployment", {"receipt_sha256": owner.file_digest(output)})
    return {
        "status": "RUNNER_DEPLOYED_AND_VERIFIED",
        "reviewed_commit": expected_commit,
        "deployment_receipt_sha256": owner.file_digest(output),
        "universe_receipt_sha256": universe["receipt_sha256"],
        "prior_receipt_sha256": prior["receipt_sha256"],
        "u10_canary_receipt_sha256": u10["receipt_sha256"],
        "existing_canary_run_id": CANARY_RUN_ID,
        "day7_autonomous_ready": "NOT_ASSERTED_C3000_U10_GATE_PENDING",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        _journal, _receipts, job = check(args.expected_commit)
        print(json.dumps({
            "status": "DAY7_BROKER_U10_V4_READ_ONLY_PREFLIGHT_PASS",
            "reviewed_commit": args.expected_commit,
            "existing_canary_run_id": job["job_run_id"],
            "no_cloud_or_protected_mutations": True,
        }, sort_keys=True))
    else:
        print(json.dumps(execute(args.expected_commit), sort_keys=True))


if __name__ == "__main__":
    main()
