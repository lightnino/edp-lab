"""Narrow protected recovery of a RAW task that failed before reservation."""

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
