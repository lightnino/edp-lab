"""Durable Vault lifecycle coordinator; the workflow and signed services own policy.

This module does not interpret business meaning or issue execution authority.  A
stage producer supplies evidence, and an independent verifier/owner supplies a
receipt where the workflow requires one.  External writes cross only the
installed Vault V2 service boundary.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.operating.authority import Denied, file_digest
from edp_lab.operating.runner import _codex_step, _event, _write_json
from edp_lab.vault.standing_v2 import NAMESPACE, SHARED_WAREHOUSE_ID, TABLES

WORKFLOW = "docs/workflows/vault_model_integration_lifecycle_v1.md"
STAGES = ("V0A", "V0", "V1", "V2", "V3", "V4", "V5", "V6", "V8", "V9")
OUTCOMES = {"PASS", "PARTIAL", "NOT_REQUIRED", "BLOCKED"}
PROTECTED = {"V4", "V9"}


def _repo_file(root: Path, relative: str, sha256: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise Denied("VAULT_PIN_OUTSIDE_REPO")
    resolved = (root / path).resolve(strict=True)
    if not resolved.is_relative_to(root.resolve()) or file_digest(resolved) != sha256:
        raise Denied("VAULT_PIN_CHANGED:" + relative)
    return resolved


def load_plan(root: Path, plan_path: Path) -> dict:
    """Validate configuration pins; a repository plan is never a write grant."""
    plan = json.loads(plan_path.read_bytes())
    if (plan.get("schema") != "EDP_VAULT_LIFECYCLE_PLAN_V1"
            or plan.get("workflow") != WORKFLOW
            or plan.get("namespace") != NAMESPACE
            or plan.get("warehouse_id") != SHARED_WAREHOUSE_ID
            or plan.get("tables") != list(TABLES)
            or not isinstance(plan.get("cohort"), str)
            or not plan["cohort"]
            or set(plan.get("stages", {})) != set(STAGES)):
        raise Denied("VAULT_LIFECYCLE_PLAN_INVALID")
    _repo_file(root, WORKFLOW, plan["workflow_sha256"])
    for name, pin in plan["inputs"].items():
        if set(pin) != {"path", "sha256"}:
            raise Denied("VAULT_INPUT_PIN_INVALID:" + name)
        _repo_file(root, pin["path"], pin["sha256"])
    for stage, spec in plan["stages"].items():
        if (set(spec) != {"receipt", "kind"}
                or spec["kind"] not in {"evidence", "protected"}
                or (stage in PROTECTED) != (spec["kind"] == "protected")):
            raise Denied("VAULT_STAGE_SPEC_INVALID:" + stage)
        receipt = Path(spec["receipt"])
        if receipt.is_absolute() or ".." in receipt.parts or receipt.suffix != ".json":
            raise Denied("VAULT_RECEIPT_PATH_INVALID:" + stage)
    return plan


def _receipt(root: Path, plan: dict, stage: str) -> dict | None:
    path = root / plan["stages"][stage]["receipt"]
    if not path.exists():
        return None
    receipt = json.loads(path.read_bytes())
    if (receipt.get("schema") != "EDP_VAULT_LIFECYCLE_STAGE_V1"
            or receipt.get("cohort") != plan["cohort"]
            or receipt.get("stage") != stage
            or receipt.get("workflow_sha256") != plan["workflow_sha256"]
            or receipt.get("status") not in OUTCOMES):
        raise Denied("VAULT_STAGE_RECEIPT_INVALID:" + stage)
    if stage == "V1":
        roster = plan["inputs"].get("roster")
        if not roster:
            raise Denied("VAULT_ROSTER_PIN_REQUIRED")
        with _repo_file(root, roster["path"], roster["sha256"]).open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        source_ids = {row["source_instance_id"] for row in rows}
        dispositions = receipt.get("source_dispositions")
        if (len(rows) != 2000 or len(source_ids) != 2000
                or not isinstance(dispositions, dict)
                or set(dispositions) != source_ids
                or not set(dispositions.values()) <= {
                    "REUSE_APPROVED", "NEW_CONTRACT_REQUIRED", "UNSUPPORTED", "UNRESOLVED"
                }):
            raise Denied("VAULT_MODEL_FIT_COVERAGE_INCOMPLETE")
    if stage == "V2" and receipt["status"] == "PASS":
        if not receipt.get("approved_contract_pins"):
            raise Denied("VAULT_CONTRACT_PINS_REQUIRED")
        for pin in receipt["approved_contract_pins"]:
            _repo_file(root, pin["path"], pin["sha256"])
        v1 = _receipt(root, plan, "V1")
        novel = (v1 is not None and "NEW_CONTRACT_REQUIRED" in
                 v1["source_dispositions"].values())
        if novel or receipt.get("new_semantics"):
            from edp_lab.operating.authority import protected_trust_dir, verified_document

            decision_path = receipt.get("owner_signed_decision")
            if not decision_path:
                raise Denied("VAULT_OWNER_SEMANTIC_DECISION_REQUIRED")
            decision = verified_document(root, Path(decision_path), protected_trust_dir(root))
            if (decision.get("cohort") != plan["cohort"]
                    or decision.get("status") != "APPROVED"
                    or decision.get("contract_pins") != receipt["approved_contract_pins"]):
                raise Denied("VAULT_OWNER_SEMANTIC_DECISION_INVALID")
    if stage in PROTECTED:
        # A self-authored JSON status cannot establish a live write or freeze.
        from edp_lab.operating.authority import protected_trust_dir, verified_document

        envelope = receipt.get("signed_live_receipt")
        if not envelope:
            raise Denied("VAULT_SIGNED_LIVE_RECEIPT_REQUIRED:" + stage)
        proof = verified_document(root, Path(envelope), protected_trust_dir(root))
        if (proof.get("cohort") != plan["cohort"]
                or proof.get("status") not in {"VERIFIED", "PASS"}
                or proof.get("live_readback") is not True):
            raise Denied("VAULT_LIVE_READBACK_REQUIRED:" + stage)
    for item in receipt.get("evidence", []):
        _repo_file(root, item["path"], item["sha256"])
    return receipt


def advance(root: Path, plan_path: Path, state_dir: Path) -> dict:
    """Advance only over verified evidence; preserve unknown external outcomes."""
    root = root.resolve()
    plan = load_plan(root, plan_path)
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = state_dir / "vault-runner.lock"
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise Denied("VAULT_RUNNER_LOCKED") from exc
    state_path = state_dir / "checkpoint.json"
    log = state_dir / "events.jsonl"
    try:
        state = json.loads(state_path.read_bytes()) if state_path.exists() else {
            "schema": "EDP_VAULT_LIFECYCLE_STATE_V1",
            "plan_sha256": file_digest(plan_path), "completed": {},
            "pending_external": None, "recovery": [],
        }
        if state["plan_sha256"] != file_digest(plan_path):
            raise Denied("VAULT_PLAN_CHANGED_DURING_RESUME")
        if state.get("pending_agent"):
            state["status"] = "AGENT_OUTCOME_RECONCILIATION_REQUIRED"
            _write_json(state_path, state)
            return state
        if state["pending_external"]:
            state["status"] = "UNCERTAIN_EXTERNAL_RECONCILIATION_REQUIRED"
            _write_json(state_path, state)
            return state
        for stage in STAGES:
            receipt = _receipt(root, plan, stage)
            if stage in state["completed"]:
                if not receipt or file_digest(root / plan["stages"][stage]["receipt"]) != state["completed"][stage]:
                    raise Denied("VAULT_COMPLETED_EVIDENCE_CHANGED:" + stage)
                continue
            if receipt is None:
                state["next_stage"] = stage
                state["status"] = "EVIDENCE_REQUIRED"
                break
            if receipt["status"] == "BLOCKED":
                state["next_stage"] = stage
                state["status"] = ("HUMAN_DECISION_REQUIRED" if receipt.get("decision_required")
                                   else "TECHNICAL_RECOVERY_REQUIRED")
                previous = state["recovery"][-1] if state["recovery"] else None
                if previous is None or previous["stage"] != stage or previous["reason"] != receipt.get("reason"):
                    state["recovery"].append({"stage": stage, "reason": receipt.get("reason"),
                                              "at": datetime.now(UTC).isoformat()})
                    _event(log, "V7_INTERRUPT", stage=stage, reason=receipt.get("reason"))
                break
            if stage == "V5" and receipt["status"] == "NOT_REQUIRED":
                raise Denied("VAULT_LOSSLESS_CANNOT_BE_SKIPPED")
            if stage in {"V3", "V6"} and receipt["status"] == "NOT_REQUIRED" and not receipt.get("applicability_evidence"):
                raise Denied("VAULT_CONDITIONAL_STAGE_NEEDS_EVIDENCE:" + stage)
            state["completed"][stage] = file_digest(root / plan["stages"][stage]["receipt"])
            _event(log, "STAGE_VERIFIED", stage=stage, status=receipt["status"])
        else:
            state["next_stage"] = None
            state["status"] = "COMPLETE"
        _write_json(state_path, state)
        return state
    finally:
        lock.rmdir()


def reserve_external(state_dir: Path, *, stage: str, operation_id: str,
                     request_sha256: str) -> dict:
    """Durably reserve one protected operation before sending it to a service."""
    if stage not in PROTECTED:
        raise Denied("VAULT_EXTERNAL_STAGE_INVALID")
    path = state_dir / "checkpoint.json"
    state = json.loads(path.read_bytes())
    if state.get("pending_external") or state.get("next_stage") != stage:
        raise Denied("VAULT_EXTERNAL_OPERATION_NOT_READY")
    state["pending_external"] = {"stage": stage, "operation_id": operation_id,
                                 "request_sha256": request_sha256,
                                 "reserved_at": datetime.now(UTC).isoformat()}
    state["status"] = "EXTERNAL_OUTCOME_PENDING"
    _write_json(path, state)
    _event(state_dir / "events.jsonl", "EXTERNAL_RESERVED", stage=stage,
           operation_id=operation_id)
    return state


def reconcile_external(root: Path, plan_path: Path, state_dir: Path) -> dict:
    """Clear an uncertain operation only against its matching signed readback."""
    plan = load_plan(root, plan_path)
    state_path = state_dir / "checkpoint.json"
    state = json.loads(state_path.read_bytes())
    pending = state.get("pending_external")
    if not pending:
        raise Denied("VAULT_NO_EXTERNAL_OPERATION_PENDING")
    stage = pending["stage"]
    receipt = _receipt(root, plan, stage)
    if receipt is None or receipt["status"] not in {"PASS", "PARTIAL"}:
        raise Denied("VAULT_EXTERNAL_RECEIPT_NOT_READY")
    from edp_lab.operating.authority import protected_trust_dir, verified_document

    proof = verified_document(root, Path(receipt["signed_live_receipt"]),
                              protected_trust_dir(root))
    if (proof.get("operation_id") != pending["operation_id"]
            or proof.get("request_sha256") != pending["request_sha256"]):
        raise Denied("VAULT_EXTERNAL_RECEIPT_OPERATION_MISMATCH")
    state["pending_external"] = None
    _write_json(state_path, state)
    _event(state_dir / "events.jsonl", "EXTERNAL_RECONCILED", stage=stage,
           operation_id=pending["operation_id"])
    return advance(root, plan_path, state_dir)


def readiness(root: Path, plan_path: Path) -> dict:
    """Local no-write check; do not mistake the old prototype for full authority."""
    plan = load_plan(root, plan_path)
    blockers = []
    base = Path("/private/var/db/edp-lab-day6-vault")
    try:
        from edp_lab.operating.authority import verified_document

        policy = verified_document(root, base / "trust/policy.signed.json", base / "trust")
        if policy.get("c2000_full_integration_allowed") is not True:
            blockers.append("INSTALLED_POLICY_EXCLUDES_FULL_C2000")
        if policy.get("max_run_data_occurrences", 0) <= 1000:
            blockers.append("INSTALLED_POLICY_CAPS_RUN_AT_1000_OCCURRENCES")
        if policy.get("protected_full_executor_validated") is not True:
            blockers.append("FULL_SCOPE_PROTECTED_EXECUTION_NOT_DEMONSTRATED")
    except (OSError, Denied):
        blockers.append("INSTALLED_FULL_SCOPE_POLICY_NOT_VERIFIABLE")
    # Stage V1/V2 decisions are evidence, not claims in a writable plan.
    try:
        for stage in ("V1", "V2"):
            receipt = _receipt(root, plan, stage)
            if receipt is None or receipt["status"] != "PASS":
                blockers.append("FULL_SOURCE_MODEL_FIT_AND_CONTRACT_DECISIONS_PENDING")
                break
    except (OSError, Denied):
        blockers.append("FULL_SOURCE_MODEL_FIT_AND_CONTRACT_DECISIONS_PENDING")
    return {"status": "READY" if not blockers else "BLOCKED", "cohort": plan["cohort"],
            "workflow_sha256": plan["workflow_sha256"], "blockers": blockers,
            "existing_step2_reused": "step2" in plan["inputs"]}


def dispatch_v4(root: Path, plan_path: Path, state_dir: Path,
                run_request: str) -> dict:
    """Submit once through the existing protected V2 service after reservation.

    A lost response stays pending.  The operator/agent must reconcile the
    protected ledger and live Delta state before clearing that reservation.
    """
    load_plan(root, plan_path)
    state = advance(root, plan_path, state_dir)
    if state["status"] != "EVIDENCE_REQUIRED" or state["next_stage"] != "V4":
        raise Denied("VAULT_V4_NOT_READY")
    if readiness(root, plan_path)["status"] != "READY":
        raise Denied("VAULT_FULL_SCOPE_AUTHORITY_BLOCKED")
    request = Path(run_request)
    if request.is_absolute() or ".." in request.parts:
        raise Denied("VAULT_RUN_REQUEST_OUTSIDE_REPO")
    request_path = (root / request).resolve(strict=True)
    if not request_path.is_relative_to(root.resolve()):
        raise Denied("VAULT_RUN_REQUEST_OUTSIDE_REPO")
    request_hash = file_digest(request_path)
    reserve_external(state_dir, stage="V4", operation_id=request_hash,
                     request_sha256=request_hash)
    command = [sys.executable, str(root / "scripts/vault_0a_v2_client.py"),
               "execute", str(request)]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True,
                            timeout=3700, check=False)
    # The response is evidence for reconciliation, never a reason to replay.
    (state_dir / "v4-protected-response.json").write_text(json.dumps({
        "returncode": result.returncode, "stdout": result.stdout,
        "stderr": result.stderr[-2000:]}, sort_keys=True) + "\n")
    return {"status": "EXTERNAL_RECONCILIATION_REQUIRED",
            "returncode": result.returncode, "request_sha256": request_hash}


def dispatch_agent(root: Path, plan_path: Path, state_dir: Path,
                   *, runtime_seconds: int = 1800) -> dict:
    """Ask the agent to perform one evidence stage from the pinned workflow.

    The agent can produce candidate evidence and code.  It cannot sign its own
    decision or perform protected writes.  Its raw session is retained so a
    failure can be diagnosed before any deliberate resume.
    """
    if runtime_seconds < 1 or runtime_seconds > 3600:
        raise Denied("VAULT_AGENT_RUNTIME_OUT_OF_BOUNDS")
    if not state_dir.resolve().is_relative_to(root.resolve()):
        raise Denied("VAULT_AGENT_STATE_OUTSIDE_REPO")
    plan = load_plan(root, plan_path)
    state = advance(root, plan_path, state_dir)
    stage = state.get("next_stage")
    if (state["status"] not in {"EVIDENCE_REQUIRED", "TECHNICAL_RECOVERY_REQUIRED"}
            or stage in PROTECTED or stage is None):
        raise Denied("VAULT_AGENT_STAGE_NOT_READY")
    if state.get("pending_agent"):
        raise Denied("VAULT_AGENT_OUTCOME_UNCERTAIN")
    prompt = state_dir / (stage.lower() + ".prompt.txt")
    recovery = state["status"] == "TECHNICAL_RECOVERY_REQUIRED"
    prompt.write_text(
        ("Apply workflow V7 to diagnose the recorded failure and repair only already "
         "authorized bounded technical code/evidence, then revalidate the affected stage. "
         if recovery else "")
        + f"Execute only Vault stage {stage} for cohort {plan['cohort']} under the exact "
        f"pinned workflow {WORKFLOW} (SHA-256 {plan['workflow_sha256']}). "
        f"Read the workflow, {plan_path}, the frozen inputs and prior checkpoint. "
        "Choose the evidence/profiling/tests called for there. Reuse accepted evidence. "
        "Do not run C2000 Delta writes, issue grants, sign decisions, change protected "
        "policy, mutate RAW/frozen inputs, or invent business semantics. "
        "Use the existing receipt path from the plan only when evidence supports it; "
        "record unresolved items and human decisions explicitly. "
        "Do not run git commit, push or merge.\n"
    )
    state["pending_agent"] = {"stage": stage, "prompt_sha256": file_digest(prompt),
                              "started_at": datetime.now(UTC).isoformat()}
    _write_json(state_dir / "checkpoint.json", state)
    _event(state_dir / "events.jsonl", "AGENT_DISPATCHED", stage=stage)
    result = _codex_step(root, {"id": stage.lower(), "prompt_path": str(prompt),
                                "prompt_sha256": file_digest(prompt),
                                "runtime_seconds": runtime_seconds}, state_dir,
                         read_only=False)
    state = json.loads((state_dir / "checkpoint.json").read_bytes())
    state["pending_agent"] = None
    state["agent_sessions"] = {**state.get("agent_sessions", {}), stage: result}
    _write_json(state_dir / "checkpoint.json", state)
    _event(state_dir / "events.jsonl", "AGENT_RETURNED", stage=stage,
           returncode=result["returncode"], timed_out=result["timed_out"])
    if result["timed_out"] or result["returncode"]:
        state["status"] = "TECHNICAL_RECOVERY_REQUIRED"
        _write_json(state_dir / "checkpoint.json", state)
        return state
    return advance(root, plan_path, state_dir)


def run_until_boundary(root: Path, plan_path: Path, state_dir: Path,
                       *, runtime_seconds: int = 1800,
                       run_request: str | None = None) -> dict:
    """Drive consecutive evidence stages and stop at an actual authority boundary."""
    for _ in STAGES:
        state = advance(root, plan_path, state_dir)
        if state["status"] != "EVIDENCE_REQUIRED":
            return state
        if state["next_stage"] == "V4":
            if run_request is None:
                state["status"] = "PROTECTED_RUN_REQUEST_REQUIRED"
                return state
            return dispatch_v4(root, plan_path, state_dir, run_request)
        if state["next_stage"] == "V9":
            state["status"] = "PROTECTED_FREEZE_RECEIPT_REQUIRED"
            return state
        current_stage = state["next_stage"]
        state = dispatch_agent(root, plan_path, state_dir,
                               runtime_seconds=runtime_seconds)
        if (state["status"] == "EVIDENCE_REQUIRED"
                and state["next_stage"] == current_stage):
            state["status"] = "STAGE_EVIDENCE_PENDING"
            return state
        if state["status"] != "EVIDENCE_REQUIRED":
            return state
    raise Denied("VAULT_STAGE_LOOP_EXCEEDED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("readiness", "advance", "run",
                                           "dispatch-agent", "dispatch-v4", "reconcile"))
    parser.add_argument("plan", type=Path)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--run-request")
    parser.add_argument("--runtime-seconds", type=int, default=1800)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if args.action != "readiness" and args.state_dir is None:
        parser.error("--state-dir is required")
    if args.action == "dispatch-v4" and not args.run_request:
        parser.error("--run-request is required")
    if args.action == "readiness":
        result = readiness(root, args.plan)
    elif args.action == "dispatch-v4":
        result = dispatch_v4(root, args.plan, args.state_dir, args.run_request)
    elif args.action == "dispatch-agent":
        result = dispatch_agent(root, args.plan, args.state_dir,
                                runtime_seconds=args.runtime_seconds)
    elif args.action == "reconcile":
        result = reconcile_external(root, args.plan, args.state_dir)
    elif args.action == "run":
        result = run_until_boundary(root, args.plan, args.state_dir,
                                    runtime_seconds=args.runtime_seconds,
                                    run_request=args.run_request)
    else:
        result = advance(root, args.plan, args.state_dir)
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
