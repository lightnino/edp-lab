"""Day 7 V3: preserve successful Job, grant only Owner SELECT on canary."""

from __future__ import annotations

import importlib.util
import inspect
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "day7_owner_canary_v3", ROOT / "scripts/owner_recover_day7_canary_select_v3.py")
assert SPEC and SPEC.loader
v3 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v3)


def test_successor_pins_old_commit_and_only_adds_two_files():
    assert v3.OLD_COMMIT == "4c5f399dd34729925d19d13b687c89c066dc304d"
    assert v3.SP_ID == "78491734320299"
    assert v3.ALLOWED_DIFF == {
        "scripts/owner_recover_day7_canary_select_v3.py",
        "tests/operating/test_day7_canary_select_v3.py",
    }


def test_grant_is_single_table_and_not_broad_or_repeated():
    source = inspect.getsource(v3.execute)
    assert source.count('owner_sql("GRANT SELECT ON TABLE "') == 1
    assert '" TO " + quoted_owner' in source
    assert 'owner_sql("SELECT universe_sha256, owner_decision_sha256 FROM "' in source
    assert source.index("day7._save_json(GRANT_INTENT") < source.index(
        'owner_sql("GRANT SELECT ON TABLE "')
    assert source.index('owner_sql("SELECT universe_sha256, owner_decision_sha256 FROM "') < source.index(
        'journal["reviewed_commit"] = commit')
    assert "day7.canary(" not in source
    assert "day7.publication(" not in source
    assert "service-principal-secrets-proxy" not in source
    assert "jobs" not in source


def test_old_successful_job_is_rechecked_instead_of_submitted():
    source = inspect.getsource(v3.precheck)
    assert 'day7.service("jobs", "get-run", run_id)' in source
    assert 'day7.service("jobs", "get-run-output", task_id)' in source
    assert '== "DAY7_PROTECTED_CANARY_PASS"' in source
    assert '== "SUCCESS"' in source
    assert "canary-submit-intent.json" in source
    assert "day7-pr80-canary-" in source
    assert "day7.service(" not in inspect.getsource(v3.execute)


def test_sql_terminal_error_never_claims_success(monkeypatch):
    monkeypatch.setattr(v3.day7, "admin", lambda *_a: {
        "statement_id": "statement-123",
        "status": {"state": "FAILED", "sql_state": "42501",
                   "error": {"error_code": "BAD_REQUEST",
                             "message": "no SELECT"}}})
    with pytest.raises(RuntimeError, match="DAY7_OWNER_SQL_FAILED:BAD_REQUEST:42501"):
        v3.owner_sql("SELECT 1")


def test_sql_success_inline_row(monkeypatch):
    monkeypatch.setattr(v3.day7, "admin", lambda *_a: {
        "statement_id": "statement-123", "status": {"state": "SUCCEEDED"},
        "result": {"data_array": [["a", "b"]]}})
    assert v3.owner_sql("SELECT 1")["result"]["data_array"] == [["a", "b"]]


def test_write_intent_before_single_grant_and_only_then_broker(monkeypatch, tmp_path):
    journal = {"reviewed_commit": v3.OLD_COMMIT, "completed": {}}
    current = tmp_path / "owner-journal.json"
    intent = tmp_path / "owner-grant-intent.json"
    receipts = [
        {"status": "UNIVERSE_PUBLISHED_AND_VERIFIED", "receipt_sha256": "a"},
        {"status": "VERIFIED", "receipt_sha256": "b"},
        {"status": "VERIFIED", "receipt_sha256": "c",
         "physical_identity": "SRC000002"},
    ]
    job = {"job_run_id": "12345", "task_run_id": "56789",
           "table": v3.day7.CANARY_TABLE, "table_id": "id",
           "notebook_sha256": "sha", "result": "DAY7_PROTECTED_CANARY_PASS",
           "independent_readback": "OWNER_SQL_EXACT_ONE_ROW"}
    monkeypatch.setattr(v3, "precheck", lambda *_: (journal, receipts, job))
    monkeypatch.setattr(v3, "GRANT_INTENT", intent)
    monkeypatch.setattr(v3.day7, "JOURNAL", current)
    monkeypatch.setattr(v3.day7, "BASE", tmp_path)
    monkeypatch.setattr(v3.day7, "_read_json",
                        lambda p: {"application_id": "existing-application-id"}
                        if p.name == "service-identity.json" else json.loads(p.read_text()))
    events = []

    def save(path, obj):
        events.append("save:" + path.name)
        path.write_text(json.dumps(obj))

    def owner_sql(sql):
        events.append(sql)
        if sql.startswith("SELECT"):
            return {"result": {"data_array": [
                [v3.day7.MANIFEST_SHA, v3.day7.DECISION_SHA]]}}
        assert intent.exists()
        return {"status": {"state": "SUCCEEDED"}}

    monkeypatch.setattr(v3.day7, "_save_json", save)
    monkeypatch.setattr(v3, "owner_sql", owner_sql)
    monkeypatch.setattr(v3.day7, "_mark",
                        lambda name, detail: events.append("mark:" + name))
    monkeypatch.setattr(v3.day7, "install_broker",
                        lambda: events.append("install_broker"))
    from edp_lab.operating import authority, protected_verifier

    monkeypatch.setattr(protected_verifier, "_sign",
                        lambda obj, _key, path: path.write_text(json.dumps(obj)))
    monkeypatch.setattr(authority, "verified_document",
                        lambda _root, path, _trust: json.loads(path.read_text()))

    def digest(path):
        return "signed-sha" if path.name == "day7-deployment.json" else "policy-sha"

    monkeypatch.setattr(v3.day7, "file_digest", digest)
    result = v3.execute("successor-commit")
    assert result["status"] == "RUNNER_DEPLOYED_AND_VERIFIED"
    assert events.index("save:owner-grant-intent.json") < next(
        i for i, x in enumerate(events) if x.startswith("GRANT SELECT ON TABLE "))
    grants = [e for e in events if e.startswith("GRANT ")]
    assert grants == [
        "GRANT SELECT ON TABLE " + v3.day7.CANARY_TABLE + " TO "
        + chr(96) + v3.OWNER + chr(96)]
    assert events.index("install_broker") > events.index("mark:job_canary")
    assert events[-1] == "mark:deployment"
    assert json.loads(current.read_text())["reviewed_commit"] == "successor-commit"
