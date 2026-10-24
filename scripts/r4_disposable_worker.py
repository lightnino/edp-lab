"""No-write process fixture for owner-controlled R4 launchd acceptance.

It accepts only one explicit noop Queue, never imports the Runner or any
Databricks adapter, and never reads the historical Day 5 state.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from edp_lab.operating.supervisor_health import persist_health

_FORBIDDEN_ENV = {"EDP_POLICY_BROKER_SOCKET", "EDP_OWNER_TRUST_DIR"}
_QUEUE = {"schema": "EDP_R4_NO_WRITE_FIXTURE_QUEUE_V1",
          "tasks": [{"id": "fixture-noop", "kind": "noop"}],
          "external_operations": []}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_fixture(root: Path, queue_sha256: str, ledger_sha256: str,
                mode: str, *, interval: float = 1.0) -> int:
    if (_FORBIDDEN_ENV & os.environ.keys()
            or any(name.startswith("DATABRICKS_") for name in os.environ)):
        raise ValueError("FIXTURE_CREDENTIAL_ENV_PRESENT")
    if root.is_symlink():
        raise ValueError("FIXTURE_ROOT_SYMLINK")
    root = root.resolve(strict=True)
    queue = root / "queue/no_write_queue.json"
    ledger = root / "ledger/operations.json"
    state = root / "state"
    if (root.is_symlink() or not state.is_dir() or queue.is_symlink()
            or ledger.is_symlink() or _digest(queue) != queue_sha256
            or _digest(ledger) != ledger_sha256
            or json.loads(queue.read_bytes()) != _QUEUE
            or json.loads(ledger.read_bytes()) != {"operations": []}):
        raise ValueError("FIXTURE_SCOPE_INVALID")
    checkpoint = state / "checkpoint.json"
    if checkpoint.is_symlink() or (checkpoint.exists() and not checkpoint.is_file()):
        raise ValueError("FIXTURE_CHECKPOINT_INVALID")
    checkpoint.write_text(json.dumps({"tasks": {
        "fixture-noop": {"status": "VALIDATING"}}}, sort_keys=True) + "\n")
    checkpoint.chmod(0o600)
    persist_health(state, "RUNNING", "SUPERVISOR_STARTED")
    if mode == "normal":
        checkpoint.write_text(json.dumps({"tasks": {
            "fixture-noop": {"status": "COMPLETE"}}}, sort_keys=True) + "\n")
        persist_health(state, "COMPLETE", "SUPERVISOR_ACCEPTED")
        code = 0
    elif mode == "blocked":
        persist_health(state, "PAUSED_WITH_DECISION_PACKET",
                       "SQL_STATEMENT_ID_MISSING")
        code = 2
    elif mode == "unexpected":
        persist_health(state, "PAUSED_WITH_DECISION_PACKET",
                       "SUPERVISOR_UNEXPECTED_ERROR")
        code = 2
    elif mode in {"hang", "stall"}:
        while True:
            if _digest(queue) != queue_sha256 or _digest(ledger) != ledger_sha256:
                raise ValueError("FIXTURE_SCOPE_CHANGED")
            if mode == "stall":
                persist_health(state, "RUNNING", "SUPERVISOR_POLLING")
            time.sleep(interval)
    else:
        raise ValueError("FIXTURE_MODE_INVALID")
    if _digest(ledger) != ledger_sha256:
        raise ValueError("FIXTURE_LEDGER_CHANGED")
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description="Isolated no-write R4 process fixture")
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--queue-sha256", required=True)
    parser.add_argument("--ledger-sha256", required=True)
    parser.add_argument("--mode", required=True,
                        choices=("normal", "blocked", "unexpected", "hang", "stall"))
    args = parser.parse_args()
    try:
        return run_fixture(args.fixture_root, args.queue_sha256,
                           args.ledger_sha256, args.mode)
    except (OSError, ValueError):
        print("FIXTURE_BLOCKED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
