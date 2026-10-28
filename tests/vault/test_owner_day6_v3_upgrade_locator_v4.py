"""V4 uses signed exact authority and a distinct, read-only canary identity."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import owner_day6_v3_upgrade_locator_v4 as upgrade


def test_new_canary_is_distinct_and_read_only():
    upgrade.configure_canary()
    assert upgrade.JOB != upgrade.canary.OLD_CANARY_JOB
    assert upgrade.RUN != upgrade.canary.OLD_CANARY_RUN
    assert upgrade.JOB != upgrade.canary.NEW_JOB_RESERVATION
    assert upgrade.JOB_RESERVATION != upgrade.RUN_RESERVATION
    params = upgrade.canary.canary_parameters()
    assert params[:4] == ["--request", upgrade.REMOTE_REQUEST,
                          "--request-sha256", upgrade.REQUEST_SHA]
    assert "--execute" not in params
    assert "--v0a-smoke" not in params
    assert upgrade.E2E_READY.name.endswith("locator-v4.signed.json")


def test_approved_request_and_wheel_are_exact():
    request = json.loads(upgrade.REQUEST.read_bytes())
    deployment = json.loads(upgrade.DEPLOYMENT.read_bytes())
    assert upgrade.REQUEST_SHA == upgrade.file_digest(upgrade.REQUEST)
    assert upgrade.WHEEL_SHA == deployment["artifact"]["sha256"]
    assert request["execution"]["runtime_artifact_sha256"] == upgrade.WHEEL_SHA
    assert deployment["artifact"]["workspace_target_proposed"].startswith(upgrade.REMOTE_DIR)
    assert len(request["new_v3_table_allowlist"]) == 23
    assert request["selection"]["physical_data_rows"] == 2047
    assert request["negative_oracles"]["isolated_fixture_count"] == 24


def test_wrong_receipt_sha_stops_before_any_signature_or_remote_call(monkeypatch):
    monkeypatch.setattr(upgrade.os, "geteuid", lambda: 0)
    monkeypatch.setattr(upgrade, "file_digest", lambda _: "wrong")
    monkeypatch.setattr(upgrade, "verified_document", lambda *_: pytest.fail("signature read"))
    monkeypatch.setattr(upgrade.canary, "admin_cli", lambda *_: pytest.fail("remote call"))
    with pytest.raises(RuntimeError, match="V4_PROTECTED_RECEIPT_SHA_CHANGED"):
        upgrade.verify_gate()


def test_uncertain_v4_reservation_blocks_second_submission(tmp_path, monkeypatch):
    upgrade.configure_canary()
    monkeypatch.setattr(upgrade.canary, "NEW_RUN", tmp_path / "missing-run.json")
    reserved = tmp_path / "reserved.json"
    reserved.write_text('{"status":"RESERVED_BEFORE_REMOTE_SUBMISSION"}')
    monkeypatch.setattr(upgrade.canary, "NEW_RUN_RESERVATION", reserved)
    monkeypatch.setattr(upgrade.canary, "admin_cli", lambda *_: pytest.fail("remote call"))
    with pytest.raises(RuntimeError, match="UNCERTAIN_RUN_SUBMISSION_DO_NOT_REPLAY"):
        upgrade.canary.ensure_run(25)
