"""Fail-closed guards for the single-checkpoint owner recovery."""
from __future__ import annotations

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


def test_unprivileged_recovery_denied_before_databricks_calls(monkeypatch):
    monkeypatch.setattr(recovery.os, "geteuid", lambda: 501)
    monkeypatch.setattr(recovery, "admin_cli", lambda *_args:
                        pytest.fail("Databricks must not be called"))
    with pytest.raises(RuntimeError, match="OWNER_ROOT_TERMINAL_AND_WORKTREE_REQUIRED"):
        recovery.preflight("0" * 40, recovery.POLICY_SHA256)
