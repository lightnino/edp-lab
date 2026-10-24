"""R4 protected watchdog + Supervisor exit semantics, no external writes."""

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.operating import checkpoint_supervisor
from edp_lab.operating.supervisor_health import persist_health, watchdog


EPOCH = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)


def _checkpoint(path: Path, status: str = "VALIDATING") -> None:
    (path / "checkpoint.json").write_text(json.dumps({
        "tasks": {"P6": {"status": "COMPLETE"}, "sql-roster": {"status": status}}
    }))


def test_heartbeat_and_progress_are_independent(tmp_path: Path) -> None:
    _checkpoint(tmp_path)
    first = persist_health(tmp_path, "RUNNING", "SUPERVISOR_STARTED", now=EPOCH)
    second = persist_health(tmp_path, "RUNNING", "SUPERVISOR_POLLING",
                            now=EPOCH + timedelta(seconds=8))
    assert second["heartbeat_at_utc"] != first["heartbeat_at_utc"]
    assert second["last_progress_at_utc"] == first["last_progress_at_utc"]
    assert second["active_task_id"] == "sql-roster"
    assert second["completed_count"] == 1
    assert second["checkpoint_sha256"] == first["checkpoint_sha256"]
    _checkpoint(tmp_path, status="COMPLETE")
    third = persist_health(tmp_path, "RUNNING", "SUPERVISOR_CHECKPOINT_OBSERVED",
                           now=EPOCH + timedelta(seconds=10))
    assert third["last_progress_at_utc"] != first["last_progress_at_utc"]
    assert third["completed_count"] == 2


def test_dead_worker_alerts_without_replaying_any_task(tmp_path: Path) -> None:
    _checkpoint(tmp_path)
    before = (tmp_path / "checkpoint.json").read_bytes()
    persist_health(tmp_path, "RUNNING", "SUPERVISOR_POLLING", now=EPOCH)
    result = watchdog(tmp_path, max_heartbeat_seconds=10, max_progress_seconds=40,
                      now=EPOCH + timedelta(seconds=1), alive=lambda _: False)
    assert result["state"] == "ALERT"
    assert result["reason_code"] == "SUPERVISOR_PROCESS_STOPPED"
    assert result["last_verified_task"] == "sql-roster"
    assert result["replay_authorized"] is False
    assert (tmp_path / "checkpoint.json").read_bytes() == before
    alert = tmp_path / "supervisor_watchdog_alert.json"
    assert alert.exists() and (alert.stat().st_mode & 0o777) == 0o600


@pytest.mark.parametrize(("beat", "progress", "reason"), [
    (11, 11, "SUPERVISOR_HEARTBEAT_EXPIRED"),
    (2, 45, "SUPERVISOR_PROGRESS_STALLED"),
])
def test_unresponsive_or_stalled_worker_alerts(tmp_path: Path, beat, progress, reason):
    persist_health(tmp_path, "RUNNING", "SUPERVISOR_STARTED",
                   now=EPOCH - timedelta(seconds=progress))
    if beat != progress:
        persist_health(tmp_path, "RUNNING", "SUPERVISOR_POLLING",
                       now=EPOCH - timedelta(seconds=beat))
    result = watchdog(tmp_path, max_heartbeat_seconds=10, max_progress_seconds=40,
                      now=EPOCH, alive=lambda _: True)
    assert result["reason_code"] == reason


def test_completed_vs_blocked_status(tmp_path: Path) -> None:
    persist_health(tmp_path, "PAUSED_WITH_DECISION_PACKET",
                   "SQL_STATEMENT_ID_MISSING", now=EPOCH)
    blocked = watchdog(tmp_path, max_heartbeat_seconds=10, max_progress_seconds=40,
                       now=EPOCH, alive=lambda _: False)
    assert blocked["reason_code"] == "SUPERVISOR_BLOCKED"
    persist_health(tmp_path, "COMPLETE", "SUPERVISOR_ACCEPTED", now=EPOCH)
    accepted = watchdog(tmp_path, max_heartbeat_seconds=10, max_progress_seconds=40,
                        now=EPOCH, alive=lambda _: False)
    assert accepted["state"] == "HEALTHY"


def test_monitor_fails_closed_if_status_absent_or_corrupt(tmp_path: Path) -> None:
    missing = watchdog(tmp_path, max_heartbeat_seconds=10,
                       max_progress_seconds=40, now=EPOCH)
    assert missing["reason_code"] == "SUPERVISOR_STATUS_MISSING"
    (tmp_path / "supervisor_status.json").write_text("{bad")
    with pytest.raises(Denied):
        watchdog(tmp_path, max_heartbeat_seconds=10,
                 max_progress_seconds=40, now=EPOCH)


def test_supervisor_status_rejects_symlink_and_leaked_secret(tmp_path: Path) -> None:
    outside = tmp_path.parent / (tmp_path.name + "-owner-protected")
    outside.write_text("original")
    (tmp_path / "supervisor_status.json").symlink_to(outside)
    with pytest.raises(Denied):
        persist_health(tmp_path, "PAUSED_WITH_DECISION_PACKET",
                       "Bearer SECRET TOKEN", now=EPOCH)
    assert outside.read_text() == "original"


def test_supervisor_main_blocked_exits_nonzero_and_never_restarts_runner(
        tmp_path: Path, monkeypatch, capsys) -> None:
    for name in ("root", "queue", "trust", "sock", "verifier"):
        (tmp_path / name).touch()
    args = ["checkpoint-supervisor.py", *[
        str(tmp_path / name) for name in
        ("root", "queue", "state", "trust", "sock", "verifier")
    ]]
    (tmp_path / "state").mkdir()
    def denied(*_a, **_kw):
        raise Denied("SQL_STATEMENT_ID_MISSING")
    monkeypatch.setattr(checkpoint_supervisor, "supervise", denied)
    monkeypatch.setattr(sys, "argv", args)
    assert checkpoint_supervisor.main() == 2
    packet = json.loads((tmp_path / "state/supervisor_status.json").read_text())
    assert packet["status"] == "PAUSED_WITH_DECISION_PACKET"
    assert packet["reason_code"] == "SQL_STATEMENT_ID_MISSING"
    assert packet["replay_authorized"] is False
    assert "SQL_STATEMENT_ID_MISSING" in capsys.readouterr().out


def test_supervisor_main_incomplete_not_false_success(tmp_path, monkeypatch):
    for name in ("root", "queue", "trust", "sock", "verifier"):
        (tmp_path / name).touch()
    (tmp_path / "state").mkdir()
    monkeypatch.setattr(checkpoint_supervisor, "supervise",
                        lambda *_args: {"accepted": False})
    monkeypatch.setattr(sys, "argv", ["cmd", *[
        str(tmp_path / x) for x in
        ("root", "queue", "state", "trust", "sock", "verifier")
    ]])
    assert checkpoint_supervisor.main() == 2
