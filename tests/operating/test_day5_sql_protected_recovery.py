"""A signed owner disposition links one stopped SQL task to a new reservation."""

import hashlib
import json
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied, canonical, file_digest
from edp_lab.operating.protected_recovery import (
    recover_pre_submission_sql,
    verify_sql_recovery,
)
from edp_lab.operating.protected_verifier import attest_sql


def case(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    protected = tmp_path / "protected"
    trust = protected / "trust"
    trust.mkdir(parents=True)
    (protected / "ledger").mkdir()
    (protected / "receipts").mkdir()
    state_dir = protected / "state"
    state_dir.mkdir()
    queue_path = root / "queue.json"
    task = {"id": "sql-roster", "kind": "databricks_write",
            "operation_id": "day5-c2000-roster-v1",
            "databricks_table": "workspace.edp_lab.n500_input_roster_day5_v1"}
    queue_path.write_bytes(canonical({"cohort": "C2000",
                                      "output": "workspace.edp_lab.o_c2000_m2_v1",
                                      "tasks": [task]}))
    external = {"status": "UNCERTAIN_REQUIRES_READBACK",
                "statement_id": None, "returncode": 1}
    original = protected / "ledger/day5-c2000-roster-v1.json"
    original.write_bytes(canonical(external))
    tasks = {f"done-{i:03d}": {"status": "COMPLETE"} for i in range(500)}
    tasks.update({"P5": {"status": "COMPLETE"}, "P6": {"status": "COMPLETE"},
                  "sql-roster": {"status": "VALIDATING", "external": external}})
    tasks.update({f"later-{i:02d}": {"status": "PLANNED"} for i in range(10)})
    state_path = state_dir / "checkpoint.json"
    state_path.write_bytes(canonical({"queue_sha256": file_digest(queue_path),
                                      "grant_id": "grant-1", "tasks": tasks}))
    operation = task["operation_id"] + "-recovery-v1"
    disposition = {
        "schema": "EDP_SQL_PRE_SUBMISSION_DISPOSITION_V1", "authority": "owner-v1",
        "decision": "AUTHORIZE_DISTINCT_TECHNICAL_RECOVERY", "task_id": "sql-roster",
        "queue_sha256": file_digest(queue_path),
        "checkpoint_sha256": file_digest(state_path),
        "original_operation_id": task["operation_id"],
        "original_ledger_sha256": file_digest(original),
        "target_table": task["databricks_table"], "original_statement_id": None,
        "recovery_operation_id": operation,
        "query_history_result": "ZERO_COMPLETE_PAGE",
        "query_history_window_start_ms": 1792791300000,
        "query_history_window_end_ms": 1792792200000,
        "uc_target_result": "AUTHENTICATED_NOT_FOUND",
        "default_auth_result": "FAILED",
        "explicit_profile_result": "AUTHENTICATED_EXPECTED_USER",
    }
    evidence_dir = state_dir / "day5/p11_sql_recovery_inspection"
    evidence_dir.mkdir(parents=True)
    uc_stdout = b""
    uc_stderr = ("Error: Table '" + task["databricks_table"] +
                 "' does not exist.\n").encode()
    (evidence_dir / "uc_target.stdout").write_bytes(uc_stdout)
    (evidence_dir / "uc_target.stderr").write_bytes(uc_stderr)
    (evidence_dir / "uc_target.exit_code").write_text("1\n")
    evidence = {
        "default_auth": ("default_auth_test.json", {"exit_code": 1}),
        "explicit_profile": ("explicit_profile_auth_test.json", {
            "exit_code": 0, "authenticated_user": "chengzhu13@gmail.com"}),
        "query_history": ("protected_query_history_2135_2150_utc.json", {
            "has_next_page": False,
            "query_start_time_range": {"start_time_ms": 1792791300000,
                                       "end_time_ms": 1792792200000}}),
        "uc_target": ("uc_target_test.json", {
            "exit_code": 1, "error_code": "TABLE_DOES_NOT_EXIST",
            "table": task["databricks_table"],
            "stdout_sha256": hashlib.sha256(uc_stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(uc_stderr).hexdigest()}),
    }
    disposition["evidence_sha256"] = {}
    for name, (filename, value) in evidence.items():
        path = evidence_dir / filename
        path.write_bytes(canonical(value))
        disposition["evidence_sha256"][name] = file_digest(path)
    disposition_path = protected / "disposition.json"
    disposition_path.write_bytes(canonical(disposition))
    monkeypatch.setattr("edp_lab.operating.protected_recovery.load_grant", lambda *_: {
        "authority": "policy-broker-v1", "grant_id": "grant-1",
        "contracts": {"queue": {"sha256": file_digest(queue_path)}}})
    monkeypatch.setattr("edp_lab.operating.protected_recovery.verified_document",
                        lambda _root, path, _trust: disposition if path == disposition_path
                        else json.loads(path.read_bytes()))
    monkeypatch.setattr("edp_lab.operating.protected_recovery._sign",
                        lambda document, _key, output: output.write_bytes(canonical(document)))
    return root, queue_path, protected, trust, state_path, disposition_path, task, disposition


def test_exact_transition_preserves_502_and_original_ledger(tmp_path, monkeypatch):
    root, queue, protected, trust, state, disposition_path, task, _ = case(
        tmp_path, monkeypatch)
    before = json.loads(state.read_bytes())
    original = protected / "ledger/day5-c2000-roster-v1.json"
    original_bytes = original.read_bytes()
    result = recover_pre_submission_sql(root, queue, protected / "grant.json", state,
                                        trust, protected / "verifier.pem", disposition_path)
    after = json.loads(state.read_bytes())
    recovery = after["tasks"]["sql-roster"]["technical_recovery"]
    assert result["recovery_operation_id"] == task["operation_id"] + "-recovery-v1"
    assert after["tasks"]["sql-roster"]["status"] == "PLANNED"
    assert after["tasks"]["sql-roster"]["original_external"] == before["tasks"][
        "sql-roster"]["external"]
    assert {k: v for k, v in after["tasks"].items() if k != "sql-roster"} == {
        k: v for k, v in before["tasks"].items() if k != "sql-roster"}
    assert original.read_bytes() == original_bytes
    assert verify_sql_recovery(root, queue, state, task, recovery, trust)[
        "recovery_operation_id"] == result["recovery_operation_id"]
    original.write_text("{}")
    with pytest.raises(Denied, match="SQL_ORIGINAL_LEDGER_CHANGED"):
        verify_sql_recovery(root, queue, state, task, recovery, trust)


@pytest.mark.parametrize("response", [
    b"Error: PERMISSION_DENIED\n",
    b"Error: connection refused\n",
    b"Error: Table 'workspace.edp_lab.other' does not exist.\n",
])
def test_protected_transition_rejects_raw_uc_failure(tmp_path, monkeypatch, response):
    root, queue, protected, trust, state, disposition_path, _, _ = case(
        tmp_path, monkeypatch)
    raw = protected / "state/day5/p11_sql_recovery_inspection/uc_target.stderr"
    raw.write_bytes(response)
    with pytest.raises(Denied, match="SQL_RECOVERY_EVIDENCE_NOT_PRE_SUBMISSION"):
        recover_pre_submission_sql(root, queue, protected / "grant.json", state,
                                   trust, protected / "verifier.pem", disposition_path)
    assert json.loads(state.read_bytes())["tasks"]["sql-roster"]["status"] == "VALIDATING"


@pytest.mark.parametrize("change,reason", [
    ("missing_disposition", "SQL_RECOVERY_DISPOSITION_INVALID"),
    ("new_ledger", "SQL_RECOVERY_OPERATION_ALREADY_RESERVED"),
    ("original_changed", "SQL_ORIGINAL_LEDGER_CHECKPOINT_MISMATCH"),
    ("checkpoint_changed", "SQL_RECOVERY_DISPOSITION_INVALID"),
    ("evidence_changed", "SQL_RECOVERY_EVIDENCE_HASH_CHANGED"),
])
def test_negative_guards(tmp_path, monkeypatch, change, reason):
    root, queue, protected, trust, state, disposition_path, task, disposition = case(
        tmp_path, monkeypatch)
    if change == "missing_disposition":
        disposition["query_history_result"] = "INCOMPLETE"
    elif change == "new_ledger":
        (protected / "ledger" / (task["operation_id"] + "-recovery-v1.json")).write_text("x")
    elif change == "original_changed":
        (protected / "ledger/day5-c2000-roster-v1.json").write_text("{}")
    else:
        if change == "checkpoint_changed":
            value = json.loads(state.read_bytes())
            value["used"] = {"operations": 1}
            state.write_bytes(canonical(value))
        else:
            evidence = protected / "state/day5/p11_sql_recovery_inspection/default_auth_test.json"
            evidence.write_text("{}")
    with pytest.raises(Denied, match=reason):
        recover_pre_submission_sql(root, queue, protected / "grant.json", state,
                                   trust, protected / "verifier.pem", disposition_path)
    assert json.loads(state.read_bytes())["tasks"]["sql-roster"]["status"] == "VALIDATING"
    assert not (protected / "receipts/recovery-sql-roster.json").exists()


def test_sql_attestation_uses_recovery_operation_and_exact_remote_readback(
        tmp_path, monkeypatch):
    root, queue, protected, trust, state, disposition_path, task, _ = case(
        tmp_path, monkeypatch)
    statement = root / "statement.json"
    statement.write_text("{\"statement\":\"CREATE TABLE " + task["databricks_table"]
                         + " AS SELECT 1\"}")
    queued = json.loads(queue.read_bytes())
    queued["tasks"][0].update({"statement_path": "statement.json",
                               "statement_contract": "roster",
                               "external_receipt": str(protected / "receipts/sql-roster.json")})
    queue.write_bytes(canonical(queued))
    checkpoint = json.loads(state.read_bytes())
    checkpoint["queue_sha256"] = file_digest(queue)
    state.write_bytes(canonical(checkpoint))
    disposition = json.loads(disposition_path.read_bytes())
    disposition["queue_sha256"] = file_digest(queue)
    disposition["checkpoint_sha256"] = file_digest(state)
    disposition_path.write_bytes(canonical(disposition))
    monkeypatch.setattr("edp_lab.operating.protected_recovery.verified_document",
                        lambda _root, path, _trust: disposition if path == disposition_path
                        else json.loads(path.read_bytes()))
    monkeypatch.setattr("edp_lab.operating.protected_recovery.load_grant", lambda *_: {
        "authority": "policy-broker-v1", "grant_id": "grant-1",
        "contracts": {"queue": {"sha256": file_digest(queue)}}})
    recover_pre_submission_sql(root, queue, protected / "grant.json", state,
                               trust, protected / "verifier.pem", disposition_path)
    checkpoint = json.loads(state.read_bytes())
    checkpoint["tasks"]["sql-roster"]["status"] = "VALIDATING"
    checkpoint["tasks"]["sql-roster"]["external"] = {
        "status": "SUBMITTED_REQUIRES_READBACK", "statement_id": "statement-123",
        "submitted_at_utc": "2026-10-24T00:00:00+00:00"}
    state.write_bytes(canonical(checkpoint))
    monkeypatch.setattr("edp_lab.operating.protected_verifier.load_grant", lambda *_: {
        "authority": "policy-broker-v1", "grant_id": "grant-1",
        "contracts": {"queue": {"sha256": file_digest(queue)},
                      "roster": {"sha256": file_digest(statement)}},
        "limits": {"runtime_seconds": 30}})
    monkeypatch.setattr("edp_lab.operating.protected_verifier._remote_json",
                        lambda path, _timeout: ({"statement_id": "statement-123",
                        "status": {"state": "SUCCEEDED"}} if "statements/" in path else
                        {"full_name": task["databricks_table"], "table_id": "table-123"}))
    monkeypatch.setattr("edp_lab.operating.protected_verifier._sign",
                        lambda document, _key, output: output.write_bytes(canonical(document)))
    result = attest_sql(root, queue, protected / "grant.json", state, "sql-roster",
                        trust, protected / "verifier.pem")
    receipt = json.loads((protected / "receipts/sql-roster.json").read_bytes())
    assert result["operation_id"] == task["operation_id"] + "-recovery-v1"
    assert receipt["operation_id"] == result["operation_id"]
    assert receipt["terminal_state"] == "SUCCEEDED"
    assert receipt["uc_table_id"] == "table-123"
