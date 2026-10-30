"""Mechanical C2000 evidence reuse and source-family Model Fit inventory.

No business key is inferred here.  These functions read pinned frozen records;
the Vault lifecycle runner owns sequencing and the workflow owns decisions.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from edp_lab.operating.authority import Denied, file_digest
from edp_lab.operating.runner import _write_json
from edp_lab.vault.lifecycle_runner import _repo_file

FAMILIES = {
    "/sec_fsds/": "SEC_FSDS",
    "/sec_13f/": "SEC_13F",
    "/sec_edgar_daily_master/": "SEC_EDGAR_DAILY_MASTER",
    "/treasury_annual_xml/": "TREASURY_ANNUAL_XML",
}
PROTOTYPE = {"SRC000005", "SRC000054", "SRC000064"}


def _pin(root: Path, plan: dict, name: str) -> Path:
    pin = plan["inputs"][name]
    return _repo_file(root, pin["path"], pin["sha256"])


def verify_reused_v0a(root: Path, plan: dict) -> dict:
    accepted = json.loads(_pin(root, plan, "vault_0a_acceptance").read_bytes())
    if (accepted.get("live_installation") is not True
            or accepted.get("installation_receipt_signature_verified") is not True
            or accepted.get("vault_schema_and_eight_delta_tables_verified") is not True
            or accepted.get("service_principal_effective_privileges_verified") is not True):
        raise Denied("VAULT_0A_HISTORICAL_ACCEPTANCE_INVALID")
    from edp_lab.operating.authority import verified_document

    base = Path("/private/var/db/edp-lab-day6-vault")
    policy_path = base / "trust/policy.signed.json"
    policy = verified_document(root, policy_path, base / "trust")
    if (file_digest(policy_path) != accepted["installed_signed_policy_sha256"]
            or policy.get("namespace") != plan["namespace"]
            or policy.get("warehouse_id") != plan["warehouse_id"]
            or policy.get("tables") != plan["tables"]):
        raise Denied("VAULT_0A_INSTALLED_POLICY_CHANGED")
    full = policy.get("c2000_full_integration_allowed") is True
    return {"status": "PASS", "effective_scope": (
                "FULL_INTEGRATION" if full else "BOUNDED_PROTOTYPE_ONLY"),
            "policy_sha256": file_digest(policy_path),
            "full_write_authorized": full}


def verify_reused_v0(root: Path, plan: dict) -> dict:
    step0 = json.loads(_pin(root, plan, "step0_evaluation").read_bytes())
    step2 = json.loads(_pin(root, plan, "step2").read_bytes())
    approval = json.loads(_pin(root, plan, "contract_approval").read_bytes())
    freeze = _pin(root, plan, "cohort_freeze")
    _pin(root, plan, "upstream_result")
    _pin(root, plan, "approved_contract")
    _pin(root, plan, "frozen_bindings")
    if (step0.get("status") != "PASS_SIGNED_C2000_FREEZE"
            or step0.get("physical_sources") != 2000
            or step2.get("status") != "VAULT_PROTOTYPE_VALIDATED"
            or step2.get("cohort_freeze_sha256") != file_digest(freeze)
            or step2.get("contract_sha256") != plan["inputs"]["approved_contract"]["sha256"]
            or approval.get("approval_id") != "DAY6_VAULT_LOAD_CONTRACT_V1_OWNER_APPROVAL"):
        raise Denied("VAULT_HISTORICAL_BASELINE_MISMATCH")
    return {"status": "PASS", "physical_sources": 2000,
            "prototype_sources": sorted(PROTOTYPE),
            "prototype_occurrences": step2["data_occurrences"],
            "historical_execution_path": step2["execution_path"]}


def classify_frozen_inventory(root: Path, plan: dict) -> dict:
    bindings = json.loads(_pin(root, plan, "frozen_bindings").read_bytes())
    with _pin(root, plan, "roster").open(newline="") as stream:
        roster = [row["source_instance_id"] for row in csv.DictReader(stream)]
    indexed = {item["source_instance_id"]: item for item in bindings}
    if len(roster) != 2000 or len(set(roster)) != 2000 or set(indexed) != set(roster):
        raise Denied("VAULT_FROZEN_INVENTORY_MISMATCH")
    sources = {}
    for source_id in roster:
        binding = indexed[source_id]
        path = binding["raw_path"]
        family = next((name for marker, name in FAMILIES.items() if marker in path), None)
        if family is None:
            raise Denied("VAULT_SOURCE_FAMILY_UNCLASSIFIED:" + source_id)
        fit = "REUSE_APPROVED" if family == "SEC_FSDS" else "NEW_CONTRACT_REQUIRED"
        sources[source_id] = {
            "family": family, "model_fit": fit, "raw_path": path,
            "raw_sha256": binding["raw_sha256"],
            "already_loaded_prototype": source_id in PROTOTYPE,
            "contract": "VAULT_LOAD_CONTRACT_V1" if family == "SEC_FSDS" else None,
            "physical_schema": ("NUM_MEMBER_HEADER_RECHECK_REQUIRED" if family == "SEC_FSDS"
                                else "SOURCE_FAMILY_SCHEMA_REVIEW_REQUIRED"),
            "field_coverage": ("NUM_VALUE_M2_60_BINDINGS_HISTORICALLY_APPROVED"
                               if family == "SEC_FSDS" else "NOT_VAULT_MAPPED"),
        }
    families = Counter(item["family"] for item in sources.values())
    fit = Counter(item["model_fit"] for item in sources.values())
    return {"schema": "EDP_VAULT_C2000_MODEL_FIT_V1", "cohort": plan["cohort"],
            "roster_sha256": plan["inputs"]["roster"]["sha256"],
            "bindings_sha256": plan["inputs"]["frozen_bindings"]["sha256"],
            "source_count": len(sources), "family_counts": dict(sorted(families.items())),
            "model_fit_counts": dict(sorted(fit.items())), "sources": sources}


def save_once(path: Path, value: dict) -> None:
    if path.exists():
        if json.loads(path.read_bytes()) != value:
            raise Denied("VAULT_EXISTING_EVIDENCE_CONFLICT:" + str(path))
        return
    _write_json(path, value)
