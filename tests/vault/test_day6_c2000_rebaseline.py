"""C2000 Step 0 and bounded Step 2 pins stay fail closed."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from edp_lab.vault.load_plan import NAMESPACE, TABLES

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "metadata/operating/day6_c2000_vault_v1"
LOCAL = ROOT / "runs/day6-vault-c2000-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_c2000_freeze_and_plan_pins():
    freeze = json.loads((ROOT / "metadata/freezes/C2000_v1/freeze.json").read_bytes())
    result = json.loads((ROOT / "metadata/freezes/O_C2000_M2_v1/databricks_result_freeze_v1.json").read_bytes())
    proposal = json.loads((BASE / "scope_approval_proposal.json").read_bytes())
    run = json.loads((BASE / "run_plan_proposal.json").read_bytes())
    assert result["input_freeze_sha256"] == sha(ROOT / "metadata/freezes/C2000_v1/freeze.json")
    assert proposal["cohort_freeze_sha256"] == result["input_freeze_sha256"]
    assert proposal["source_manifest_sha256"] == freeze["files_sha256"]["C2000.bindings.json"]
    assert proposal["result_freeze_sha256"] == sha(
        ROOT / "metadata/freezes/O_C2000_M2_v1/databricks_result_freeze_v1.json")
    assert proposal["input_manifest_sha256"] == run["input_manifest_sha256"]
    assert proposal["load_plan_sha256"] == run["load_plan_sha256"]
    if (LOCAL / "input_manifest.json").exists():
        input_manifest = json.loads((LOCAL / "input_manifest.json").read_bytes())
        plan = json.loads((LOCAL / "load_plan.json").read_bytes())
        assert proposal["input_manifest_sha256"] == sha(LOCAL / "input_manifest.json")
        assert proposal["load_plan_sha256"] == sha(LOCAL / "load_plan.json")
        assert input_manifest["cohort_id"] == plan["cohort_id"] == "C2000"
        assert len(input_manifest["rows"]) == plan["data_occurrences"] == 127
        assert plan["input_manifest_sha256"] == run["input_manifest_sha256"]
        assert plan["synthetic_rows"] == 6
        assert set(plan["expected_tables"]) == set(TABLES)
        assert all(stage["table"].startswith(NAMESPACE + ".") for stage in plan["stages"])


def test_c2000_proposal_is_not_eligible_without_owner_gate():
    proposal = json.loads((BASE / "scope_approval_proposal.json").read_bytes())
    run = json.loads((BASE / "run_plan_proposal.json").read_bytes())
    assert proposal["status"] == "PROPOSED_NOT_APPROVED"
    assert proposal["protected_owner_signature"] == "PENDING_OWNER"
    assert proposal["independent_c2000_live_verified_receipt"] == "PENDING_PROTECTED_VERIFIER"
    assert run["status"] == "INELIGIBLE_PENDING_OWNER_AND_PROTECTED_VERIFIER_GATES"
    assert not (ROOT / "metadata/authorizations/day6_vault_c1500_prototype_exception_v1.json").exists()
