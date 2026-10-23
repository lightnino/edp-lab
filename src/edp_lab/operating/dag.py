"""Compile a pinned Cohort/Model stage DAG for PR #51's signed queue runner.

A stage receipt is a *gate*, not an implementation of Databricks processing.
Any unimplemented live adapter must supply separately verified external evidence.
"""

import argparse
import json
from pathlib import Path

from edp_lab.operating.authority import Denied, canonical, file_digest
from edp_lab.operating.runner import _ordered, applicable_controls

STAGES = tuple(f"P{i}" for i in range(11)) + ("P12",)
ROUTES = {"INITIAL_MODEL", "CORPUS_ONLY", "ADDITIVE", "CORRECTIVE"}
LOCAL_TASK_STAGES = {"P2", "P4", "P7"}
FAMILY_TAGS = {"FSDS": {"FSDS", "FIN"}, "TREASURY": {"TREASURY"}}


def compile_dag(root: Path, plan: dict) -> dict:
    """Produce a deterministic EDP_QUEUE_V1, ready for owner review/signing.

    Every stage has an independent receipt gate and explicit predecessor.
    Untrusted plan content cannot grant approvals or make a live write.
    """
    if plan.get("schema") != "EDP_COHORT_DAG_PLAN_V1":
        raise Denied("INVALID_DAG_SCHEMA")
    if plan.get("route") not in ROUTES:
        raise Denied("MODEL_ROUTE_NOT_APPROVED")
    if not isinstance(plan.get("cohort"), str) or not plan["cohort"]:
        raise Denied("INVALID_COHORT")
    if not isinstance(plan.get("output"), str) or not plan["output"]:
        raise Denied("INVALID_OUTPUT")
    stage_receipts = plan.get("stage_receipts")
    if not isinstance(stage_receipts, dict) or set(stage_receipts) != set(STAGES):
        raise Denied("MISSING_STAGE_RECEIPTS")
    for path in stage_receipts.values():
        if not isinstance(path, str) or not path:
            raise Denied("INVALID_STAGE_RECEIPT_PATH")
    contracts = plan.get("contracts", {})
    if not {"parser", "model", "rule", "registry", "budget_policy"} <= set(contracts):
        raise Denied("MISSING_DAG_CONTRACTS")
    root = root.resolve()
    for name, pin in contracts.items():
        rel = pin.get("path")
        if not isinstance(rel, str) or not isinstance(pin.get("version"), str):
            raise Denied("INVALID_DAG_CONTRACT")
        source = (root / rel).resolve(strict=True)
        if not source.is_relative_to(root):
            raise Denied("DAG_CONTRACT_OUTSIDE_REPO")
        if "sha256" in pin and pin["sha256"] != file_digest(source):
            raise Denied("DAG_CONTRACT_HASH_CHANGED")
    tags = set(plan.get("tags", []))
    if "RAW" not in tags:
        raise Denied("RAW_CONTROL_TAG_REQUIRED")
    families = set(plan.get("source_families", []))
    for family in families:
        tags.update(FAMILY_TAGS.get(family, set()))
    if "PRESERVED_NOT_MODELED" in tags:
        raise Denied("ECONOMIC_DECISION_PACKET_TASK_REQUIRED")
    selected = applicable_controls(root, sorted(tags), contracts["registry"]["path"])
    if not selected:
        raise Denied("NO_VALIDATION_CONTROLS_SELECTED")
    local_tasks = plan.get("local_tasks", {})
    if not isinstance(local_tasks, dict) or set(local_tasks) - LOCAL_TASK_STAGES:
        raise Denied("UNAUTHORIZED_DAG_LOCAL_STAGE")
    tasks = []
    previous = None
    for stage in STAGES:
        depends = [previous] if previous is not None else []
        if stage == "P9":
            tasks.append({"id": "P9_controls", "kind": "validate_controls",
                          "depends_on": depends,
                          "control_ids": sorted(c["id"] for c in selected),
                          "receipts": plan.get("control_receipts", {})})
            depends = ["P9_controls"]
        if stage == "P12":
            phases = plan.get("budget_phases")
            if not isinstance(phases, list) or not phases:
                raise Denied("BUDGET_PHASES_REQUIRED")
            seen = set()
            for index, item in enumerate(phases):
                phase_id, receipt = item.get("phase_id"), item.get("receipt")
                if not phase_id or not isinstance(receipt, str) or phase_id in seen:
                    raise Denied("INVALID_BUDGET_PHASE")
                seen.add(phase_id)
                task_id = f"P12_budget_{index}"
                tasks.append({"id": task_id, "kind": "budget_gate",
                              "phase_id": phase_id, "receipt": receipt,
                              "depends_on": depends})
                depends = [task_id]
        if stage in local_tasks:
            local = local_tasks[stage]
            prompt = (root / local["prompt_path"]).resolve(strict=True)
            if not prompt.is_relative_to(root) or file_digest(prompt) != local["prompt_sha256"]:
                raise Denied("DAG_PROMPT_HASH_CHANGED")
            task_id = stage + "_local"
            tasks.append({"id": task_id, "kind": "codex_task",
                          "prompt_path": local["prompt_path"],
                          "prompt_sha256": local["prompt_sha256"],
                          "runtime_seconds": local["runtime_seconds"],
                          "depends_on": depends})
            depends = [task_id]
        tasks.append({"id": stage, "kind": "stage_gate", "stage": stage,
                      "depends_on": depends, "receipt": stage_receipts[stage]})
        previous = stage
    # The shared runner guarantees a final freeze that depends on ALL previous tasks.
    tasks.append({"id": "P13_freeze", "kind": "freeze_verify",
                  "depends_on": [t["id"] for t in tasks],
                  "receipt": plan["freeze_receipt"]})
    queue = {"schema": "EDP_QUEUE_V1", "cohort": plan["cohort"],
             "output": plan["output"], "route": plan["route"],
             "tags": sorted(tags), "contracts": contracts, "tasks": tasks}
    _ordered(tasks)
    return queue


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile an owner-reviewable signed-runner DAG")
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    plan = json.loads(args.plan.read_bytes())
    queue = compile_dag(root, plan)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(queue))
    print(json.dumps({"status": "COMPILED_NOT_AUTHORIZED",
                      "tasks": len(queue["tasks"]), "queue": str(args.output)}))


if __name__ == "__main__":
    main()
