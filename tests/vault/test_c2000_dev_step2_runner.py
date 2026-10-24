"""The separately authorized DEV runner stays bounded and fail closed."""
from __future__ import annotations

import json

import pytest

from scripts import run_c2000_vault_dev_step2 as runner


def test_audit_sql_uses_literals_in_values_and_pins_real_statement_id():
    keys = [f"{index:064x}" for index in range(127)]
    write_id = "01f1cfc5-aff2-1200-a619-9300506bca95"
    sql = runner.audit_sql(keys, write_id)
    assert sql.startswith("MERGE INTO workspace.edp_lab_day6_vault_proto.r_load_event AS t\n")
    assert "FROM VALUES\n    ('" in sql
    assert "USING (SELECT decode(unhex(v.c1), 'UTF-8') AS occurrence_hk" in sql
    assert "WHEN MATCHED THEN" not in sql
    assert write_id.encode().hex() in sql
    assert runner.INPUT_SHA.encode().hex() in sql
    with pytest.raises(RuntimeError, match="AUDIT_SCOPE_INVALID"):
        runner.audit_sql([keys[0]] * 127, write_id)


def test_retry_requires_inspected_zero_submission_checkpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "OUT", tmp_path)
    previous = tmp_path / "journal.json"
    previous.write_text(json.dumps({"status": "PARTIAL_OR_FAILED_REQUIRES_INSPECTION",
                                    "statements": [], "counts": {}}))
    resumed = runner.Run(resume_after_no_submit=True)
    assert resumed.path.name == "journal-attempt-2.json"
    with pytest.raises(RuntimeError, match="EXISTING_RUN_REQUIRES_INSPECTION"):
        runner.Run(resume_after_no_submit=True)
    previous.write_text(json.dumps({"status": "PARTIAL_OR_FAILED_REQUIRES_INSPECTION",
                                    "statements": [{"status": "SUBMISSION_RESERVED"}],
                                    "counts": {}}))
    with pytest.raises(RuntimeError, match="PRIOR_ATTEMPT_MAY_HAVE_SUBMITTED_SQL"):
        runner.Run(resume_after_no_submit=True)
