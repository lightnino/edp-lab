"""The Owner V3 entry point cannot submit after an uncertain first attempt."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from edp_lab.vault.v3_one_shot_gate import verify_saved_job

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_day6_v3_one_shot as owner


@pytest.mark.parametrize(
    ("returncode", "stderr", "accepted"),
    [
        (1, "Error: Path (/Workspace/Shared/target.whl) doesn't exist.\n", True),
        (0, "Path (/Workspace/Shared/target.whl) doesn't exist.", False),
        (1, "Path (/Workspace/Shared/other.whl) doesn't exist.", False),
        (1, "Permission denied for /Workspace/Shared/target.whl", False),
        (1, "Authentication failed", False),
        (1, "Permission denied. Path (/Workspace/Shared/target.whl) doesn't exist.", False),
        (1, "Unexpected workspace error", False),
    ],
)
def test_workspace_absence_requires_matching_not_found_response(
        monkeypatch, returncode, stderr, accepted):
    remote = "/Workspace/Shared/target.whl"
    monkeypatch.setattr(owner.subprocess, "run", lambda *_args, **_kwargs:
                        subprocess.CompletedProcess([], returncode, "", stderr))
    if accepted:
        owner._workspace_absent(remote)
    else:
        with pytest.raises(RuntimeError, match="V3_REMOTE_FILE_ABSENCE_UNVERIFIED"):
            owner._workspace_absent(remote)


def test_directory_requires_independent_status_readback(monkeypatch):
    calls = []

    def cli(*args):
        calls.append(args)
        return {"path": owner.WHEEL_DIR, "object_type": "DIRECTORY", "object_id": 123}

    monkeypatch.setattr(owner, "admin_cli", cli)
    owner._workspace_directory()
    assert calls == [("workspace", "get-status", owner.WHEEL_DIR)]
    monkeypatch.setattr(owner, "admin_cli", lambda *_args: {"object_type": "DIRECTORY"})
    with pytest.raises(RuntimeError, match="V3_WORKSPACE_DIRECTORY_UNVERIFIED"):
        owner._workspace_directory()


def test_import_accepts_empty_response_only_after_digest_readback(tmp_path, monkeypatch):
    source = tmp_path / "selection.json"
    source.write_bytes(b"test")
    calls = []

    def cli(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(owner, "admin_cli", cli)
    monkeypatch.setattr(owner, "_remote_digest", lambda _remote: owner.file_digest(source))
    owner._upload(source, owner.WHEEL_DIR + "/selection.json")
    assert calls[0][0][:2] == ("workspace", "import")
    assert calls[0][1] == {"allow_empty": True}
    monkeypatch.setattr(owner, "_remote_digest", lambda _remote: "0" * 64)
    with pytest.raises(RuntimeError, match="UPLOADED_WORKSPACE_BYTES_UNVERIFIED"):
        owner._upload(source, owner.WHEEL_DIR + "/selection.json")


def test_grant_update_requires_effective_rights_readback(monkeypatch):
    calls = []

    def cli(*args, **kwargs):
        calls.append((args, kwargs))
        if args[:2] == ("grants", "get-effective"):
            return {"privilege_assignments": []}
        return None

    monkeypatch.setattr(owner, "admin_cli", cli)
    with pytest.raises(RuntimeError, match="V3_GRANT_UPDATE_UNVERIFIED"):
        owner._ensure_rights("schema", "workspace.edp_lab", ["USE_SCHEMA"])
    assert [call[0][1] for call in calls] == ["get-effective", "update", "get-effective"]
    assert calls[1][1] == {"allow_empty": True}


def test_grant_update_accepts_verified_effective_rights(monkeypatch):
    calls = []

    def cli(*args, **kwargs):
        calls.append((args, kwargs))
        if args[:2] == ("grants", "get-effective"):
            privileges = [] if len(calls) == 1 else [{"privilege": "USE_SCHEMA"}]
            return {"privilege_assignments": [{"privileges": privileges}]}

    monkeypatch.setattr(owner, "admin_cli", cli)
    owner._ensure_rights("schema", "workspace.edp_lab", ["USE_SCHEMA"])
    assert [call[0][1] for call in calls] == ["get-effective", "update", "get-effective"]


def test_proposed_job_is_the_exact_saved_job_shape():
    request = json.loads(owner.REQUEST.read_bytes())
    deployment = json.loads(owner.DEPLOYMENT.read_bytes())
    settings = owner._job_settings("a" * 64, deployment)
    assert not {"max_retries", "retry_on_timeout", "disable_auto_optimization"} & settings.keys()
    assert settings["tasks"][0]["max_retries"] == 0
    assert settings["tasks"][0]["retry_on_timeout"] is False
    assert settings["tasks"][0]["disable_auto_optimization"] is True
    assert settings["environments"][0]["spec"]["environment_version"] == "4"
    assert verify_saved_job(
        settings, wheel_path=deployment["artifact"]["workspace_target_proposed"],
        run_as={"service_principal_name": owner.APP_ID},
        parameters=owner._job_parameters("a" * 64, deployment))["status"] == (
            "SAVED_ONE_SHOT_SETTINGS_VERIFIED")
    assert len(request["new_v3_table_allowlist"]) == 23


def test_unprivileged_owner_entry_stops_before_remote_call(monkeypatch):
    monkeypatch.setattr(owner.os, "geteuid", lambda: 501)
    monkeypatch.setattr(owner, "admin_cli", lambda *_args:
                        pytest.fail("remote call before Owner root gate"))
    with pytest.raises(RuntimeError, match="OWNER_ROOT_TERMINAL_REQUIRED"):
        owner.install("0" * 40)
    with pytest.raises(RuntimeError, match="OWNER_ROOT_TERMINAL_REQUIRED"):
        owner.resume_install("0" * 40)


def test_partial_resume_reuses_files_and_grants(tmp_path, monkeypatch):
    request = json.loads(owner.REQUEST.read_bytes())
    deployment = json.loads(owner.DEPLOYMENT.read_bytes())
    derived = json.loads(owner.REQUEST.read_bytes())
    derived["execution"]["protected_grant_id"] = owner.GRANT_ID
    private = tmp_path / "private"
    private.mkdir()
    local = private / "day6-v3-request.granted.json"
    local.write_bytes(owner.canonical(derived))
    wheel = Path(deployment["artifact"]["local_build_output_uncommitted"])
    original_digest = owner.file_digest
    monkeypatch.setattr(owner, "file_digest", lambda path:
                        deployment["artifact"]["sha256"] if path == wheel else
                        original_digest(path))
    monkeypatch.setattr(owner, "BASE", tmp_path)
    for name in ("INSTALL", "GRANT", "RESERVATION", "SUBMISSION"):
        monkeypatch.setattr(owner, name, tmp_path / name.lower())
    monkeypatch.setattr(owner, "_owner", lambda _commit: None)
    monkeypatch.setattr(owner, "_pins", lambda: (request, deployment))
    monkeypatch.setattr(owner, "_targets", lambda _request: {"old": "id"})
    monkeypatch.setattr(owner, "_workspace_directory", lambda: None)
    monkeypatch.setattr(owner, "_source_rights", lambda: None)
    monkeypatch.setattr(owner, "_remote_digest", lambda remote: {
        deployment["artifact"]["workspace_target_proposed"]: deployment["artifact"]["sha256"],
        owner.WHEEL_DIR + "/selection.json": request["selection"]["sha256"],
        owner.WHEEL_DIR + "/negative-oracles.json": request["negative_oracles"]["sha256"],
        owner.WHEEL_DIR + "/request.granted.json": owner.file_digest(local),
    }[remote])
    monkeypatch.setattr(owner.os, "geteuid", lambda: 0)
    original_stat = owner.Path.stat
    monkeypatch.setattr(owner.Path, "stat", lambda path, *args, **kwargs:
                        original_stat(path, *args, **kwargs) if path != local else
                        type("Stat", (), {"st_uid": 0, "st_mode": 0o100600})())
    calls = []

    def cli(*args, **_kwargs):
        calls.append(args)
        if args[:2] == ("current-user", "me"):
            return {"userName": "chengzhu13@gmail.com", "groups": [{"display": "admins"}]}
        if args[:2] == ("service-principals", "get"):
            return {"applicationId": owner.APP_ID, "active": True}
        if args[:2] == ("jobs", "list"):
            return []
        raise AssertionError(args)

    monkeypatch.setattr(owner, "admin_cli", cli)
    monkeypatch.setattr(owner, "_finish_install", lambda *_args: {"status": "ready"})
    assert owner.resume_install("reviewed") == {"status": "ready"}
    assert ("jobs", "list") in calls
    assert not any(args[:2] in (("workspace", "import"), ("grants", "update"))
                   for args in calls)
    monkeypatch.setattr(owner, "_remote_digest", lambda _remote: "0" * 64)
    with pytest.raises(RuntimeError, match="V3_REMOTE_ARTIFACT_CHANGED"):
        owner.resume_install("reviewed")
    monkeypatch.setattr(owner, "admin_cli", lambda *args: [{"job_id": 123}]
                        if args[:2] == ("jobs", "list") else cli(*args))
    with pytest.raises(RuntimeError, match="V3_JOB_LIST_CHANGED"):
        owner.resume_install("reviewed")


def test_partial_resume_stops_if_receipt_present(tmp_path, monkeypatch):
    monkeypatch.setattr(owner, "_owner", lambda _commit: None)
    monkeypatch.setattr(owner, "_pins", lambda: ({}, {}))
    monkeypatch.setattr(owner, "INSTALL", tmp_path / "existing-install")
    owner.INSTALL.write_text("receipt")
    monkeypatch.setattr(owner, "admin_cli", lambda *_args:
                        pytest.fail("remote call after checkpoint mismatch"))
    with pytest.raises(RuntimeError, match="V3_LATER_CHECKPOINT_ALREADY_EXISTS"):
        owner.resume_install("reviewed")


def test_failed_submission_consumes_reservation(tmp_path, monkeypatch):
    request = json.loads(owner.REQUEST.read_bytes())
    deployment = json.loads(owner.DEPLOYMENT.read_bytes())
    proof = {"commit": "reviewed", "job_id": 123,
             "derived_request_sha256": "a" * 64}
    now = datetime.now(UTC)
    grant = {"schema": "EDP_DAY6_V3_ONE_SHOT_GRANT_V1",
             "grant_id": owner.GRANT_ID, "status": "ISSUED_NOT_SUBMITTED",
             "job_id": 123, "install_receipt_sha256": "b" * 64,
             "request_sha256": "c" * 64,
             "derived_request_sha256": "a" * 64,
             "semantic_receipt_sha256": "d" * 64,
             "selection_sha256": request["selection"]["sha256"],
             "negative_oracles_sha256": request["negative_oracles"]["sha256"],
             "ddl_sha256": request["target_ddl"]["sha256"],
             "wheel_sha256": deployment["artifact"]["sha256"],
             "run_as": owner.APP_ID, "tables": request["new_v3_table_allowlist"],
             "job_submissions_max": 1, "runtime_seconds_max": 3600,
             "automatic_retries_max": 0,
             "issued_at_utc": (now - timedelta(minutes=1)).isoformat(),
             "expires_at_utc": (now + timedelta(minutes=1)).isoformat()}
    grant_path = tmp_path / "grant.json"
    grant_path.write_text("{}"); (tmp_path / "install.json").write_text("{}")
    (tmp_path / "semantic.json").write_text("{}")
    monkeypatch.setattr(owner, "GRANT", grant_path)
    monkeypatch.setattr(owner, "INSTALL", tmp_path / "install.json")
    monkeypatch.setattr(owner, "SEMANTIC", tmp_path / "semantic.json")
    monkeypatch.setattr(owner, "RESERVATION", tmp_path / "reservation.json")
    monkeypatch.setattr(owner, "SUBMISSION", tmp_path / "submission.json")
    monkeypatch.setattr(owner, "_owner", lambda _commit: None)
    monkeypatch.setattr(owner, "_pins", lambda: (request, deployment))
    monkeypatch.setattr(owner, "_installed", lambda *_args: proof)
    monkeypatch.setattr(owner, "verified_document", lambda *_args: grant)

    def fake_digest(path):
        return {owner.GRANT: "e" * 64, owner.INSTALL: "b" * 64,
                owner.REQUEST: "c" * 64, owner.SEMANTIC: "d" * 64}.get(path, "x" * 64)

    monkeypatch.setattr(owner, "file_digest", fake_digest)
    calls = []

    def failed_cli(*args):
        calls.append(args)
        assert owner.RESERVATION.exists()
        raise OSError("transport response lost")

    monkeypatch.setattr(owner, "admin_cli", failed_cli)
    assert owner.execute("reviewed")["status"] == "UNCERTAIN_REQUIRES_READBACK"
    assert json.loads(owner.RESERVATION.read_bytes())["status"] == (
        "UNCERTAIN_REQUIRES_READBACK")
    with pytest.raises(RuntimeError, match="V3_SUBMISSION_ALREADY_RESERVED"):
        owner.execute("reviewed")
    assert len(calls) == 1
