"""Small durable, fail-closed local queue runner for signed future grants."""

import argparse
import json
import math
import os
import subprocess
import sys
import time
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
from edp_lab.operating.boundaries import databricks_write, git_write


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_suffix(path.suffix + ".next")
    staged.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    os.replace(staged, path)


def _event(log: Path, kind: str, **detail: object) -> None:
    with log.open("a") as stream:
        stream.write(json.dumps({"at": datetime.now(UTC).isoformat(),
                                 "kind": kind, **detail}, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def applicable_controls(root: Path, tags: list[str],
                        registry_path: str = "metadata/operating/validation_registry_v1.json") -> list[dict]:
    path = (root / registry_path).resolve(strict=True)
    if not path.is_relative_to(root.resolve()):
        raise Denied("REGISTRY_OUTSIDE_REPO")
    registry = json.loads(path.read_bytes())
    if registry["schema"] != "EDP_VALIDATION_REGISTRY_V1" or registry["version"] < 1:
        raise Denied("INVALID_REGISTRY")
    result = []
    for control in registry["controls"]:
        if set(control["tags"]) <= set(tags):
            sql = (root / control["path"]).resolve(strict=True)
            if not sql.is_relative_to(root.resolve()) or file_digest(sql) != control["sha256"]:
                raise Denied("CONTROL_HASH_CHANGED")
            result.append(control)
    return result


def _execute_controls(root: Path, controls: list[dict], receipts: dict) -> None:
    for control in controls:
        if control["execution"] == "pytest":
            result = subprocess.run([sys.executable, "-m", "pytest", "-q", control["path"]],
                                    cwd=root, capture_output=True, timeout=300, check=False)
            if result.returncode:
                raise Denied("LOCAL_CONTROL_FAILED:" + control["id"])
        elif control["execution"] == "databricks_sql":
            path = receipts.get(control["id"])
            if not path:
                raise Denied("LIVE_CONTROL_RECEIPT_MISSING:" + control["id"])
            proof = verified_document(root, Path(path), protected_trust_dir(root))
            if (proof.get("control_id") != control["id"]
                    or proof.get("sql_sha256") != control["sha256"]
                    or proof.get("status") != "PASS"
                    or proof.get("live_databricks") is not True):
                raise Denied("LIVE_CONTROL_RECEIPT_INVALID:" + control["id"])
        else:
            raise Denied("UNKNOWN_CONTROL_EXECUTION")


def _codex_step(root: Path, task: dict, state_dir: Path, *, read_only: bool) -> dict:
    """Run or resume a bounded local Codex task; retain raw JSONL session events."""
    prompt = (root / task["prompt_path"]).resolve(strict=True)
    if not prompt.is_relative_to(root):
        raise Denied("PROMPT_OUTSIDE_REPO")
    if file_digest(prompt) != task["prompt_sha256"]:
        raise Denied("PROMPT_HASH_CHANGED")
    session = task.get("resume_session_id")
    if session:
        command = ["codex", "exec", "resume", session, "--json", "-"]
    else:
        command = ["codex", "exec", "-C", str(root), "-s",
                   "read-only" if read_only else "workspace-write", "--json", "-"]
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("DATABRICKS_", "AWS_", "GITHUB_", "GH_"))}
    instruction = ("Work only inside this repository. Do not run Git mutations, "
                   "Databricks writes, network APIs, or semantic promotions. "
                   "Report completed work and blockers.\n\n"
                   + ("Diagnose and repair the previous ordinary code/execution failure within "
                      "the same approved task and scope.\n\n"
                      if task.get("repair_reason") else "") + prompt.read_text())
    timed_out = False
    try:
        result = subprocess.run(command, input=instruction, text=True, capture_output=True,
                                cwd=root, env=environment, timeout=task["runtime_seconds"], check=False)
        stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = (exc.stdout or b"").decode(errors="replace")
        stderr = (exc.stderr or b"").decode(errors="replace")
        returncode = 124
    event_path = state_dir / (task["id"] + ".codex.jsonl")
    event_path.write_text(stdout)
    session_id = session
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
            if event.get("type") == "thread.started":
                session_id = event.get("thread_id")
        except ValueError:
            pass
    return {"returncode": returncode, "timed_out": timed_out, "session_id": session_id,
            "event_path": str(event_path), "stderr": stderr[-1000:]}


def _freeze_verified(root: Path, path: Path, expected_output: str) -> bool:
    """Gate on independently retained live evidence, never the Day 4 Git marker."""
    evidence = verified_document(root, path, protected_trust_dir(root))
    required = ("delta_ids", "delta_history", "delta_properties", "row_counts",
                "source_lineage", "queryable_versions", "live_readback")
    return (evidence.get("schema") == "EDP_LIVE_FREEZE_RECEIPT_V1"
            and evidence.get("output") == expected_output
            and all(evidence.get(k) == "VERIFIED" for k in required)
            and bool(evidence.get("remote_receipt_sha256")))


def _external_verified(root: Path, task: dict, request: dict) -> bool:
    receipt = Path(task["external_receipt"])
    if not receipt.is_file():
        return False
    proof = verified_document(root, receipt, protected_trust_dir(root))
    return (proof.get("schema") == "EDP_EXTERNAL_OPERATION_RECEIPT_V1"
            and proof.get("operation_id") == request["operation_id"]
            and proof.get("request_sha256") == digest(canonical(request))
            and proof.get("status") == "VERIFIED"
            and proof.get("live_readback") is True)


def _ordered(tasks: list[dict]) -> list[dict]:
    ids = {task["id"] for task in tasks}
    if len(ids) != len(tasks):
        raise Denied("DUPLICATE_TASK_ID")
    pending = list(tasks)
    done = set()
    result = []
    while pending:
        ready = [task for task in pending if set(task["depends_on"]) <= done]
        if not ready:
            raise Denied("TASK_DEPENDENCY_CYCLE_OR_UNKNOWN_ID")
        for task in ready:
            pending.remove(task)
            result.append(task)
            done.add(task["id"])
    if result[-1]["kind"] != "freeze_verify" or set(result[-1]["depends_on"]) != (
            ids - {result[-1]["id"]}):
        raise Denied("FINAL_FREEZE_DEPENDENCIES_INCOMPLETE")
    return result


def run(root: Path, queue_path: Path, envelope: Path, state_dir: Path,
        *, dry_run: bool = False, pause_after: int | None = None) -> dict:
    root = root.resolve()
    queue = json.loads(queue_path.read_bytes())
    if queue["schema"] != "EDP_QUEUE_V1":
        raise Denied("INVALID_QUEUE")
    grant = load_grant(root, envelope, protected_trust_dir(root))
    if file_digest(queue_path) != grant["contracts"]["queue"]["sha256"]:
        raise Denied("QUEUE_HASH_CHANGED")
    if queue["cohort"] != grant["cohort"] or queue["output"] not in grant["outputs"]:
        raise Denied("QUEUE_OUT_OF_SCOPE")
    registry_file = (root / queue["contracts"]["registry"]["path"]).resolve(strict=True)
    if (not registry_file.is_relative_to(root)
            or file_digest(registry_file) != grant["contracts"]["registry"]["sha256"]):
        raise Denied("REGISTRY_HASH_CHANGED")
    ordered = _ordered(queue["tasks"])
    if "PRESERVED_NOT_MODELED" in queue["tags"] and not any(
            task["kind"] == "economic_research" for task in ordered):
        raise Denied("ECONOMIC_RESEARCH_TASK_REQUIRED")
    selected_controls = applicable_controls(root, queue["tags"],
                                            queue["contracts"]["registry"]["path"])
    if selected_controls and not any(task["kind"] == "validate_controls" for task in ordered):
        raise Denied("VALIDATION_TASK_REQUIRED")
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = state_dir / (queue["output"].replace("/", "_").replace(".", "_") + ".lock")
    retry_needed = False
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise Denied("OUTPUT_LOCKED") from exc
    state_path = state_dir / "checkpoint.json"
    log = state_dir / "events.jsonl"
    try:
        state = json.loads(state_path.read_bytes()) if state_path.exists() else {
            "schema": "EDP_RUN_STATE_V1", "queue_sha256": file_digest(queue_path),
            "grant_id": grant["grant_id"],
            "tasks": {t["id"]: {"status": "PLANNED", "attempts": 0} for t in queue["tasks"]},
            "used": {"operations": 0,
            "retries": 0, "runtime_seconds": 0, "compute_units": 0, "token_count": 0},
            "owner_approval_requests": 0, "tool_permission_requests": 0,
            "manual_sha_installations": 0, "agent_steering_messages": 0,
            "human_active_minutes": None, "false_pass_incidents": 0,
        }
        if state["queue_sha256"] != file_digest(queue_path) or state["grant_id"] != grant["grant_id"]:
            raise Denied("CHECKPOINT_SCOPE_CHANGED")
        for task in ordered:
            current = state["tasks"].get(task["id"], {})
            if current.get("status") == "COMPLETE":
                continue
            if not set(task["depends_on"]) <= {key for key, value in state["tasks"].items()
                                                    if value["status"] == "COMPLETE"}:
                continue
            request = {"operation": task["kind"], "cohort": queue["cohort"],
                       "output": queue["output"], "source": task.get("source"),
                       "contracts": {**queue.get("contracts", {}),
                                     "queue": {"version": "EDP_QUEUE_V1",
                                               "path": str(queue_path.resolve().relative_to(root))}},
                       "budget": {"operations": 1,
                                  "runtime_seconds": task.get("runtime_seconds", 0),
                                  "compute_units": task.get("compute_units", 0),
                                  "token_count": task.get("token_budget", 0)}}
            if task["kind"] in {"databricks_write", "git_write"}:
                request.update({key: task[key] for key in (
                    "operation_id", "databricks_path", "databricks_table", "statement_path",
                    "git_operation", "branch", "argv", "pr", "head_sha", "merge_gate_receipt")
                    if key in task})
                request["grant_path"] = str(envelope)
            if current.get("status") == "VALIDATING" and task["kind"] in {
                    "databricks_write", "git_write"}:
                if _external_verified(root, task, request):
                    state["tasks"][task["id"]]["status"] = "COMPLETE"
                    _write_json(state_path, state)
                    _event(log, "COMPLETE_AFTER_READBACK", task=task["id"])
                    continue
                _event(log, "WAITING_EXTERNAL_READBACK", task=task["id"])
                break
            if (current.get("status") == "RUNNING" and task["kind"] != "verify_file"
                    and not (task["kind"] in {"codex_task", "economic_research"}
                             and current.get("codex", {}).get("session_id"))):
                state["tasks"][task["id"]] = {"status": "NEEDS_HUMAN_DECISION",
                                               "reason": "INTERRUPTED_NON_IDEMPOTENT_TASK"}
                _write_json(state_path, state)
                _event(log, "PAUSED", task=task["id"])
                break
            started = time.monotonic()
            try:
                authorize(grant, request, root=root, used=state["used"])
                state["tasks"][task["id"]].update(
                    status="AUTHORIZED", attempts=current.get("attempts", 0))
                _write_json(state_path, state)
                _event(log, "AUTHORIZED", task=task["id"])
                state["tasks"][task["id"]]["status"] = "RUNNING"
                _write_json(state_path, state)
                if task["kind"] == "verify_file":
                    source = task["source"]
                    if file_digest(Path(source["path"])) != source["sha256"]:
                        raise Denied("RAW_HASH_CHANGED")
                elif task["kind"] == "transient_probe":
                    # Deterministic local recovery probe; never performs an external write.
                    if current.get("attempts", 0) == 0:
                        raise TimeoutError("simulated transient interruption")
                elif task["kind"] == "validate_controls":
                    selected = applicable_controls(root, queue["tags"],
                                                   queue["contracts"]["registry"]["path"])
                    expected = set(task["control_ids"])
                    if expected != {x["id"] for x in selected}:
                        raise Denied("APPLICABLE_CONTROLS_NOT_COVERED")
                    if not dry_run:
                        _execute_controls(root, selected, task.get("receipts", {}))
                elif task["kind"] == "economic_research":
                    if "PRESERVED_NOT_MODELED" in queue["tags"]:
                        if dry_run:
                            if not task.get("simulated_packet"):
                                raise Denied("DRY_RUN_RESEARCH_PACKET_REQUIRED")
                        else:
                            resumed = dict(task, resume_session_id=current.get("codex", {}).get("session_id"))
                            result = _codex_step(root, resumed, state_dir, read_only=True)
                            state["tasks"][task["id"]]["codex"] = result
                            _write_json(state_path, state)
                            if result["timed_out"]:
                                raise TimeoutError("economic research timed out")
                            if result["returncode"]:
                                # Research is independent; record an unresolved warning.
                                state["tasks"][task["id"]]["warning"] = "RESEARCH_NOT_COMPLETED"
                elif task["kind"] == "codex_task":
                    if dry_run:
                        if not task.get("simulated_success"):
                            raise Denied("DRY_RUN_CODEX_RESULT_REQUIRED")
                    else:
                        resumed = dict(task, resume_session_id=current.get("codex", {}).get("session_id"),
                                       repair_reason=current.get("reason"))
                        result = _codex_step(root, resumed, state_dir, read_only=False)
                        state["tasks"][task["id"]]["codex"] = result
                        _write_json(state_path, state)
                        if result["timed_out"]:
                            raise TimeoutError("Codex task timed out")
                        if result["returncode"]:
                            raise RuntimeError("CODEX_TASK_REPAIR_REQUIRED")
                elif task["kind"] in {"databricks_write", "git_write"}:
                    if dry_run:
                        ledger = Path("/private/tmp/edp-dry-run-ledger")
                    else:
                        ledger_value = os.environ.get("EDP_OWNER_LEDGER_DIR")
                        if not ledger_value:
                            raise Denied("PROTECTED_LEDGER_REQUIRED")
                        ledger = Path(ledger_value)
                    if task["kind"] == "databricks_write":
                        outcome = databricks_write(root, grant, request, ledger,
                                                  execute=not dry_run)
                    else:
                        outcome = git_write(root, grant, request, ledger,
                                            execute=not dry_run)
                    state["tasks"][task["id"]]["external"] = outcome
                    if not dry_run:
                        state["tasks"][task["id"]]["status"] = "VALIDATING"
                        state["used"]["operations"] += 1
                        state["used"]["runtime_seconds"] += math.ceil(time.monotonic() - started)
                        state["used"]["compute_units"] += task.get("compute_units", 0)
                        _write_json(state_path, state)
                        _event(log, "WAITING_EXTERNAL_READBACK", task=task["id"])
                        break
                elif task["kind"] == "freeze_verify":
                    if dry_run:
                        if not task.get("simulated_receipt"):
                            raise Denied("DRY_RUN_FREEZE_RECEIPT_REQUIRED")
                    elif not _freeze_verified(root, Path(task["receipt"]), queue["output"]):
                        raise Denied("LIVE_FREEZE_NOT_VERIFIED")
                else:
                    raise Denied("UNKNOWN_TASK_KIND")
                state["tasks"][task["id"]]["status"] = "VALIDATING"
                _write_json(state_path, state)
                state["tasks"][task["id"]]["status"] = "COMPLETE"
                state["used"]["operations"] += 1
                state["used"]["runtime_seconds"] += math.ceil(time.monotonic() - started)
                state["used"]["compute_units"] += task.get("compute_units", 0)
                state["used"]["token_count"] += task.get("token_budget", 0)
                _write_json(state_path, state)
                _event(log, "COMPLETE", task=task["id"])
            except TimeoutError as exc:
                state["used"]["runtime_seconds"] += math.ceil(time.monotonic() - started)
                attempts = current.get("attempts", 0) + 1
                state["used"]["retries"] += 1
                state["tasks"][task["id"]].update(
                    status="RECOVERABLE_FAILURE", attempts=attempts, reason=str(exc))
                _write_json(state_path, state)
                _event(log, "RETRY", task=task["id"], attempts=attempts)
                if state["used"]["retries"] > grant["limits"]["retries"]:
                    state["tasks"][task["id"]]["status"] = "NEEDS_HUMAN_DECISION"
                    _write_json(state_path, state)
                    break
                time.sleep(min(2 ** (attempts - 1), 4))
                retry_needed = True
                break
            except RuntimeError as exc:
                state["used"]["runtime_seconds"] += math.ceil(time.monotonic() - started)
                attempts = current.get("attempts", 0) + 1
                state["used"]["retries"] += 1
                state["tasks"][task["id"]].update(
                    status="RECOVERABLE_FAILURE", attempts=attempts, reason=str(exc))
                _write_json(state_path, state)
                _event(log, "REPAIR", task=task["id"], attempts=attempts)
                if state["used"]["retries"] > grant["limits"]["retries"]:
                    state["tasks"][task["id"]]["status"] = "NEEDS_HUMAN_DECISION"
                    _write_json(state_path, state)
                    break
                retry_needed = True
                break
            except Denied as exc:
                state["used"]["runtime_seconds"] += math.ceil(time.monotonic() - started)
                state["tasks"][task["id"]] = {"status": "FAILED_INTEGRITY", "reason": str(exc)}
                _write_json(state_path, state)
                _event(log, "STOPPED", task=task["id"], reason=str(exc))
                break
            if pause_after is not None and state["used"]["operations"] >= pause_after:
                break
        all_complete = all(state["tasks"].get(t["id"], {}).get("status") == "COMPLETE"
                           for t in queue["tasks"])
        final_freeze = queue["tasks"][-1]["kind"] == "freeze_verify"
        state["summary"] = {"complete": sum(v["status"] == "COMPLETE" for v in state["tasks"].values()),
                            "total": len(queue["tasks"]), "dry_run": dry_run,
                            "simulation_complete": dry_run and all_complete and final_freeze,
                            "accepted": not dry_run and all_complete and final_freeze}
        _write_json(state_path, state)
    finally:
        lock.rmdir()
    if retry_needed:
        return run(root, queue_path, envelope, state_dir, dry_run=dry_run,
                   pause_after=pause_after)
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("queue", type=Path)
    parser.add_argument("grant", type=Path)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(root, args.queue, args.grant, args.state_dir,
                         dry_run=args.dry_run)["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
