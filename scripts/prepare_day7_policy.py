"""Build the unsigned, exactly scoped Day 7 successor Cohort policy."""

from __future__ import annotations

import json
from pathlib import Path

from edp_lab.operating.authority import canonical, file_digest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "metadata/operating/day7_c3000_standing_policy_unsigned_v1.json"
CONTRACTS = {
    "parser": ("C300_PARSER_V1", "src/edp_lab/parsers/c300_v1.py"),
    "model": ("M1_LEXICAL_V1", "src/edp_lab/materialization/c300_m1.py"),
    "rule": ("C300_LITERAL_IDENTITY_V1", "docs/parsing_profiling_freeze_v2.md"),
    "registry": ("EDP_VALIDATION_REGISTRY_V1", "metadata/operating/validation_registry_v1.json"),
    "budget_policy": ("EDP_LAB_AUTONOMOUS_PILOT_C3_4_BUDGET_V1",
                      "metadata/operating/edp_lab_pilot_c3_4_budget_v1.json"),
    "universe": ("SOURCE_UNIVERSE_AUTHORITY_V1",
                 "metadata/source_universes/approved/manifest.json"),
    "universe_approval": ("EDP_DAY7_UNIVERSE_EXPANSION_OWNER_DECISION_V1",
                          "metadata/authorizations/day7_universe_expansion_800_owner_decision.json"),
    "prior_freeze": ("C2000_INPUT_FREEZE_V1", "metadata/freezes/C2000_v1/freeze.json"),
    "prior_result": ("O_C2000_M2_DATABRICKS_RESULT_FREEZE_V1",
                     "metadata/freezes/O_C2000_M2_v1/databricks_result_freeze_v1.json"),
}


def prepare() -> dict:
    policy = {
        "schema": "EDP_STANDING_POLICY_V1",
        "policy_id": "edp-lab-standing-day7-c3000-v1",
        "issued_at": "2026-10-25T00:00:00+00:00",
        "expires_at": "2027-01-21T00:00:00+00:00",
        "cohort_pattern": "C3000",
        "routes": ["CORPUS_ONLY", "INITIAL_MODEL", "ADDITIVE", "CORRECTIVE"],
        "max_increment": 1000,
        "universe_path": "metadata/source_universes/approved/manifest.json",
        "universe_sha256": "dcc63767c88ae712eab8f5ba29d52a206b4262710740e591a4b233d9c04c699b",
        "prior_receipt_path": "/private/var/db/edp-lab-day7/receipts/c2000-prior.json",
        "output_prefix": "workspace.edp_lab_day7_c3000.o_c3000_",
        "contracts": {name: {"version": version, "sha256": file_digest(ROOT / path)}
                      for name, (version, path) in CONTRACTS.items()},
        "operations": ["verify_file", "stage_gate", "cohort_admit",
                       "databricks_write", "databricks_job_submit",
                       "validate_controls", "budget_gate", "freeze_verify"],
        "databricks_path_prefixes": [
            "dbfs:/Volumes/workspace/edp_lab_day7_c3000/artifacts/"],
        "databricks_table_prefixes": ["workspace.edp_lab_day7_c3000.n1000_",
                                      "workspace.edp_lab_day7_c3000.clean_n1000_",
                                      "workspace.edp_lab_day7_c3000.o_c3000_",
                                      "workspace.edp_lab_day7_c3000.canary_"],
        "git_operations": [], "protected_branches": ["main", "master"],
        "grant_hours": 24,
        "limits": {"runtime_seconds": 150000, "compute_units": 10000,
                   "token_count": 1000000, "retries": 20, "operations": 3000},
    }
    if policy["contracts"]["universe"]["sha256"] != policy["universe_sha256"]:
        raise ValueError("Active Universe digest changed")
    if (policy["contracts"]["universe_approval"]["sha256"]
            != "416efc5f7ab18b2570ba9beab26bba33210c5e0a75ec813a92ccac953af36d74"):
        raise ValueError("Owner decision digest changed")
    if "raw_stage" in policy["operations"]:
        raise ValueError("Cohort RAW mutation forbidden")
    encoded = canonical(policy)
    OUTPUT.write_bytes(encoded)
    return {"path": str(OUTPUT), "sha256": file_digest(OUTPUT),
            "universe_sha256": policy["universe_sha256"]}


if __name__ == "__main__":
    print(json.dumps(prepare(), sort_keys=True))
