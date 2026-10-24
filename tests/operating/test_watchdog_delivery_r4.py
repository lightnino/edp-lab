"""Disposable process/alert tests; never use the historical protected Queue."""

import json
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.operating.supervisor_health import persist_health
from edp_lab.operating.watchdog_delivery_r4 import check_and_deliver, load_config


def config(state_dir: Path) -> dict:
    return {"schema": "EDP_WATCHDOG_INSTALL_V1", "state_dir": str(state_dir),
            "heartbeat_seconds": 10, "progress_seconds": 20,
            "alert_argv": ["/usr/bin/true"], "operator_id": "fixture-operator"}


def test_private_config_and_actual_fixture_alert_delivery(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config(tmp_path)))
    os.chmod(path, 0o600)
    loaded = load_config(path)
    sent = []
    def deliver(argv, payload):
        sent.append((argv, json.loads(payload)))
        return subprocess.CompletedProcess(argv, 0)
    result = check_and_deliver(loaded, run_alert=deliver)
    assert result["reason_code"] == "SUPERVISOR_STATUS_MISSING"
    assert result["delivered"] is True
    assert sent[0][1]["replay_authorized"] is False
    os.chmod(path, 0o644)
    with pytest.raises(Denied, match="WATCHDOG_CONFIG_UNTRUSTED"):
        load_config(path)


def test_separate_alert_command_receives_sanitized_payload(tmp_path: Path) -> None:
    destination = tmp_path / "fixture-operator-inbox.json"
    configured = config(tmp_path)
    configured["alert_argv"] = ["/usr/bin/tee", str(destination)]
    result = check_and_deliver(configured)
    assert result["delivered"] is True
    payload = json.loads(destination.read_text())
    assert payload["reason_code"] == "SUPERVISOR_STATUS_MISSING"
    assert payload["replay_authorized"] is False


def test_real_sigkill_is_detected_without_checkpoint_mutation(tmp_path: Path) -> None:
    worker = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        checkpoint = tmp_path / "checkpoint.json"
        checkpoint.write_text(json.dumps({"tasks": {"fixture": {"status": "VALIDATING"}}}))
        before = checkpoint.read_bytes()
        persist_health(tmp_path, "RUNNING", "SUPERVISOR_STARTED")
        status = tmp_path / "supervisor_status.json"
        saved = json.loads(status.read_text())
        saved["pid"] = worker.pid
        status.write_text(json.dumps(saved))
        os.chmod(status, 0o600)
        os.kill(worker.pid, signal.SIGKILL)
        worker.wait(timeout=5)
        report = check_and_deliver(config(tmp_path), run_alert=lambda a, p:
                                   subprocess.CompletedProcess(a, 0))
        assert report["reason_code"] == "SUPERVISOR_PROCESS_STOPPED"
        assert checkpoint.read_bytes() == before
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait(timeout=5)


def test_alert_delivery_failure_remains_visible(tmp_path: Path) -> None:
    report = check_and_deliver(config(tmp_path), run_alert=lambda a, p:
                               subprocess.CompletedProcess(a, 1))
    assert report["state"] == "ALERT"
    assert report["delivered"] is False


@pytest.mark.parametrize(("beat_age", "progress_age", "expected"), [
    (30, 30, "SUPERVISOR_HEARTBEAT_EXPIRED"),
    (1, 30, "SUPERVISOR_PROGRESS_STALLED"),
])
def test_live_but_unresponsive_fixture_process(
        tmp_path: Path, beat_age: int, progress_age: int, expected: str) -> None:
    worker = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        persist_health(tmp_path, "RUNNING", "SUPERVISOR_STARTED")
        status = tmp_path / "supervisor_status.json"
        saved = json.loads(status.read_text())
        now = datetime.now(UTC)
        saved["pid"] = worker.pid
        saved["heartbeat_at_utc"] = (now - timedelta(seconds=beat_age)).isoformat()
        saved["last_progress_at_utc"] = (now - timedelta(seconds=progress_age)).isoformat()
        status.write_text(json.dumps(saved))
        os.chmod(status, 0o600)
        report = check_and_deliver(config(tmp_path), run_alert=lambda a, p:
                                   subprocess.CompletedProcess(a, 0))
        assert worker.poll() is None
        assert report["reason_code"] == expected
    finally:
        worker.kill()
        worker.wait(timeout=5)
