"""Protected canary v3 must be a distinct one-shot after v1/v2 terminal proofs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_day6_v3_upgrade_coverpage as upgrade


def test_v3_scope_is_only_new_wheel_and_deployment():
    old = json.loads(upgrade.V2_REQUEST.read_bytes())
    new = json.loads(upgrade.REQUEST.read_bytes())
    dep = json.loads(upgrade.DEPLOYMENT.read_bytes())
    assert {key: item for key, item in old.items() if key != "execution"} == {
        key: item for key, item in new.items() if key != "execution"
    }
    assert {k: v for k, v in old["execution"].items()
            if k not in {"runtime_artifact_sha256", "deployment_sha256"}} == {
        k: v for k, v in new["execution"].items()
        if k not in {"runtime_artifact_sha256", "deployment_sha256"}
    }
    assert new["selection"]["physical_data_rows"] == 2047
    assert new["negative_oracles"]["isolated_fixture_count"] == 24
    assert len(new["new_v3_table_allowlist"]) == 23
    assert dep["artifact"]["sha256"] == upgrade.WHEEL_SHA
    assert new["execution"]["runtime_artifact_sha256"] == upgrade.WHEEL_SHA
    assert dep["artifact"]["workspace_target_proposed"].startswith(upgrade.REMOTE_DIR)
    assert upgrade.V2_WHEEL_SHA != upgrade.WHEEL_SHA
    assert upgrade.V2_REQUEST != upgrade.REQUEST


def test_v3_canary_ledger_and_owner_approval_are_distinct():
    assert upgrade.V2_RUN_ID == 321745477125884
    assert upgrade.V2_JOB_ID == 552562574530819
    assert upgrade.V2_TASK_ID == 299105441863960
    assert upgrade.JOB != upgrade.V2_JOB_LEDGER
    assert upgrade.RUN != upgrade.V2_RUN_LEDGER
    assert upgrade.JOB_RESERVATION != upgrade.predecessor.NEW_JOB_RESERVATION
    assert upgrade.RUN_RESERVATION != upgrade.predecessor.NEW_RUN_RESERVATION
    assert upgrade.E2E_READY.name == "day6-v3-e2e-ready-coverpage-fix-v3.signed.json"
    assert upgrade.UPGRADE_APPROVAL.name == "day6-v3-coverpage-fix-upgrade-v3.signed.json"
    assert upgrade.V2_NO_EFFECT.name == "day6-v3-13f-canary-2-no-effect.signed.json"
    assert upgrade.V1_NO_EFFECT != upgrade.V2_NO_EFFECT


def test_v3_only_configures_new_canary_and_stays_read_only():
    upgrade.configure_distinct_canary()
    p = upgrade.predecessor
    assert p.WHEEL_SHA == upgrade.WHEEL_SHA
    assert p.REQUEST == upgrade.REQUEST
    assert p.DEPLOYMENT == upgrade.DEPLOYMENT
    assert p.UPGRADE_APPROVAL == upgrade.UPGRADE_APPROVAL
    assert p.OLD_CANARY_NO_EFFECT == upgrade.V2_NO_EFFECT
    assert p.NEW_JOB == upgrade.JOB
    assert p.NEW_RUN == upgrade.RUN
    assert p.NEW_REMOTE_DIR == upgrade.REMOTE_DIR
    params = p.canary_parameters()
    assert params[0:2] == ["--request", upgrade.REMOTE_REQUEST]
    assert "--execute" not in params
    assert "--v0a-smoke" not in params
    assert "--verify-only" not in params


def test_v3_uncertain_prior_reservations_refuse_new_submission(tmp_path, monkeypatch):
    upgrade.configure_distinct_canary()
    p = upgrade.predecessor
    monkeypatch.setattr(p, "NEW_RUN", tmp_path / "missing.json")
    reservation = tmp_path / "run-reservation.json"
    reservation.write_text('{"status":"RESERVED_BEFORE_REMOTE_SUBMISSION"}')
    monkeypatch.setattr(p, "NEW_RUN_RESERVATION", reservation)
    monkeypatch.setattr(p, "admin_cli", lambda *_args, **_kw:
                        pytest.fail("must not contact Databricks after uncertain reservation"))
    with pytest.raises(RuntimeError, match="UNCERTAIN_RUN_SUBMISSION_DO_NOT_REPLAY"):
        p.ensure_run(17)


def test_v3_wheel_provenance_rejects_wrong_bytes_before_unattended_upgrade(
        tmp_path, monkeypatch):
    wrong = tmp_path / "bad.whl"
    wrong.write_bytes(b"bad")
    with pytest.raises(RuntimeError, match="V3_COVERPAGE_WHEEL_SHA_CHANGED"):
        upgrade.wheel_provenance({
            "artifact": {"local_build_output_uncommitted": str(wrong)}
        })


def test_v2_terminal_no_effect_receipt_must_be_signed(monkeypatch):
    """Fail before any signing or canary creation if predecessor v1 proof absent."""
    monkeypatch.setattr(upgrade, "verified_document",
                        lambda *_a, **_kw: {"status": "INVALID"})
    monkeypatch.setattr(upgrade, "admin_cli",
                        lambda *_a, **_kw: pytest.fail("untrusted predecessor contacted"))
    monkeypatch.setattr(upgrade, "_signed_once",
                        lambda *_a, **_kw: pytest.fail("must not sign an invalid receipt"))
    with pytest.raises(RuntimeError, match="FIRST_CANARY_NO_EFFECT_REQUIRED"):
        upgrade.predecessor_no_effect(
            json.loads(upgrade.REQUEST.read_bytes()),
            {"historical_table_ids": {}},
        )
