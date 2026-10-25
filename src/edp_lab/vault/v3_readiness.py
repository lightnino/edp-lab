"""Read-only V3 preparation check; neither unsigned files nor Git confer grants."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from edp_lab.operating.authority import Denied, protected_trust_dir, verified_document
from edp_lab.vault.v3_ddl import plan as ddl_plan


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def readiness(root: Path, signed_semantic_envelope: Path | None = None) -> dict:
    """Verify local pins and report genuine authority/technical boundaries."""
    root = root.resolve()
    plan = json.loads((root / "metadata/operating/day6_c2000_vault_v3_bounded_request_v1.json").read_bytes())
    if plan.get("schema") != "EDP_C2000_VAULT_V3_BOUNDED_REQUEST_V1":
        raise Denied("VAULT_V3_PLAN_INVALID")
    predecessor = json.loads((root / "metadata/evaluations/day6_c2000_vault_semantic_successor_v1.json").read_bytes())
    historical = (("runs/day6-vault-pilot/v2.json", "predecessor_v2_receipt_sha256"),
                  ("runs/day6-vault-pilot/v3.json", "predecessor_v3_receipt_sha256"))
    for relative, field in historical:
        if _sha(root / relative) != predecessor[field]:
            raise Denied("VAULT_HISTORICAL_RECEIPT_CHANGED:" + relative)
    for name in ("selection", "negative_oracles", "semantic_approval_request"):
        pin = plan[name]
        if _sha(root / pin["path"]) != pin["sha256"]:
            raise Denied("VAULT_V3_PIN_CHANGED:" + name)
    for name in ("target_ddl", "resource_proposal"):
        pin = plan[name]
        if _sha(root / pin["path"]) != pin["sha256"]:
            raise Denied("VAULT_V3_PIN_CHANGED:" + name)
    ddl = json.loads((root / plan["target_ddl"]["path"]).read_bytes())
    if ddl != ddl_plan(plan["new_v3_table_allowlist"]):
        raise Denied("VAULT_V3_DDL_PLAN_CHANGED")
    semantic = json.loads((root / plan["semantic_approval_request"]["path"]).read_bytes())
    if (semantic.get("signature_status") != "PENDING_OWNER_CONTROLLED_SIGNATURE"
            or "signature_base64" in semantic):
        raise Denied("VAULT_SEMANTIC_REQUEST_NOT_UNSIGNED")
    document = semantic["document"]
    if (document.get("cohort") != "C2000" or document.get("status") != "APPROVED"
            or document.get("frozen_roster_sha256") != plan["frozen_roster_sha256"]
            or document.get("frozen_bindings_sha256") != plan["frozen_bindings_sha256"]):
        raise Denied("VAULT_SEMANTIC_REQUEST_SCOPE_INVALID")
    for pin in document["contract_pins"]:
        if _sha(root / pin["path"]) != pin["sha256"]:
            raise Denied("VAULT_SEMANTIC_CONTRACT_CHANGED:" + pin["version"])
    blockers = []
    if signed_semantic_envelope is None:
        blockers.append("OWNER_SIGNED_SEMANTIC_ENVELOPE_REQUIRED")
    else:
        proof = verified_document(root, signed_semantic_envelope, protected_trust_dir(root))
        if proof != document:
            raise Denied("VAULT_SIGNED_SEMANTIC_DOCUMENT_MISMATCH")
    execution = plan["execution"]
    deployment_path = root / "metadata/operating/day6_c2000_vault_v3_deployment_v1.json"
    if _sha(deployment_path) != execution["deployment_sha256"]:
        raise Denied("VAULT_V3_DEPLOYMENT_PIN_CHANGED")
    deployment = json.loads(deployment_path.read_bytes())
    if (deployment["artifact"]["sha256"] != execution["runtime_artifact_sha256"]
            or deployment["pinned_documents"]["ddl_plan_sha256"] !=
            plan["target_ddl"]["sha256"]):
        raise Denied("VAULT_V3_RUNTIME_OR_DDL_PIN_CHANGED")
    local_wheel = Path(deployment["artifact"]["local_build_output_uncommitted"])
    if local_wheel.exists() and _sha(local_wheel) != execution["runtime_artifact_sha256"]:
        raise Denied("VAULT_V3_LOCAL_WHEEL_CHANGED")
    for name in ("runtime_artifact_sha256", "deployment_sha256", "protected_grant_id"):
        if execution[name] is None:
            blockers.append(name.upper() + "_REQUIRED")
    if deployment["status"] != "INSTALLED_BY_OWNER_PROTECTED_EXTENSION":
        blockers.append("V3_PROTECTED_EXTENSION_INSTALL_REQUIRES_OWNER_AUTHORIZATION")
    if execution["job_submissions_max"] != 1 or execution["automatic_retries_max"] != 0:
        raise Denied("VAULT_V3_JOB_LIMIT_CHANGED")
    selected = json.loads((root / plan["selection"]["path"]).read_bytes())
    if (selected["selected_data_rows"] != plan["selection"]["physical_data_rows"]
            or sorted(selected["sources"]) != plan["selection"]["source_ids"]
            or selected["selected_data_rows"] > execution["data_rows_max"]):
        raise Denied("VAULT_V3_SELECTION_OUT_OF_SCOPE")
    return {"schema": "EDP_VAULT_V3_READINESS_V1",
            "status": "AUTHORIZATION_REQUIRED" if blockers else "LOCAL_PINS_READY_PROTECTED_PREFLIGHT_REQUIRED",
            "selected_sources": len(selected["sources"]),
            "selected_data_rows": selected["selected_data_rows"],
            "blockers": blockers}
