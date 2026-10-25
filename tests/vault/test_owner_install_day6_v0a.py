"""One-time V0A installer must not repeat uncertain Jobs mutations."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_install_day6_v0a as install


def test_smoke_job_create_rejects_existing_named_job(monkeypatch, tmp_path):
    monkeypatch.setattr(install, "SMOKE_JOB", tmp_path / "missing.json")
    monkeypatch.setattr(install, "admin_cli", lambda *_args: [
        {"settings": {"name": "day6-v0a-e2e-smoke"}}])
    monkeypatch.setattr(install, "_upload", lambda *_args:
                        pytest.fail("upload after duplicate Job"))
    with pytest.raises(RuntimeError, match="V0A_SMOKE_JOB_ABSENCE_UNVERIFIED"):
        install._job({})


def test_smoke_reservation_blocks_second_submission(monkeypatch, tmp_path):
    reservation = tmp_path / "reservation.json"
    reservation.write_text("reserved")
    monkeypatch.setattr(install, "SMOKE_RESERVATION", reservation)
    monkeypatch.setattr(install, "SMOKE_SUBMISSION", tmp_path / "missing.json")
    monkeypatch.setattr(install, "admin_cli", lambda *_args:
                        pytest.fail("run-now after uncertain reservation"))
    with pytest.raises(RuntimeError, match="V0A_SMOKE_UNCERTAIN_NO_REPLAY"):
        install._run(42)
