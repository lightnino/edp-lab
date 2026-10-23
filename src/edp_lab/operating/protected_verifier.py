"""Independent protected readback for exact RAW staging operations."""

import argparse
import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    canonical,
    digest,
    file_digest,
    load_grant,
)
from edp_lab.operating.protected_cli import databricks_argv
from edp_lab.operating.runner import task_request


def _remote_bytes(path: str, timeout: int) -> bytes:
    result = subprocess.run(databricks_argv("fs", "cat", path, "-p", "edp-lab"),
                            capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        raise Denied("REMOTE_RAW_READBACK_FAILED")
    return result.stdout


def _remote_json(path: str, timeout: int) -> dict:
    result = subprocess.run(databricks_argv("api", "get", path, "-p", "edp-lab", "-o", "json"),
                            capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        raise Denied("REMOTE_SQL_READBACK_FAILED")
    return json.loads(result.stdout)


def _sign(document: dict, key: Path, output: Path) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        payload = Path(temporary) / "payload"
        signature = Path(temporary) / "signature"
        payload.write_bytes(canonical(document))
        subprocess.run(["/opt/homebrew/bin/openssl", "pkeyutl", "-sign", "-inkey", str(key),
                        "-rawin", "-in", str(payload), "-out", str(signature)],
                       check=True, capture_output=True)
        envelope = {"document": document,
                    "signature_base64": base64.b64encode(signature.read_bytes()).decode()}
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical(envelope))
        stream.flush()
        os.fsync(stream.fileno())


def attest_raw(root: Path, queue_path: Path, grant_path: Path, state_path: Path,
               task_id: str, trust: Path, key: Path) -> dict:
    root = root.resolve()
    if any(p.resolve().is_relative_to(root) for p in (trust, key)):
        raise Denied("VERIFIER_MUST_BE_PROTECTED")
    queue_path = queue_path.resolve(strict=True)
    if not queue_path.is_relative_to(root):
        raise Denied("QUEUE_OUTSIDE_REPO")
    queue = json.loads(queue_path.read_bytes())
    tasks = [task for task in queue["tasks"] if task["id"] == task_id]
    if len(tasks) != 1 or tasks[0]["kind"] != "raw_stage":
        raise Denied("RAW_STAGE_TASK_REQUIRED")
    task = tasks[0]
    grant = load_grant(root, grant_path, trust)
    state = json.loads(state_path.read_bytes())
    if (grant["authority"] != "policy-broker-v1"
            or state["queue_sha256"] != file_digest(queue_path)
            or grant["contracts"]["queue"]["sha256"] != state["queue_sha256"]
            or state["grant_id"] != grant["grant_id"]
            or state["tasks"][task_id]["status"] != "VALIDATING"):
        raise Denied("RAW_STAGE_CHECKPOINT_MISMATCH")
    source = task["source"]
    if grant["sources"].get(source["identity"]) != source["sha256"]:
        raise Denied("RAW_SOURCE_OUT_OF_GRANT")
    external = state["tasks"][task_id].get("external", {})
    if (external.get("remote_path") != task["databricks_path"]
            or external.get("remote_sha256") != source["sha256"]):
        raise Denied("RAW_STAGE_SUBMISSION_MISMATCH")
    observed = digest(_remote_bytes(task["databricks_path"], grant["limits"][
        "runtime_seconds"]))
    if observed != source["sha256"]:
        raise Denied("INDEPENDENT_REMOTE_RAW_HASH_MISMATCH")
    output = Path(task["external_receipt"])
    if output.parent.resolve() != (trust.parent / "receipts").resolve():
        raise Denied("RECEIPT_OUTSIDE_PROTECTED_STORE")
    request = task_request(root, queue, queue_path, task, grant_path)
    document = {"schema": "EDP_EXTERNAL_OPERATION_RECEIPT_V1",
                "authority": "protected-verifier-v1",
                "operation_id": task["operation_id"],
                "request_sha256": digest(canonical(request)),
                "status": "VERIFIED", "live_readback": True,
                "remote_sha256": observed, "remote_path": task["databricks_path"]}
    _sign(document, key, output)
    return {"status": "VERIFIED", "receipt_sha256": file_digest(output),
            "operation_id": task["operation_id"]}


def attest_sql(root: Path, queue_path: Path, grant_path: Path, state_path: Path,
               task_id: str, trust: Path, key: Path) -> dict:
    """Check terminal SQL success and live UC identity before signing a receipt."""
    root = root.resolve()
    if any(p.resolve().is_relative_to(root) for p in (trust, key)):
        raise Denied("VERIFIER_MUST_BE_PROTECTED")
    queue_path = queue_path.resolve(strict=True)
    if not queue_path.is_relative_to(root):
        raise Denied("QUEUE_OUTSIDE_REPO")
    queue = json.loads(queue_path.read_bytes())
    tasks = [task for task in queue["tasks"] if task["id"] == task_id]
    if len(tasks) != 1 or tasks[0]["kind"] != "databricks_write":
        raise Denied("SQL_WRITE_TASK_REQUIRED")
    task = tasks[0]
    grant = load_grant(root, grant_path, trust)
    state = json.loads(state_path.read_bytes())
    if (grant["authority"] != "policy-broker-v1"
            or state["queue_sha256"] != file_digest(queue_path)
            or grant["contracts"]["queue"]["sha256"] != state["queue_sha256"]
            or state["grant_id"] != grant["grant_id"]
            or state["tasks"][task_id]["status"] != "VALIDATING"):
        raise Denied("SQL_WRITE_CHECKPOINT_MISMATCH")
    external = state["tasks"][task_id].get("external", {})
    statement_id = external.get("statement_id")
    if not isinstance(statement_id, str) or not statement_id:
        raise Denied("SQL_STATEMENT_ID_MISSING")
    statement_path = (root / task["statement_path"]).resolve(strict=True)
    contract_name = task.get("statement_contract", "statement")
    if (not statement_path.is_relative_to(root)
            or file_digest(statement_path) != grant["contracts"][contract_name]["sha256"]):
        raise Denied("SQL_STATEMENT_PIN_CHANGED")
    expected = json.loads(statement_path.read_bytes())["statement"]
    if task["databricks_table"] not in expected:
        raise Denied("SQL_TARGET_MISMATCH")
    terminal = _remote_json("/api/2.0/sql/statements/" + statement_id,
                            grant["limits"]["runtime_seconds"])
    if (terminal.get("statement_id") != statement_id
            or terminal.get("status", {}).get("state") != "SUCCEEDED"):
        raise Denied("SQL_STATEMENT_NOT_SUCCEEDED")
    if terminal.get("statement") not in (None, expected):
        raise Denied("REMOTE_SQL_TEXT_MISMATCH")
    uc = _remote_json("/api/2.1/unity-catalog/tables/" + task["databricks_table"],
                      grant["limits"]["runtime_seconds"])
    if (uc.get("full_name") != task["databricks_table"]
            or not isinstance(uc.get("table_id"), str) or not uc["table_id"]):
        raise Denied("SQL_RESULT_OBJECT_NOT_VERIFIED")
    output = Path(task["external_receipt"])
    if output.parent.resolve() != (trust.parent / "receipts").resolve():
        raise Denied("RECEIPT_OUTSIDE_PROTECTED_STORE")
    request = task_request(root, queue, queue_path, task, grant_path)
    document = {"schema": "EDP_EXTERNAL_OPERATION_RECEIPT_V1",
                "authority": "protected-verifier-v1",
                "operation_id": task["operation_id"],
                "request_sha256": digest(canonical(request)),
                "status": "VERIFIED", "live_readback": True,
                "statement_id": statement_id, "table": uc["full_name"],
                "uc_table_id": uc["table_id"],
                "terminal_response_sha256": digest(canonical(terminal)),
                "uc_response_sha256": digest(canonical(uc))}
    _sign(document, key, output)
    return {"status": "VERIFIED", "receipt_sha256": file_digest(output),
            "operation_id": task["operation_id"], "statement_id": statement_id}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("raw", "sql"))
    for name in ("root", "queue", "grant", "state", "task_id", "trust", "key"):
        parser.add_argument(name, type=Path if name != "task_id" else str)
    parser.add_argument("--databricks-user", required=True)
    args = parser.parse_args()
    os.environ["EDP_DATABRICKS_RUN_AS_USER"] = args.databricks_user
    verify = attest_raw if args.kind == "raw" else attest_sql
    print(json.dumps(verify(args.root, args.queue, args.grant, args.state,
                            args.task_id, args.trust, args.key), sort_keys=True))


if __name__ == "__main__":
    main()
