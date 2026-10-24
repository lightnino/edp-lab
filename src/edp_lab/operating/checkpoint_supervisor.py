"""Protected receipt-driven supervisor for one pinned Day 5 checkpoint.

Run from the root-owned runtime. It never retries an uncertain submission; it
only resumes the Runner after the independent verifier signs live readback.
"""

import argparse
import json
import os
import time
from pathlib import Path

from edp_lab.operating.authority import Denied, file_digest, load_grant
from edp_lab.operating.day5_control_verifier import attest_controls
from edp_lab.operating.day5_freeze_verifier import attest_freeze
from edp_lab.operating.day5_stage_verifier import attest_stage
from edp_lab.operating.day5_timing_verifier import attest_timing
from edp_lab.operating.policy_broker import request as request_grant
from edp_lab.operating.protected_recovery import recover_pre_submission_raw
from edp_lab.operating.protected_verifier import attest_cohort, attest_raw, attest_sql
from edp_lab.operating.runner import run


def supervise(root: Path, queue: Path, state_dir: Path, trust: Path, socket: Path,
              verifier_key: Path, *, interval: int = 5) -> dict:
    root = root.resolve()
    if any(path.resolve().is_relative_to(root) for path in (
            state_dir, trust, socket, verifier_key)):
        raise Denied("SUPERVISOR_MUST_BE_PROTECTED")
    os.environ["EDP_OWNER_TRUST_DIR"] = str(trust)
    os.environ["EDP_POLICY_BROKER_SOCKET"] = str(socket)
    os.environ["EDP_LOCAL_TEST_RUN_AS_USER"] = "lightnino"
    os.environ["EDP_LOCAL_TEST_PYTHON"] = str(root / ".venv/bin/python")
    for attempt in range(30):
        try:
            grant_path = request_grant(socket, queue)
            break
        except OSError:
            if attempt == 29:
                raise
            time.sleep(1)
    load_grant(root, grant_path, trust)
    checkpoint = state_dir / "checkpoint.json"
    if checkpoint.exists():
        recover_pre_submission_raw(root, queue, grant_path, checkpoint, trust,
                                   verifier_key)
    queue_sha = file_digest(queue)
    tasks = json.loads(queue.read_bytes())["tasks"]
    pending_started = None
    while True:
        state = run(root, queue, grant_path, state_dir, pause_at_receipt_barrier=True)
        if state["queue_sha256"] != queue_sha:
            raise Denied("SUPERVISOR_QUEUE_CHANGED")
        if state["summary"]["accepted"]:
            return state["summary"]
        stopped = {task_id: item.get("reason", item["status"])
                   for task_id, item in state["tasks"].items()
                   if item["status"] in {"FAILED_INTEGRITY", "NEEDS_HUMAN_DECISION"}}
        if stopped:
            return {**state["summary"], "stopped": stopped}
        active = [(task_id, item) for task_id, item in state["tasks"].items()
                  if item["status"] == "VALIDATING"]
        if len(active) > 1:
            raise Denied("MULTIPLE_UNVERIFIED_OPERATIONS")
        if not active:
            complete = {task_id for task_id, item in state["tasks"].items()
                        if item["status"] == "COMPLETE"}
            ready = next((task for task in tasks if task["id"] not in complete
                          and set(task["depends_on"]) <= complete), None)
            if ready is None:
                return state["summary"]
            if ready["kind"] == "stage_gate" and ready["id"] in {"P7", "P8", "P9"}:
                attest_stage(root, queue, grant_path, state_dir / "checkpoint.json",
                             ready["id"], trust, verifier_key)
            elif ready["kind"] == "validate_controls":
                attest_controls(root, queue, grant_path, state_dir / "checkpoint.json",
                                trust, verifier_key)
            elif ready["kind"] == "budget_gate":
                attest_timing(root, queue, grant_path, state_dir / "checkpoint.json",
                              trust, verifier_key)
            elif ready["kind"] == "freeze_verify":
                attest_freeze(root, queue, grant_path, state_dir / "checkpoint.json",
                              trust, verifier_key)
            continue
        task_id, _item = active[0]
        task = next(task for task in json.loads(queue.read_bytes())["tasks"]
                    if task["id"] == task_id)
        verifier = {"raw_stage": attest_raw, "cohort_admit": attest_cohort,
                    "databricks_write": attest_sql}.get(task["kind"])
        if verifier is None:
            raise Denied("UNSUPPORTED_SUPERVISOR_READBACK")
        if pending_started is None:
            pending_started = time.monotonic()
        try:
            verifier(root, queue, grant_path, state_dir / "checkpoint.json", task_id,
                     trust, verifier_key)
        except Denied as exc:
            # A pending SQL statement may finish later. No submission is replayed.
            transient = (task["kind"] == "databricks_write" and str(exc) in {
                    "SQL_STATEMENT_NOT_SUCCEEDED", "SQL_RESULT_OBJECT_NOT_VERIFIED",
                    "REMOTE_SQL_READBACK_FAILED"} or task["kind"] == "raw_stage"
                    and str(exc) == "REMOTE_RAW_READBACK_FAILED")
            if transient:
                if time.monotonic() - pending_started > task["runtime_seconds"]:
                    raise Denied("SQL_READBACK_HARD_LIMIT_EXHAUSTED") from exc
                time.sleep(interval)
                continue
            raise
        pending_started = None


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("root", "queue", "state_dir", "trust", "socket", "verifier_key"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(supervise(args.root, args.queue, args.state_dir, args.trust,
                               args.socket, args.verifier_key), sort_keys=True))


if __name__ == "__main__":
    main()
