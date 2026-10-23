"""Independent protected readback for exact RAW staging operations."""

import argparse
import base64
import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    canonical,
    digest,
    file_digest,
    load_grant,
    verified_document,
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
            or external.get("status") not in {
                "SUBMITTED_REQUIRES_INDEPENDENT_READBACK",
                "UNCERTAIN_REQUIRES_INDEPENDENT_READBACK"}
            or external.get("remote_sha256") not in (None, source["sha256"])):
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
    submitted_at = external.get("submitted_at_utc")
    try:
        if datetime.fromisoformat(submitted_at).tzinfo is None:
            raise ValueError("timezone required")
    except (TypeError, ValueError) as exc:
        raise Denied("SQL_SUBMISSION_TIME_MISSING") from exc
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
    if terminal.get("statement_id") != statement_id:
        raise Denied("SQL_STATEMENT_ID_MISMATCH")
    if terminal.get("status", {}).get("state") in {"FAILED", "CANCELED", "CLOSED"}:
        raise Denied("SQL_STATEMENT_FAILED")
    if terminal.get("status", {}).get("state") != "SUCCEEDED":
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
                "submitted_at_utc": submitted_at,
                "attested_at_utc": datetime.now(UTC).isoformat(),
                "uc_table_id": uc["table_id"],
                "terminal_response_sha256": digest(canonical(terminal)),
                "uc_response_sha256": digest(canonical(uc))}
    _sign(document, key, output)
    return {"status": "VERIFIED", "receipt_sha256": file_digest(output),
            "operation_id": task["operation_id"], "statement_id": statement_id}


def attest_cohort(root: Path, queue_path: Path, grant_path: Path, state_path: Path,
                  task_id: str, trust: Path, key: Path) -> dict:
    """Independently attest exact C2000 publication and its live RAW receipts."""
    root = root.resolve()
    if any(p.resolve().is_relative_to(root) for p in (trust, key)):
        raise Denied("VERIFIER_MUST_BE_PROTECTED")
    queue_path = queue_path.resolve(strict=True)
    if not queue_path.is_relative_to(root):
        raise Denied("QUEUE_OUTSIDE_REPO")
    queue = json.loads(queue_path.read_bytes())
    tasks = [task for task in queue["tasks"] if task["id"] == task_id]
    if len(tasks) != 1 or tasks[0]["kind"] != "cohort_admit":
        raise Denied("COHORT_ADMISSION_TASK_REQUIRED")
    task = tasks[0]
    grant = load_grant(root, grant_path, trust)
    state = json.loads(state_path.read_bytes())
    if (grant["authority"] != "policy-broker-v1"
            or state["queue_sha256"] != file_digest(queue_path)
            or grant["contracts"]["queue"]["sha256"] != state["queue_sha256"]
            or state["grant_id"] != grant["grant_id"]
            or state["tasks"][task_id]["status"] != "VALIDATING"):
        raise Denied("COHORT_CHECKPOINT_MISMATCH")
    freeze_path = root / "metadata/freezes/C2000_v1/freeze.json"
    freeze = json.loads(freeze_path.read_bytes())
    if (freeze.get("schema") != "C2000_INPUT_FREEZE_V1"
            or freeze.get("status") != "FROZEN_INPUT_NOT_RESULT"
            or freeze.get("queue_sha256") != file_digest(queue_path)
            or freeze.get("candidate_sha256") != grant["contracts"]["candidate"]["sha256"]
            or len(freeze.get("raw_receipts_sha256", {})) != 500
            or state["tasks"][task_id].get("external", {}).get("freeze_sha256")
            != file_digest(freeze_path)):
        raise Denied("COHORT_FREEZE_NOT_VERIFIED")
    folder = freeze_path.parent
    for name, expected in freeze["files_sha256"].items():
        if file_digest(folder / name) != expected:
            raise Denied("COHORT_FILE_CHANGED")
    if file_digest(root / "metadata/cohorts/C2000.csv") != freeze[
            "files_sha256"]["C2000.csv"]:
        raise Denied("COHORT_ALIAS_CHANGED")
    combined = json.loads((folder / "C2000.bindings.json").read_bytes())
    new = json.loads((folder / "N500.bindings.json").read_bytes())
    if (len(combined) != 2000 or len(new) != 500
            or {row["source_identity"]: row["raw_sha256"] for row in combined}
            != grant["sources"]):
        raise Denied("COHORT_SOURCE_MAP_MISMATCH")
    for source in new:
        identity = source["source_identity"]
        receipt = next((task for task in queue["tasks"] if task["kind"] == "raw_stage"
                        and task["source"]["identity"] == identity), None)
        if receipt is None or file_digest(Path(receipt["external_receipt"])) != freeze[
                "raw_receipts_sha256"].get(identity):
            raise Denied("COHORT_RAW_RECEIPT_CHANGED")
        signed = verified_document(root, Path(receipt["external_receipt"]), trust)
        exact_request = task_request(root, queue, queue_path, receipt, grant_path)
        if (signed.get("authority") != "protected-verifier-v1"
                or signed.get("schema") != "EDP_EXTERNAL_OPERATION_RECEIPT_V1"
                or signed.get("operation_id") != receipt["operation_id"]
                or signed.get("request_sha256") != digest(canonical(exact_request))
                or signed.get("remote_sha256") != source["raw_sha256"]
                or signed.get("remote_path") != source["remote_raw_path"]
                or signed.get("status") != "VERIFIED"
                or signed.get("live_readback") is not True):
            raise Denied("COHORT_RAW_RECEIPT_INVALID")
    output = Path(task["external_receipt"])
    if output.parent.resolve() != (trust.parent / "receipts").resolve():
        raise Denied("RECEIPT_OUTSIDE_PROTECTED_STORE")
    request = task_request(root, queue, queue_path, task, grant_path)
    document = {"schema": "EDP_EXTERNAL_OPERATION_RECEIPT_V1",
                "authority": "protected-verifier-v1",
                "operation_id": task["operation_id"],
                "request_sha256": digest(canonical(request)),
                "status": "VERIFIED", "live_readback": True,
                "freeze_sha256": file_digest(freeze_path),
                "cohort_csv_sha256": freeze["files_sha256"]["C2000.csv"],
                "physical_sources": 2000, "new_sources": 500}
    _sign(document, key, output)
    return {"status": "VERIFIED", "receipt_sha256": file_digest(output),
            "operation_id": task["operation_id"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("raw", "sql", "cohort"))
    for name in ("root", "queue", "grant", "state", "task_id", "trust", "key"):
        parser.add_argument(name, type=Path if name != "task_id" else str)
    parser.add_argument("--databricks-user", required=True)
    args = parser.parse_args()
    os.environ["EDP_DATABRICKS_RUN_AS_USER"] = args.databricks_user
    verify = {"raw": attest_raw, "sql": attest_sql,
              "cohort": attest_cohort}[args.kind]
    print(json.dumps(verify(args.root, args.queue, args.grant, args.state,
                            args.task_id, args.trust, args.key), sort_keys=True))


if __name__ == "__main__":
    main()
