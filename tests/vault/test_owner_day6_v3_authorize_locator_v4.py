"""The Owner gate proves canary no-effect before any signature is made."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import owner_day6_v3_authorize_locator_v4 as gate


def _remote(monkeypatch, *, add_target=False, run_state="FAILED"):
    historical = {name: str(n) for n, name in enumerate((
        "h_concept", "h_filing", "l_fact_slot", "r_load_event",
        "r_source_occurrence", "s_fact_assertion", "s_num_m2_value",
        "vault_reject_quarantine"), 1)}
    listed = [{"name": name, "table_id": identity,
               "data_source_format": "DELTA",
               "properties": {"delta.lastUpdateVersion": "0"}}
              for name, identity in historical.items()]
    listed.append({"name": "v0a_day6_e2e_20261025"})
    if add_target:
        listed.append({"name": "v3_r_source_occurrence"})
    run = {"job_id": gate.JOB_ID, "run_id": gate.RUN_ID,
           "state": {"result_state": run_state},
           "status": {"state": "TERMINATED"},
           "tasks": [{"run_id": gate.TASK_ID,
                      "python_wheel_task": {"parameters": ["--request", "readonly"]}}]}

    def cli(*args):
        if args[:2] == ("jobs", "get"):
            return {"job_id": gate.JOB_ID}
        if args[:2] == ("jobs", "get-run"):
            return run
        if args[:2] == ("jobs", "get-run-output"):
            return {"error": "ValueError: INVALID_OCCURRENCE_LOCATOR",
                    "error_trace": "run -> _prepare_rows -> project -> occurrence_key"}
        if args[:2] == ("tables", "list"):
            return listed
        raise AssertionError(args)

    monkeypatch.setattr(gate, "admin_cli", cli)
    monkeypatch.setattr(gate, "verified_document",
                        lambda *_: {"historical_table_ids": historical})
    return {"new_v3_table_allowlist": ["v3_r_source_occurrence"] +
            [f"v3_target_{n}" for n in range(22)]}


def test_exact_terminal_readonly_failure_and_unchanged_delta(monkeypatch):
    request = _remote(monkeypatch)
    result = gate.reconcile(request)
    assert result["status"] == "TERMINAL_NO_REMOTE_EFFECT"
    assert result["target_absent_count"] == 23
    assert len(result["historical_table_ids"]) == 8


@pytest.mark.parametrize("change", ["target", "state"])
def test_remote_effect_or_nonfailure_blocks_signature(monkeypatch, change):
    request = _remote(monkeypatch, add_target=change == "target",
                      run_state="SUCCESS" if change == "state" else "FAILED")
    with pytest.raises(RuntimeError, match="V4_"):
        gate.reconcile(request)
