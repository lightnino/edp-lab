"""Narrow protected RAW and SQL recovery transitions."""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    file_digest,
    load_grant,
    verified_document,
)
from edp_lab.operating.protected_cli import databricks_argv
from edp_lab.operating.protected_verifier import _sign


def recover_pre_submission_raw(root: Path, queue_path: Path, grant_path: Path,
                               state_path: Path, trust: Path, key: Path) -> dict | None:
    """Reset only raw-001 after proving both ledger and remote object absent."""
    root = root.resolve()
    if any(path.resolve().is_relative_to(root) for path in (trust, key, state_path)):
        raise Denied("RECOVERY_MUST_BE_PROTECTED")
    state = json.loads(state_path.read_bytes())
    current = state["tasks"].get("raw-001", {})
    if current.get("status") != "FAILED_INTEGRITY":
        return None
    if current.get("reason") != "RAW_PARENT_CREATION_UNCERTAIN":
        raise Denied("RECOVERY_REASON_OUT_OF_SCOPE")
    queue = json.loads(queue_path.read_bytes())
    grant = load_grant(root, grant_path, trust)
    if (queue.get("cohort") != "C2000" or grant.get("authority") != "policy-broker-v1"
            or state["queue_sha256"] != file_digest(queue_path)
            or grant["contracts"]["queue"]["sha256"] != state["queue_sha256"]
            or state["grant_id"] != grant["grant_id"]
            or state["tasks"]["P5"]["status"] != "COMPLETE"
            or any(value["status"] not in {"PLANNED", "COMPLETE", "FAILED_INTEGRITY"}
                   for value in state["tasks"].values())
            or any(key != "P5" and value["status"] == "COMPLETE"
                   for key, value in state["tasks"].items())
            or any(key != "raw-001" and value["status"] == "FAILED_INTEGRITY"
                   for key, value in state["tasks"].items())):
        raise Denied("RECOVERY_CHECKPOINT_OUT_OF_SCOPE")
    task = next(task for task in queue["tasks"] if task["id"] == "raw-001")
    ledger_record = trust.parent / "ledger" / (task["operation_id"] + ".json")
    if ledger_record.exists():
        raise Denied("RECOVERY_LEDGER_RESERVATION_EXISTS")
    parent = task["databricks_path"].rsplit("/", 1)[0]
    result = subprocess.run(databricks_argv("fs", "ls", parent, "-p", "edp-lab",
                                         "-o", "json"), capture_output=True, text=True,
                            timeout=180, check=False)
    if result.returncode:
        if "no such directory" not in result.stderr.lower():
            raise Denied("RECOVERY_REMOTE_ABSENCE_NOT_PROVEN")
    else:
        try:
            inventory = json.loads(result.stdout)
        except ValueError as exc:
            raise Denied("RECOVERY_REMOTE_INVENTORY_INVALID") from exc
        if any(item["name"] == Path(task["source"]["path"]).name
               for item in inventory):
            raise Denied("RECOVERY_REMOTE_OBJECT_EXISTS")
    before = file_digest(state_path)
    receipt = trust.parent / "receipts/recovery-raw-001.json"
    document = {"schema": "EDP_TECHNICAL_RECOVERY_RECEIPT_V1",
                "authority": "protected-verifier-v1", "status": "VERIFIED",
                "cohort": "C2000", "queue_sha256": file_digest(queue_path),
                "task_id": "raw-001", "operation_id": task["operation_id"],
                "reason": "RAW_PARENT_CREATION_UNCERTAIN",
                "state_before_sha256": before, "ledger_reservation_absent": True,
                "remote_object_absent": True, "remote_path": task["databricks_path"],
                "verified_at_utc": datetime.now(UTC).isoformat()}
    if receipt.exists():
        existing = verified_document(root, receipt, trust)
        # A prior recovery receipt may exist after a crash. Its old time is
        # allowed only when all operation and checkpoint evidence matches.
        if any(existing.get(key) != value for key, value in document.items()
               if key != "verified_at_utc"):
            raise Denied("RECOVERY_RECEIPT_CHANGED")
    else:
        _sign(document, key, receipt)
    state["tasks"]["raw-001"] = {"status": "PLANNED", "attempts": 0,
                                   "technical_recovery_receipt": str(receipt)}
    staged = state_path.with_suffix(".next")
    with staged.open("x") as stream:
        json.dump(state, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(staged, state_path)
    events = state_path.parent / "events.jsonl"
    with events.open("a") as stream:
        stream.write(json.dumps({"at": datetime.now(UTC).isoformat(),
                                 "kind": "TECHNICAL_RECOVERY", "task": "raw-001",
                                 "receipt_sha256": file_digest(receipt)}, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return {"status": "VERIFIED_PRE_SUBMISSION_RECOVERY",
            "receipt_sha256": file_digest(receipt)}


def verify_sql_recovery(root: Path, queue_path: Path, state_path: Path,
                        task: dict, recovery: dict, trust: Path) -> dict:
    """Verify the protected link from the signed Queue task to a new operation."""
    receipt = Path(recovery["receipt"])
    if (receipt.resolve().parent != (trust.parent / "receipts").resolve()
            or receipt.name != "recovery-sql-roster.json"):
        raise Denied("SQL_RECOVERY_RECEIPT_PATH_INVALID")
    proof = verified_document(root, receipt, trust)
    if (proof.get("schema") != "EDP_SQL_TECHNICAL_RECOVERY_V1"
            or proof.get("authority") != "protected-verifier-v1"
            or proof.get("status") != "VERIFIED_PRE_SUBMISSION"
            or proof.get("task_id") != "sql-roster"
            or proof.get("queue_sha256") != file_digest(queue_path)
            or proof.get("original_operation_id") != task["operation_id"]
            or proof.get("recovery_operation_id") != recovery.get("operation_id")
            or proof.get("original_ledger_sha256") != recovery.get("original_ledger_sha256")
            or proof.get("disposition_sha256") != recovery.get("disposition_sha256")
            or recovery.get("operation_id") == task["operation_id"]
            or not recovery.get("operation_id", "").endswith("-recovery-v1")):
        raise Denied("SQL_RECOVERY_RECEIPT_INVALID")
    original = trust.parent / "ledger" / (task["operation_id"] + ".json")
    if file_digest(original) != proof["original_ledger_sha256"]:
        raise Denied("SQL_ORIGINAL_LEDGER_CHANGED")
    state = json.loads(state_path.read_bytes())
    if state["tasks"]["sql-roster"].get("technical_recovery") != recovery:
        raise Denied("SQL_RECOVERY_CHECKPOINT_LINK_CHANGED")
    return proof


def recover_pre_submission_sql(root: Path, queue_path: Path, grant_path: Path,
                               state_path: Path, trust: Path, key: Path,
                               disposition_path: Path) -> dict:
    """One protected, owner-dispositioned transition; no SQL is submitted here."""
    root = root.resolve()
    if any(path.resolve().is_relative_to(root) for path in
           (trust, key, state_path, disposition_path)):
        raise Denied("RECOVERY_MUST_BE_PROTECTED")
    queue = json.loads(queue_path.read_bytes())
    state = json.loads(state_path.read_bytes())
    grant = load_grant(root, grant_path, trust)
    tasks = [task for task in queue["tasks"] if task["id"] == "sql-roster"]
    if len(tasks) != 1 or tasks[0]["kind"] != "databricks_write":
        raise Denied("SQL_RECOVERY_TASK_MISSING")
    task = tasks[0]
    current = state["tasks"]["sql-roster"]
    if (queue.get("cohort") != "C2000" or grant.get("authority") != "policy-broker-v1"
            or state["queue_sha256"] != file_digest(queue_path)
            or grant["contracts"]["queue"]["sha256"] != state["queue_sha256"]
            or state["grant_id"] != grant["grant_id"]
            or current.get("status") != "VALIDATING"
            or current.get("technical_recovery") is not None
            or current.get("external", {}).get("status") != "UNCERTAIN_REQUIRES_READBACK"
            or current["external"].get("statement_id") is not None
            or current["external"].get("returncode") != 1
            or sum(v["status"] == "COMPLETE" for v in state["tasks"].values()) != 502
            or sum(v["status"] == "PLANNED" for v in state["tasks"].values()) != 10
            or len(state["tasks"]) != 513):
        raise Denied("SQL_RECOVERY_CHECKPOINT_OUT_OF_SCOPE")
    if any(state["tasks"][t["id"]]["status"] != "COMPLETE" for t in queue["tasks"]
           if t["id"] in {"P5", "P6"}):
        raise Denied("SQL_RECOVERY_DEPENDENCY_INCOMPLETE")
    original = trust.parent / "ledger" / (task["operation_id"] + ".json")
    ledger = json.loads(original.read_bytes())
    if ledger != current["external"]:
        raise Denied("SQL_ORIGINAL_LEDGER_CHECKPOINT_MISMATCH")
    before = file_digest(state_path)
    original_hash = file_digest(original)
    disposition = verified_document(root, disposition_path, trust)
    operation_id = disposition.get("recovery_operation_id")
    if (disposition.get("schema") != "EDP_SQL_PRE_SUBMISSION_DISPOSITION_V1"
            or disposition.get("authority") != "owner-v1"
            or disposition.get("decision") != "AUTHORIZE_DISTINCT_TECHNICAL_RECOVERY"
            or disposition.get("task_id") != "sql-roster"
            or disposition.get("queue_sha256") != file_digest(queue_path)
            or disposition.get("checkpoint_sha256") != before
            or disposition.get("original_operation_id") != task["operation_id"]
            or disposition.get("original_ledger_sha256") != original_hash
            or disposition.get("target_table") != task["databricks_table"]
            or disposition.get("original_statement_id") is not None
            or disposition.get("query_history_result") != "ZERO_COMPLETE_PAGE"
            or disposition.get("query_history_window_start_ms") != 1792791300000
            or disposition.get("query_history_window_end_ms") != 1792792200000
            or disposition.get("uc_target_result") != "AUTHENTICATED_NOT_FOUND"
            or disposition.get("default_auth_result") != "FAILED"
            or disposition.get("explicit_profile_result") != "AUTHENTICATED_EXPECTED_USER"
            or not isinstance(operation_id, str)
            or operation_id != task["operation_id"] + "-recovery-v1"
            or not isinstance(disposition.get("evidence_sha256"), dict)
            or set(disposition["evidence_sha256"]) != {
                "default_auth", "explicit_profile", "query_history", "uc_target"}
            or any(not isinstance(value, str) or len(value) != 64
                   for value in disposition["evidence_sha256"].values())):
        raise Denied("SQL_RECOVERY_DISPOSITION_INVALID")
    evidence_dir = trust.parent / "state/day5/p11_sql_recovery_inspection"
    evidence_files = {
        "default_auth": "default_auth_test.json",
        "explicit_profile": "explicit_profile_auth_test.json",
        "query_history": "protected_query_history_2135_2150_utc.json",
        "uc_target": "uc_target_test.json",
    }
    if any(file_digest(evidence_dir / filename) != disposition["evidence_sha256"][name]
           for name, filename in evidence_files.items()):
        raise Denied("SQL_RECOVERY_EVIDENCE_HASH_CHANGED")
    default_auth = json.loads((evidence_dir / evidence_files["default_auth"]).read_bytes())
    explicit = json.loads((evidence_dir / evidence_files["explicit_profile"]).read_bytes())
    history = json.loads((evidence_dir / evidence_files["query_history"]).read_bytes())
    uc = json.loads((evidence_dir / evidence_files["uc_target"]).read_bytes())
    uc_stdout = (evidence_dir / "uc_target.stdout").read_bytes()
    uc_stderr = (evidence_dir / "uc_target.stderr").read_bytes()
    uc_exit_code = (evidence_dir / "uc_target.exit_code").read_text()
    uc_response = (uc_stderr or uc_stdout).decode("utf-8", errors="replace").strip()
    uc_message = f"Table '{task['databricks_table']}' does not exist."
    try:
        uc_body = json.loads(uc_response.removeprefix("Error: "))
    except ValueError:
        uc_body = None
    uc_not_found = (uc_response == "Error: " + uc_message
                    or isinstance(uc_body, dict)
                    and uc_body.get("error_code") == "TABLE_DOES_NOT_EXIST"
                    and uc_body.get("message") == uc_message)
    if (default_auth.get("exit_code") != 1
            or explicit.get("exit_code") != 0
            or explicit.get("authenticated_user") != "chengzhu13@gmail.com"
            or history.get("has_next_page") is not False
            or history.get("query_start_time_range") != {
                "start_time_ms": 1792791300000,
                "end_time_ms": 1792792200000}
            or any(history.get(key) for key in ("res", "queries", "results"))
            or uc.get("error_code") != "TABLE_DOES_NOT_EXIST"
            or uc.get("table") != task["databricks_table"]
            or uc.get("exit_code") != 1
            or uc_exit_code != "1\n"
            or bool(uc_stdout.strip()) and bool(uc_stderr.strip())
            or uc.get("stdout_sha256") != hashlib.sha256(uc_stdout).hexdigest()
            or uc.get("stderr_sha256") != hashlib.sha256(uc_stderr).hexdigest()
            or not uc_not_found):
        raise Denied("SQL_RECOVERY_EVIDENCE_NOT_PRE_SUBMISSION")
    if (trust.parent / "ledger" / (operation_id + ".json")).exists():
        raise Denied("SQL_RECOVERY_OPERATION_ALREADY_RESERVED")
    receipt = trust.parent / "receipts/recovery-sql-roster.json"
    if receipt.exists():
        raise Denied("SQL_RECOVERY_RECEIPT_ALREADY_EXISTS")
    document = {"schema": "EDP_SQL_TECHNICAL_RECOVERY_V1",
                "authority": "protected-verifier-v1",
                "status": "VERIFIED_PRE_SUBMISSION", "task_id": "sql-roster",
                "queue_sha256": file_digest(queue_path),
                "state_before_sha256": before,
                "original_operation_id": task["operation_id"],
                "original_ledger_sha256": original_hash,
                "recovery_operation_id": operation_id,
                "disposition_sha256": file_digest(disposition_path),
                "verified_at_utc": datetime.now(UTC).isoformat()}
    _sign(document, key, receipt)
    current["technical_recovery"] = {
        "operation_id": operation_id, "receipt": str(receipt),
        "original_ledger_sha256": original_hash,
        "disposition_sha256": file_digest(disposition_path)}
    current["status"] = "PLANNED"
    current["original_external"] = current.pop("external")
    staged = state_path.with_suffix(".next")
    with staged.open("x") as stream:
        json.dump(state, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(staged, state_path)
    events = state_path.parent / "events.jsonl"
    with events.open("a") as stream:
        stream.write(json.dumps({"at": datetime.now(UTC).isoformat(),
                                 "kind": "TECHNICAL_RECOVERY", "task": "sql-roster",
                                 "receipt_sha256": file_digest(receipt)}, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return {"status": "VERIFIED_PRE_SUBMISSION_RECOVERY",
            "recovery_operation_id": operation_id,
            "receipt_sha256": file_digest(receipt)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("queue", type=Path)
    parser.add_argument("grant", type=Path)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("trust", type=Path)
    parser.add_argument("verifier_key", type=Path)
    parser.add_argument("owner_disposition", type=Path)
    args = parser.parse_args()
    print(json.dumps(recover_pre_submission_sql(
        args.root, args.queue, args.grant, args.checkpoint,
        args.trust, args.verifier_key, args.owner_disposition), sort_keys=True))


if __name__ == "__main__":
    main()
