"""Prepare the exact one-time standing policy for owner-only protected signing.

This writes an unsigned proposal. Only the protected setup script can sign it.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from edp_lab.operating.authority import canonical, file_digest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/day5/standing_policy_unsigned_v1.json"
UNIVERSE = "metadata/source_universes/approved_v1/manifest.json"
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
    if OUT.exists():
        raise FileExistsError(OUT)
    issued = datetime.now(UTC)
    policy = {
        "schema": "EDP_STANDING_POLICY_V1", "policy_id": "edp-lab-standing-0a-v1",
        "issued_at": issued.isoformat(),
        "expires_at": (issued + timedelta(days=90)).isoformat(),
        "cohort_pattern": r"C[0-9]+", "routes": ["CORPUS_ONLY"],
        "max_increment": 500, "universe_path": UNIVERSE,
        "universe_sha256": file_digest(ROOT / UNIVERSE),
        "output_prefix": "workspace.edp_lab.o_c",
        "contracts": {name: {"version": version, "sha256": file_digest(ROOT / path)}
                      for name, (version, path) in CONTRACTS.items()},
        "operations": ["verify_file", "stage_gate", "raw_stage", "cohort_admit",
                       "databricks_write", "validate_controls", "budget_gate",
                       "freeze_verify"],
        "databricks_path_prefixes": ["dbfs:/Volumes/workspace/edp_lab/raw/day5-n500-"],
        "databricks_table_prefixes": ["workspace.edp_lab.n500_input_roster_day5_v1",
                                      "workspace.edp_lab.clean_n500_m1_",
                                      "workspace.edp_lab.o_c2000_m2_"],
        "git_operations": [],
        "protected_branches": ["main", "master"], "grant_hours": 72,
        "limits": {"runtime_seconds": 150000, "compute_units": 10000,
                   "token_count": 1000000, "retries": 20, "operations": 1000},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(canonical(policy))
    print(json.dumps({"path": str(OUT), "sha256": file_digest(OUT),
                      "universe_sha256": policy["universe_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
