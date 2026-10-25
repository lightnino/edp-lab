"""The existing Day 7 installation must never blindly repeat OAuth creation."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "day7_secret_recovery", ROOT / "scripts/owner_recover_day7_secret_v1.py")
assert SPEC and SPEC.loader
import sys
sys.path.insert(0, str(ROOT / "scripts"))
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


def test_old_commit_and_exact_sp_are_hard_pinned():
    assert recovery.OLD_COMMIT == "c2c4c1e5ffb4f795d345ce95023287b174c13b28"
    assert recovery.SP_ID == "78491734320299"
    assert not any(path.startswith("src/") for path in recovery.ALLOWED_CHANGES)
    assert "scripts/owner_install_day7.py" in recovery.ALLOWED_CHANGES


def test_secret_inventory_must_be_complete_and_empty(monkeypatch):
    monkeypatch.setattr(recovery.install, "admin", lambda *_: {
        "secrets": [{"id": "unexpected-secret"}],
        "next_page_token": "another-page",
    })
    with pytest.raises(RuntimeError, match="DAY7_SECRET_INVENTORY_PAGINATION_UNVERIFIED"):
        recovery._secret_metadata()


def test_captured_secret_is_stored_only_in_root_mode_0600(monkeypatch, tmp_path):
    monkeypatch.setattr(recovery, "CONFIG", tmp_path / "databrickscfg")
    monkeypatch.setattr(recovery, "CONFIG_TEMP", tmp_path / "databrickscfg.new")
    identity = {"service_principal_id": recovery.SP_ID,
                "application_id": "app-id"}
    recovery._store_oauth_profile(
        identity, {"id": "created-secret-id", "secret": "dont-print-this-secret"})
    contents = recovery.CONFIG.read_text()
    assert contents.startswith("[edp-lab]\nhost = ")
    assert "auth_type = oauth-m2m\nclient_id = app-id\n" in contents
    assert "\nclient_secret = dont-print-this-secret\n" in contents
    assert not recovery.CONFIG_TEMP.exists()
    assert recovery.CONFIG.stat().st_mode & 0o077 == 0


def test_secret_store_fails_closed_on_existing_profile(monkeypatch, tmp_path):
    config = tmp_path / "databrickscfg"
    config.write_text("previous credentials")
    monkeypatch.setattr(recovery, "CONFIG", config)
    monkeypatch.setattr(recovery, "CONFIG_TEMP", tmp_path / "databrickscfg.new")
    with pytest.raises(RuntimeError, match="DAY7_SECRET_DESTINATION_ALREADY_EXISTS"):
        recovery._store_oauth_profile(
            {"application_id": "app-id"},
            {"id": "created-secret-id", "secret": "correctly-secret"})


def test_controlled_recovery_creates_exactly_one_secret_and_resumes(monkeypatch, tmp_path):
    config = tmp_path / "databrickscfg"
    journal = tmp_path / "day7-install.json"
    intent = tmp_path / "day7-secret-recovery-intent.json"
    revoked = tmp_path / "revoked_grants.json"
    revoked.write_bytes(b"[]\\n")
    monkeypatch.setattr(recovery, "CONFIG", config)
    monkeypatch.setattr(recovery, "CONFIG_TEMP", tmp_path / "databrickscfg.new")
    monkeypatch.setattr(recovery, "RECOVERY_INTENT", intent)
    monkeypatch.setattr(recovery, "REVOKED", revoked)
    monkeypatch.setattr(recovery.install, "JOURNAL", journal)
    monkeypatch.setattr(recovery, "_confirmed_before_mutation",
                        lambda *_args: ({"completed": {
                            "protected_files": {"status": "VERIFIED"}
                        }}, {"service_principal_id": recovery.SP_ID,
                              "application_id": "app-id"}))
    calls = []
    def run(cmd, **_kwargs):
        calls.append(cmd)
        return SimpleNamespace(
            returncode=0, stdout=json.dumps({
                "id": "created-id", "secret": "m2m-secret-that-is-private"}),
            stderr="")
    monkeypatch.setattr(recovery.subprocess, "run", run)
    monkeypatch.setattr(recovery.install, "service",
                        lambda *_: {"id": recovery.SP_ID})
    rows = [[], [{"id": "created-id", "status": "ACTIVE"}]]
    monkeypatch.setattr(recovery, "_secret_metadata", lambda: rows.pop(0))
    executed = []
    monkeypatch.setattr(recovery.install, "main", lambda: executed.append(True))

    result = recovery.recover("new-reviewed-commit")
    assert result["status"] == "DAY7_PARTIAL_INSTALL_RECOVERED"
    assert len(calls) == 1
    assert "service-principal-secrets-proxy" in calls[0]
    assert "create" in calls[0]
    assert result["secret_value"] == "NEVER_PRINTED"
    assert executed == [True]
    assert revoked.read_bytes() == b"[]\n"
    assert json.loads(journal.read_text())["reviewed_commit"] == "new-reviewed-commit"
    assert config.stat().st_mode & 0o077 == 0


def test_failed_remote_secret_create_never_retries_or_writes_credentials(monkeypatch, tmp_path):
    config = tmp_path / "databrickscfg"
    monkeypatch.setattr(recovery, "CONFIG", config)
    monkeypatch.setattr(recovery, "CONFIG_TEMP", tmp_path / "databrickscfg.new")
    monkeypatch.setattr(recovery, "RECOVERY_INTENT", tmp_path / "recovery-intent.json")
    monkeypatch.setattr(recovery, "_confirmed_before_mutation",
                        lambda *_: ({"completed": {}},
                                    {"service_principal_id": recovery.SP_ID,
                                     "application_id": "app-id"}))
    attempts = []
    def run(command, **_kwargs):
        attempts.append(command)
        return SimpleNamespace(returncode=1, stdout="",
                               stderr="PERMISSION_DENIED client_secret=very-private")
    monkeypatch.setattr(recovery.subprocess, "run", run)
    monkeypatch.setattr(recovery, "_secret_metadata", lambda: [])
    with pytest.raises(RuntimeError, match="NO_AUTOMATIC_RETRY") as err:
        recovery.recover("new-reviewed-commit")
    assert "very-private" not in str(err.value)
    assert len(attempts) == 1
    assert not config.exists()


def test_error_redaction():
    assert "hidden-value" not in recovery._safe_error(
        "PERMISSION_DENIED Authorization: hidden-value")
    assert "bearer-secret" not in recovery._safe_error(
        "Bearer bearer-secret invalid")
