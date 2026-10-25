"""No Codex needed: stable Owner-bound Day 7 deployment contracts.

Unit tests exercise only mocked external side effects. Passing CI never
substitutes for an actual Owner-approved protected installation and canary.
"""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/owner_install_day7.py"
SPEC = importlib.util.spec_from_file_location("day7_owner_installer_ready", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def test_original_src_canary_full_hash_before_any_write(monkeypatch, tmp_path):
    raw = b"pinned SRC000002 original bytes\n"
    source = {
        "physical_identity": "SRC000002",
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_bytes": len(raw),
    }
    index = {
        "original_sources": [source],
        "known_original_locators": [{
            "physical_identity": "SRC000002",
            "sha256": source["raw_sha256"],
            "bytes": source["raw_bytes"],
            "remote_path": "dbfs:/Volumes/workspace/edp_lab/raw/edp-native-v1/nasdaqlisted.txt",
        }],
    }
    index_path = tmp_path / "source.json"
    index_path.write_text(json.dumps(index))
    monkeypatch.setattr(installer, "SOURCE_INDEX", index_path)
    monkeypatch.setattr(installer.os, "geteuid", lambda: 0)
    calls = []

    def run(argv, **_kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout=raw)

    monkeypatch.setattr(installer.subprocess, "run", run)
    receipt = installer.verify_canary_raw_read_only()
    assert receipt["raw_sha256"] == source["raw_sha256"]
    assert receipt["raw_bytes"] == len(raw)
    assert calls[0][:6] == ["/usr/bin/sudo", "-n", "-u", "lightnino", "-H",
                             installer.CLI]
    assert calls[0][6:8] == ["fs", "cat"]


def test_original_src_canary_hash_mismatch_fails_closed(monkeypatch, tmp_path):
    index = {
        "original_sources": [{
            "physical_identity": "SRC000002", "raw_sha256": "a" * 64,
            "raw_bytes": 4}],
        "known_original_locators": [{
            "physical_identity": "SRC000002", "sha256": "a" * 64,
            "bytes": 4, "remote_path": "dbfs:/Volumes/workspace/edp_lab/raw/file"}],
    }
    path = tmp_path / "index.json"
    path.write_text(json.dumps(index))
    monkeypatch.setattr(installer, "SOURCE_INDEX", path)
    monkeypatch.setattr(installer.subprocess, "run",
                        lambda *_args, **_kwargs: SimpleNamespace(
                            returncode=0, stdout=b"bad!"))
    with pytest.raises(RuntimeError, match="DAY7_CANARY_REMOTE_FULL_HASH_READBACK_FAILED"):
        installer.verify_canary_raw_read_only()


def test_m2m_scim_identity_not_application_id(monkeypatch):
    invocations = []
    monkeypatch.setattr(installer, "service",
                        lambda *_: {"id": "123456789", "active": True,
                                    "userName": "test-sp"})
    def admin(*args):
        invocations.append(args)
        return {"id": "123456789", "applicationId": "app-uuid"}
    monkeypatch.setattr(installer, "admin", admin)
    monkeypatch.setattr(installer, "_mark", lambda *_: None)
    installer.verify_service_identity("123456789", "app-uuid")
    assert invocations == [("service-principals", "get", "123456789")]
    with pytest.raises(RuntimeError, match="DAY7_M2M_IDENTITY_MISMATCH"):
        installer.verify_service_identity("unexpected-id", "app-uuid")


def test_workspace_entitlements_updated_by_owner_only(monkeypatch):
    current = {"principal_id": 1234, "principal_type": "SERVICE_PRINCIPAL",
               "entitlements": [], "effective_entitlements": []}
    events = []

    def admin(*args):
        events.append(args)
        if args[:2] == ("workspace-iam-v2", "get-workspace-assignment-proxy"):
            return dict(current)
        if args[:2] == ("workspace-iam-v2", "update-workspace-assignment-proxy"):
            payload = json.loads(args[-1])
            current["entitlements"] = payload["entitlements"]
            current["effective_entitlements"] = payload["entitlements"]
            return dict(current)
        raise AssertionError(args)
    monkeypatch.setattr(installer, "admin", admin)
    monkeypatch.setattr(installer, "_mark", lambda *_: None)
    installer.ensure_workspace_access("1234")
    assert current["effective_entitlements"] == [
        "DATABRICKS_SQL_ACCESS", "WORKSPACE_ACCESS"]
    assert not any("WORKSPACE_ADMIN" in str(x) for x in events)
    assert not any(str(x[0]).startswith("service") for x in events)


def test_workspace_admin_entitlement_is_rejected(monkeypatch):
    monkeypatch.setattr(installer, "admin", lambda *_args: {
        "principal_id": 1234, "principal_type": "SERVICE_PRINCIPAL",
        "entitlements": ["WORKSPACE_ADMIN"],
        "effective_entitlements": ["WORKSPACE_ADMIN"]})
    with pytest.raises(RuntimeError, match="DAY7_SP_UNEXPECTED_ADMIN"):
        installer.ensure_workspace_access("1234")


def test_secret_intent_without_recoverable_secret_stops(monkeypatch, tmp_path):
    base = tmp_path / "protected"
    (base / "private").mkdir(parents=True)
    (base / "ledger").mkdir()
    monkeypatch.setattr(installer, "BASE", base)
    monkeypatch.setattr(installer, "_find_exact_service_principals",
                        lambda: [{"id": "1234", "applicationId": "app-id",
                                  "displayName": installer.SP_NAME}])
    intent = base / "ledger/secret-creation-intent.json"
    intent.write_text("{}")
    seen = []

    def admin(*args):
        seen.append(args)
        if args[:2] == ("service-principals", "get"):
            return {"id": "1234", "applicationId": "app-id",
                    "displayName": installer.SP_NAME}
        raise AssertionError("Must not regenerate unknown OAuth secret")
    monkeypatch.setattr(installer, "admin", admin)
    with pytest.raises(RuntimeError, match="DAY7_SECRET_UNCERTAIN_MANUAL_RECONCILIATION"):
        installer.service_identity()
    assert seen == [("service-principals", "get", "1234")]


def test_readiness_is_not_conflated_with_c3000_admission():
    source = inspect.getsource(installer.main)
    assert source.index("preflight(args.expected_commit)") < source.index(
        "protected_files(args.expected_commit)")
    assert "RUNNER_DEPLOYED_AND_VERIFIED" in source
    assert "NOT_ASSERTED_C3000_U10_GATE_PENDING" in source
    assert "N1000" not in source
    assert "cohort_admit" not in source


def test_protected_service_env_cannot_inherit_owner_pat(monkeypatch):
    monkeypatch.setenv("DATABRICKS_TOKEN", "unsafe-owner-token")
    monkeypatch.setenv("DATABRICKS_HOST", "https://wrong.example")
    observed = {}
    def runner(*_args, env=None):
        observed.update(env)
        return "{}"
    monkeypatch.setattr(installer, "run", runner)
    installer.service("current-user", "me")
    assert "DATABRICKS_TOKEN" not in observed
    assert "DATABRICKS_HOST" not in observed
    assert observed["DATABRICKS_CONFIG_FILE"] == str(
        installer.BASE / "private/databrickscfg")


def test_privilege_readback_supports_databricks_string_shape(monkeypatch):
    actions = []
    acl = []
    monkeypatch.setattr(installer, "admin_sql", lambda statement: actions.append(
        ("SQL", statement)))
    def admin(*args):
        actions.append(args)
        if args[:3] == ("api", "get", f"/api/2.0/permissions/warehouses/{installer.WAREHOUSE}"):
            return {"access_control_list": acl}
        if args[:3] == ("permissions", "update", "warehouses"):
            change = json.loads(args[-1])["access_control_list"]
            assert len(change) == 1
            acl[:] = [{"service_principal_name": "app-id",
                       "all_permissions": [{"permission_level": "CAN_USE"}]}]
            return {}
        if args[:3] == ("grants", "get-effective", "volume"):
            return {"privilege_assignments": [{"privileges": ["READ_VOLUME"]}]}
        if args[:3] == ("grants", "get-effective", "table"):
            return {"privilege_assignments": [{"privileges": ["SELECT"]}]}
        raise AssertionError(args)
    monkeypatch.setattr(installer, "admin", admin)
    installer.permissions("app-id")
    assert any(item[0] == "SQL" for item in actions)



def test_nonroot_read_only_preflight_does_not_require_root_or_write(monkeypatch):
    monkeypatch.setattr(installer.os, "geteuid", lambda: 501)
    monkeypatch.setattr(installer, "run", lambda *args: (
        "pinned-sha" if args[-2:] == ("rev-parse", "HEAD") else ""))
    monkeypatch.setattr(installer, "file_digest", lambda path: {
        str(installer.POLICY): installer.POLICY_SHA,
        str(installer.SOURCE_INDEX): installer.SOURCE_INDEX_SHA,
        str(installer.ROOT / "metadata/source_universes/approved/manifest.json"): installer.MANIFEST_SHA,
        str(installer.ROOT /
            "metadata/authorizations/day7_universe_expansion_800_owner_decision.json"): installer.DECISION_SHA,
    }[str(path)])
    monkeypatch.setattr(installer, "verify_canary_raw_read_only",
                        lambda: {"physical_identity": "SRC000002"})
    result = installer.read_only_preflight("pinned-sha")
    assert result["status"] == "DAY7_OWNER_READ_ONLY_PREFLIGHT_PASS"
    assert result["protected_deployment"] == "NOT_YET_EXECUTED"
