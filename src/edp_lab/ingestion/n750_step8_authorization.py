"""Fail-closed N750 Step 8 grant check, using the existing owner-pin pattern.

This module only validates authority. It does not verify remote RAW or dispatch work.
The trusted owner installation changes the one pin below after separate approval.
"""

import hashlib
import json
from pathlib import Path

from edp_lab.ingestion.universe import ScopeDenied


N750_OWNER_GRANT_SHA256 = "5ae18d7d2ee770cbefb3f6ad0a6b05eac87282d8e88b2c9f6422dff7c9b7b120"
N750_OWNER_GRANT_PATH = Path("metadata/authorizations/n750_processing_v1.json")
PROPOSAL_PATH = Path("proposals/n750-step8-v1/owner-record.proposed.json")
PROPOSAL_SHA256 = "0c0571e45de48ea96ebac0c6d6a28a2cf6c6ee5086558da23087014d07f05b36"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def authorize(root, action, source_ids):
    """Validate an installed grant and a bounded source batch; no side effects."""
    root = Path(root)
    if action not in {"remote_raw_resolution", "processing"}:
        raise ScopeDenied("INVALID_N750_ACTION")
    if N750_OWNER_GRANT_SHA256 is None:
        raise ScopeDenied("N750_PROCESSING_GRANT_NOT_INSTALLED")
    try:
        proposal_raw = (root / PROPOSAL_PATH).read_bytes()
        if _sha(proposal_raw) != PROPOSAL_SHA256:
            raise ScopeDenied("N750_PROPOSAL_PIN_MISMATCH")
        proposal = json.loads(proposal_raw)
        grant_raw = (root / N750_OWNER_GRANT_PATH).read_bytes()
        if _sha(grant_raw) != N750_OWNER_GRANT_SHA256:
            raise ScopeDenied("N750_OWNER_GRANT_PIN_MISMATCH")
        grant = json.loads(grant_raw)
        expected = dict(proposal, status="OWNER_APPROVED")
        if grant != expected or grant["status"] != "OWNER_APPROVED":
            raise ScopeDenied("INVALID_N750_OWNER_GRANT")
        for relative, digest in grant["input_files_sha256"].items():
            if _sha((root / relative).read_bytes()) != digest:
                raise ScopeDenied("N750_INPUT_PIN_MISMATCH")
        bindings = json.loads((root / "metadata/admissions/N750_v1/bindings.json").read_bytes())
        all_ids = {row["source_instance_id"] for row in bindings}
        if len(bindings) != 750 or len(all_ids) != 750:
            raise ScopeDenied("N750_BINDING_COUNT_MISMATCH")
        requested = list(source_ids)
        if not requested or len(requested) != len(set(requested)):
            raise ScopeDenied("INVALID_N750_BATCH")
        if action == "remote_raw_resolution":
            qualification = json.loads((root / "proposals/n750-step1-v3/qualification.json").read_bytes())
            reused_identities = {row["source_identity"] for row in qualification["remote_reuse"]}
            allowed = {row["source_instance_id"] for row in bindings
                       if row["source_identity"] not in reused_identities}
            if len(reused_identities) != 450 or len(allowed) != 300:
                raise ScopeDenied("N750_REMOTE_SCOPE_MISMATCH")
        else:
            allowed = all_ids
        if not set(requested) <= allowed:
            raise ScopeDenied("N750_BATCH_OUT_OF_SCOPE")
        return {"status": "AUTHORIZED_PREFLIGHT_ONLY", "action": action,
                "source_ids": requested, "owner_grant_sha256": _sha(grant_raw)}
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ScopeDenied("INVALID_N750_OWNER_EVIDENCE") from exc
