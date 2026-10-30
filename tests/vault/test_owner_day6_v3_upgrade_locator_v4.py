"""V4 uses signed exact authority and a distinct, read-only canary identity."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import owner_day6_v3_upgrade_locator_v4 as upgrade
from owner_day6_v3_one_shot import _job_settings

from edp_lab.operating.authority import Denied


def test_new_canary_is_distinct_and_read_only():
    upgrade.configure_canary()
    assert upgrade.JOB != upgrade.canary.OLD_CANARY_JOB
    assert upgrade.RUN != upgrade.canary.OLD_CANARY_RUN
    assert upgrade.JOB != upgrade.canary.NEW_JOB_RESERVATION
    assert upgrade.JOB_RESERVATION != upgrade.RUN_RESERVATION
    params = upgrade.canary.canary_parameters()
    assert params[:4] == ["--request", upgrade.REMOTE_REQUEST,
                          "--request-sha256", upgrade.REQUEST_SHA]
    assert "--execute" not in params
    assert "--v0a-smoke" not in params
    assert upgrade.E2E_READY.name.endswith("locator-v4.signed.json")


def test_approved_request_and_wheel_are_exact():
    request = json.loads(upgrade.REQUEST.read_bytes())
    deployment = json.loads(upgrade.DEPLOYMENT.read_bytes())
    assert upgrade.REQUEST_SHA == upgrade.file_digest(upgrade.REQUEST)
    assert upgrade.WHEEL_SHA == deployment["artifact"]["sha256"]
    assert request["execution"]["runtime_artifact_sha256"] == upgrade.WHEEL_SHA
    assert deployment["artifact"]["workspace_target_proposed"].startswith(upgrade.REMOTE_DIR)
    assert len(request["new_v3_table_allowlist"]) == 23
    assert request["selection"]["physical_data_rows"] == 2047
    assert request["negative_oracles"]["isolated_fixture_count"] == 24


def test_wrong_receipt_sha_stops_before_any_signature_or_remote_call(monkeypatch):
    monkeypatch.setattr(upgrade.os, "geteuid", lambda: 0)
    monkeypatch.setattr(upgrade, "file_digest", lambda _: "wrong")
    monkeypatch.setattr(upgrade, "verified_document", lambda *_: pytest.fail("signature read"))
    monkeypatch.setattr(upgrade.canary, "admin_cli", lambda *_: pytest.fail("remote call"))
    with pytest.raises(RuntimeError, match="V4_PROTECTED_RECEIPT_SHA_CHANGED"):
        upgrade.verify_gate()


def test_uncertain_v4_reservation_blocks_second_submission(tmp_path, monkeypatch):
    upgrade.configure_canary()
    monkeypatch.setattr(upgrade.canary, "NEW_RUN", tmp_path / "missing-run.json")
    reserved = tmp_path / "reserved.json"
    reserved.write_text('{"status":"RESERVED_BEFORE_REMOTE_SUBMISSION"}')
    monkeypatch.setattr(upgrade.canary, "NEW_RUN_RESERVATION", reserved)
    monkeypatch.setattr(upgrade.canary, "admin_cli", lambda *_: pytest.fail("remote call"))
    with pytest.raises(RuntimeError, match="UNCERTAIN_RUN_SUBMISSION_DO_NOT_REPLAY"):
        upgrade.canary.ensure_run(25)


def _existing_run(monkeypatch, change=None):
    upgrade.configure_canary()
    deployment = json.loads(upgrade.DEPLOYMENT.read_bytes())
    approval = upgrade.APPROVAL_SHA
    ledgers = {
        upgrade.JOB_RESERVATION: {"approval_sha256": approval,
                                  "request_sha256": upgrade.REQUEST_SHA,
                                  "status": "RESERVED_BEFORE_CREATE"},
        upgrade.JOB: {"job_id": 123, "approval_sha256": approval},
        upgrade.RUN_RESERVATION: {"job_id": 123, "approval_sha256": approval,
                                  "status": "RESERVED_BEFORE_REMOTE_SUBMISSION"},
        upgrade.RUN: {"job_id": 123, "run_id": 456, "approval_sha256": approval},
    }
    if change == "missing_ledger": del ledgers[upgrade.RUN]
    if change == "foreign_ledger": ledgers[upgrade.RUN]["job_id"] = 999
    monkeypatch.setattr(upgrade, "_protected_ledger", lambda path: ledgers[path])
    settings = _job_settings(upgrade.REQUEST_SHA, deployment)
    settings["name"] = upgrade.JOB_NAME
    settings["tasks"][0]["python_wheel_task"]["parameters"] = upgrade.canary.canary_parameters()
    if change == "saved_params":
        settings["tasks"][0]["python_wheel_task"]["parameters"].append("--execute")
    job = {"job_id": 123, "run_as_user_name": upgrade.APP_ID, "settings": settings}
    task = {"run_id": 789, "task_key": "day6_v3_one_shot", "attempt_number": 0,
            "environment_key": "v3_fixed_runtime",
            "python_wheel_task": {"parameters": upgrade.canary.canary_parameters()}}
    if change == "retry": task["attempt_number"] = 1
    run = {"job_id": 123, "run_id": 456, "creator_user_name": upgrade.APP_ID,
           "run_name": upgrade.JOB_NAME, "status": {"state": "TERMINATED"},
           "state": {"result_state": "SUCCESS"}, "tasks": [task]}
    task_run = {"job_id": 123, "run_id": 789, "parent_run_id": 456,
                "state": {"result_state": "SUCCESS"}}
    calls = []
    def cli(*args):
        calls.append(args)
        assert args[:2] in {("jobs", "get"), ("jobs", "get-run")}
        return job if args[:2] == ("jobs", "get") else (
            run if args[2] == "456" else task_run)
    monkeypatch.setattr(upgrade, "admin_cli", cli)
    return deployment, calls


def test_resume_adopts_exact_existing_success_without_write_calls(monkeypatch):
    deployment, calls = _existing_run(monkeypatch)
    assert upgrade.verify_existing_run(deployment) == (123, 456)
    assert calls == [("jobs", "get", "123"), ("jobs", "get-run", "456"),
                     ("jobs", "get-run", "789")]


@pytest.mark.parametrize("change", ["missing_ledger", "foreign_ledger",
                                     "saved_params", "retry"])
def test_resume_fails_closed_on_missing_or_changed_existing_run(monkeypatch, change):
    deployment, calls = _existing_run(monkeypatch, change)
    with pytest.raises((RuntimeError, KeyError, Denied)):
        upgrade.verify_existing_run(deployment)
    assert all(call[:2] in {("jobs", "get"), ("jobs", "get-run")} for call in calls)


@pytest.mark.parametrize("change", [None, "target", "version", "duplicate", "missing"])
def test_one_complete_table_list_verifies_targets_and_history(monkeypatch, change):
    historical = {f"historical_{n}": str(n) for n in range(8)}
    listed = [{"name": name, "table_id": table_id, "data_source_format": "DELTA",
               "properties": {"delta.lastUpdateVersion": "0"}}
              for name, table_id in historical.items()]
    listed.append({"name": "v0a_day6_e2e_20261025", "data_source_format": "DELTA"})
    if change == "target": listed.append({"name": "target_0"})
    if change == "version": listed[0]["properties"]["delta.lastUpdateVersion"] = "1"
    if change == "duplicate": listed.append(listed[0].copy())
    if change == "missing": listed.pop(0)
    calls = []
    def cli(*args):
        calls.append(args)
        assert args == ("tables", "list", "workspace", "edp_lab_day6_vault_proto")
        return listed
    monkeypatch.setattr(upgrade, "admin_cli", cli)
    request = {"new_v3_table_allowlist": [f"target_{n}" for n in range(23)]}
    if change is None:
        upgrade.verify_tables_once(request, {"historical_table_ids": historical})
    else:
        with pytest.raises(RuntimeError):
            upgrade.verify_tables_once(request, {"historical_table_ids": historical})
    assert len(calls) == 1
