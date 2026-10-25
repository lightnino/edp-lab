"""Distinct V3 authority cannot consume the original grant or skip PARTIAL."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_day6_v3_successor as successor


def test_successor_job_reuses_wheel_but_changes_request_identity():
    deployment = json.loads((ROOT / "metadata/operating/day6_c2000_vault_v3_deployment_v1.json").read_bytes())
    settings = successor._settings("a" * 64, deployment)
    assert settings["tasks"][0]["python_wheel_task"]["parameters"] == (
        successor._parameters("a" * 64))
    assert settings["tasks"][0]["python_wheel_task"]["parameters"][1] == (
        successor.REMOTE_REQUEST)
    assert settings["environments"][0]["spec"]["dependencies"] == [
        deployment["artifact"]["workspace_target_proposed"]]
    assert settings["max_concurrent_runs"] == 1
    assert settings["tasks"][0]["max_retries"] == 0


def test_entitle_adds_only_workspace_access_then_reads_back(monkeypatch):
    monkeypatch.setattr(successor, "_owner", lambda _sha: None)
    monkeypatch.setattr(successor, "_partial", dict)
    direct = ["DATABRICKS_SQL_ACCESS"]
    calls = []

    def cli(*args, **kwargs):
        calls.append((args, kwargs))
        if args[:2] == ("service-principals", "get"):
            return {"applicationId": successor.APP_ID, "active": True}
        if args[:2] == ("workspace-iam-v2", "get-workspace-access-detail-local"):
            return {"status": "ACTIVE", "access_type": "DIRECT"}
        if args[:2] == ("workspace-iam-v2", "get-workspace-assignment-proxy"):
            return {"principal_id": successor.SERVICE_PRINCIPAL_ID,
                    "principal_type": "SERVICE_PRINCIPAL",
                    "entitlements": direct.copy(),
                    "effective_entitlements": direct.copy()}
        if args[:2] == ("workspace-iam-v2", "update-workspace-assignment-proxy"):
            direct.append("WORKSPACE_ACCESS")
            return None
        pytest.fail(f"unexpected call {args}")

    monkeypatch.setattr(successor, "admin_cli", cli)
    monkeypatch.setattr(successor, "_workspace_access", lambda: None)
    assert successor.entitle("reviewed")["status"] == (
        "V3_RUN_AS_WORKSPACE_ACCESS_READY")
    updates = [args for args, _ in calls if args[:2] == (
        "workspace-iam-v2", "update-workspace-assignment-proxy")]
    assert len(updates) == 1
    assert updates[0][:5] == (
        "workspace-iam-v2", "update-workspace-assignment-proxy",
        successor.SERVICE_PRINCIPAL_ID, "entitlements", "--json")
    assert json.loads(updates[0][-1]) == {
        "principal_id": int(successor.SERVICE_PRINCIPAL_ID),
        "entitlements": ["DATABRICKS_SQL_ACCESS", "WORKSPACE_ACCESS"],
    }
    successor.entitle("reviewed")
    assert len([args for args, _ in calls if args[:2] == (
        "workspace-iam-v2", "update-workspace-assignment-proxy")]) == 1


def test_entitle_rejects_changed_scope_before_mutation(monkeypatch):
    monkeypatch.setattr(successor, "_owner", lambda _sha: None)
    monkeypatch.setattr(successor, "_partial", dict)

    def cli(*args, **_kwargs):
        if args[:2] == ("service-principals", "get"):
            return {"applicationId": successor.APP_ID, "active": True}
        if args[:2] == ("workspace-iam-v2", "get-workspace-access-detail-local"):
            return {"status": "ACTIVE", "access_type": "DIRECT"}
        if args[:2] == ("workspace-iam-v2", "get-workspace-assignment-proxy"):
            return {"principal_id": successor.SERVICE_PRINCIPAL_ID,
                    "principal_type": "SERVICE_PRINCIPAL",
                    "entitlements": ["WORKSPACE_CONSUME"],
                    "effective_entitlements": ["WORKSPACE_CONSUME"]}
        pytest.fail("mutation after entitlement scope mismatch")

    monkeypatch.setattr(successor, "admin_cli", cli)
    with pytest.raises(RuntimeError, match="V3_RUN_AS_ENTITLEMENT_SCOPE_CHANGED"):
        successor.entitle("reviewed")


def test_authorize_requires_original_signed_partial_before_any_new_remote_write(
        monkeypatch):
    monkeypatch.setattr(successor, "_owner", lambda _sha: None)
    monkeypatch.setattr(successor, "_pins", lambda: ({}, {}))
    monkeypatch.setattr(successor, "_partial", lambda: (_ for _ in ()).throw(
        RuntimeError("V3_ORIGINAL_SIGNED_PARTIAL_REQUIRED")))
    monkeypatch.setattr(successor, "admin_cli", lambda *_args, **_kwargs:
                        pytest.fail("remote call before signed original PARTIAL"))
    with pytest.raises(RuntimeError, match="V3_ORIGINAL_SIGNED_PARTIAL_REQUIRED"):
        successor.authorize("reviewed")


def test_admission_requires_installed_standing_and_live_smoke(monkeypatch):
    request = json.loads(successor.REQUEST.read_bytes())
    deployment = json.loads((ROOT / "metadata/operating/day6_c2000_vault_v3_deployment_v1.json").read_bytes())
    monkeypatch.setattr(successor, "verified_document", lambda *_args:
                        {"schema": "EDP_DAY6_V3_STANDING_AUTHORIZATION_V1",
                         "status": "PROPOSED"})
    with pytest.raises(RuntimeError, match="V3_INSTALLED_STANDING_AUTHORITY_REQUIRED"):
        successor._admission(request, deployment)
    standing = {
        "schema": "EDP_DAY6_V3_STANDING_AUTHORIZATION_V1", "status": "INSTALLED",
        "request_sha256": successor.CURRENT_REQUEST_SHA256,
        "job_submissions_max": 10000000, "runtime_seconds_max": 3600,
        "run_as": successor.APP_ID, "target_namespace": request["target_namespace"],
        "source_ids": request["selection"]["source_ids"],
        "table_allowlist": request["new_v3_table_allowlist"],
        "distinct_no_effect_recovery_allowed": True,
    }
    monkeypatch.setattr(successor, "verified_document", lambda _root, path, _trust:
                        standing if path == successor.STANDING else {})
    with pytest.raises(RuntimeError, match="V3_SIGNED_E2E_READINESS_REQUIRED"):
        successor._admission(request, deployment)


def test_distinct_execute_consumes_its_own_reservation_once(tmp_path, monkeypatch):
    request = json.loads(successor.REQUEST.read_bytes())
    deployment = json.loads((ROOT / "metadata/operating/day6_c2000_vault_v3_deployment_v1.json").read_bytes())
    baseline = {name: "unchanged-id" for name in request["existing_tables_read_only"]}
    now = datetime.now(UTC)
    job_id = successor.ORIGINAL_JOB_ID + 1
    install = {
        "schema": "EDP_DAY6_V3_DISTINCT_INSTALL_RECEIPT_V1",
        "reviewed_commit": "reviewed", "original_partial_receipt_sha256": "a" * 64,
        "request_sha256": "a" * 64, "derived_request_sha256": "a" * 64,
        "run_as": successor.APP_ID, "historical_table_ids": baseline,
        "job_id": job_id,
    }
    grant = {
        "schema": "EDP_DAY6_V3_DISTINCT_ONE_SHOT_GRANT_V1",
        "grant_id": successor.GRANT_ID, "status": "ISSUED_NOT_SUBMITTED",
        "job_id": job_id, "install_receipt_sha256": "a" * 64,
        "original_partial_receipt_sha256": "a" * 64,
        "original_job_id": successor.ORIGINAL_JOB_ID,
        "original_run_id": successor.ORIGINAL_RUN_ID,
        "original_grant_sha256": "a" * 64,
        "request_sha256": "a" * 64, "derived_request_sha256": "a" * 64,
        "selection_sha256": request["selection"]["sha256"],
        "negative_oracles_sha256": request["negative_oracles"]["sha256"],
        "ddl_sha256": request["target_ddl"]["sha256"],
        "wheel_sha256": deployment["artifact"]["sha256"],
        "run_as": successor.APP_ID,
        "tables": request["new_v3_table_allowlist"],
        "job_submissions_max": 1, "automatic_retries_max": 0,
        "issued_at_utc": (now - timedelta(minutes=1)).isoformat(),
        "expires_at_utc": (now + timedelta(minutes=30)).isoformat(),
    }
    monkeypatch.setattr(successor, "RESERVATION", tmp_path / "reservation.json")
    monkeypatch.setattr(successor, "SUBMISSION", tmp_path / "submission.json")
    monkeypatch.setattr(successor, "_owner", lambda _sha: None)
    monkeypatch.setattr(successor, "_pins", lambda: (request, deployment))
    monkeypatch.setattr(successor, "_partial", dict)
    monkeypatch.setattr(successor, "_admission", lambda *_args: None)
    monkeypatch.setattr(successor, "_installed", lambda *_args: {
        "job_id": successor.ORIGINAL_JOB_ID, "historical_table_ids": baseline})
    monkeypatch.setattr(successor, "verified_document", lambda _root, path, _trust:
                        install if path == successor.SUCCESSOR_INSTALL else grant)
    monkeypatch.setattr(successor, "file_digest", lambda _path: "a" * 64)
    monkeypatch.setattr(successor, "_workspace_access", lambda: None)
    monkeypatch.setattr(successor, "_source_rights", lambda: None)
    monkeypatch.setattr(successor, "_remote_digest", lambda _remote: "a" * 64)
    monkeypatch.setattr(successor, "_readback_job", lambda *_args: None)
    monkeypatch.setattr(successor, "_targets", lambda _request: baseline)
    calls = []

    def cli(*args):
        calls.append(args)
        assert successor.RESERVATION.exists()
        return {"run_id": 700}

    monkeypatch.setattr(successor, "admin_cli", cli)
    assert successor.execute("reviewed")["run_id"] == 700
    with pytest.raises(RuntimeError, match="V3_DISTINCT_SUBMISSION_ALREADY_RESERVED"):
        successor.execute("reviewed")
    assert len(calls) == 1
