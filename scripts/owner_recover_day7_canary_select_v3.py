"""Bounded Day 7 continuation after Owner-only canary SELECT failure.

Only the old canary table's SELECT permission may be granted to the known Owner.
Reuse the existing protected OAuth identity, signed receipts and successful
non-admin Job. Never recreate secrets, resubmit canary, or reprocess RAW.

Requires pinned clean HEAD and root on the Owner's Mac.
--check-only verifies the old state and live evidence without writes.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/Users/lightnino/Projects/edp-lab-day7-universe")
sys.path.insert(0, str(ROOT / "scripts"))
import owner_install_day7 as day7

OLD_COMMIT = "4c5f399dd34729925d19d13b687c89c066dc304d"
SP_ID = "78491734320299"
OWNER = "chengzhu13@gmail.com"
GRANT_INTENT = day7.BASE / "ledger/day7-owner-select-recovery-intent-v3.json"
ALLOWED_DIFF = {
    "scripts/owner_recover_day7_canary_select_v3.py",
    "tests/operating/test_day7_canary_select_v3.py",
}


def need(ok: bool, name: str) -> None:
    if not ok:
        raise RuntimeError(name)


def git(*args: str) -> str:
    return subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C",
         str(ROOT), *args], capture_output=True, text=True,
        check=True, timeout=60).stdout.strip()


def protected(path: Path) -> None:
    need(path.is_file() and not path.is_symlink()
         and path.stat().st_uid == 0
         and not path.stat().st_mode & 0o022,
         "DAY7_PROTECTED_FILE_NOT_TRUSTED:" + path.name)


def owner_sql(statement: str) -> dict:
    """Bounded new SQL statement, with error code rather than hidden status."""
    data = day7.admin(
        "api", "post", "/api/2.0/sql/statements", "--json",
        json.dumps({"warehouse_id": day7.WAREHOUSE, "statement": statement,
                    "disposition": "INLINE", "wait_timeout": "50s",
                    "on_wait_timeout": "CONTINUE"}))
    started = time.monotonic()
    while data.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        need(time.monotonic() - started < 180,
             "DAY7_OWNER_SQL_UNCERTAIN_" + str(data.get("statement_id")))
        time.sleep(3)
        data = day7.admin(
            "api", "get", "/api/2.0/sql/statements/" + data["statement_id"])
    if data.get("status", {}).get("state") != "SUCCEEDED":
        err = data.get("status", {}).get("error", {})
        raise RuntimeError(
            "DAY7_OWNER_SQL_FAILED:"
            + str(err.get("error_code", "UNKNOWN"))[:64]
            + ":" + str(data.get("status", {}).get("sql_state", "UNKNOWN"))[:12]
            + ":statement_id=" + str(data.get("statement_id"))
            + ":STOP_NO_AUTOMATIC_RETRY")
    return data


def signed_receipts() -> tuple[dict, dict, dict]:
    sys.path.insert(0, str(ROOT / "src"))
    from edp_lab.operating.authority import verified_document

    docs = []
    for filename in ("day7-universe.json", "c2000-prior.json",
                     "day7-u10-SRC000002.json"):
        path = day7.BASE / "receipts" / filename
        protected(path)
        body = verified_document(ROOT, path, day7.BASE / "trust")
        docs.append((path, body))
    (u_path, u), (p_path, p), (h_path, h) = docs
    need(u.get("status") == "UNIVERSE_PUBLISHED_AND_VERIFIED"
         and u.get("manifest_sha256") == day7.MANIFEST_SHA
         and u.get("owner_decision_sha256") == day7.DECISION_SHA
         and u.get("members") == 3821 and u.get("raw_uploads") == 0,
         "DAY7_UNIVERSE_SIGNED_RECEIPT_INVALID")
    need(p.get("status") == "VERIFIED" and p.get("cohort") == "C2000"
         and p.get("live_readback") is True
         and len(p.get("identities", [])) == 2000,
         "DAY7_C2000_SIGNED_RECEIPT_INVALID")
    need(h.get("status") == "VERIFIED"
         and h.get("physical_identity") == "SRC000002"
         and h.get("manifest_sha256") == day7.MANIFEST_SHA
         and h.get("source_evidence_index_sha256") == day7.SOURCE_INDEX_SHA
         and h.get("readback_mode") == "CURRENT_FULL_HASH"
         and h.get("live_readback") is True
         and h.get("remote_bytes") == 349417
         and h.get("remote_sha256")
         == "1d3656d26cfddd35363ce8022d50cbb5342ae2b1cfebee74f3c3b168b0f0f808",
         "DAY7_CANARY_U10_SIGNED_RECEIPT_INVALID")
    universe = {"status": u["status"], "receipt": str(u_path),
                "receipt_sha256": day7.file_digest(u_path)}
    prior = {"status": p["status"], "receipt": str(p_path),
             "receipt_sha256": day7.file_digest(p_path)}
    handoff = {"status": h["status"], "receipt": str(h_path),
               "receipt_sha256": day7.file_digest(h_path),
               "physical_identity": h["physical_identity"],
               "source_instance_id": h["source_instance_id"],
               "raw_sha256": h["remote_sha256"],
               "raw_bytes": h["remote_bytes"],
               "remote_raw_path": h["remote_path"]}
    return universe, prior, handoff


def precheck(commit: str) -> tuple[dict, tuple[dict, dict, dict], dict]:
    need(os.geteuid() == 0, "DAY7_OWNER_ROOT_REQUIRED")
    need(len(commit) == 40 and git("rev-parse", "HEAD") == commit
         and not git("status", "--porcelain"),
         "DAY7_HEAD_UNPINNED_OR_WORKTREE_DIRTY")
    changed = set(git("diff", "--name-only", OLD_COMMIT, commit).splitlines())
    need(changed == ALLOWED_DIFF, "DAY7_UNEXPECTED_SUCCESSOR_CODE_CHANGES")
    need(day7.BASE.is_dir() and not day7.BASE.is_symlink()
         and day7.BASE.stat().st_uid == 0
         and stat.S_IMODE(day7.BASE.stat().st_mode) == 0o710
         and not day7.PLIST.exists(),
         "DAY7_EXISTING_PROTECTED_RUNTIME_CHANGED")
    need(not GRANT_INTENT.exists() and not GRANT_INTENT.is_symlink(),
         "DAY7_OWNER_SELECT_RECOVERY_ALREADY_ATTEMPTED")
    protected(day7.JOURNAL)
    protected(day7.BASE / "private/databrickscfg")
    protected(day7.BASE / "private/service-identity.json")
    protected(day7.BASE / "ledger/canary-submit-intent.json")
    protected(day7.BASE / "ledger/canary-run-id")
    need(day7.file_digest(day7.POLICY) == day7.POLICY_SHA
         and day7.file_digest(day7.SOURCE_INDEX) == day7.SOURCE_INDEX_SHA
         and day7.file_digest(
             ROOT / "metadata/source_universes/approved/manifest.json")
         == day7.MANIFEST_SHA,
         "DAY7_PINNED_PUBLICATION_INPUT_CHANGED")
    journal = day7._read_json(day7.JOURNAL)
    need({k: v for k, v in journal.items() if k != "completed"}
         == day7._install_intent(OLD_COMMIT),
         "DAY7_OLD_INSTALL_JOURNAL_COMMIT_CHANGED")
    stages = journal.get("completed", {})
    expected = {"protected_files", "service_identity", "workspace_assignment",
                "service_auth", "permissions", "publication",
                "secret_duration_v2_recovery"}
    need(expected <= set(stages) and not set(stages) & {
        "job_canary", "broker", "deployment"},
        "DAY7_EXISTING_JOURNAL_STAGES_UNEXPECTED")
    need(stages["secret_duration_v2_recovery"] == {
        "from_commit": "c2c4c1e5ffb4f795d345ce95023287b174c13b28",
        "service_principal_id": SP_ID, "m2m_verified": True},
        "DAY7_V2_CREDENTIAL_RECOVERY_CHANGED")
    identity = day7._read_json(day7.BASE / "private/service-identity.json")
    need(str(identity.get("service_principal_id")) == SP_ID
         and isinstance(identity.get("application_id"), str)
         and identity["application_id"],
         "DAY7_EXISTING_SP_PIN_CHANGED")
    owner = day7.admin("current-user", "me")
    need(owner.get("userName") == OWNER, "DAY7_OWNER_IDENTITY_CHANGED")
    m2m = day7.service("current-user", "me")
    need(str(m2m.get("id")) == SP_ID and m2m.get("active", True),
         "DAY7_EXISTING_M2M_IDENTITY_CHANGED")
    uc = day7.service("tables", "get", day7.CANARY_TABLE)
    need(uc.get("full_name") == day7.CANARY_TABLE and uc.get("table_id"),
         "DAY7_EXISTING_CANARY_TABLE_CHANGED")
    intent = day7._read_json(day7.BASE / "ledger/canary-submit-intent.json")
    payload = intent.get("payload", {})
    need(intent.get("source_sha256") == day7.file_digest(day7.CANARY_SOURCE)
         and payload.get("idempotency_token")
         == "day7-pr80-canary-" + OLD_COMMIT[:32]
         and payload.get("run_name") == "day7-pr80-protected-canary"
         and len(payload.get("tasks", [])) == 1
         and payload["tasks"][0].get("notebook_task", {}).get("notebook_path")
         == day7.NOTEBOOK, "DAY7_CANARY_ORIGINAL_SUBMISSION_CHANGED")
    run_id = (day7.BASE / "ledger/canary-run-id").read_text().strip()
    need(run_id.isdecimal(), "DAY7_OLD_CANARY_RUN_ID_INVALID")
    run = day7.service("jobs", "get-run", run_id)
    need(str(run.get("run_id")) == run_id
         and run.get("state", {}).get("life_cycle_state") == "TERMINATED"
         and run.get("state", {}).get("result_state") == "SUCCESS"
         and len(run.get("tasks", [])) == 1,
         "DAY7_ORIGINAL_CANARY_JOB_NOT_SUCCESSFUL")
    task_id = str(run["tasks"][0].get("run_id"))
    need(task_id.isdecimal(), "DAY7_ORIGINAL_CANARY_TASK_INVALID")
    outcome = day7.service("jobs", "get-run-output", task_id)
    need(outcome.get("notebook_output", {}).get("result")
         == "DAY7_PROTECTED_CANARY_PASS",
         "DAY7_ORIGINAL_NOTEBOOK_RESULT_CHANGED")
    receipts = signed_receipts()
    need(stages["publication"] == {
        "universe_receipt_sha256": receipts[0]["receipt_sha256"],
        "prior_receipt_sha256": receipts[1]["receipt_sha256"],
        "u10_canary_sha256": receipts[2]["receipt_sha256"]},
        "DAY7_PUBLICATION_JOURNAL_RECEIPTS_CHANGED")
    need(not (day7.BASE / "receipts/day7-deployment.json").exists(),
         "DAY7_DEPLOYMENT_ALREADY_SIGNED")
    job = {"job_run_id": run_id, "task_run_id": task_id,
           "table": day7.CANARY_TABLE, "table_id": uc["table_id"],
           "notebook_sha256": day7.file_digest(day7.CANARY_SOURCE),
           "result": "DAY7_PROTECTED_CANARY_PASS",
           "independent_readback": "OWNER_SQL_EXACT_ONE_ROW"}
    return journal, receipts, job


def execute(commit: str) -> dict:
    journal, (universe, prior, handoff), job = precheck(commit)
    # Durable one-use grant intent precedes the only narrowly scoped GRANT.
    day7._save_json(GRANT_INTENT, {
        "schema": "EDP_DAY7_CANARY_OWNER_READBACK_V3_INTENT",
        "old_commit": OLD_COMMIT, "successor_commit": commit,
        "table": day7.CANARY_TABLE, "owner": OWNER,
        "privilege": "SELECT", "existing_run_id": job["job_run_id"]})
    quoted_owner = chr(96) + OWNER + chr(96)
    owner_sql("GRANT SELECT ON TABLE " + day7.CANARY_TABLE
              + " TO " + quoted_owner)
    readback = owner_sql("SELECT universe_sha256, owner_decision_sha256 FROM "
                         + day7.CANARY_TABLE)
    need(readback.get("result", {}).get("data_array")
         == [[day7.MANIFEST_SHA, day7.DECISION_SHA]],
         "DAY7_INDEPENDENT_OWNER_SQL_VALUE_MISMATCH_NO_RETRY")
    # Do not call canary() or publication() again: already accepted!
    journal["reviewed_commit"] = commit
    day7._save_json(day7.JOURNAL, journal)
    day7._mark("job_canary", {
        "run_id": job["job_run_id"],
        "table_id": job["table_id"],
        "readback": "OWNER_SQL_EXACT_ONE_ROW"})
    day7.install_broker()
    day7._mark("broker", {
        "launchd_label": day7.LABEL, "live_m2m_u10": True})
    from edp_lab.operating.authority import verified_document
    from edp_lab.operating.protected_verifier import _sign
    identity = day7._read_json(day7.BASE / "private/service-identity.json")
    document = {
        "schema": "EDP_DAY7_DEPLOYMENT_RECEIPT_V1",
        "authority": "protected-verifier-v1",
        "status": "RUNNER_DEPLOYED_AND_VERIFIED",
        "commit": commit,
        "policy_sha256": day7.file_digest(
            day7.BASE / "trust/policy.signed.json"),
        "source_evidence_index_sha256": day7.SOURCE_INDEX_SHA,
        "service_principal_id": SP_ID,
        "service_application_id": identity["application_id"],
        "service_auth": "OAUTH_M2M",
        "service_workspace_access": "OWNER_VERIFIED_AND_M2M_PROBED",
        "raw_write_volume_privilege": False,
        "prior_modify_privilege": False,
        "universe": universe, "prior": prior,
        "u10_canary": handoff, "job_canary": job,
    }
    path = day7.BASE / "receipts/day7-deployment.json"
    need(not path.exists(), "DAY7_DEPLOYMENT_RECEIPT_ALREADY_EXISTS")
    _sign(document, day7.DAY5 / "private/verifier.pem", path)
    need(verified_document(ROOT, path, day7.BASE / "trust") == document,
         "DAY7_DEPLOYMENT_SIGNATURE_FAILED")
    day7._mark("deployment", {"receipt_sha256": day7.file_digest(path)})
    return {
        "status": "RUNNER_DEPLOYED_AND_VERIFIED",
        "reviewed_commit": commit,
        "deployment_receipt_sha256": day7.file_digest(path),
        "universe_receipt_sha256": universe["receipt_sha256"],
        "prior_receipt_sha256": prior["receipt_sha256"],
        "u10_canary_receipt_sha256": handoff["receipt_sha256"],
        "existing_canary_run_id": job["job_run_id"],
        "day7_autonomous_ready": "NOT_ASSERTED_C3000_U10_GATE_PENDING",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        _journal, _receipts, job = precheck(args.expected_commit)
        print(json.dumps({
            "status": "DAY7_CANARY_OWNER_SELECT_READ_ONLY_PREFLIGHT_PASS",
            "existing_canary_run_id": job["job_run_id"],
            "reviewed_commit": args.expected_commit,
            "no_cloud_writes": True,
        }, sort_keys=True))
    else:
        print(json.dumps(execute(args.expected_commit), sort_keys=True))


if __name__ == "__main__":
    main()
