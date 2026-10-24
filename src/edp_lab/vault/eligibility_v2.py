"""Protected one-time registration of an independently approved Vault cohort."""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.operating.authority import Denied, file_digest, verified_document
from edp_lab.vault.broker_v2 import _protected, _signed
from edp_lab.vault.protected_readback import _sign
from edp_lab.vault.standing_v2 import validate_cohort_receipt, validate_standing_policy


def receipt_from_owner_approval(policy: dict, approval: dict,
                                *, now: datetime | None = None) -> dict:
    """Mechanical scope transfer; the approval signature is checked by caller."""
    current = now or datetime.now(UTC)
    if (approval.get("schema") != "EDP_VAULT_COHORT_SCOPE_APPROVAL_V1"
            or approval.get("authority") != "requesting-owner-vault-dev-v2"
            or approval.get("status") != "APPROVED"
            or approval.get("contract") not in policy["contracts"]
            or approval.get("mapping_rule") not in policy["mapping_rules"]):
        raise Denied("VAULT_COHORT_OWNER_APPROVAL_INVALID")
    expires = min(datetime.fromisoformat(policy["expires_at"]),
                  datetime.fromisoformat(approval["expires_at"]))
    if expires <= current:
        raise Denied("VAULT_COHORT_OWNER_APPROVAL_EXPIRED")
    fields = ("cohort_id", "workload_kind", "namespace", "tables", "contract", "mapping_rule",
              "freeze", "source_manifest", "approval", "input_manifest", "load_plan",
              "input_manifest_sha256", "load_plan_sha256", "sources",
              "data_occurrence_limit", "synthetic_row_limit",
              "independent_freeze_receipt_sha256")
    if any(field not in approval for field in fields):
        raise Denied("VAULT_COHORT_OWNER_APPROVAL_INCOMPLETE")
    return {"schema": "EDP_VAULT_COHORT_ELIGIBILITY_V1",
            "authority": "protected-verifier-v1", "status": "VERIFIED_FROZEN",
            "issued_at": current.isoformat(), "expires_at": expires.isoformat(),
            **{field: approval[field] for field in fields}}


def register(root: Path, base: Path, cohort_id: str) -> Path:
    """Verify an owner-signed cohort approval, then sign its frozen eligibility."""
    _protected(root, base)
    policy = _signed(root, base, "policy.signed.json")
    validate_standing_policy(policy, root=root)
    if not cohort_id or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:-"
                            for character in cohort_id):
        raise Denied("VAULT_COHORT_ID_INVALID")
    owner_path = base / "approvals" / (cohort_id + ".signed.json")
    if (owner_path.stat().st_uid != 0 or owner_path.stat().st_mode & 0o022):
        raise Denied("VAULT_COHORT_APPROVAL_UNPROTECTED")
    approval = verified_document(root, owner_path, base / "trust")
    if approval.get("cohort_id") != cohort_id:
        raise Denied("VAULT_COHORT_APPROVAL_ID_MISMATCH")
    prior_name = approval.get("independent_freeze_receipt")
    if (not isinstance(prior_name, str) or not prior_name.endswith(".signed.json")
            or "/" in prior_name or ".." in prior_name):
        raise Denied("VAULT_INDEPENDENT_FREEZE_RECEIPT_REQUIRED")
    prior_path = base / "receipts" / prior_name
    if prior_path.stat().st_uid != 0 or prior_path.stat().st_mode & 0o022:
        raise Denied("VAULT_INDEPENDENT_FREEZE_RECEIPT_UNPROTECTED")
    prior = verified_document(root, prior_path, base / "trust")
    if (prior.get("authority") != "protected-verifier-v1"
            or prior.get("status") != "LIVE_VERIFIED"
            or prior.get("cohort_id") != cohort_id
            or prior.get("freeze_sha256") != approval.get("freeze", {}).get("sha256")):
        raise Denied("VAULT_INDEPENDENT_FREEZE_NOT_VERIFIED")
    if file_digest(prior_path) != approval.get("independent_freeze_receipt_sha256"):
        raise Denied("VAULT_INDEPENDENT_FREEZE_RECEIPT_CHANGED")
    receipt = receipt_from_owner_approval(policy, approval)
    validate_cohort_receipt(policy, receipt, root, protected_base=base)
    output = base / "eligibility" / (cohort_id + ".signed.json")
    if output.exists():
        raise Denied("VAULT_COHORT_ELIGIBILITY_ALREADY_INSTALLED")
    key = base / "private/verifier.pem"
    if key.stat().st_uid != 0 or key.stat().st_mode & 0o077:
        raise Denied("VAULT_VERIFIER_KEY_UNPROTECTED")
    _sign(receipt, key, output)
    if verified_document(root, output, base / "trust") != receipt:
        raise Denied("VAULT_COHORT_ELIGIBILITY_SIGNATURE_FAILED")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("base", type=Path)
    parser.add_argument("cohort_id")
    args = parser.parse_args()
    print(json.dumps({"status": "VAULT_COHORT_ELIGIBLE",
                      "receipt_path": str(register(args.root, args.base, args.cohort_id))},
                     sort_keys=True))


if __name__ == "__main__":
    main()
