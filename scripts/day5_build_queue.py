"""Pin the preserved N500 roster and P3/P4 contracts into one live queue."""

import json
from pathlib import Path

from edp_lab.operating.authority import canonical, file_digest
from edp_lab.operating.runner import applicable_controls

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "runs/day5/p6_candidate_v1"
QUEUE = ROOT / "runs/day5/c2000_live_queue_v1.json"
RECEIPTS = Path("/private/var/db/edp-lab/receipts")
CONTRACTS = {
    "parser": ("C300_PARSER_V1", "src/edp_lab/parsers/c300_v1.py"),
    "model": ("M1_LEXICAL_V1", "src/edp_lab/materialization/c300_m1.py"),
    "rule": ("C300_LITERAL_IDENTITY_V1", "docs/parsing_profiling_freeze_v2.md"),
    "registry": ("EDP_VALIDATION_REGISTRY_V1", "metadata/operating/validation_registry_v1.json"),
    "candidate": ("DAY5_P6_CANDIDATE_V1", "runs/day5/p6_candidate_v1/candidate.json"),
    "budget_policy": ("EDP_LAB_AUTONOMOUS_PILOT_C3_4_BUDGET_V1",
                      "metadata/operating/edp_lab_pilot_c3_4_budget_v1.json"),
    **{name: ("DAY5_SQL_BUILD_V1", f"runs/day5/sql_v1/{name}.json")
       for name in ("roster", "smoke", "full_clean", "candidate_view", "result_view")},
}


def main() -> None:
    if QUEUE.exists():
        raise FileExistsError(QUEUE)
    candidate = json.loads((BASE / "candidate.json").read_bytes())
    rows = json.loads((BASE / "N500.bindings.json").read_bytes())
    build = json.loads((ROOT / "runs/day5/sql_v1/build.json").read_bytes())
    if (candidate["status"] != "PREPARED_NOT_ADMITTED_REMOTE_READBACK_PENDING"
            or candidate["new_count"] != 500 or len(rows) != 500
            or candidate["outputs_sha256"]["N500.bindings.json"]
            != file_digest(BASE / "N500.bindings.json")
            or build["p6_candidate_sha256"] != file_digest(BASE / "candidate.json")):
        raise ValueError("PRESERVED_CANDIDATE_CHANGED")
    contracts = {name: {"version": version, "path": path, "sha256": file_digest(ROOT / path)}
                 for name, (version, path) in CONTRACTS.items()}
    tasks = [{"id": "P5", "kind": "stage_gate", "stage": "P5", "depends_on": []}]
    raw_ids = []
    for index, row in enumerate(rows, 1):
        identity = row["source_identity"]
        task_id = f"raw-{index:03d}"
        raw_ids.append(task_id)
        tasks.append({"id": task_id, "kind": "raw_stage", "depends_on": ["P5"],
                      "operation_id": f"day5-n500-raw-{index:03d}-{identity[:12]}",
                      "source": {"identity": identity, "path": row["raw_path"],
                                 "sha256": row["raw_sha256"]},
                      "databricks_path": row["remote_raw_path"],
                      "runtime_seconds": 180,
                      "external_receipt": str(RECEIPTS / f"raw-{index:03d}.json")})
    tasks.append({"id": "P6", "kind": "cohort_admit", "depends_on": raw_ids,
                  "operation_id": "day5-c2000-cohort-admit-v1",
                  "candidate_path": "runs/day5/p6_candidate_v1/candidate.json",
                  "runtime_seconds": 180,
                  "external_receipt": str(RECEIPTS / "c2000-cohort.json")})
    previous = "P6"
    for name, stage in (("roster", None), ("smoke", "P7"),
                        ("full_clean", "P8"), ("candidate_view", None),
                        ("result_view", "P9")):
        task_id = f"sql-{name}"
        tasks.append({"id": task_id, "kind": "databricks_write",
                      "depends_on": [previous], "operation_id": f"day5-c2000-{name}-v1",
                      "statement_path": contracts[name]["path"],
                      "statement_contract": name,
                      "databricks_table": build["targets"][name],
                      "runtime_seconds": 900,
                      "external_receipt": str(RECEIPTS / f"sql-{name}.json")})
        previous = task_id
        if stage:
            tasks.append({"id": stage, "kind": "stage_gate", "stage": stage,
                          "depends_on": [previous],
                          "receipt": str(RECEIPTS / f"stage-{stage.lower()}.json")})
            previous = stage
    tags = ["RAW", "C2000", "M2", "FSDS", "FIN", "TREASURY"]
    controls = applicable_controls(ROOT, tags)
    tasks.append({"id": "P10-P11", "kind": "validate_controls", "depends_on": [previous],
                  "control_ids": [control["id"] for control in controls],
                  "receipts": {control["id"]: str(RECEIPTS / f"control-{control['id']}.json")
                               for control in controls if control["execution"] == "databricks_sql"}})
    tasks.append({"id": "P12-budget", "kind": "budget_gate", "depends_on": ["P10-P11"],
                  "phase_id": "sql_table_creation",
                  "receipt": str(RECEIPTS / "timing-sql-table-creation.json")})
    ids = [task["id"] for task in tasks]
    queue = {"schema": "EDP_QUEUE_V1", "cohort": "C2000",
             "previous_cohort": "C1500", "route": "CORPUS_ONLY",
             "prior_receipt": str(RECEIPTS / "c1500-prior.json"),
             "sources": [{"identity": row["source_identity"], "path": row["raw_path"],
                          "sha256": row["raw_sha256"]} for row in rows],
             "output": build["targets"]["result_view"], "tags": tags,
             "contracts": contracts, "tasks": tasks + [{
                 "id": "P13", "kind": "freeze_verify", "depends_on": ids,
                 "receipt": str(RECEIPTS / "c2000-result-freeze.json")}]}
    QUEUE.write_bytes(canonical(queue))
    print(json.dumps({"queue": str(QUEUE), "sha256": file_digest(QUEUE),
                      "tasks": len(queue["tasks"]), "raw_sources": len(raw_ids)}, sort_keys=True))


if __name__ == "__main__":
    main()
