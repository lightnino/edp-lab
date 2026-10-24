"""R4: protected heartbeat, independent watchdog and sanitized diagnostic surface.

The watchdog runs in a *separate owner-installed process or scheduler*. Merely
merging this module does not start it or deliver an alert. Neither the watchdog
nor the Supervisor can authorize re-execution of an uncertain external write.
"""

import argparse
import hashlib
import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from edp_lab.operating.authority import Denied

_STATUS = "supervisor_status.json"
_ALERT = "supervisor_watchdog_alert.json"
_ALLOWED = {"RUNNING", "PAUSED_WITH_DECISION_PACKET", "COMPLETE"}
_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,79}\Z")


def _directory(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise Denied("SUPERVISOR_STATE_DIR_INVALID")
    real = path.resolve(strict=True)
    if real.stat().st_mode & 0o022:
        raise Denied("SUPERVISOR_STATE_DIR_WRITABLE")
    return real


def _read_private(path: Path) -> dict | None:
    if not path.exists():
        return None
    if path.is_symlink():
        raise Denied("SUPERVISOR_STATUS_SYMLINK")
    if not path.is_file():
        raise Denied("SUPERVISOR_STATE_FILE_INVALID")
    if path.stat().st_mode & 0o077:
        raise Denied("SUPERVISOR_STATE_PERMISSIONS")
    try:
        with path.open("rb") as stream:
            content = json.load(stream)
    except (ValueError, OSError) as exc:
        raise Denied("SUPERVISOR_STATE_INVALID") from exc
    if not isinstance(content, dict):
        raise Denied("SUPERVISOR_STATE_INVALID")
    return content


def _atomic_private(path: Path, data: dict) -> None:
    if path.is_symlink():
        raise Denied("SUPERVISOR_STATE_SYMLINK")
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w") as writer:
            json.dump(data, writer, sort_keys=True)
            writer.write("\n")
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _progress(checkpoint_path: Path) -> tuple[str | None, int | None, str | None, str | None]:
    """Read only task progress fingerprint; never alter signed checkpoint."""
    if not checkpoint_path.exists():
        return None, None, None, None
    if checkpoint_path.is_symlink() or not checkpoint_path.is_file():
        raise Denied("SUPERVISOR_CHECKPOINT_INVALID")
    try:
        data = json.loads(checkpoint_path.read_bytes())
    except (OSError, ValueError) as exc:
        raise Denied("SUPERVISOR_CHECKPOINT_INVALID") from exc
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), dict):
        raise Denied("SUPERVISOR_CHECKPOINT_INVALID")
    tasks = data["tasks"]
    statuses = {k: {"status": v.get("status"), "attempts": v.get("attempts"),
                    "reason": v.get("reason")} for k, v in tasks.items()
                if isinstance(k, str) and isinstance(v, dict)}
    if len(statuses) != len(tasks):
        raise Denied("SUPERVISOR_CHECKPOINT_INVALID")
    serialized = json.dumps(statuses, sort_keys=True, separators=(",", ":"))
    signature = hashlib.sha256(serialized.encode()).hexdigest()
    completed = sum(t["status"] == "COMPLETE" for t in statuses.values())
    active = next((k for k, v in statuses.items()
                   if v["status"] in {"RUNNING", "VALIDATING", "FAILED_INTEGRITY",
                                      "NEEDS_HUMAN_DECISION"}), None)
    checkpoint_hash = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    return signature, completed, active, checkpoint_hash


def persist_health(
    state_dir: Path, status: str, code: str, *, now: datetime | None = None,
) -> dict:
    root = _directory(state_dir)
    if status not in _ALLOWED:
        raise Denied("SUPERVISOR_STATUS_INVALID")
    safe_code = code if _CODE.fullmatch(code) else "UNCLASSIFIED_DENIAL"
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise Denied("SUPERVISOR_TIME_INVALID")
    iso = now.astimezone(UTC).isoformat()
    signature, completed, active, checkpoint_hash = _progress(root / "checkpoint.json")
    previous = _read_private(root / _STATUS)
    last_progress = iso
    if (previous and previous.get("pid") == os.getpid()
            and previous.get("status") == "RUNNING"
            and previous.get("progress_sha256") == signature
            and previous.get("last_progress_at_utc")):
        last_progress = previous["last_progress_at_utc"]
    record = {
        "schema": "EDP_SUPERVISOR_STATUS_V2",
        "status": status,
        "reason_code": safe_code,
        "replay_authorized": False,
        "pid": os.getpid(),
        "heartbeat_at_utc": iso,
        "last_progress_at_utc": last_progress,
        "progress_sha256": signature,
        "completed_count": completed,
        "active_task_id": active if active and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", active)
                          else None,
        "checkpoint_sha256": checkpoint_hash,
    }
    _atomic_private(root / _STATUS, record)
    return record


def _is_alive(pid: int) -> bool | None:
    if type(pid) is not int or pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return None
    return True


def sanitized_status(state_dir: Path) -> dict:
    """Read-only diagnostic projection; never expose raw checkpoint or ledger."""
    saved = _read_private(_directory(state_dir) / _STATUS)
    if saved is None or saved.get("schema") != "EDP_SUPERVISOR_STATUS_V2":
        raise Denied("SUPERVISOR_STATUS_UNAVAILABLE")
    if saved.get("status") not in _ALLOWED:
        raise Denied("SUPERVISOR_STATUS_INVALID")
    reason = saved.get("reason_code")
    if not isinstance(reason, str) or not _CODE.fullmatch(reason):
        raise Denied("SUPERVISOR_REASON_INVALID")
    task = saved.get("active_task_id")
    if task is not None and (not isinstance(task, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,80}", task)):
        raise Denied("SUPERVISOR_TASK_INVALID")
    digest = saved.get("checkpoint_sha256")
    if digest is not None and (not isinstance(digest, str) or not re.fullmatch(
            r"[0-9a-f]{64}", digest)):
        raise Denied("SUPERVISOR_CHECKPOINT_DIGEST_INVALID")
    count = saved.get("completed_count")
    if count is not None and (type(count) is not int or count < 0):
        raise Denied("SUPERVISOR_COUNT_INVALID")
    for field in ("heartbeat_at_utc", "last_progress_at_utc"):
        value = saved.get(field)
        if not isinstance(value, str):
            raise Denied("SUPERVISOR_TIMESTAMP_INVALID")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise Denied("SUPERVISOR_TIMESTAMP_INVALID") from exc
        if parsed.tzinfo is None:
            raise Denied("SUPERVISOR_TIMESTAMP_INVALID")
    return {"schema": "EDP_SUPERVISOR_STATUS_READONLY_V1",
            "status": saved["status"], "reason_code": reason,
            "active_task_id": task,
            "completed_count": count,
            "checkpoint_sha256": digest,
            "heartbeat_at_utc": saved.get("heartbeat_at_utc"),
            "last_progress_at_utc": saved.get("last_progress_at_utc"),
            "replay_authorized": False}


def watchdog(
    state_dir: Path, *, max_heartbeat_seconds: int, max_progress_seconds: int,
    now: datetime | None = None, alive=None,
) -> dict:
    """Independent owner-invoked check; returns safe diagnostics and alert status.

    Process/PID alone is not trusted evidence of progress: missed heartbeats
    and no-progress thresholds remain independent even with PID reuse.
    """
    if (type(max_heartbeat_seconds) is not int or max_heartbeat_seconds < 1
            or type(max_progress_seconds) is not int or max_progress_seconds < 1):
        raise Denied("SUPERVISOR_WATCHDOG_BOUNDS_INVALID")
    root = _directory(state_dir)
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise Denied("SUPERVISOR_TIME_INVALID")
    saved = _read_private(root / _STATUS)
    reason = None
    if saved is None:
        reason = "SUPERVISOR_STATUS_MISSING"
    elif saved.get("schema") != "EDP_SUPERVISOR_STATUS_V2":
        reason = "SUPERVISOR_STATUS_SCHEMA_INVALID"
    elif saved.get("status") == "COMPLETE":
        if saved.get("reason_code") != "SUPERVISOR_ACCEPTED":
            reason = "SUPERVISOR_COMPLETION_UNVERIFIED"
    elif saved.get("status") == "PAUSED_WITH_DECISION_PACKET":
        reason = "SUPERVISOR_BLOCKED"
    elif saved.get("status") != "RUNNING":
        reason = "SUPERVISOR_STATUS_UNKNOWN"
    else:
        pid = saved.get("pid")
        is_alive = (alive or _is_alive)(pid)
        if is_alive is False:
            reason = "SUPERVISOR_PROCESS_STOPPED"
        elif is_alive is None:
            reason = "SUPERVISOR_PROCESS_UNVERIFIED"
        else:
            try:
                beat = datetime.fromisoformat(saved["heartbeat_at_utc"])
                progress = datetime.fromisoformat(saved["last_progress_at_utc"])
                if beat.tzinfo is None or progress.tzinfo is None:
                    raise ValueError("timezone missing")
                delay = now - beat
                stalled = now - progress
                if (delay < timedelta(0) or stalled < timedelta(0)):
                    reason = "SUPERVISOR_CLOCK_INCONSISTENT"
                elif delay > timedelta(seconds=max_heartbeat_seconds):
                    reason = "SUPERVISOR_HEARTBEAT_EXPIRED"
                elif stalled > timedelta(seconds=max_progress_seconds):
                    reason = "SUPERVISOR_PROGRESS_STALLED"
            except (KeyError, ValueError, TypeError):
                reason = "SUPERVISOR_TIMESTAMP_INVALID"
    report = {
        "schema": "EDP_SUPERVISOR_WATCHDOG_V1",
        "state": "ALERT" if reason else "HEALTHY",
        "reason_code": reason or "SUPERVISOR_HEALTHY",
        "replay_authorized": False,
        "checked_at_utc": now.astimezone(UTC).isoformat(),
        "last_verified_task": (saved.get("active_task_id") if saved and isinstance(
            saved.get("active_task_id"), str) and re.fullmatch(
                r"[A-Za-z0-9_-]{1,80}", saved["active_task_id"]) else None),
        "last_completed_count": (saved.get("completed_count") if saved and type(
            saved.get("completed_count")) is int and saved["completed_count"] >= 0
            else None),
        "checkpoint_sha256": (saved.get("checkpoint_sha256") if saved and isinstance(
            saved.get("checkpoint_sha256"), str) and re.fullmatch(
                r"[0-9a-f]{64}", saved["checkpoint_sha256"]) else None),
    }
    if reason:
        _atomic_private(root / _ALERT, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Owner-controlled protected status monitor")
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--heartbeat-seconds", type=int, required=True)
    parser.add_argument("--progress-seconds", type=int, required=True)
    args = parser.parse_args()
    try:
        outcome = watchdog(args.state_dir, max_heartbeat_seconds=args.heartbeat_seconds,
                           max_progress_seconds=args.progress_seconds)
    except Denied:
        print(json.dumps({"state": "ALERT", "reason_code": "WATCHDOG_CHECK_FAILED",
                          "replay_authorized": False}))
        return 3
    print(json.dumps(outcome, sort_keys=True))
    return 0 if outcome["state"] == "HEALTHY" else 3


if __name__ == "__main__":
    raise SystemExit(main())
