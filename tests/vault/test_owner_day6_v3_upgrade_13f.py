"""13F recovery is a separate, one-shot, signed successor of failed canary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_day6_v3_upgrade_13f as newer


def test_versioned_deployment_keeps_same_exact_source_and_target_scope():
    previous = json.loads(newer.OLD_REQUEST.read_bytes())
    current = json.loads((ROOT / "metadata/operating/"
                          "day6_c2000_vault_v3_bounded_request_13f_fix_v1.json").read_bytes())
    assert current["selection"] == previous["selection"]
    assert current["semantic_approval_request"] == previous["semantic_approval_request"]
    assert current["target_namespace"] == previous["target_namespace"]
    assert current["new_v3_table_allowlist"] == previous["new_v3_table_allowlist"]
    assert current["existing_tables_read_only"] == previous["existing_tables_read_only"]
    assert current["execution"]["data_rows_max"] == 2048
    assert current["execution"]["automatic_retries_max"] == 0
    assert current["execution"]["runtime_artifact_sha256"] == newer.WHEEL_SHA
    assert newer.OLD_WHEEL_SHA != newer.WHEEL_SHA


def test_successor_canary_does_not_allow_execute_or_old_job_replay():
    args = newer.canary_parameters()
    assert "--execute" not in args
    assert "--verify-only" not in args
    assert "--v0a-smoke" not in args
    assert newer.NEW_REMOTE_REQUEST in args
    assert newer.CURRENT_REQUEST_SHA256 in args
    assert newer.EXPECTED_OLD_JOB not in [newer.NEW_JOB, newer.NEW_RUN]
    assert newer.NEW_REMOTE_DIR != "/Workspace/Shared/edp-lab/day6-c2000-v3-edgar-fix-v1"


def test_new_canary_job_reservation_is_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(newer, "NEW_JOB", tmp_path / "absent.json")
    reservation = tmp_path / "pending.json"
    reservation.write_text('{"status":"RESERVED_BEFORE_CREATE"}')
    monkeypatch.setattr(newer, "NEW_JOB_RESERVATION", reservation)
    monkeypatch.setattr(newer, "admin_cli", lambda *_args, **_kwargs:
                        pytest.fail("remote call after uncertain create"))
    with pytest.raises(RuntimeError, match="V3_13F_UNCERTAIN_JOB_CREATE_DO_NOT_REPLAY"):
        newer.ensure_job({})


def test_new_canary_run_reservation_is_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(newer, "NEW_RUN", tmp_path / "absent.json")
    reservation = tmp_path / "pending.json"
    reservation.write_text('{"status":"RESERVED_BEFORE_REMOTE_SUBMISSION"}')
    monkeypatch.setattr(newer, "NEW_RUN_RESERVATION", reservation)
    monkeypatch.setattr(newer, "admin_cli", lambda *_args, **_kwargs:
                        pytest.fail("remote call after uncertain submission"))
    with pytest.raises(RuntimeError, match="V3_13F_UNCERTAIN_RUN_SUBMISSION_DO_NOT_REPLAY"):
        newer.ensure_run(99)


def test_existing_run_must_bind_exact_new_owner_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(newer, "NEW_RUN", tmp_path / "run.json")
    (tmp_path / "run.json").write_text(json.dumps(
        {"job_id": 77, "run_id": 88, "approval_sha256": "x" * 64}))
    monkeypatch.setattr(newer, "file_digest", lambda *_: "a" * 64)
    monkeypatch.setattr(newer, "admin_cli", lambda *_args, **_kwargs:
                        pytest.fail("existing run must not submit again"))
    with pytest.raises(RuntimeError, match="V3_13F_CANARY_RUN_LEDGER_CHANGED"):
        newer.ensure_run(77)


def test_predecessor_failure_cannot_be_adopted_without_exact_terminal_proof(
        tmp_path, monkeypatch):
    old_job = tmp_path / "old-job.json"
    old_run = tmp_path / "old-run.json"
    old_job.write_text(json.dumps({"job_id": newer.EXPECTED_OLD_JOB}))
    old_run.write_text(json.dumps({
        "job_id": newer.EXPECTED_OLD_JOB,
        "run_id": newer.EXPECTED_OLD_RUN,
        "approval_sha256": "a" * 64,
    }))
    monkeypatch.setattr(newer, "OLD_CANARY_JOB", old_job)
    monkeypatch.setattr(newer, "OLD_CANARY_RUN", old_run)
    monkeypatch.setattr(newer, "file_digest", lambda *_: "a" * 64)
    monkeypatch.setattr(newer, "_remote_digest", lambda *_: newer.OLD_WHEEL_SHA)
    monkeypatch.setattr(newer, "verified_document", lambda _root, path, _trust:
                        {
                            "status": "APPROVED",
                            "request_sha256": newer.OLD_REQUEST_SHA,
                            "deployment_sha256": newer.OLD_DEPLOYMENT_SHA,
                            "wheel_sha256": newer.OLD_WHEEL_SHA,
                            "standing_sha256": newer.STANDING_SHA,
                            "original_e2e_sha256": newer.OLD_E2E_SHA,
                        } if path == newer.OLD_APPROVAL else {
                            "status": "APPROVED",
                            "original_approval_sha256": "a" * 64,
                            "wheel_sha256": newer.OLD_WHEEL_SHA,
                        })
    monkeypatch.setattr(newer, "admin_cli", lambda *_args, **_kwargs: {
        "job_id": newer.EXPECTED_OLD_JOB,
        "settings": {"tasks": []},
    })
    monkeypatch.setattr(newer, "_signed_once", lambda *_: pytest.fail(
        "must not sign failed canary if previous settings do not validate"))
    with pytest.raises((IndexError, RuntimeError)):
        newer.predecessor_no_effect(
            json.loads(newer.REQUEST.read_bytes()),
            {"historical_table_ids": {}},
        )


def test_approved_successor_canary_is_separate_from_old_failed_run():
    assert newer.EXPECTED_OLD_RUN == 1057011099528821
    assert newer.EXPECTED_OLD_TASK == 749464491620163
    assert newer.OLD_CANARY_RUN.name != newer.NEW_RUN.name
    assert newer.OLD_CANARY_NO_EFFECT.name != newer.E2E_READY.name
