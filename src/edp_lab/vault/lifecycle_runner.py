"""Durable Vault lifecycle coordinator; the workflow and signed services own policy.

This module does not interpret business meaning or issue execution authority.  A
stage producer supplies evidence, and an independent verifier/owner supplies a
receipt where the workflow requires one.  External writes cross only the
installed Vault V2 service boundary.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import socket
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
        if (not rows or len(source_ids) != len(rows)
                or not isinstance(dispositions, dict)
                or set(dispositions) != source_ids
                or not set(dispositions.values()) <= {
                    "REUSE_APPROVED", "NEW_CONTRACT_REQUIRED", "UNSUPPORTED", "UNRESOLVED"
                }):
            raise Denied("VAULT_MODEL_FIT_COVERAGE_INCOMPLETE")
    if stage == "V2" and receipt["status"] in {"PASS", "PARTIAL"}:
        if not receipt.get("approved_contract_pins"):
            raise Denied("VAULT_CONTRACT_PINS_REQUIRED")
        for pin in receipt["approved_contract_pins"]:
            _repo_file(root, pin["path"], pin["sha256"])
        v1 = _receipt(root, plan, "V1")
        novel = (v1 is not None and "NEW_CONTRACT_REQUIRED" in
                 v1["source_dispositions"].values())
        if receipt["status"] == "PARTIAL":
            reused = {sid for sid, fit in v1["source_dispositions"].items()
                      if fit == "REUSE_APPROVED"}
            pending = set(v1["source_dispositions"]) - reused
            if (set(receipt.get("approved_sources", [])) != reused
                    or set(receipt.get("pending_sources", [])) != pending
                    or receipt.get("new_semantics") is not False):
                raise Denied("VAULT_PARTIAL_CONTRACT_SCOPE_INVALID")
        if (receipt["status"] == "PASS" and novel) or receipt.get("new_semantics"):
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

        if stage == "V4":
            runs = receipt.get("protected_runs")
            if not isinstance(runs, list) or not runs:
                raise Denied("VAULT_V4_RUN_RECEIPTS_REQUIRED")
            covered = set()
            for run in runs:
                request_path = _repo_file(root, run["request_path"], run["request_sha256"])
                request = json.loads(request_path.read_bytes())
                expected_run_sha = hashlib.sha256(json.dumps(
                    request, sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False).encode()).hexdigest()
                proof = verified_document(root, Path(run["signed_live_receipt"]),
                                          protected_trust_dir(root))
                checks = proof.get("checks")
                if (proof.get("schema") != "EDP_VAULT_RUN_READBACK_RECEIPT_V2"
                        or proof.get("authority") != "protected-verifier-v1"
                        or proof.get("cohort_id") != plan["cohort"]
                        or proof.get("status") != "VERIFIED"
                        or proof.get("namespace") != plan["namespace"]
                        or not isinstance(checks, dict)
                        or set(checks) != set(plan["tables"])
                        or any(not item.get("uc_table_id") or not item.get("statement_id")
                               or not isinstance(item.get("rows"), int)
                               for item in checks.values())
                        or run.get("run_sha256") != proof.get("run_sha256")
                        or expected_run_sha != proof.get("run_sha256")
                        or request.get("cohort_id") != plan["cohort"]
                        or not isinstance(request.get("sources"), dict)
                        or file_digest(Path(run["signed_live_receipt"])) != run.get("receipt_sha256")):
                    raise Denied("VAULT_V4_SIGNED_READBACK_INVALID")
                covered.update(request["sources"])
            if set(receipt.get("selected_sources", [])) != covered:
                raise Denied("VAULT_V4_SOURCE_COVERAGE_MISMATCH")
            if receipt["status"] == "PASS":
                roster = plan["inputs"]["roster"]
                with _repo_file(root, roster["path"], roster["sha256"]).open(newline="") as stream:
                    all_sources = {row["source_instance_id"] for row in csv.DictReader(stream)}
                v2 = _receipt(root, plan, "V2")
                if covered != all_sources or v2 is None or v2["status"] != "PASS":
                    raise Denied("VAULT_FULL_POPULATION_PASS_UNSUPPORTED")
        else:
            envelope = receipt.get("signed_live_receipt")
            if not envelope:
                raise Denied("VAULT_SIGNED_LIVE_RECEIPT_REQUIRED:" + stage)
            proof = verified_document(root, Path(envelope), protected_trust_dir(root))
            if (proof.get("schema") != "EDP_VAULT_LIVE_FREEZE_RECEIPT_V1"
              or proof.get("authority") != "protected-verifier-v1"
              or proof.get("cohort") != plan["cohort"]
              or proof.get("status") != "VERIFIED"
              or proof.get("live_readback") is not True
              or not proof.get("delta_ids") or not proof.get("delta_versions")
              or not proof.get("source_coverage")):
                raise Denied("VAULT_V9_LIVE_FREEZE_INVALID")
            if receipt["status"] == "PASS":
                for prerequisite in ("V2", "V4", "V5", "V8"):
                    prior = _receipt(root, plan, prerequisite)
                    if prior is None or prior["status"] != "PASS":
                        raise Denied("VAULT_V9_FULL_PASS_PREREQUISITE_MISSING")
            _verify_git_exit(receipt)
    for item in receipt.get("evidence", []):
        _repo_file(root, item["path"], item["sha256"])
    return receipt


def _verify_git_exit(receipt: dict) -> None:
    """Verify the actual remote PR merge after any required human review."""
    git_exit = receipt.get("git_exit")
    if (not isinstance(git_exit, dict) or type(git_exit.get("pr")) is not int
            or not isinstance(git_exit.get("merge_sha"), str)
            or not isinstance(git_exit.get("head_sha"), str)):
        raise Denied("VAULT_GIT_EXIT_EVIDENCE_REQUIRED")
    response = subprocess.run(
        ["gh", "pr", "view", str(git_exit["pr"]), "--json",
         "state,mergedAt,mergeCommit,headRefOid,baseRefName"],
        capture_output=True, text=True, timeout=30, check=False)
    if response.returncode:
        raise Denied("VAULT_GIT_EXIT_REMOTE_READBACK_FAILED")
    live = json.loads(response.stdout)
    if (live.get("state") != "MERGED" or not live.get("mergedAt")
            or live.get("mergeCommit", {}).get("oid") != git_exit["merge_sha"]
            or live.get("headRefOid") != git_exit["head_sha"]
            or live.get("baseRefName") != "main"):
        raise Denied("VAULT_GIT_EXIT_REMOTE_MISMATCH")


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
                for incident in state["recovery"]:
                    if incident["stage"] == stage and "resolved_at" not in incident:
                        incident["resolved_at"] = datetime.now(UTC).isoformat()
                        incident["resolution"] = "SUPERSEDED_BY_VERIFIED_STAGE_EVIDENCE"
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
            if stage in {"V0A", "V0"} and receipt["status"] != "PASS":
                state["next_stage"] = stage
                state["status"] = "HUMAN_DECISION_REQUIRED"
                break
            if stage == "V5" and receipt["status"] == "NOT_REQUIRED":
                raise Denied("VAULT_LOSSLESS_CANNOT_BE_SKIPPED")
            if stage == "V9":
                frozen = state.get("v9_freeze")
                if (not frozen or receipt.get("signed_live_receipt") != frozen["receipt_path"]
                        or file_digest(Path(frozen["receipt_path"])) != frozen["receipt_sha256"]):
                    raise Denied("VAULT_V9_FREEZE_CHECKPOINT_MISMATCH")
            if stage in {"V3", "V6"} and receipt["status"] == "NOT_REQUIRED" and not receipt.get("applicability_evidence"):
                raise Denied("VAULT_CONDITIONAL_STAGE_NEEDS_EVIDENCE:" + stage)
            state["completed"][stage] = file_digest(root / plan["stages"][stage]["receipt"])
            for incident in state["recovery"]:
                if incident["stage"] == stage and "resolved_at" not in incident:
                    incident["resolved_at"] = datetime.now(UTC).isoformat()
                    incident["resolution"] = "SUPERSEDED_BY_VERIFIED_STAGE_EVIDENCE"
            _event(log, "STAGE_VERIFIED", stage=stage, status=receipt["status"])
        else:
            state["next_stage"] = None
            state["status"] = "COMPLETE"
        _write_json(state_path, state)
        return state
    finally:
        lock.rmdir()


def reserve_external(state_dir: Path, *, stage: str, operation_id: str,
                     request_sha256: str, request_path: str | None = None) -> dict:
    """Durably reserve one protected operation before sending it to a service."""
    if stage not in PROTECTED:
        raise Denied("VAULT_EXTERNAL_STAGE_INVALID")
    path = state_dir / "checkpoint.json"
    state = json.loads(path.read_bytes())
    if state.get("pending_external") or state.get("next_stage") != stage:
        raise Denied("VAULT_EXTERNAL_OPERATION_NOT_READY")
    state["pending_external"] = {"stage": stage, "operation_id": operation_id,
                                 "request_sha256": request_sha256,
                                 "request_path": request_path,
                                 "reserved_at": datetime.now(UTC).isoformat()}
    state["status"] = "EXTERNAL_OUTCOME_PENDING"
    _write_json(path, state)
    _event(state_dir / "events.jsonl", "EXTERNAL_RESERVED", stage=stage,
           operation_id=operation_id)
    return state


def _finish_v4_batch(root: Path, plan: dict, state_dir: Path, signed: Path) -> dict:
    """Record one exact protected readback and release only its reservation."""
    from edp_lab.operating.authority import protected_trust_dir, verified_document

    state_path = state_dir / "checkpoint.json"
    state = json.loads(state_path.read_bytes())
    pending = state.get("pending_external")
    if not pending or pending["stage"] != "V4" or not pending.get("request_path"):
        raise Denied("VAULT_NO_V4_BATCH_PENDING")
    request_path = _repo_file(root, pending["request_path"], pending["request_sha256"])
    request = json.loads(request_path.read_bytes())
    run_sha = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False).encode()).hexdigest()
    proof = verified_document(root, signed, protected_trust_dir(root))
    if (run_sha != pending["operation_id"] or proof.get("run_sha256") != run_sha
            or proof.get("schema") != "EDP_VAULT_RUN_READBACK_RECEIPT_V2"
            or proof.get("authority") != "protected-verifier-v1"
            or proof.get("cohort_id") != plan["cohort"]
            or proof.get("namespace") != plan["namespace"]
            or proof.get("status") != "VERIFIED"
            or set(proof.get("checks", {})) != set(plan["tables"])
            or any(not check.get("uc_table_id") or not check.get("statement_id")
                   or not isinstance(check.get("rows"), int)
                   for check in proof["checks"].values())):
        raise Denied("VAULT_V4_BATCH_READBACK_MISMATCH")
    entry = {"request_path": pending["request_path"],
             "request_sha256": pending["request_sha256"],
             "run_sha256": run_sha, "signed_live_receipt": str(signed),
             "receipt_sha256": file_digest(signed)}
    state.setdefault("v4_batches", {})[run_sha] = entry
    state["pending_external"] = None
    _write_json(state_path, state)
    _event(state_dir / "events.jsonl", "EXTERNAL_RECONCILED", stage="V4",
           operation_id=run_sha)
    return state


def reconcile_external(root: Path, plan_path: Path, state_dir: Path,
                       signed_receipt: Path | None = None) -> dict:
    """Reconcile an uncertain write from signed readback; never replay it."""
    plan = load_plan(root, plan_path)
    state_path = state_dir / "checkpoint.json"
    state = json.loads(state_path.read_bytes())
    pending = state.get("pending_external")
    if not pending:
        raise Denied("VAULT_NO_EXTERNAL_OPERATION_PENDING")
    if signed_receipt is None:
        raise Denied("VAULT_EXTERNAL_RECEIPT_NOT_READY")
    if pending["stage"] == "V4":
        return _finish_v4_batch(root, plan, state_dir, signed_receipt)
    if pending["stage"] == "V9":
        return _finish_v9_freeze(root, plan, state_dir, signed_receipt)
    raise Denied("VAULT_EXTERNAL_STAGE_INVALID")


def _finish_v9_freeze(root: Path, plan: dict, state_dir: Path, signed: Path) -> dict:
    from edp_lab.operating.authority import protected_trust_dir, verified_document

    state_path = state_dir / "checkpoint.json"
    state = json.loads(state_path.read_bytes())
    pending = state.get("pending_external")
    if not pending or pending["stage"] != "V9":
        raise Denied("VAULT_NO_V9_FREEZE_PENDING")
    if not pending.get("request_path"):
        raise Denied("VAULT_V9_FREEZE_REQUEST_PIN_MISSING")
    _repo_file(root, pending["request_path"], pending["request_sha256"])
    proof = verified_document(root, signed, protected_trust_dir(root))
    if (proof.get("schema") != "EDP_VAULT_LIVE_FREEZE_RECEIPT_V1"
            or proof.get("authority") != "protected-verifier-v1"
            or proof.get("status") != "VERIFIED"
            or proof.get("cohort") != plan["cohort"]
            or proof.get("request_sha256") != pending["request_sha256"]
            or proof.get("live_readback") is not True
            or not proof.get("delta_ids") or not proof.get("delta_versions")
            or not proof.get("source_coverage")):
        raise Denied("VAULT_V9_FREEZE_READBACK_MISMATCH")
    state["v9_freeze"] = {"receipt_path": str(signed),
                          "receipt_sha256": file_digest(signed),
                          "request_sha256": pending["request_sha256"]}
    state["pending_external"] = None
    _write_json(state_path, state)
    _event(state_dir / "events.jsonl", "EXTERNAL_RECONCILED", stage="V9",
           operation_id=pending["operation_id"])
    state["status"] = "EVIDENCE_REQUIRED"
    return state


def dispatch_v9_freeze(root: Path, plan_path: Path, state_dir: Path,
                       freeze_request: str) -> dict:
    """Use the installed protected executor socket for a versioned freeze action."""
    plan = load_plan(root, plan_path)
    state = advance(root, plan_path, state_dir)
    if state["status"] != "EVIDENCE_REQUIRED" or state["next_stage"] != "V9":
        raise Denied("VAULT_V9_NOT_READY")
    path = Path(freeze_request)
    if path.is_absolute() or ".." in path.parts:
        raise Denied("VAULT_FREEZE_REQUEST_OUTSIDE_REPO")
    resolved = (root / path).resolve(strict=True)
    if not resolved.is_relative_to(root.resolve()):
        raise Denied("VAULT_FREEZE_REQUEST_OUTSIDE_REPO")
    request = json.loads(resolved.read_bytes())
    if (request.get("schema") != "EDP_VAULT_FREEZE_REQUEST_V1"
            or request.get("cohort") != plan["cohort"]
            or request.get("namespace") != plan["namespace"]):
        raise Denied("VAULT_FREEZE_REQUEST_INVALID")
    request_sha = file_digest(resolved)
    reserve_external(state_dir, stage="V9", operation_id=request_sha,
                     request_sha256=request_sha, request_path=str(path))
    try:
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(3700)
            client.connect("/private/var/db/edp-lab-day6-vault/executor.sock")
            client.sendall((json.dumps({"action": "freeze", "request_path": str(path)},
                                       sort_keys=True) + "\n").encode())
            client.shutdown(socket.SHUT_WR)
            response = json.loads(client.recv(8192))
        if response.get("status") != "VAULT_LIVE_FREEZE_VERIFIED":
            raise Denied("VAULT_PROTECTED_FREEZE_NOT_VERIFIED")
        return _finish_v9_freeze(root, plan, state_dir, Path(response["receipt_path"]))
    except (OSError, ValueError, KeyError, Denied) as exc:
        _event(state_dir / "events.jsonl", "EXTERNAL_RECONCILIATION_REQUIRED",
               stage="V9", reason=str(exc))
        return {"status": "EXTERNAL_RECONCILIATION_REQUIRED", "stage": "V9",
                "request_sha256": request_sha}


def reconcile_agent(root: Path, plan_path: Path, state_dir: Path) -> dict:
    """Recover a lost agent response only from a retained terminal session event."""
    load_plan(root, plan_path)
    state_path = state_dir / "checkpoint.json"
    state = json.loads(state_path.read_bytes())
    pending = state.get("pending_agent")
    if not pending:
        raise Denied("VAULT_NO_AGENT_PENDING")
    stage = pending["stage"]
    prompt = state_dir / (stage.lower() + ".prompt.txt")
    if file_digest(prompt) != pending["prompt_sha256"]:
        raise Denied("VAULT_AGENT_PROMPT_CHANGED")
    events = state_dir / (stage.lower() + ".codex.jsonl")
    if not events.is_file():
        raise Denied("VAULT_AGENT_TERMINAL_EVENT_MISSING")
    kinds = []
    for line in events.read_text().splitlines():
        try:
            kinds.append(json.loads(line).get("type"))
        except ValueError:
            raise Denied("VAULT_AGENT_EVENT_CORRUPT") from None
    if "turn.completed" not in kinds and "turn.failed" not in kinds:
        raise Denied("VAULT_AGENT_TERMINAL_EVENT_MISSING")
    state["pending_agent"] = None
    state["status"] = ("EVIDENCE_REQUIRED" if "turn.completed" in kinds
                       else "TECHNICAL_RECOVERY_REQUIRED")
    _write_json(state_path, state)
    _event(state_dir / "events.jsonl", "AGENT_RECONCILED", stage=stage,
           status=state["status"])
    return advance(root, plan_path, state_dir) if "turn.completed" in kinds else state


def readiness(root: Path, plan_path: Path) -> dict:
    """Separate pilot startup from later protected full-write authority."""
    plan = load_plan(root, plan_path)
    startup_blockers = []
    authority_blockers = []
    closeout_blockers = []
    max_run_occurrences = None
    base = Path("/private/var/db/edp-lab-day6-vault")
    try:
        from edp_lab.operating.authority import verified_document

        policy = verified_document(root, base / "trust/policy.signed.json", base / "trust")
        if policy.get("c2000_full_integration_allowed") is not True:
            authority_blockers.append("INSTALLED_POLICY_EXCLUDES_FULL_C2000")
        max_run_occurrences = policy.get("max_run_data_occurrences")
        if policy.get("protected_full_executor_validated") is not True:
            authority_blockers.append("FULL_SCOPE_PROTECTED_EXECUTION_NOT_DEMONSTRATED")
        if policy.get("vault_live_freeze_action_v1") is not True:
            closeout_blockers.append("PROTECTED_V9_FREEZE_ACTION_NOT_INSTALLED")
    except (OSError, Denied):
        startup_blockers.append("INSTALLED_POLICY_NOT_VERIFIABLE")
        authority_blockers.append("INSTALLED_FULL_SCOPE_POLICY_NOT_VERIFIABLE")
        closeout_blockers.append("PROTECTED_V9_FREEZE_ACTION_NOT_VERIFIABLE")
    return {"startup_status": "READY" if not startup_blockers else "BLOCKED",
            "startup_blockers": startup_blockers,
            "protected_full_write_status": "READY" if not authority_blockers else "BLOCKED",
            "authority_blockers": authority_blockers, "cohort": plan["cohort"],
            "closeout_blockers": closeout_blockers,
            "max_run_data_occurrences": max_run_occurrences,
            "workflow_sha256": plan["workflow_sha256"],
            "existing_step2_reused": "step2" in plan["inputs"]}


def dispatch_v4(root: Path, plan_path: Path, state_dir: Path,
                run_request: str) -> dict:
    """Drive pinned protected batches, resuming only after signed readback."""
    plan = load_plan(root, plan_path)
    state = advance(root, plan_path, state_dir)
    if state["status"] != "EVIDENCE_REQUIRED" or state["next_stage"] != "V4":
        raise Denied("VAULT_V4_NOT_READY")
    if readiness(root, plan_path)["protected_full_write_status"] != "READY":
        raise Denied("VAULT_FULL_SCOPE_AUTHORITY_BLOCKED")
    manifest_path = Path(run_request)
    if manifest_path.is_absolute() or ".." in manifest_path.parts:
        raise Denied("VAULT_RUN_REQUEST_OUTSIDE_REPO")
    manifest_file = (root / manifest_path).resolve(strict=True)
    if not manifest_file.is_relative_to(root.resolve()):
        raise Denied("VAULT_RUN_REQUEST_OUTSIDE_REPO")
    manifest = json.loads(manifest_file.read_bytes())
    if (manifest.get("schema") != "EDP_VAULT_EXECUTION_MANIFEST_V1"
            or manifest.get("cohort") != plan["cohort"]
            or not isinstance(manifest.get("runs"), list)
            or not manifest["runs"]):
        raise Denied("VAULT_BATCH_MANIFEST_INVALID")
    manifest_hash = file_digest(manifest_file)
    state_path = state_dir / "checkpoint.json"
    state = json.loads(state_path.read_bytes())
    if state.get("v4_manifest_sha256") not in {None, manifest_hash}:
        raise Denied("VAULT_BATCH_MANIFEST_CHANGED_DURING_RESUME")
    if state.get("v4_manifest_sha256") is None:
        state["v4_manifest_sha256"] = manifest_hash
        _write_json(state_path, state)
    from edp_lab.vault.pilot_evidence import save_once

    covered = set()
    expected_hashes = []
    for item in manifest["runs"]:
        request_file = _repo_file(root, item["path"], item["sha256"])
        run = json.loads(request_file.read_bytes())
        if (run.get("cohort_id") != plan["cohort"]
                or not isinstance(run.get("sources"), dict)
                or covered.intersection(run["sources"])):
            raise Denied("VAULT_BATCH_SOURCE_SCOPE_INVALID")
        covered.update(run["sources"])
        run_hash = hashlib.sha256(json.dumps(run, sort_keys=True, separators=(",", ":"),
                                             ensure_ascii=False).encode()).hexdigest()
        expected_hashes.append(run_hash)
        state = json.loads((state_dir / "checkpoint.json").read_bytes())
        if run_hash in state.get("v4_batches", {}):
            entry = state["v4_batches"][run_hash]
            if entry["request_sha256"] != item["sha256"]:
                raise Denied("VAULT_COMPLETED_BATCH_CHANGED")
            # Recheck signed readback before skipping a completed batch.
            from edp_lab.operating.authority import protected_trust_dir, verified_document

            proof = verified_document(root, Path(entry["signed_live_receipt"]),
                                      protected_trust_dir(root))
            if proof.get("run_sha256") != run_hash:
                raise Denied("VAULT_COMPLETED_BATCH_READBACK_CHANGED")
            continue
        reserve_external(state_dir, stage="V4", operation_id=run_hash,
                         request_sha256=item["sha256"], request_path=item["path"])
        result = subprocess.run(
            [sys.executable, str(root / "scripts/vault_0a_v2_client.py"),
             "execute", item["path"]], cwd=root, capture_output=True, text=True,
            timeout=3700, check=False)
        response_path = state_dir / ("v4-" + run_hash + "-response.json")
        save_once(response_path, {"returncode": result.returncode,
                                  "stdout": result.stdout, "stderr": result.stderr[-2000:]})
        if result.returncode:
            return {"status": "EXTERNAL_RECONCILIATION_REQUIRED",
                    "run_sha256": run_hash, "returncode": result.returncode}
        try:
            response = json.loads(result.stdout)
            signed = Path(response["receipt_path"])
            if (response.get("status") != "VAULT_RUN_READBACK_VERIFIED"
                    or file_digest(signed) != response["receipt_sha256"]):
                raise Denied("VAULT_PROTECTED_RESPONSE_INVALID")
            _finish_v4_batch(root, plan, state_dir, signed)
        except (KeyError, OSError, ValueError, Denied):
            return {"status": "EXTERNAL_RECONCILIATION_REQUIRED",
                    "run_sha256": run_hash, "returncode": result.returncode}
    if set(manifest.get("selected_sources", [])) != covered:
        raise Denied("VAULT_BATCH_MANIFEST_COVERAGE_MISMATCH")
    state = json.loads((state_dir / "checkpoint.json").read_bytes())
    if set(state.get("v4_batches", {})) != set(expected_hashes):
        raise Denied("VAULT_BATCH_READBACK_INCOMPLETE")
    save_once(root / plan["stages"]["V4"]["receipt"], {
        "schema": "EDP_VAULT_LIFECYCLE_STAGE_V1", "cohort": plan["cohort"],
        "stage": "V4", "workflow_sha256": plan["workflow_sha256"],
        "status": "PARTIAL", "selected_sources": sorted(covered),
        "protected_runs": [state["v4_batches"][key] for key in expected_hashes],
        "evidence": [{"path": str(manifest_path), "sha256": manifest_hash}],
    })
    return advance(root, plan_path, state_dir)


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
            or stage == "V4" or stage is None):
        raise Denied("VAULT_AGENT_STAGE_NOT_READY")
    if state.get("pending_agent"):
        raise Denied("VAULT_AGENT_OUTCOME_UNCERTAIN")
    if stage == "V9" and not state.get("v9_freeze"):
        raise Denied("VAULT_V9_PROTECTED_FREEZE_REQUIRED")
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
        "For V9, prepare live-freeze and Git exit evidence under the workflow; "
        "do not claim a protected freeze or merge without independent proof. "
        "Use the existing receipt path from the plan only when evidence supports it; "
        "record unresolved items and human decisions explicitly. "
        + (f"Verified protected live-freeze receipt: {state['v9_freeze']['receipt_path']} "
           f"(SHA-256 {state['v9_freeze']['receipt_sha256']}). "
           "Commit, push and create the PR only after checking this exact receipt; "
           "stop before merge when review approval is required.\n"
           if stage == "V9" else "Do not run git commit, push or merge.\n")
    )
    state["pending_agent"] = {"stage": stage, "prompt_sha256": file_digest(prompt),
                              "started_at": datetime.now(UTC).isoformat()}
    _write_json(state_dir / "checkpoint.json", state)
    _event(state_dir / "events.jsonl", "AGENT_DISPATCHED", stage=stage)
    result = _codex_step(root, {"id": stage.lower(), "prompt_path": str(prompt),
                                "prompt_sha256": file_digest(prompt),
                                "runtime_seconds": runtime_seconds}, state_dir,
                         read_only=False, allow_git=stage == "V9")
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


def _mechanical_stage(root: Path, plan_path: Path, state_dir: Path,
                      stage: str) -> dict:
    """Reuse immutable evidence and classify the frozen roster without semantics."""
    from edp_lab.vault.pilot_evidence import (
        classify_frozen_inventory,
        save_once,
        verify_reused_v0,
        verify_reused_v0a,
    )

    plan = load_plan(root, plan_path)
    receipt_path = root / plan["stages"][stage]["receipt"]
    common = {"schema": "EDP_VAULT_LIFECYCLE_STAGE_V1", "cohort": plan["cohort"],
              "stage": stage, "workflow_sha256": plan["workflow_sha256"]}
    if stage == "V0A":
        result = verify_reused_v0a(root, plan)
        evidence_names = ["vault_0a_acceptance"]
    elif stage == "V0":
        result = verify_reused_v0(root, plan)
        evidence_names = ["step0_evaluation", "cohort_freeze", "upstream_result",
                          "frozen_bindings", "approved_contract", "contract_approval",
                          "step2"]
    elif stage == "V1":
        inventory = classify_frozen_inventory(root, plan)
        inventory_path = state_dir.parent / "model-fit-2000.json"
        save_once(inventory_path, inventory)
        result = {"status": "PASS", "source_dispositions": {
            sid: item["model_fit"] for sid, item in inventory["sources"].items()},
            "family_counts": inventory["family_counts"],
            "model_fit_counts": inventory["model_fit_counts"],
            "inventory_sha256": file_digest(inventory_path)}
        evidence_names = ["roster", "frozen_bindings"]
        result["evidence"] = [{"path": str(inventory_path.relative_to(root)),
                               "sha256": file_digest(inventory_path)}]
    elif stage == "V2":
        v1 = _receipt(root, plan, "V1")
        if v1 is None:
            raise Denied("VAULT_V1_REQUIRED_BEFORE_V2")
        approved = sorted(sid for sid, fit in v1["source_dispositions"].items()
                          if fit == "REUSE_APPROVED")
        pending = sorted(sid for sid in v1["source_dispositions"] if sid not in approved)
        result = {"status": "PARTIAL", "decision_required": True,
                  "reason": "NEW_SOURCE_FAMILY_VAULT_CONTRACTS_PENDING",
                  "approved_contract_pins": [plan["inputs"]["approved_contract"]],
                  "approved_sources": approved, "pending_sources": pending,
                  "new_semantics": False,
                  "reused_contract": "VAULT_LOAD_CONTRACT_V1",
                  "new_contract_family_counts": {
                      family: count for family, count in v1["family_counts"].items()
                      if family != "SEC_FSDS"},
                  "approval_packet": "reports/day6_c2000_vault_pilot_owner_review_v1.md"}
        evidence_names = ["approved_contract", "contract_approval", "frozen_bindings"]
        for relative in ("reports/day6_c2000_vault_pilot_owner_review_v1.md",
                         "runs/day6-vault-pilot/family-probe-v1.json"):
            path = (root / relative).resolve(strict=True)
            if not path.is_relative_to(root):
                raise Denied("VAULT_V2_EVIDENCE_OUTSIDE_REPO")
            result.setdefault("evidence", []).append(
                {"path": relative, "sha256": file_digest(path)})
    elif stage == "V3":
        headers_path = root / "runs/day6-vault-pilot/fsds-num-headers-v1.json"
        headers = json.loads(headers_path.read_bytes())
        expected = "adsh\ttag\tversion\tddate\tqtrs\tuom\tsegments\tcoreg\tvalue\tfootnote"
        if (headers.get("bindings_sha256") != plan["inputs"]["frozen_bindings"]["sha256"]
                or headers.get("source_count") != 60
                or headers.get("header_patterns") != {expected: 60}):
            raise Denied("VAULT_FSDS_SHAPE_PROBE_MISMATCH")
        result = {"status": "PARTIAL", "decision_required": True,
                  "fsds_prototype_reused": sorted(
                      ("SRC000005", "SRC000054", "SRC000064")),
                  "fsds_shape_check": "60_OF_60_RAW_HASH_VERIFIED_IDENTICAL_NUM_HEADER",
                  "new_contract_prototype": "PENDING_SEMANTIC_DECISIONS",
                  "applicability_evidence": "Existing accepted 127-occurrence Delta prototype matches the approved FSDS Contract V1 and all 60 verified physical NUM headers.",
                  "evidence": [{"path": "runs/day6-vault-pilot/fsds-num-headers-v1.json",
                                "sha256": file_digest(headers_path)},
                               {"path": "reports/day6_c2000_vault_pilot_v3_shape_addendum_v1.md",
                                "sha256": file_digest(root / "reports/day6_c2000_vault_pilot_v3_shape_addendum_v1.md")}]}
        evidence_names = ["step2", "approved_contract", "frozen_bindings"]
    else:
        raise Denied("VAULT_MECHANICAL_STAGE_INVALID")
    result.setdefault("evidence", [])
    result["evidence"].extend(plan["inputs"][name] for name in evidence_names)
    save_once(receipt_path, {**common, **result})
    return advance(root, plan_path, state_dir)


def run_until_boundary(root: Path, plan_path: Path, state_dir: Path,
                       *, runtime_seconds: int = 1800,
                       run_request: str | None = None,
                       freeze_request: str | None = None) -> dict:
    """Drive consecutive evidence stages and stop at an actual authority boundary."""
    root = root.resolve()
    state_dir = (root / state_dir).resolve() if not state_dir.is_absolute() else state_dir.resolve()
    for _ in STAGES:
        state = advance(root, plan_path, state_dir)
        if (state["status"] == "TECHNICAL_RECOVERY_REQUIRED"
                and state.get("next_stage") not in PROTECTED):
            prior_stage = state["next_stage"]
            recovered = dispatch_agent(root, plan_path, state_dir,
                                       runtime_seconds=runtime_seconds)
            if (recovered["status"] == "EVIDENCE_REQUIRED"
                    and recovered.get("next_stage") != prior_stage):
                continue
            return recovered
        if state["status"] != "EVIDENCE_REQUIRED":
            return state
        if state["next_stage"] == "V4":
            authority = readiness(root, plan_path)
            if authority["protected_full_write_status"] != "READY":
                state["status"] = "HUMAN_AUTHORIZATION_REQUIRED"
                state["authority_blockers"] = authority["authority_blockers"]
                state["approval_packet"] = "reports/day6_c2000_vault_pilot_owner_review_v1.md"
                return state
            if run_request is None:
                state["status"] = "PROTECTED_RUN_REQUEST_REQUIRED"
                return state
            state = dispatch_v4(root, plan_path, state_dir, run_request)
            if state.get("status") == "EVIDENCE_REQUIRED":
                continue
            return state
        if state["next_stage"] == "V9":
            if not state.get("v9_freeze"):
                if freeze_request is None:
                    state["status"] = "PROTECTED_FREEZE_REQUEST_REQUIRED"
                    return state
                state = dispatch_v9_freeze(root, plan_path, state_dir, freeze_request)
                if state.get("status") == "EVIDENCE_REQUIRED":
                    continue
                return state
            if state.get("agent_sessions", {}).get("V9"):
                state["status"] = "GIT_REVIEW_OR_SIGNED_EXIT_PENDING"
                return state
        current_stage = state["next_stage"]
        if current_stage in {"V0A", "V0", "V1", "V2", "V3"}:
            state = _mechanical_stage(root, plan_path, state_dir, current_stage)
        else:
            state = dispatch_agent(root, plan_path, state_dir,
                                   runtime_seconds=runtime_seconds)
        if (state["status"] == "EVIDENCE_REQUIRED"
                and state["next_stage"] == current_stage):
            state["status"] = ("GIT_REVIEW_OR_SIGNED_EXIT_PENDING"
                               if current_stage == "V9" else "STAGE_EVIDENCE_PENDING")
            return state
        if state["status"] != "EVIDENCE_REQUIRED":
            return state
    raise Denied("VAULT_STAGE_LOOP_EXCEEDED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("readiness", "advance", "run",
                                           "dispatch-agent", "dispatch-v4", "reconcile",
                                           "reconcile-agent"))
    parser.add_argument("plan", type=Path)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--run-request")
    parser.add_argument("--freeze-request")
    parser.add_argument("--signed-receipt", type=Path)
    parser.add_argument("--runtime-seconds", type=int, default=1800)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if args.state_dir is not None and not args.state_dir.is_absolute():
        args.state_dir = root / args.state_dir
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
        result = reconcile_external(root, args.plan, args.state_dir,
                                    args.signed_receipt)
    elif args.action == "reconcile-agent":
        result = reconcile_agent(root, args.plan, args.state_dir)
    elif args.action == "run":
        result = run_until_boundary(root, args.plan, args.state_dir,
                                    runtime_seconds=args.runtime_seconds,
                                    run_request=args.run_request,
                                    freeze_request=args.freeze_request)
    else:
        result = advance(root, args.plan, args.state_dir)
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
