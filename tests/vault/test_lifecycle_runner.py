"""Focused fail-closed checks for the Vault control-plane runner."""

import json
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied, file_digest
from edp_lab.vault.lifecycle_runner import (
    STAGES,
    _receipt,
    advance,
    load_plan,
    readiness,
    reconcile_external,
    reserve_external,
    run_until_boundary,
)
from edp_lab.vault.standing_v2 import NAMESPACE, SHARED_WAREHOUSE_ID, TABLES


def setup_plan(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path
    workflow = root / "docs/workflows/vault_model_integration_lifecycle_v1.md"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("approved workflow\n")
    baseline = root / "freeze.json"
    baseline.write_text("{}\n")
    plan = {
        "schema": "EDP_VAULT_LIFECYCLE_PLAN_V1", "cohort": "C2000",
        "workflow": "docs/workflows/vault_model_integration_lifecycle_v1.md",
        "workflow_sha256": file_digest(workflow), "namespace": NAMESPACE,
        "warehouse_id": SHARED_WAREHOUSE_ID, "tables": list(TABLES),
        "inputs": {"freeze": {"path": "freeze.json", "sha256": file_digest(baseline)}},
        "stages": {stage: {"kind": "protected" if stage in {"V4", "V9"} else "evidence",
                           "receipt": f"receipts/{stage}.json"} for stage in STAGES},
    }
    path = root / "plan.json"
    path.write_text(json.dumps(plan))
    return root, path


def test_pins_and_scope_fail_closed(tmp_path):
    root, path = setup_plan(tmp_path)
    assert load_plan(root, path)["cohort"] == "C2000"
    (root / "freeze.json").write_text("changed\n")
    with pytest.raises(Denied, match="VAULT_PIN_CHANGED"):
        load_plan(root, path)


def test_resume_does_not_repeat_or_accept_changed_receipt(tmp_path):
    root, path = setup_plan(tmp_path)
    state_dir = root / "state"
    assert advance(root, path, state_dir)["next_stage"] == "V0A"
    receipt = root / "receipts/V0A.json"
    receipt.parent.mkdir()
    receipt.write_text(json.dumps({"schema": "EDP_VAULT_LIFECYCLE_STAGE_V1",
                                   "cohort": "C2000", "stage": "V0A",
                                   "workflow_sha256": json.loads(path.read_text())["workflow_sha256"],
                                   "status": "PASS", "evidence": []}))
    state = advance(root, path, state_dir)
    assert state["next_stage"] == "V0"
    assert advance(root, path, state_dir)["completed"] == state["completed"]
    receipt.write_text(receipt.read_text() + "\n")
    with pytest.raises(Denied, match="VAULT_COMPLETED_EVIDENCE_CHANGED"):
        advance(root, path, state_dir)


def test_uncertain_external_is_never_replayed(tmp_path):
    root, path = setup_plan(tmp_path)
    state_dir = root / "state"
    advance(root, path, state_dir)
    state = json.loads((state_dir / "checkpoint.json").read_text())
    state["next_stage"] = "V4"
    (state_dir / "checkpoint.json").write_text(json.dumps(state))
    reserve_external(state_dir, stage="V4", operation_id="op1", request_sha256="a" * 64)
    assert advance(root, path, state_dir)["status"] == "UNCERTAIN_EXTERNAL_RECONCILIATION_REQUIRED"
    with pytest.raises(Denied, match="VAULT_EXTERNAL_OPERATION_NOT_READY"):
        reserve_external(state_dir, stage="V4", operation_id="op1", request_sha256="a" * 64)
    with pytest.raises(Denied, match="VAULT_EXTERNAL_RECEIPT_NOT_READY"):
        reconcile_external(root, path, state_dir)


def test_readiness_does_not_inherit_prototype_authority(tmp_path):
    root, path = setup_plan(tmp_path)
    result = readiness(root, path)
    assert result["protected_full_write_status"] == "BLOCKED"
    assert result["authority_blockers"]


def test_v1_requires_exact_roster_coverage(tmp_path):
    root, path = setup_plan(tmp_path)
    roster = root / "roster.csv"
    roster.write_text("source_instance_id\nSRC000001\n")
    plan = json.loads(path.read_text())
    plan["inputs"]["roster"] = {"path": "roster.csv", "sha256": file_digest(roster)}
    path.write_text(json.dumps(plan))
    receipt = root / "receipts/V1.json"
    receipt.parent.mkdir()
    receipt.write_text(json.dumps({"schema": "EDP_VAULT_LIFECYCLE_STAGE_V1",
                                   "cohort": "C2000", "stage": "V1",
                                   "workflow_sha256": plan["workflow_sha256"],
                                   "status": "PASS", "source_dispositions": {}}))
    with pytest.raises(Denied, match="VAULT_MODEL_FIT_COVERAGE_INCOMPLETE"):
        _receipt(root, plan, "V1")


def test_agent_inflight_requires_reconciliation(tmp_path):
    root, path = setup_plan(tmp_path)
    state_dir = root / "state"
    state = advance(root, path, state_dir)
    state["pending_agent"] = {"stage": "V0A"}
    (state_dir / "checkpoint.json").write_text(json.dumps(state))
    assert advance(root, path, state_dir)["status"] == "AGENT_OUTCOME_RECONCILIATION_REQUIRED"


def test_full_stage_orchestration_needs_no_manual_stage_invocations(tmp_path, monkeypatch):
    """A trusted V4 response flows through V5/V6/V8/V9 in the same run."""
    root, plan_path = setup_plan(tmp_path)
    index = {"value": 0}

    def fake_advance(*_args):
        return ({"status": "COMPLETE", "next_stage": None}
                if index["value"] == len(STAGES)
                else {"status": "EVIDENCE_REQUIRED", "next_stage": STAGES[index["value"]],
                      "v9_freeze": {"receipt_path": "signed.json", "receipt_sha256": "a" * 64}
                      if STAGES[index["value"]] == "V9" else None})

    def complete_stage(*_args, **_kwargs):
        index["value"] += 1
        return fake_advance()

    import edp_lab.vault.lifecycle_runner as runner

    monkeypatch.setattr(runner, "advance", fake_advance)
    monkeypatch.setattr(runner, "_mechanical_stage", complete_stage)
    monkeypatch.setattr(runner, "dispatch_agent", complete_stage)
    monkeypatch.setattr(runner, "dispatch_v4", complete_stage)
    monkeypatch.setattr(runner, "readiness", lambda *_: {
        "protected_full_write_status": "READY"})
    result = run_until_boundary(root, plan_path, root / "state", run_request="approved.json")
    assert result["status"] == "COMPLETE"
    assert index["value"] == len(STAGES)


def test_v4_authority_boundary_does_not_submit(tmp_path, monkeypatch):
    root, plan_path = setup_plan(tmp_path)
    import edp_lab.vault.lifecycle_runner as runner

    monkeypatch.setattr(runner, "advance", lambda *_: {
        "status": "EVIDENCE_REQUIRED", "next_stage": "V4"})
    monkeypatch.setattr(runner, "readiness", lambda *_: {
        "protected_full_write_status": "BLOCKED",
        "authority_blockers": ["INSTALLED_POLICY_EXCLUDES_FULL_C2000"]})
    monkeypatch.setattr(runner, "dispatch_v4", lambda *_: pytest.fail("write submitted"))
    result = run_until_boundary(root, plan_path, root / "state")
    assert result["status"] == "HUMAN_AUTHORIZATION_REQUIRED"


def test_v9_freeze_handoff_then_git_stage_is_automatic(tmp_path, monkeypatch):
    root, plan_path = setup_plan(tmp_path)
    import edp_lab.vault.lifecycle_runner as runner

    phase = {"value": "freeze"}

    def state(*_args):
        if phase["value"] == "done":
            return {"status": "COMPLETE", "next_stage": None}
        return {"status": "EVIDENCE_REQUIRED", "next_stage": "V9",
                "v9_freeze": {"receipt_path": "signed.json"}
                if phase["value"] == "git" else None}

    def freeze(*_args):
        phase["value"] = "git"
        return state()

    def git(*_args, **_kwargs):
        phase["value"] = "done"
        return state()

    monkeypatch.setattr(runner, "advance", state)
    monkeypatch.setattr(runner, "dispatch_v9_freeze", freeze)
    monkeypatch.setattr(runner, "dispatch_agent", git)
    result = run_until_boundary(root, plan_path, root / "state",
                                freeze_request="approved-freeze.json")
    assert result["status"] == "COMPLETE"
