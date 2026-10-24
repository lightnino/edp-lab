"""The post-secret checkpoint cannot create a second credential or retry a write."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_resume_vault_0a_v2 as resume


def test_unprivileged_preflight_stops_before_remote_calls(monkeypatch):
    monkeypatch.setattr(resume.os, "geteuid", lambda: 501)
    monkeypatch.setattr(resume, "admin_cli", lambda *_args:
                        pytest.fail("remote calls must not run"))
    with pytest.raises(RuntimeError, match="OWNER_ROOT_TERMINAL_AND_WORKTREE_REQUIRED"):
        resume.preflight("0" * 40, resume.POLICY_SHA256)


def test_remote_checkpoint_requires_exactly_one_secret(monkeypatch):
    def cli(*args):
        if args[:2] == ("service-principals", "get"):
            return {"id": resume.PRINCIPAL_ID, "applicationId": resume.APPLICATION_ID,
                    "displayName": resume.NAME, "active": True}
        if args[:2] == ("service-principals", "list"):
            return [{"id": resume.PRINCIPAL_ID}]
        if args[:2] == ("workspace-iam-v2", "get-workspace-assignment-proxy"):
            return {"principal_id": resume.PRINCIPAL_ID,
                    "principal_type": "SERVICE_PRINCIPAL"}
        if args[:2] == ("workspace-iam-v2", "get-workspace-access-detail-local"):
            return {"status": "ACTIVE", "access_type": "DIRECT"}
        if args[:2] == ("service-principal-secrets-proxy", "list"):
            return []
        pytest.fail(f"unexpected remote call: {args}")

    monkeypatch.setattr(resume, "admin_cli", cli)
    with pytest.raises(RuntimeError, match="VAULT_SECRET_METADATA_COUNT_CHANGED"):
        resume._remote_checkpoint()


def test_protected_config_is_verified_without_disclosure(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, "BASE", tmp_path)
    for name in ("private", "trust", "grants", "approvals", "eligibility",
                 "receipts", "ledger", "runtime/src/edp_lab",
                 "runtime/src/edp_lab-original-d841204", "python/bin"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    (tmp_path / "python/bin/python3.12").touch()
    config = tmp_path / "private/databrickscfg"
    config.write_text(f"[vault-dev]\nhost = {resume.HOST}\n"
                      f"client_id = {resume.APPLICATION_ID}\nclient_secret = test-only-secret\n")
    identity = tmp_path / "private/service-principal.json"
    identity.write_text(json.dumps({"service_principal_id": resume.PRINCIPAL_ID,
                                    "application_id": resume.APPLICATION_ID}))
    for path in tmp_path.rglob("*"):
        if path.is_file():
            path.chmod(0o600)
    monkeypatch.setattr(resume, "_root_owned", lambda _path: True)
    resume._protected_checkpoint()
    config.write_text(config.read_text().replace(resume.APPLICATION_ID, "wrong"))
    with pytest.raises(RuntimeError, match="VAULT_PROTECTED_CONFIG_MISMATCH") as error:
        resume._protected_checkpoint()
    assert "test-only-secret" not in str(error.value)


def test_warehouse_failure_reports_sanitized_error_and_never_retries(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["resume", "reviewed", resume.POLICY_SHA256])
    monkeypatch.setattr(resume, "preflight", lambda *_args: {"policy": "test"})
    calls = []
    monkeypatch.setattr(resume, "_warehouse_absent", lambda: calls.append("list"))

    def failed_create(_application_id):
        calls.append("create")
        raise subprocess.CalledProcessError(
            1, ["databricks", "warehouses", "create"],
            stderr="Error: HTTP 403: token=private-value at https://example.test/path\n")

    monkeypatch.setattr(resume, "_warehouse_v2", failed_create)
    monkeypatch.setattr(resume, "complete_after_warehouse", lambda *_args:
                        pytest.fail("completion must not run"))
    with pytest.raises(RuntimeError, match="VAULT_WAREHOUSE_CREATE_OR_PERMISSION_FAILED") as error:
        resume.main()
    assert calls == ["list", "create"]
    assert "private-value" not in str(error.value)
    assert "https://example.test" not in str(error.value)


def test_success_continues_existing_installation(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["resume", "reviewed", resume.POLICY_SHA256])
    policy = {"policy": "test"}
    monkeypatch.setattr(resume, "preflight", lambda *_args: policy)
    calls = []
    monkeypatch.setattr(resume, "_warehouse_absent", lambda: calls.append("list"))
    monkeypatch.setattr(resume, "_warehouse_v2", lambda application_id:
                        calls.append(application_id) or "abcdef0123456789")
    monkeypatch.setattr(resume, "complete_after_warehouse", lambda *args:
                        calls.append(args))
    resume.main()
    assert calls == ["list", resume.APPLICATION_ID, (policy, "abcdef0123456789")]
