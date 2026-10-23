"""Guarded external-write adapters for future tasks.

Callers supply a signed grant and exact pinned request. The reservation is durable:
an uncertain external result requires readback and human disposition, not replay.
"""

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    authorize,
    canonical,
    digest,
    file_digest,
    load_grant,
    protected_trust_dir,
    verified_document,
)
from edp_lab.operating.protected_cli import databricks_argv, git_argv


def _reserve(ledger: Path, operation_id: str, request: dict) -> Path:
    ledger.mkdir(parents=True, exist_ok=True)
    if not operation_id or "/" in operation_id or ".." in operation_id:
        raise Denied("INVALID_OPERATION_ID")
    record = ledger / (operation_id + ".json")
    try:
        fd = os.open(record, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Denied("OPERATION_REPLAY_OR_UNCERTAIN_RESULT") from exc
    with os.fdopen(fd, "w") as stream:
        json.dump({"status": "RESERVED", "request_sha256": digest(
            canonical(request))}, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    return record


def _persist_sql_result(record: Path, result: dict) -> None:
    with record.open("w") as stream:
        json.dump(result, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def databricks_write(root: Path, grant: dict, request: dict, ledger: Path,
                     *, execute: bool = False) -> dict:
    """Submit one exact pinned statement; no implicit retry or overwrite."""
    if request["operation"] != "databricks_write":
        raise Denied("WRONG_BOUNDARY")
    if ledger.resolve().is_relative_to(root.resolve()):
        raise Denied("LEDGER_MUST_BE_OUTSIDE_WORKTREE")
    if execute:
        fresh = load_grant(root, Path(request["grant_path"]), protected_trust_dir(root))
        if fresh != grant:
            raise Denied("GRANT_CHANGED_AT_WRITE_BOUNDARY")
    authorize(grant, request, root=root)
    statement = (root / request["statement_path"]).resolve(strict=True)
    if not statement.is_relative_to(root.resolve()):
        raise Denied("STATEMENT_OUTSIDE_REPO")
    name = request.get("statement_contract", "statement")
    if (name not in grant["contracts"]
            or request.get("contracts", {}).get(name, {}).get("path")
            != request["statement_path"]
            or file_digest(statement) != grant["contracts"][name]["sha256"]):
        raise Denied("STATEMENT_HASH_CHANGED")
    content = json.loads(statement.read_bytes())
    if not isinstance(content, dict) or not isinstance(content.get("statement"), str):
        raise Denied("INVALID_PINNED_SQL_REQUEST")
    sql = content["statement"].strip()
    # Day 2-4 uses versioned CREATE TABLE AS SELECT and CREATE VIEW AS
    # SELECT/WITH. A pinned request is still not a general SQL execution grant.
    import re

    no_header = re.sub(r"\A(?:--[^\n]*\n\s*)*", "", sql)
    match = re.match(
        r"\ACREATE\s+(TABLE|VIEW)\s+([A-Za-z_][\w]*\.[A-Za-z_][\w]*"
        r"\.[A-Za-z_][\w]*)\s+(.*)\Z",
        no_header, flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None or ";" in no_header.rstrip(";"):
        raise Denied("NON_EXCLUSIVE_WRITE")
    kind, target, remainder = match.groups()
    if (not isinstance(request.get("databricks_table"), str)
            or target.lower() != request["databricks_table"].lower()):
        raise Denied("TABLE_NOT_IN_STATEMENT")
    if (kind.upper() == "TABLE" and not re.match(
            r"(?:USING\s+DELTA\s+)?AS\s+(SELECT|WITH)\b", remainder, re.IGNORECASE)
            or kind.upper() == "VIEW" and not re.match(
                r"AS\s+(SELECT|WITH)\b", remainder, re.IGNORECASE)):
        raise Denied("NON_EXCLUSIVE_WRITE")
    if re.search(r"\b(OR\s+REPLACE|IF\s+NOT\s+EXISTS)\b", no_header, re.IGNORECASE):
        raise Denied("NON_EXCLUSIVE_WRITE")
    if not execute:
        return {"status": "AUTHORIZED_DRY_RUN"}
    record = _reserve(ledger, request["operation_id"], request)
    submitted_at = datetime.now(UTC).isoformat()
    try:
        outcome = subprocess.run(databricks_argv("api", "post", "/api/2.0/sql/statements",
                                                 "--json", "@" + str(statement),
                                                 "-p", "edp-lab", "-o", "json"),
                                 capture_output=True, text=True,
                                 timeout=grant["limits"]["runtime_seconds"], check=False)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        result = {"status": "UNCERTAIN_REQUIRES_READBACK", "statement_id": None,
                  "remote_state": None, "submitted_at_utc": submitted_at,
                  "returncode": None,
                  "stdout_sha256": digest(stdout.encode() if isinstance(stdout, str) else stdout),
                  "stderr_sha256": digest(stderr.encode() if isinstance(stderr, str) else stderr)}
        _persist_sql_result(record, result)
        return result
    except OSError:
        result = {"status": "UNCERTAIN_REQUIRES_READBACK", "statement_id": None,
                  "remote_state": None, "submitted_at_utc": submitted_at,
                  "returncode": None, "stdout_sha256": digest(b""),
                  "stderr_sha256": digest(b"")}
        _persist_sql_result(record, result)
        return result
    try:
        remote = json.loads(outcome.stdout) if outcome.returncode == 0 else {}
    except ValueError:
        remote = {}
    statement_id = remote.get("statement_id") if isinstance(remote, dict) else None
    status = remote.get("status") if isinstance(remote, dict) else None
    remote_state = status.get("state") if isinstance(status, dict) else None
    result = {"status": "SUBMITTED_REQUIRES_READBACK" if isinstance(
                  statement_id, str) and statement_id and outcome.returncode == 0
                  else "UNCERTAIN_REQUIRES_READBACK",
              "statement_id": statement_id, "remote_state": remote_state,
              "submitted_at_utc": submitted_at,
              "returncode": outcome.returncode,
              "stdout_sha256": digest(outcome.stdout.encode()),
              "stderr_sha256": digest(outcome.stderr.encode())}
    _persist_sql_result(record, result)
    return result


def raw_stage(root: Path, grant: dict, request: dict, ledger: Path,
              *, execute: bool = False) -> dict:
    """Stage one immutable RAW source and read back its exact remote bytes."""
    if request["operation"] != "raw_stage":
        raise Denied("WRONG_BOUNDARY")
    if ledger.resolve().is_relative_to(root.resolve()):
        raise Denied("LEDGER_MUST_BE_OUTSIDE_WORKTREE")
    if execute:
        fresh = load_grant(root, Path(request["grant_path"]), protected_trust_dir(root))
        if fresh != grant:
            raise Denied("GRANT_CHANGED_AT_WRITE_BOUNDARY")
    authorize(grant, request, root=root)
    source = request["source"]
    remote = request["databricks_path"]
    parts = remote.removeprefix("dbfs:").split("/") if isinstance(remote, str) else []
    if (not isinstance(remote, str)
            or not remote.startswith("dbfs:/Volumes/workspace/edp_lab/raw/")
            or any(part in {"", ".", ".."} for part in parts[1:])
            or len(parts) < 7 or parts[-2] != source["identity"]
            or parts[-1] != Path(source["path"]).name):
        raise Denied("RAW_DESTINATION_OUT_OF_SCOPE")
    if not execute:
        return {"status": "AUTHORIZED_DRY_RUN"}
    parent = remote.rsplit("/", 1)[0]
    created = subprocess.run(databricks_argv("fs", "mkdir", parent, "-p", "edp-lab"),
                             capture_output=True, timeout=grant["limits"]["runtime_seconds"],
                             check=False)
    if created.returncode:
        raise Denied("RAW_PARENT_CREATION_UNCERTAIN")
    inventory = subprocess.run(databricks_argv("fs", "ls", parent, "-p", "edp-lab",
                                            "-o", "json"), capture_output=True,
                               timeout=grant["limits"]["runtime_seconds"], check=False)
    if inventory.returncode:
        raise Denied("RAW_DESTINATION_INVENTORY_FAILED")
    if any(item["name"] == Path(source["path"]).name for item in json.loads(
            inventory.stdout)):
        raise Denied("RAW_DESTINATION_ALREADY_EXISTS")
    _reserve(ledger, request["operation_id"], request)
    command = databricks_argv("fs", "cp", source["path"], remote, "-p", "edp-lab")
    try:
        outcome = subprocess.run(command, capture_output=True, timeout=grant["limits"][
            "runtime_seconds"], check=False)
    except subprocess.TimeoutExpired:
        return {"status": "UNCERTAIN_REQUIRES_INDEPENDENT_READBACK",
                "remote_path": remote}
    if outcome.returncode:
        return {"status": "UNCERTAIN_REQUIRES_INDEPENDENT_READBACK",
                "remote_path": remote}
    try:
        observed = subprocess.run(databricks_argv("fs", "cat", remote, "-p", "edp-lab"),
                                  capture_output=True, timeout=grant["limits"][
                                      "runtime_seconds"], check=False)
    except subprocess.TimeoutExpired:
        return {"status": "UNCERTAIN_REQUIRES_INDEPENDENT_READBACK",
                "remote_path": remote}
    if observed.returncode:
        return {"status": "UNCERTAIN_REQUIRES_INDEPENDENT_READBACK",
                "remote_path": remote}
    if digest(observed.stdout) != source["sha256"]:
        raise Denied("REMOTE_RAW_HASH_MISMATCH")
    return {"status": "SUBMITTED_REQUIRES_INDEPENDENT_READBACK",
            "remote_sha256": digest(observed.stdout), "remote_path": remote}


def git_write(root: Path, grant: dict, request: dict, ledger: Path,
              *, execute: bool = False) -> dict:
    """Guard one exact Git operation; merge still requires CI/approval evidence."""
    if request["operation"] != "git_write":
        raise Denied("WRONG_BOUNDARY")
    if ledger.resolve().is_relative_to(root.resolve()):
        raise Denied("LEDGER_MUST_BE_OUTSIDE_WORKTREE")
    if execute:
        fresh = load_grant(root, Path(request["grant_path"]), protected_trust_dir(root))
        if fresh != grant:
            raise Denied("GRANT_CHANGED_AT_WRITE_BOUNDARY")
    authorize(grant, request, root=root)
    argv = request["argv"]
    kind = request.get("git_operation")
    branch = request.get("branch")
    if kind == "push":
        allowed = ["git", "push", "-u", "origin", branch]
        if argv != allowed or not branch or branch in grant["protected_branches"]:
            raise Denied("GIT_COMMAND_OUT_OF_SCOPE")
    elif kind == "pr_create":
        if argv[:3] != ["gh", "pr", "create"] or "--base" not in argv or "main" not in argv:
            raise Denied("GIT_COMMAND_OUT_OF_SCOPE")
    elif kind == "pr_merge":
        if (argv[:3] != ["gh", "pr", "merge"] or "--merge" not in argv
                or "--admin" in argv or "--delete-branch" in argv):
            raise Denied("GIT_COMMAND_OUT_OF_SCOPE")
        proof = verified_document(root, Path(request["merge_gate_receipt"]),
                                  protected_trust_dir(root))
        if (proof.get("schema") != "EDP_PR_MERGE_GATE_V1"
                or proof.get("pr") != request["pr"]
                or proof.get("head_sha") != request["head_sha"]
                or proof.get("ci") != "PASS" or proof.get("approval") != "PASS"):
            raise Denied("MERGE_GATES_NOT_VERIFIED")
    else:
        raise Denied("GIT_COMMAND_OUT_OF_SCOPE")
    if not execute:
        return {"status": "AUTHORIZED_DRY_RUN"}
    record = _reserve(ledger, request["operation_id"], request)
    outcome = subprocess.run(git_argv(*argv), cwd=root, capture_output=True, text=True,
                             timeout=grant["limits"]["runtime_seconds"], check=False)
    result = {"status": "SUBMITTED_REQUIRES_READBACK" if outcome.returncode == 0 else
              "UNCERTAIN_REQUIRES_READBACK", "returncode": outcome.returncode,
              "stdout_sha256": digest(outcome.stdout.encode()),
              "stderr_sha256": digest(outcome.stderr.encode())}
    record.write_text(json.dumps(result, sort_keys=True) + "\n")
    return result
