"""Fail-closed SQL submission checks for the protected Day 5 boundary."""

import json
import subprocess
from types import SimpleNamespace

import pytest

from edp_lab.operating.authority import Denied, digest
from edp_lab.operating.boundaries import databricks_write
from edp_lab.operating.runner import _external_verified


def _case(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    statement = root / "statement.json"
    statement.write_text(json.dumps({
        "warehouse_id": "approved-warehouse",
        "statement": "CREATE TABLE workspace.edp_lab.n500_roster USING DELTA AS SELECT 1",
    }))
    for name in ("parser", "model", "rule"):
        (root / name).write_text(name)
    contracts = {name: {"version": "V1", "sha256": digest((root / name).read_bytes())}
                 for name in ("parser", "model", "rule")}
    contracts["statement"] = {"version": "V1", "sha256": digest(statement.read_bytes())}
    grant = {
        "cohort": "C2000", "operations": ["databricks_write"], "sources": {},
        "contracts": contracts,
        "databricks_paths": [], "databricks_tables": ["workspace.edp_lab.n500_roster"],
        "outputs": ["workspace.edp_lab.result"], "git_operations": [],
        "protected_branches": ["main"], "limits": {"runtime_seconds": 30,
                                                   "operations": 1, "compute_units": 0,
                                                   "token_count": 0, "retries": 0},
    }
    request = {
        "operation": "databricks_write", "cohort": "C2000",
        "output": "workspace.edp_lab.result", "operation_id": "roster-once",
        "databricks_table": "workspace.edp_lab.n500_roster",
        "statement_path": "statement.json", "grant_path": str(tmp_path / "grant.json"),
        "contracts": {name: {"version": "V1", "path": name}
                      for name in ("parser", "model", "rule")}
        | {"statement": {"version": "V1", "path": "statement.json"}},
    }
    monkeypatch.setattr("edp_lab.operating.boundaries.load_grant", lambda *_: grant)
    monkeypatch.setattr("edp_lab.operating.boundaries.protected_trust_dir",
                        lambda *_: tmp_path / "trust")
    monkeypatch.setattr("edp_lab.operating.boundaries.databricks_argv",
                        lambda *args: ["databricks", *args])
    return root, grant, request, tmp_path / "ledger"


def test_submission_uses_profile_and_durably_records_statement_id(tmp_path, monkeypatch):
    root, grant, request, ledger = _case(tmp_path, monkeypatch)
    calls = []

    def submit(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            "statement_id": "statement-123", "status": {"state": "PENDING"}}), stderr="")

    monkeypatch.setattr("edp_lab.operating.boundaries.subprocess.run", submit)
    result = databricks_write(root, grant, request, ledger, execute=True)
    assert calls == [["databricks", "api", "post", "/api/2.0/sql/statements",
                      "--json", "@" + str(root / "statement.json"),
                      "-p", "edp-lab", "-o", "json"]]
    assert result["status"] == "SUBMITTED_REQUIRES_READBACK"
    assert result["statement_id"] == "statement-123"
    assert json.loads((ledger / "roster-once.json").read_text()) == result
    with pytest.raises(Denied, match="OPERATION_REPLAY_OR_UNCERTAIN_RESULT"):
        databricks_write(root, grant, request, ledger, execute=True)
    assert len(calls) == 1


@pytest.mark.parametrize("response", [
    SimpleNamespace(returncode=1, stdout="", stderr="authentication failed"),
    SimpleNamespace(returncode=0, stdout="{}", stderr=""),
    SimpleNamespace(returncode=0, stdout="[]", stderr=""),
    subprocess.TimeoutExpired("databricks", 30, output=b"", stderr=b"timed out"),
])
def test_uncertain_submission_remains_reserved(tmp_path, monkeypatch, response):
    root, grant, request, ledger = _case(tmp_path, monkeypatch)

    def submit(_argv, **_kwargs):
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr("edp_lab.operating.boundaries.subprocess.run", submit)
    result = databricks_write(root, grant, request, ledger, execute=True)
    assert result["status"] == "UNCERTAIN_REQUIRES_READBACK"
    assert result["statement_id"] is None
    assert json.loads((ledger / "roster-once.json").read_text()) == result
    with pytest.raises(Denied, match="OPERATION_REPLAY_OR_UNCERTAIN_RESULT"):
        databricks_write(root, grant, request, ledger, execute=True)


def test_sql_receipt_cannot_complete_checkpoint_without_submitted_id(
        tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    receipt = tmp_path / "receipt.json"
    receipt.write_text("signed receipt fixture")
    monkeypatch.setattr("edp_lab.operating.runner.verified_document", lambda *_: {
        "schema": "EDP_EXTERNAL_OPERATION_RECEIPT_V1", "operation_id": "roster-once",
        "request_sha256": digest(b"request"), "status": "VERIFIED",
        "live_readback": True, "statement_id": "statement-123",
        "terminal_state": "SUCCEEDED", "table": "workspace.edp_lab.n500_roster",
        "uc_table_id": "table-123", "terminal_response_sha256": "a" * 64,
        "uc_response_sha256": "b" * 64,
    })
    monkeypatch.setattr("edp_lab.operating.runner.protected_trust_dir",
                        lambda *_: tmp_path / "trust")
    # The receipt is otherwise exact; only the checkpoint Statement ID is absent.
    monkeypatch.setattr("edp_lab.operating.runner.digest", lambda *_: digest(b"request"))
    task = {"kind": "databricks_write", "external_receipt": str(receipt),
            "databricks_table": "workspace.edp_lab.n500_roster",
            "_statement_id": None}
    assert not _external_verified(root, task, {"operation_id": "roster-once"})
    task["_statement_id"] = "statement-123"
    assert _external_verified(root, task, {"operation_id": "roster-once"})
