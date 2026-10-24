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
import owner_setup_vault_0a_v2 as setup


def test_shared_warehouse_adds_only_can_use_and_preserves_acl(monkeypatch):
    existing = {"user_name": "owner@example.test",
                "all_permissions": [{"permission_level": "CAN_MANAGE"}]}
    target = {"service_principal_name": resume.APPLICATION_ID,
              "all_permissions": [{"permission_level": "CAN_USE"}]}
    calls = []

    def cli(*args):
        calls.append(args)
        if args[:2] == ("warehouses", "get"):
            return {"id": setup.SHARED_WAREHOUSE_ID,
                    "name": setup.SHARED_WAREHOUSE_NAME}
        if args[:2] == ("permissions", "get"):
            return {"access_control_list": [existing] if len(
                [call for call in calls if call[:2] == ("permissions", "get")]) == 1
                    else [existing, target]}
        if args[:2] == ("permissions", "update"):
            assert args[2:4] == ("warehouses", setup.SHARED_WAREHOUSE_ID)
            assert json.loads(args[5]) == {"access_control_list": [{
                "service_principal_name": resume.APPLICATION_ID,
                "permission_level": "CAN_USE"}]}
            return {}
        pytest.fail(f"unexpected command: {args}")

    monkeypatch.setattr(setup, "admin_cli", cli)
    assert setup._warehouse_v2(resume.APPLICATION_ID) == setup.SHARED_WAREHOUSE_ID
    assert sum(call[:2] == ("permissions", "update") for call in calls) == 1
    calls.clear()
    monkeypatch.setattr(setup, "admin_cli", lambda *args: (
        {"id": setup.SHARED_WAREHOUSE_ID, "name": setup.SHARED_WAREHOUSE_NAME}
        if args[:2] == ("warehouses", "get")
        else {"access_control_list": [existing, target]}
        if args[:2] == ("permissions", "get")
        else pytest.fail("CAN_USE must not be granted twice")))
    assert setup._warehouse_v2(resume.APPLICATION_ID) == setup.SHARED_WAREHOUSE_ID


@pytest.mark.parametrize("warehouse,acl", [
    ({"id": "other", "name": setup.SHARED_WAREHOUSE_NAME}, []),
    ({"id": setup.SHARED_WAREHOUSE_ID, "name": "Renamed"}, []),
    ({"id": setup.SHARED_WAREHOUSE_ID, "name": setup.SHARED_WAREHOUSE_NAME},
     [{"service_principal_name": resume.APPLICATION_ID,
       "all_permissions": [{"permission_level": "CAN_MANAGE"}]}]),
])
def test_shared_warehouse_drift_or_elevated_permission_denied(monkeypatch, warehouse, acl):
    def cli(*args):
        if args[:2] == ("warehouses", "get"):
            return warehouse
        if args[:2] == ("permissions", "get"):
            return {"access_control_list": acl}
        pytest.fail("warehouse must not be mutated")

    monkeypatch.setattr(setup, "admin_cli", cli)
    with pytest.raises(RuntimeError, match="VAULT_SHARED_WAREHOUSE"):
        setup._warehouse_v2(resume.APPLICATION_ID)


def test_shared_warehouse_rejects_unrelated_acl_change(monkeypatch):
    owner = {"user_name": "owner@example.test",
             "all_permissions": [{"permission_level": "CAN_MANAGE"}]}
    calls = 0

    def cli(*args):
        nonlocal calls
        if args[:2] == ("warehouses", "get"):
            return {"id": setup.SHARED_WAREHOUSE_ID,
                    "name": setup.SHARED_WAREHOUSE_NAME}
        if args[:2] == ("permissions", "get"):
            calls += 1
            return {"access_control_list": [owner] if calls == 1 else [
                {"user_name": "owner@example.test",
                 "all_permissions": [{"permission_level": "CAN_USE"}]},
                {"service_principal_name": resume.APPLICATION_ID,
                 "all_permissions": [{"permission_level": "CAN_USE"}]}]}
        if args[:2] == ("permissions", "update"):
            return {}
        pytest.fail(f"unexpected command: {args}")

    monkeypatch.setattr(setup, "admin_cli", cli)
    with pytest.raises(RuntimeError, match="VAULT_SHARED_WAREHOUSE_ACL_CHANGED"):
        setup._warehouse_v2(resume.APPLICATION_ID)


def test_resume_policy_sha_is_exact():
    assert setup.digest(setup.PROPOSAL) == resume.POLICY_SHA256


@pytest.mark.parametrize("securable,name,privilege", [
    ("schema", "workspace.edp_lab", "USE_SCHEMA"),
    ("schema", "workspace.edp_lab", "SELECT"),
    ("volume", "workspace.edp_lab.raw", "READ_VOLUME"),
    ("volume", "workspace.edp_lab.raw", "WRITE_VOLUME"),
])
def test_service_principal_day5_and_raw_access_denied(
        monkeypatch, securable, name, privilege):
    def cli(*args):
        assert args[:2] == ("grants", "get-effective")
        return {"privilege_assignments": [{"privileges": [
            {"privilege": privilege}]}]} if args[2:4] == (securable, name) else {
                "privilege_assignments": []}

    monkeypatch.setattr(setup, "admin_cli", cli)
    with pytest.raises(RuntimeError, match="VAULT_SERVICE_PRINCIPAL_PROTECTED_ACCESS"):
        setup._verify_service_principal_boundaries(resume.APPLICATION_ID)


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
    original_exists = Path.exists
    monkeypatch.setattr(Path, "exists", lambda path: (
        False if path.parent == Path("/Library/LaunchDaemons")
        else original_exists(path)))
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
    monkeypatch.setattr(resume, "_refresh_reviewed_runtime", lambda: calls.append("runtime"))

    def failed_verify(_application_id):
        calls.append("verify")
        raise subprocess.CalledProcessError(
            1, ["databricks", "permissions", "get"],
            stderr="Error: HTTP 403: token=private-value at https://example.test/path\n")

    monkeypatch.setattr(resume, "_warehouse_v2", failed_verify)
    monkeypatch.setattr(resume, "complete_after_warehouse", lambda *_args:
                        pytest.fail("completion must not run"))
    with pytest.raises(RuntimeError, match="VAULT_SHARED_WAREHOUSE_VERIFY_OR_PERMISSION_FAILED") as error:
        resume.main()
    assert calls == ["runtime", "verify"]
    assert "private-value" not in str(error.value)
    assert "https://example.test" not in str(error.value)


def test_success_continues_existing_installation(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["resume", "reviewed", resume.POLICY_SHA256])
    policy = {"policy": "test"}
    monkeypatch.setattr(resume, "preflight", lambda *_args: policy)
    calls = []
    monkeypatch.setattr(resume, "_refresh_reviewed_runtime", lambda: calls.append("runtime"))
    monkeypatch.setattr(resume, "_warehouse_v2", lambda application_id:
                        calls.append(application_id) or "589e80595c7c8cb8")
    monkeypatch.setattr(resume, "complete_after_warehouse", lambda *args:
                        calls.append(args))
    resume.main()
    assert calls == ["runtime", resume.APPLICATION_ID,
                     (policy, "589e80595c7c8cb8")]
