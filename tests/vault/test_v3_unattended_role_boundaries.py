"""Service-principal runtime never uses administrator-only IAM/UC introspection."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import owner_day6_v3_one_shot as owner  # noqa: E402


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
