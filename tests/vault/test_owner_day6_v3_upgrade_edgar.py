"""Artifact upgrade is additive, one-canary-only, and cannot replay uncertainty."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_day6_v3_upgrade_edgar as upgrade


def test_upgrade_canary_run_reservation_blocks_unknown_submission(tmp_path, monkeypatch):
    monkeypatch.setattr(upgrade, "CANARY_RUN", tmp_path / "missing.json")
    reserved = tmp_path / "reserved.json"
    reserved.write_text('{"status":"RESERVED_BEFORE_REMOTE_SUBMISSION"}')
    monkeypatch.setattr(upgrade, "CANARY_RUN_RESERVATION", reserved)
    monkeypatch.setattr(upgrade, "admin_cli", lambda *_args: pytest.fail("remote replay"))
    with pytest.raises(RuntimeError, match="UPGRADE_CANARY_RUN_UNCERTAIN_NO_REPLAY"):
        upgrade.ensure_canary_run(42)


def test_upgrade_canary_job_reservation_blocks_unknown_creation(tmp_path, monkeypatch):
    monkeypatch.setattr(upgrade, "CANARY_JOB", tmp_path / "missing.json")
    reserved = tmp_path / "reserved.json"
    reserved.write_text('{"status":"RESERVED_BEFORE_REMOTE_SUBMISSION"}')
    monkeypatch.setattr(upgrade, "CANARY_JOB_RESERVATION", reserved)
    monkeypatch.setattr(upgrade, "admin_cli", lambda *_args: pytest.fail("remote replay"))
    with pytest.raises(RuntimeError, match="UPGRADE_CANARY_JOB_CREATE_UNCERTAIN_NO_REPLAY"):
        upgrade.ensure_canary_job({})


def test_upgrade_canary_never_requests_write_mode():
    args = upgrade.canary_parameters()
    assert "--execute" not in args
    assert "--verify-only" not in args
    assert "--v0a-smoke" not in args
    assert args[args.index("--request") + 1] == upgrade.CANARY_REQUEST
    assert args[args.index("--request-sha256") + 1] == upgrade.CURRENT_REQUEST_SHA256


def test_upgrade_canary_adopts_only_exact_existing_run(tmp_path, monkeypatch):
    record = tmp_path / "run.json"
    monkeypatch.setattr(upgrade, "CANARY_RUN", record)
    monkeypatch.setattr(upgrade, "file_digest", lambda *_: "a" * 64)
    monkeypatch.setattr(upgrade, "admin_cli", lambda *_args: pytest.fail("remote replay"))
    record.write_text(json.dumps({
        "job_id": 33, "run_id": 44, "approval_sha256": "a" * 64,
    }))
    assert upgrade.ensure_canary_run(33) == 44
    with pytest.raises(RuntimeError, match="UPGRADE_CANARY_RUN_LEDGER_CHANGED"):
        upgrade.ensure_canary_run(35)


def test_upgrade_code_install_rejects_modified_existing_root_module(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime-v3"
    path = runtime / "src/edp_lab/vault/v3_service.py"
    path.parent.mkdir(parents=True)
    path.write_text("modified")
    pin = tmp_path / "installed-commit.txt"
    pin.write_text(upgrade.OLD_COMMIT)
    monkeypatch.setattr(upgrade, "RUNTIME", runtime)
    monkeypatch.setattr(upgrade, "PIN", pin)
    monkeypatch.setattr(upgrade, "LOCAL_MODULES",
                        ("src/edp_lab/vault/v3_service.py",))
    monkeypatch.setattr(upgrade, "git", lambda *_args: b"original")
    with pytest.raises(RuntimeError, match="UPGRADE_ORIGINAL_INSTALLED_MODULE_CHANGED"):
        upgrade.install_runtime("f" * 40)
    assert path.read_text() == "modified"
    assert pin.read_text() == upgrade.OLD_COMMIT


def test_upgrade_proposal_cannot_expand_source_or_target_population():
    request = json.loads(upgrade.REQUEST.read_bytes())
    original = json.loads(upgrade.ORIGINAL_ACTIVE_REQUEST.read_bytes())
    assert request["selection"] == original["selection"]
    assert request["target_namespace"] == original["target_namespace"]
    assert request["new_v3_table_allowlist"] == original["new_v3_table_allowlist"]
    assert request["existing_tables_read_only"] == original["existing_tables_read_only"]
    assert request["execution"]["runtime_artifact_sha256"] == upgrade.NEW_WHEEL_SHA


def test_upgrade_requires_verified_original_no_effect(monkeypatch):
    monkeypatch.setattr(upgrade, "_owner", lambda *_: None)
    monkeypatch.setattr(upgrade, "_pins", lambda: ({}, {}))
    monkeypatch.setattr(upgrade, "git", lambda *_: b"commit")
    monkeypatch.setattr(upgrade, "verified_document", lambda *_: pytest.fail(
        "No trust read until exact reviewed artifact pins"))
    with pytest.raises((RuntimeError, KeyError)):
        upgrade.preflight("reviewed")
