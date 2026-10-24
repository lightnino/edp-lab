"""Fail-closed guards for the single-checkpoint owner recovery."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_recover_vault_0a_v2 as recovery


def test_existing_secret_blocks_create(monkeypatch):
    def cli(*args):
        assert args[:2] == ("service-principal-secrets-proxy", "list")
        return [{"id": "existing-secret"}]

    monkeypatch.setattr(recovery, "admin_cli", cli)
    monkeypatch.setattr(recovery.subprocess, "run", lambda *_args, **_kwargs:
                        pytest.fail("secret create must not run"))
    with pytest.raises(RuntimeError, match="VAULT_SECRET_ALREADY_EXISTS_NO_DUPLICATE"):
        recovery._create_single_secret()


def test_secret_failure_surfaces_api_error_without_retry(monkeypatch):
    calls = []

    def cli(*args):
        if args[:2] == ("service-principal-secrets-proxy", "list"):
            return []
        assert args[:2] == ("workspace-iam-v2", "get-workspace-assignment-proxy")
        return {"principal_id": int(recovery.PRINCIPAL_ID)}

    def failed_create(*args, **_kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=1, stderr="HTTP 403: test permission error")

    monkeypatch.setattr(recovery, "admin_cli", cli)
    monkeypatch.setattr(recovery.subprocess, "run", failed_create)
    with pytest.raises(RuntimeError, match="VAULT_SECRET_CREATE_FAILED: HTTP 403"):
        recovery._create_single_secret()
    assert len(calls) == 1
    assert calls[0][0] == [
        "/usr/bin/sudo", "-n", "-u", recovery.ADMIN_USER, "-H",
        "/opt/homebrew/bin/databricks", "service-principal-secrets-proxy", "create",
        recovery.PRINCIPAL_ID, "--json", '{"lifetime":"604800s"}',
        "-p", "edp-lab", "-o", "json"]


def test_unprivileged_recovery_denied_before_databricks_calls(monkeypatch):
    monkeypatch.setattr(recovery.os, "geteuid", lambda: 501)
    monkeypatch.setattr(recovery, "admin_cli", lambda *_args:
                        pytest.fail("Databricks must not be called"))
    with pytest.raises(RuntimeError, match="OWNER_ROOT_TERMINAL_AND_WORKTREE_REQUIRED"):
        recovery.preflight("0" * 40, recovery.POLICY_SHA256)


def test_successful_single_response_saves_existing_identity(tmp_path, monkeypatch):
    (tmp_path / "private").mkdir()
    monkeypatch.setattr(recovery, "BASE", tmp_path)

    def cli(*args):
        if args[:2] == ("service-principal-secrets-proxy", "list"):
            return []
        return {"principal_id": recovery.PRINCIPAL_ID}

    calls = []

    def created(command, **_kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=json.dumps({"secret": "test-only-value"}))

    monkeypatch.setattr(recovery, "admin_cli", cli)
    monkeypatch.setattr(recovery.subprocess, "run", created)
    recovery._create_single_secret()
    assert len(calls) == 1
    assert json.loads(calls[0][calls[0].index("--json") + 1]) == {"lifetime": "604800s"}
    assert json.loads((tmp_path / "private/service-principal.json").read_text()) == {
        "service_principal_id": recovery.PRINCIPAL_ID,
        "application_id": recovery.APPLICATION_ID,
    }
    assert "test-only-value" in (tmp_path / "private/databrickscfg").read_text()
    with pytest.raises(FileExistsError):
        recovery._create_single_secret()
