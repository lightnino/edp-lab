"""The Owner V3 entry point cannot submit after an uncertain first attempt."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from edp_lab.vault.v3_one_shot_gate import verify_saved_job

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_day6_v3_one_shot as owner


def test_proposed_job_is_the_exact_saved_job_shape():
    request = json.loads(owner.REQUEST.read_bytes())
    deployment = json.loads(owner.DEPLOYMENT.read_bytes())
    settings = owner._job_settings("a" * 64, deployment)
    assert verify_saved_job(
        settings, wheel_path=deployment["artifact"]["workspace_target_proposed"],
        run_as={"service_principal_name": owner.APP_ID},
        parameters=owner._job_parameters("a" * 64, deployment))["status"] == (
            "SAVED_ONE_SHOT_SETTINGS_VERIFIED")
    assert len(request["new_v3_table_allowlist"]) == 23


def test_unprivileged_owner_entry_stops_before_remote_call(monkeypatch):
    monkeypatch.setattr(owner.os, "geteuid", lambda: 501)
    monkeypatch.setattr(owner, "admin_cli", lambda *_args:
                        pytest.fail("remote call before Owner root gate"))
    with pytest.raises(RuntimeError, match="OWNER_ROOT_TERMINAL_REQUIRED"):
        owner.install("0" * 40)


def test_failed_submission_consumes_reservation(tmp_path, monkeypatch):
    request = json.loads(owner.REQUEST.read_bytes())
    deployment = json.loads(owner.DEPLOYMENT.read_bytes())
    proof = {"commit": "reviewed", "job_id": 123,
             "derived_request_sha256": "a" * 64}
    now = datetime.now(UTC)
    grant = {"schema": "EDP_DAY6_V3_ONE_SHOT_GRANT_V1",
             "grant_id": owner.GRANT_ID, "status": "ISSUED_NOT_SUBMITTED",
             "job_id": 123, "install_receipt_sha256": "b" * 64,
             "request_sha256": "c" * 64,
             "derived_request_sha256": "a" * 64,
             "semantic_receipt_sha256": "d" * 64,
             "selection_sha256": request["selection"]["sha256"],
             "negative_oracles_sha256": request["negative_oracles"]["sha256"],
             "ddl_sha256": request["target_ddl"]["sha256"],
             "wheel_sha256": deployment["artifact"]["sha256"],
             "run_as": owner.APP_ID, "tables": request["new_v3_table_allowlist"],
             "job_submissions_max": 1, "runtime_seconds_max": 3600,
             "automatic_retries_max": 0,
             "issued_at_utc": (now - timedelta(minutes=1)).isoformat(),
             "expires_at_utc": (now + timedelta(minutes=1)).isoformat()}
    grant_path = tmp_path / "grant.json"
    grant_path.write_text("{}"); (tmp_path / "install.json").write_text("{}")
    (tmp_path / "semantic.json").write_text("{}")
    monkeypatch.setattr(owner, "GRANT", grant_path)
    monkeypatch.setattr(owner, "INSTALL", tmp_path / "install.json")
    monkeypatch.setattr(owner, "SEMANTIC", tmp_path / "semantic.json")
    monkeypatch.setattr(owner, "RESERVATION", tmp_path / "reservation.json")
    monkeypatch.setattr(owner, "SUBMISSION", tmp_path / "submission.json")
    monkeypatch.setattr(owner, "_owner", lambda _commit: None)
    monkeypatch.setattr(owner, "_pins", lambda: (request, deployment))
    monkeypatch.setattr(owner, "_installed", lambda *_args: proof)
    monkeypatch.setattr(owner, "verified_document", lambda *_args: grant)

    def fake_digest(path):
        return {owner.GRANT: "e" * 64, owner.INSTALL: "b" * 64,
                owner.REQUEST: "c" * 64, owner.SEMANTIC: "d" * 64}.get(path, "x" * 64)

    monkeypatch.setattr(owner, "file_digest", fake_digest)
    calls = []

    def failed_cli(*args):
        calls.append(args)
        assert owner.RESERVATION.exists()
        raise OSError("transport response lost")

    monkeypatch.setattr(owner, "admin_cli", failed_cli)
    assert owner.execute("reviewed")["status"] == "UNCERTAIN_REQUIRES_READBACK"
    assert json.loads(owner.RESERVATION.read_bytes())["status"] == (
        "UNCERTAIN_REQUIRES_READBACK")
    with pytest.raises(RuntimeError, match="V3_SUBMISSION_ALREADY_RESERVED"):
        owner.execute("reviewed")
    assert len(calls) == 1
