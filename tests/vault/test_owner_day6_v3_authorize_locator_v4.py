"""Fail closed before signing canary v3 no-effect and v4 approval."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import owner_day6_v3_authorize_locator_v4 as gate
from owner_day6_v3_one_shot import _job_settings

from edp_lab.operating.authority import Denied


def test_missing_failed_canary_e2e_uses_real_signed_baseline(monkeypatch, tmp_path):
    digests = {gate.STANDING: gate.STANDING_SHA, gate.E2E: gate.OLD_E2E_SHA,
               gate.V1_NO_EFFECT: "1", gate.V2_NO_EFFECT: "2",
               gate.V2_APPROVAL: "3", gate.PRIOR_DEPLOYMENT: "4"}
    docs = {
        gate.STANDING: {"status": "INSTALLED"},
        gate.E2E: {"schema": "EDP_VAULT_E2E_READY_V1", "status": "VERIFIED",
                   "standing_sha256": gate.STANDING_SHA, "run_as": gate.APP_ID,
                   "isolated_persisted_readback": True},
        gate.INSTALL: {"schema": "EDP_DAY6_V3_INSTALL_RECEIPT_V1",
                       "status": "INSTALLED_NOT_GRANTED", "run_as": gate.APP_ID,
                       "historical_table_ids": {str(n): str(n) for n in range(8)}},
        gate.V1_NO_EFFECT: {"schema": "EDP_DAY6_V3_UPGRADE_CANARY_NO_EFFECT_V1",
                            "status": "TERMINAL_NO_REMOTE_EFFECT",
                            "job_id": gate.EXPECTED_OLD_JOB, "run_id": gate.EXPECTED_OLD_RUN,
                            "task_run_id": gate.EXPECTED_OLD_TASK},
        gate.V2_NO_EFFECT: {"schema": "EDP_DAY6_V3_UPGRADE_CANARY_NO_EFFECT_V1",
                            "status": "TERMINAL_NO_REMOTE_EFFECT",
                            "job_id": gate.V2_JOB_ID, "run_id": gate.V2_RUN_ID,
                            "task_run_id": gate.V2_TASK_ID,
                            "old_approval_sha256": "3", "old_wheel_sha256": gate.V2_WHEEL_SHA,
                            "prior_canary_no_effect_sha256": "1"},
        gate.V2_APPROVAL: {"schema": "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1",
                           "status": "APPROVED", "request_sha256": gate.V2_REQUEST_SHA,
                           "deployment_sha256": gate.V2_DEPLOYMENT_SHA,
                           "wheel_sha256": gate.V2_WHEEL_SHA,
                           "failed_canary_no_effect_sha256": "1"},
        gate.V3_APPROVAL: {"schema": "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1",
                           "status": "APPROVED", "request_sha256": gate.V3_REQUEST_SHA,
                           "deployment_sha256": "4", "wheel_sha256": gate.V3_WHEEL_SHA,
                           "standing_sha256": gate.STANDING_SHA,
                           "original_e2e_sha256": gate.OLD_E2E_SHA,
                           "failed_canary_no_effect_sha256": "2",
                           "previous_upgrade_approval_sha256": "3",
                           "first_canary_no_effect_sha256": "1"},
    }
    monkeypatch.setattr(gate, "file_digest", lambda path: digests[path])
    monkeypatch.setattr(gate, "verified_document", lambda _, path, __: docs[path])
    failed = tmp_path / "v3-e2e.signed.json"
    monkeypatch.setattr(gate, "FAILED_CANARY_E2E", failed)

    class Pin:
        def is_file(self): return True
        def is_symlink(self): return False
        def stat(self): return SimpleNamespace(st_uid=0, st_mode=0o644)
        def read_text(self): return gate.OLD_COMMIT

    monkeypatch.setattr(gate, "INSTALLED_COMMIT", Pin())
    monkeypatch.setattr(gate, "socket_action", lambda _: {
        "status": "READY_FOR_DISTINCT_ATTEMPT", "next_attempt": 2,
        "standing_sha256": gate.STANDING_SHA, "e2e_sha256": gate.OLD_E2E_SHA})
    assert len(gate._prior_trust()["historical_table_ids"]) == 8
    failed.write_text("invalid retrospective receipt")
    with pytest.raises(RuntimeError, match="V4_PRIOR_SIGNED_CHAIN_INVALID"):
        gate._prior_trust()
    failed.unlink()
    docs[gate.V2_NO_EFFECT]["prior_canary_no_effect_sha256"] = "foreign"
    with pytest.raises(RuntimeError, match="V4_PRIOR_SIGNED_CHAIN_INVALID"):
        gate._prior_trust()
    docs[gate.V2_NO_EFFECT]["prior_canary_no_effect_sha256"] = "1"
    docs[gate.V3_APPROVAL]["request_sha256"] = "foreign"
    with pytest.raises(RuntimeError, match="V4_PRIOR_SIGNED_CHAIN_INVALID"):
        gate._prior_trust()


def _remote(monkeypatch, change=None):
    hist = {name: str(n) for n, name in enumerate((
        "h_concept", "h_filing", "l_fact_slot", "r_load_event", "r_source_occurrence",
        "s_fact_assertion", "s_num_m2_value", "vault_reject_quarantine"), 1)}
    targets = ["v3_r_source_occurrence"] + [f"v3_target_{n}" for n in range(22)]
    listed = [{"name": k, "table_id": v, "data_source_format": "DELTA",
               "properties": {"delta.lastUpdateVersion": "0"}} for k, v in hist.items()]
    listed.append({"name": "v0a_day6_e2e_20261025"})
    if change == "target": listed.append({"name": targets[0]})
    if change == "historical_version": listed[0]["properties"]["delta.lastUpdateVersion"] = "1"
    approval = "a" * 64
    ledgers = {
        gate.V3_JOB_RESERVATION: {"approval_sha256": approval,
                                  "request_sha256": gate.V3_REQUEST_SHA,
                                  "status": "RESERVED_BEFORE_CREATE"},
        gate.V3_JOB_LEDGER: {"job_id": gate.JOB_ID, "approval_sha256": approval},
        gate.V3_RUN_RESERVATION: {"job_id": gate.JOB_ID,
                                  "status": "RESERVED_BEFORE_REMOTE_SUBMISSION",
                                  "approval_sha256": approval},
        gate.V3_RUN_LEDGER: {"job_id": gate.JOB_ID, "run_id": gate.RUN_ID,
                             "approval_sha256": approval},
    }
    if change == "job_ledger": ledgers[gate.V3_JOB_LEDGER]["job_id"] += 1
    if change == "run_ledger": ledgers[gate.V3_RUN_LEDGER]["run_id"] += 1
    if change == "reservation": ledgers[gate.V3_JOB_RESERVATION]["request_sha256"] = "foreign"
    monkeypatch.setattr(gate, "_protected_ledger", lambda path: ledgers[path])
    monkeypatch.setattr(gate, "file_digest", lambda path: approval if path == gate.V3_APPROVAL else "b" * 64)
    monkeypatch.setattr(gate, "_remote_digest", lambda path:
                        "foreign" if change == "wheel" else
                        gate.V3_REQUEST_SHA if path == gate.V3_REMOTE_REQUEST else gate.V3_WHEEL_SHA)
    monkeypatch.setattr(gate, "_prior_trust", lambda: {"historical_table_ids": hist})
    deployment = json.loads(gate.PRIOR_DEPLOYMENT.read_bytes())
    params = ["--request", gate.V3_REMOTE_REQUEST, "--request-sha256", gate.V3_REQUEST_SHA,
              "--selection", "/Workspace/Shared/edp-lab/day6-c2000-v3/selection.json",
              "--negative-oracles", "/Workspace/Shared/edp-lab/day6-c2000-v3/negative-oracles.json"]
    settings = _job_settings(gate.V3_REQUEST_SHA, deployment)
    settings["name"] = gate.V3_JOB_NAME
    settings["tasks"][0]["python_wheel_task"]["parameters"] = params.copy()
    if change == "saved_job": settings["environments"][0]["spec"]["dependencies"] = ["foreign.whl"]
    if change == "saved_params": settings["tasks"][0]["python_wheel_task"]["parameters"] += ["--execute"]
    job = {"job_id": gate.JOB_ID, "run_as_user_name":
           "foreign" if change == "run_as" else gate.APP_ID, "settings": settings}
    if change == "foreign_job": job["job_id"] += 1
    run = {"job_id": gate.JOB_ID + (1 if change == "foreign_run" else 0),
           "run_id": gate.RUN_ID, "creator_user_name": gate.APP_ID,
           "run_name": gate.V3_JOB_NAME,
           "state": {"result_state": "SUCCESS" if change == "state" else "FAILED"},
           "status": {"state": "TERMINATED"},
           "tasks": [{"run_id": gate.TASK_ID, "task_key": "day6_v3_one_shot",
                      "attempt_number": 0, "environment_key": "v3_fixed_runtime",
                      "python_wheel_task": {"parameters": params +
                                             (["--execute"] if change == "run_params" else [])}}]}
    result = {"error": "ValueError: INVALID_OCCURRENCE_LOCATOR",
              "error_trace": "run -> _prepare_rows -> project -> occurrence_key",
              "metadata": {"job_id": gate.JOB_ID,
                           "run_id": gate.TASK_ID,
                           "creator_user_name": gate.APP_ID,
                           "python_wheel_task": {"parameters": params}}}
    if change == "output_meta": result["metadata"]["run_id"] += 1
    def cli(*args):
        return {("jobs", "get"): job, ("jobs", "get-run"): run,
                ("jobs", "get-run-output"): result, ("tables", "list"): listed}[args[:2]]
    monkeypatch.setattr(gate, "admin_cli", cli)
    return {"new_v3_table_allowlist": targets}


def test_exact_ledgers_saved_job_run_and_absent_targets(monkeypatch):
    proof = gate.reconcile(_remote(monkeypatch))
    assert proof["status"] == "TERMINAL_NO_REMOTE_EFFECT"
    assert proof["target_absent_count"] == 23
    assert len(proof["historical_table_ids"]) == 8
    assert proof["v3_request_sha256"] == gate.V3_REQUEST_SHA


@pytest.mark.parametrize("change", ["target", "historical_version", "state",
                                    "job_ledger", "run_ledger", "reservation",
                                    "wheel", "saved_job", "saved_params", "run_as",
                                    "foreign_job", "foreign_run", "run_params", "output_meta"])
def test_tampered_ledger_remote_job_or_run_blocks_signature(monkeypatch, change):
    with pytest.raises((RuntimeError, ValueError, Denied), match="V4_|VAULT_V3_"):
        gate.reconcile(_remote(monkeypatch, change))
