"""Service-principal runtime never uses administrator-only IAM/UC introspection."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import owner_day6_v3_one_shot as owner


def test_service_identity_checks_are_nonadmin(monkeypatch):
    seen = []
    monkeypatch.setenv("EDP_DAY6_V3_SERVICE_CONTEXT", "1")
    monkeypatch.setattr(owner.os, "geteuid", lambda: 0)
    monkeypatch.setattr(owner, "_signed_service_readiness", lambda: None)

    def cli(*args, **_kwargs):
        seen.append(args)
        if args == ("current-user", "me"):
            return {"id": owner.SERVICE_PRINCIPAL_ID}
        if args == ("workspace", "get-status", owner.WHEEL_DIR):
            return {"object_type": "DIRECTORY", "path": owner.WHEEL_DIR}
        if len(args) == 3 and args[:2] == ("tables", "get"):
            return {"table_id": "fixed-id", "name": args[2].split(".")[-1]}
        raise AssertionError("Unexpected/privileged service API: " + repr(args))

    monkeypatch.setattr(owner, "admin_cli", cli)
    owner._workspace_access()
    owner._source_rights()
    assert len(seen) == len(owner.SOURCE_TABLES) + 2
    assert not any(call[0] in {"workspace-iam-v2", "grants", "service-principals"}
                   for call in seen)


def test_service_requires_original_signed_readiness(monkeypatch):
    monkeypatch.setenv("EDP_DAY6_V3_SERVICE_CONTEXT", "1")
    monkeypatch.setattr(owner.os, "geteuid", lambda: 0)

    def denied():
        raise RuntimeError("V3_OWNER_SIGNED_IAM_UC_READINESS_REQUIRED")

    monkeypatch.setattr(owner, "_signed_service_readiness", denied)
    monkeypatch.setattr(owner, "admin_cli", lambda *a, **k: pytest.fail("No API before trust"))
    with pytest.raises(RuntimeError, match="V3_OWNER_SIGNED_IAM_UC_READINESS_REQUIRED"):
        owner._workspace_access()
    with pytest.raises(RuntimeError, match="V3_OWNER_SIGNED_IAM_UC_READINESS_REQUIRED"):
        owner._source_rights()


def test_service_requires_correct_m2m_principal(monkeypatch):
    monkeypatch.setenv("EDP_DAY6_V3_SERVICE_CONTEXT", "1")
    monkeypatch.setattr(owner.os, "geteuid", lambda: 0)
    monkeypatch.setattr(owner, "_signed_service_readiness", lambda: None)
    monkeypatch.setattr(owner, "admin_cli", lambda *_args: {"id": "someone-else"})
    with pytest.raises(RuntimeError, match="V3_UNATTENDED_PRINCIPAL_CHANGED"):
        owner._workspace_access()


def test_service_requires_root_even_with_signed_readiness(monkeypatch):
    monkeypatch.setenv("EDP_DAY6_V3_SERVICE_CONTEXT", "1")
    monkeypatch.setattr(owner.os, "geteuid", lambda: 501)
    monkeypatch.setattr(owner, "_signed_service_readiness", lambda: None)
    with pytest.raises(RuntimeError, match="V3_SERVICE_ROOT_REQUIRED"):
        owner._source_rights()


def test_owner_mode_still_uses_admin_iam_check(monkeypatch):
    monkeypatch.delenv("EDP_DAY6_V3_SERVICE_CONTEXT", raising=False)
    seen = []
    def cli(*args):
        seen.append(args)
        if args[1] == "get-workspace-assignment-proxy":
            return {"principal_id": int(owner.SERVICE_PRINCIPAL_ID),
                    "principal_type": "SERVICE_PRINCIPAL",
                    "effective_entitlements": ["WORKSPACE_ACCESS"]}
        if args[1] == "get-workspace-access-detail-local":
            return {"principal_id": int(owner.SERVICE_PRINCIPAL_ID),
                    "principal_type": "SERVICE_PRINCIPAL", "status": "ACTIVE"}
        raise AssertionError(args)
    monkeypatch.setattr(owner, "admin_cli", cli)
    owner._workspace_access()
    assert {call[1] for call in seen} == {
        "get-workspace-assignment-proxy", "get-workspace-access-detail-local",
    }


def test_service_checks_exact_target_absence_without_owner_sudo(monkeypatch):
    import owner_setup_day6_vault_0a as setup

    from edp_lab.vault import v3_service

    observed = []
    def cli(*args, **_kwargs):
        observed.append(args)
        return [{"name": "v0a_day6_e2e_20261025"}]

    monkeypatch.setattr(setup, "admin_cli", cli)
    v3_service._service_target_absent(
        "workspace.edp_lab_day6_vault_proto.new_v3_table")
    assert observed == [("tables", "list", "workspace", "edp_lab_day6_vault_proto")]
    with pytest.raises(RuntimeError, match="V3_TARGET_ALREADY_PRESENT"):
        v3_service._service_target_absent(
            "workspace.edp_lab_day6_vault_proto.v0a_day6_e2e_20261025")
    with pytest.raises(RuntimeError, match="V3_TARGET_ABSENCE_SCOPE_INVALID"):
        v3_service._service_target_absent("workspace.edp_lab.hidden_table")


def test_audit_reports_multiple_read_only_errors_without_first_error_stop(monkeypatch):
    from types import SimpleNamespace

    import owner_setup_day6_vault_0a as setup

    from edp_lab.vault import v3_service

    monkeypatch.setattr(v3_service, "_ready", lambda *_: None)
    monkeypatch.setattr(v3_service, "_commit", lambda *_: "commit")
    monkeypatch.setattr(v3_service, "_next_attempt",
                        lambda *_: (1, "READY_FOR_DISTINCT_ATTEMPT"))
    monkeypatch.setattr(owner, "SOURCE_TABLES", ("fixed_source",))
    monkeypatch.setattr(owner, "_installed", lambda *_: {"job_id": 2})
    monkeypatch.setattr(owner, "_workspace_access", lambda: (_ for _ in ()).throw(
        RuntimeError("WORKSPACE_READ_DENIED")))
    monkeypatch.setattr(owner, "_source_rights", lambda: (_ for _ in ()).throw(
        RuntimeError("UC_READ_DENIED")))
    monkeypatch.setattr(owner, "_remote_digest", lambda *_: "correct")
    monkeypatch.setattr(setup, "admin_sql", lambda *_: (_ for _ in ()).throw(
        RuntimeError("SQL_WAREHOUSE_READ_DENIED")))

    def cli(*args):
        if args == ("current-user", "me"):
            return {"id": owner.SERVICE_PRINCIPAL_ID}
        if args == ("jobs", "list"):
            raise RuntimeError("JOBS_LIST_DENIED")
        return []

    def required(cond, reason):
        if not cond:
            raise RuntimeError(reason)

    successor = SimpleNamespace(
        configure_attempt=lambda _: None,
        REMOTE_REQUEST="/Workspace/Shared/test/absent",
    )
    monkeypatch.setattr(v3_service, "_imports", lambda: (
        successor, lambda _: None,
        lambda: ({}, {"artifact": {"workspace_target_proposed": "/wheel",
                                  "sha256": "correct"}}),
        None, lambda _: {}, lambda _: None, required, cli,
    ))
    report = v3_service.audit(Path("."), Path("."))
    assert report["status"] == "V3_RUNTIME_CAPABILITY_AUDIT_BLOCKED"
    assert report["attempt_number"] == 1
    for label in ("owner_signed_workspace_scope", "source_table_metadata",
                  "jobs_list", "sql_select:fixed_source"):
        assert report["checks"][label]["status"] == "BLOCKED"
    assert report["checks"]["identity"]["status"] == "PASS"
    assert report["write_capabilities"] == "NOT_TESTED_NO_MUTATION"



def test_owner_role_installer_does_not_gate_on_transient_old_probe_error():
    import inspect

    import owner_repair_day6_v3_service_roles as installer

    source = inspect.getsource(installer.repair)
    assert 'request("probe")' not in source
    assert "V3_UNEXPECTED_PRE_REPAIR_PROBE_STATE" not in source
    assert 'request("status")' in source
    assert "NOT_EXPECTED_PARTIALLY_INSTALLED_COMMIT" in source
    assert "INSTALLED_M2M_MODULE_CHANGED" in source
    assert "V3_CHECKPOINT_CHANGED" in source
    # The new deployment must still invoke a comprehensive read-only audit,
    # never submit V3 as a side effect of repairing the service.
    assert 'request("audit")' in source
    assert 'request("run")' not in source
