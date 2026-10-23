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
    required_receipts = set(STAGES) - ({"P5"} if "sources" in plan else set())
    if (not isinstance(stage_receipts, dict)
            or not required_receipts <= set(stage_receipts)
            or set(stage_receipts) - set(STAGES)):
        raise Denied("MISSING_STAGE_RECEIPTS")
    for path in stage_receipts.values():
        if not isinstance(path, str) or not path:
            raise Denied("INVALID_STAGE_RECEIPT_PATH")
    contracts = plan.get("contracts", {})
    if not {"parser", "model", "rule", "registry", "budget_policy"} <= set(contracts):
        raise Denied("MISSING_DAG_CONTRACTS")
    root = root.resolve()
    for pin in contracts.values():
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
    simulation = plan.get("simulation_only", False)
    if not isinstance(simulation, bool):
        raise Denied("INVALID_SIMULATION_MODE")
    local_tasks = plan.get("local_tasks", {})
    if not isinstance(local_tasks, dict) or set(local_tasks) - LOCAL_TASK_STAGES:
        raise Denied("UNAUTHORIZED_DAG_LOCAL_STAGE")
    guarded_jobs = plan.get("guarded_jobs", [])
    if not isinstance(guarded_jobs, list) or len(guarded_jobs) > 16:
        raise Denied("INVALID_GUARDED_JOBS")
    seen_operations = set()
    for job in guarded_jobs:
        expected = {"stage", "operation_id", "submission_path", "deployment_path",
                    "submission_contract", "deployment_contract", "databricks_path",
                    "external_receipt"}
        if not isinstance(job, dict) or set(job) != expected or job["stage"] not in {
                "P7", "P8"}:
            raise Denied("INVALID_GUARDED_JOB")
        if job["operation_id"] in seen_operations:
            raise Denied("DUPLICATE_JOB_OPERATION_ID")
        seen_operations.add(job["operation_id"])
        for contract_key, path_key in (("submission_contract", "submission_path"),
                                       ("deployment_contract", "deployment_path")):
            name = job[contract_key]
            if name not in contracts or contracts[name]["path"] != job[path_key]:
                raise Denied("JOB_CONTRACT_NOT_PINNED")
            # Request payload and remote deployment manifest must be byte-pinned
            # at compile time; the live adapter rechecks against the signed grant.
            if contracts[name].get("sha256") != file_digest(
                    (root / job[path_key]).resolve(strict=True)):
                raise Denied("JOB_CONTRACT_HASH_CHANGED")
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
                budget_task = {"id": task_id, "kind": "budget_gate",
                               "phase_id": phase_id, "receipt": receipt,
                               "depends_on": depends}
                if simulation:
                    budget_task["simulated_measurement"] = True
                tasks.append(budget_task)
                depends = [task_id]
        # Only the existing #51 guarded CREATE TABLE adapter is available today.
        # Do not generalize it into RAW/CLEAN/QUERYABLE or Delta freeze permissions.
        write = plan.get("guarded_create_table")
        if stage == "P8" and write is not None:
            if "statement" not in contracts or not isinstance(write, dict):
                raise Denied("GUARDED_WRITE_STATEMENT_NOT_PINNED")
            required = {"operation_id", "databricks_path", "databricks_table",
                        "statement_path", "external_receipt"}
            if set(write) != required:
                raise Denied("INVALID_GUARDED_WRITE")
            if write["statement_path"] != contracts["statement"]["path"]:
                raise Denied("GUARDED_WRITE_STATEMENT_NOT_PINNED")
            task_id = "P8_guarded_create_table"
            tasks.append({"id": task_id, "kind": "databricks_write",
                          "operation_id": write["operation_id"],
                          "databricks_path": write["databricks_path"],
                          "databricks_table": write["databricks_table"],
                          "statement_path": write["statement_path"],
                          "external_receipt": write["external_receipt"],
                          "depends_on": depends})
            depends = [task_id]
        for index, job in enumerate(guarded_jobs):
            if stage != job["stage"]:
                continue
            task_id = f"{stage}_job_{index}"
            tasks.append({"id": task_id, "kind": "databricks_job_submit",
                          "depends_on": depends,
                          **{key: value for key, value in job.items()
                             if key != "stage"}})
            depends = [task_id]
        if stage in local_tasks:
            local = local_tasks[stage]
            prompt = (root / local["prompt_path"]).resolve(strict=True)
            if not prompt.is_relative_to(root) or file_digest(prompt) != local["prompt_sha256"]:
                raise Denied("DAG_PROMPT_HASH_CHANGED")
            task_id = stage + "_local"
            local_task = {"id": task_id, "kind": "codex_task",
                          "prompt_path": local["prompt_path"],
                          "prompt_sha256": local["prompt_sha256"],
                          "runtime_seconds": local["runtime_seconds"],
                          "depends_on": depends}
            if simulation:
                local_task["simulated_success"] = True
            tasks.append(local_task)
            depends = [task_id]
        stage_task = {"id": stage, "kind": "stage_gate", "stage": stage,
                      "depends_on": depends,
                      "receipt": stage_receipts.get(stage, "BROKER_GRANT")}
        if simulation:
            stage_task["simulated_receipt"] = True
        tasks.append(stage_task)
        previous = stage
    # The shared runner guarantees a final freeze that depends on ALL previous tasks.
    freeze = {"id": "P13_freeze", "kind": "freeze_verify",
              "depends_on": [t["id"] for t in tasks],
              "receipt": plan["freeze_receipt"]}
    if simulation:
        freeze["simulated_receipt"] = True
    tasks.append(freeze)
    queue = {"schema": "EDP_QUEUE_V1", "cohort": plan["cohort"],
             "output": plan["output"], "route": plan["route"],
             "tags": sorted(tags), "contracts": contracts, "tasks": tasks,
             "simulation_only": simulation}
    if "sources" in plan:
        queue.update(sources=plan["sources"], previous_cohort=plan["previous_cohort"],
                     prior_receipt=plan["prior_receipt"])
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
