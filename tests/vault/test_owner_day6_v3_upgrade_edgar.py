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


def test_successor_accepts_only_config_bound_signed_upgrade(monkeypatch):
    import owner_day6_v3_successor as successor

    request = json.loads(upgrade.REQUEST.read_bytes())
    deployment = json.loads(upgrade.DEPLOYMENT.read_bytes())
    stable_digest = "a" * 64
    standing = {
        "schema": "EDP_DAY6_V3_STANDING_AUTHORIZATION_V1",
        "status": "INSTALLED",
        "request_sha256": upgrade.ORIGINAL_ACTIVE_REQUEST_SHA256,
        "job_submissions_max": 10000000,
        "runtime_seconds_max": 3600,
        "run_as": upgrade.APP_ID,
        "target_namespace": request["target_namespace"],
        "source_ids": request["selection"]["source_ids"],
        "table_allowlist": request["new_v3_table_allowlist"],
        "distinct_no_effect_recovery_allowed": True,
    }
    approval = {
        "schema": "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1",
        "status": "APPROVED",
        "request_sha256": upgrade.CURRENT_REQUEST_SHA256,
        "wheel_sha256": upgrade.NEW_WHEEL_SHA,
        "original_e2e_sha256": stable_digest,
        "standing_sha256": stable_digest,
    }
    ready = {
        "schema": "EDP_VAULT_E2E_UPGRADE_V1",
        "status": "VERIFIED",
        "approval_sha256": stable_digest,
        "original_e2e_sha256": stable_digest,
        "standing_sha256": stable_digest,
        "request_sha256": upgrade.CURRENT_REQUEST_SHA256,
        "wheel_sha256": upgrade.NEW_WHEEL_SHA,
        "environment_version": "4",
        "target_namespace": request["target_namespace"],
        "run_as": upgrade.APP_ID,
        "canary_terminal_state": "SUCCESS",
        "isolated_persisted_readback_reused": True,
        "read_only_new_wheel_verified": True,
        "signed_readback_sha256": stable_digest,
        "workspace_access_verified": True,
        "effective_uc_access_verified": True,
    }
    monkeypatch.setattr(successor, "file_digest", lambda *_: stable_digest)

    def document(_root, path, _trust):
        return {
            successor.STANDING: standing,
            successor.UPGRADE_APPROVAL: approval,
            successor.E2E_READY: ready,
        }[path]

    monkeypatch.setattr(successor, "verified_document", document)
    successor._admission(request, deployment)

    ready["read_only_new_wheel_verified"] = False
    with pytest.raises(RuntimeError, match="V3_SIGNED_E2E_READINESS_REQUIRED"):
        successor._admission(request, deployment)

    ready["read_only_new_wheel_verified"] = True
    approval["wheel_sha256"] = "bad" * 21 + "b"
    with pytest.raises(RuntimeError, match="V3_UPGRADE_OWNER_APPROVAL_REQUIRED"):
        successor._admission(request, deployment)
