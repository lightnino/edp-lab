"""The consumed V3 run can produce only a signed failure disposition."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_reconcile_day6_v3_partial as partial


def test_unprivileged_reconciliation_stops_before_remote_or_ledger(monkeypatch):
    monkeypatch.setattr(partial, "admin_cli", lambda *_args:
                        pytest.fail("remote call before Owner gate"))
    monkeypatch.setattr(partial, "_original_ledger", lambda:
                        pytest.fail("protected ledger read before Owner gate"))
    monkeypatch.setattr(partial, "_owner", lambda _sha:
                        (_ for _ in ()).throw(RuntimeError("OWNER_ROOT_TERMINAL_REQUIRED")))
    with pytest.raises(RuntimeError, match="OWNER_ROOT_TERMINAL_REQUIRED"):
        partial.reconcile("reviewed")


def test_target_absence_requires_exact_named_table_error(monkeypatch):
    full = "workspace.edp_lab_day6_vault_proto.v3_h_filing"

    def remote(returncode, stderr):
        monkeypatch.setattr(partial.subprocess, "run", lambda *_a, **_kw:
                            subprocess.CompletedProcess([], returncode, "", stderr))

    remote(1, f"Error: Table '{full}' does not exist.\n")
    partial._target_absent(full)
    for code, error in ((0, ""), (1, "no cached credentials"),
                        (1, "Error: Table 'other' does not exist.")):
        remote(code, error)
        with pytest.raises(RuntimeError, match="V3_TARGET_ABSENCE_UNVERIFIED"):
            partial._target_absent(full)


def test_terminal_failure_rejects_a_retry_or_nonterminal_run(monkeypatch):
    saved = {"job_id": partial.JOB_ID, "run_as_user_name": partial.APP_ID,
             "settings": {"run_as": {"service_principal_name": partial.APP_ID},
                          "queue": {"enabled": False},
                          "tasks": [{"max_retries": 0, "retry_on_timeout": False,
                                     "disable_auto_optimization": True}]}}
    run = {"job_id": partial.JOB_ID, "run_id": partial.RUN_ID,
           "job_run_id": partial.RUN_ID,
           "state": {"result_state": "FAILED",
                     "state_message": "does not have access to Databricks Workspace"},
           "status": {"state": "TERMINATED",
                      "termination_details": {"code": "UNAUTHORIZED_ERROR"}},
           "tasks": [{"run_id": partial.TASK_RUN_ID,
                      "task_key": "day6_v3_one_shot", "attempt_number": 0,
                      "execution_duration": 0, "state": {"result_state": "FAILED"}}]}
    output = {"error": "does not have access to Databricks Workspace"}

    def cli(*args):
        return {"get": saved, "get-run": run, "get-run-output": output}[args[1]]

    monkeypatch.setattr(partial, "admin_cli", cli)
    partial._terminal_failure()
    run["tasks"][0]["attempt_number"] = 1
    with pytest.raises(RuntimeError, match="V3_ORIGINAL_TERMINAL_FAILURE_MISMATCH"):
        partial._terminal_failure()
    run["tasks"][0]["attempt_number"] = 0
    run["status"]["state"] = "RUNNING"
    with pytest.raises(RuntimeError, match="V3_ORIGINAL_TERMINAL_FAILURE_MISMATCH"):
        partial._terminal_failure()


def test_reconcile_signs_only_after_all_readbacks_and_preserves_ledger(tmp_path, monkeypatch):
    request = json.loads(partial.REQUEST.read_bytes())
    receipt = tmp_path / "partial.signed.json"
    reservation = tmp_path / "reservation.json"
    submission = tmp_path / "submission.json"
    reservation.write_text('{"original":"reservation"}')
    submission.write_text('{"original":"submission"}')
    before = (reservation.read_bytes(), submission.read_bytes())
    monkeypatch.setattr(partial, "RECEIPT", receipt)
    monkeypatch.setattr(partial, "RESERVATION", reservation)
    monkeypatch.setattr(partial, "SUBMISSION", submission)
    monkeypatch.setattr(partial, "_owner", lambda _sha: None)
    monkeypatch.setattr(partial, "_original_ledger", lambda: (
        request, {"historical_table_ids": {name: "id" for name in
                                           request["existing_tables_read_only"]}},
        {"grant_id": partial.GRANT_ID}, {}))
    monkeypatch.setattr(partial, "_terminal_failure", lambda: ({}, {}, {}))
    checked = []
    monkeypatch.setattr(partial, "_remote_tables", lambda _req, _ids:
                        checked.append("tables") or {})
    monkeypatch.setattr(partial, "admin_cli", lambda *_args: {
        "principal_id": partial.SERVICE_PRINCIPAL_ID,
        "principal_type": "SERVICE_PRINCIPAL",
        "effective_entitlements": ["DATABRICKS_SQL_ACCESS"]})
    monkeypatch.setattr(partial, "file_digest", lambda _path: "a" * 64)

    def sign(document, key, path):
        assert checked == ["tables"]
        assert key == "verifier.pem" and path == receipt
        assert document["status"] == "PARTIAL_RECONCILE_AND_STOP"
        assert document["v3_pass"] is False
        assert document["new_write_authority"] is False
        path.write_text("signed in test")

    monkeypatch.setattr(partial, "_signed_once", sign)
    assert partial.reconcile("reviewed")["status"] == "PARTIAL_RECONCILE_AND_STOP"
    assert (reservation.read_bytes(), submission.read_bytes()) == before
    with pytest.raises(RuntimeError, match="V3_PARTIAL_RECEIPT_ALREADY_EXISTS"):
        partial.reconcile("reviewed")
