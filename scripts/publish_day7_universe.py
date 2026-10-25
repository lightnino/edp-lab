"""Reconcile the retained 800 against original receipts and publish one active manifest.

This is a local publication tool. It does not sign a protected approval or touch RAW.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "metadata/source_universes/approved_v1/manifest.json"
DECISION = ROOT / "metadata/authorizations/day7_universe_expansion_800_owner_decision.json"
LEDGER = ROOT / "docs/incidents/2026-10-21-source-universe/retained_raw_references.md"
REMOTE = Path("/Users/lightnino/Projects/edp-lab-incident/docs/incidents/evidence/800_remote_verification/objects.csv")
REMOTE_EVIDENCE = REMOTE.parent
ACTIVE = ROOT / "metadata/source_universes/approved/manifest.json"
EVIDENCE = ROOT / "metadata/source_universes/approved/verification.json"
PRIOR_BINDINGS = ROOT / "metadata/freezes/C2000_v1/C2000.bindings.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def field(block: str, pattern: str) -> str:
    match = re.search(pattern, block)
    if match is None:
        raise ValueError(f"Missing ledger field: {pattern}")
    return match.group(1)


def publish() -> dict:
    parent = json.loads(PARENT.read_bytes())
    decision = json.loads(DECISION.read_bytes())
    assert digest(PARENT) == decision["parent_manifest_sha256"]
    assert digest(LEDGER) == decision["new_member_set"]["source_reference_original_sha256"]
    assert decision["decision"] == "APPROVE_ALL_REFERENCED_RETAINED_800_FOR_PROSPECTIVE_UNIVERSE_V2"
    assert len(parent["members"]) == 3021
    artifact_digests = json.loads((REMOTE_EVIDENCE / "artifact_digests.json").read_bytes())
    validation = json.loads((REMOTE_EVIDENCE / "validation.json").read_bytes())
    assert digest(REMOTE) == artifact_digests["objects.csv"]
    assert (validation["status"], validation["objects"], validation["hash_match"],
            validation["size_match"], validation["bytes"]) == ("PASS", 800, 800, 800, 79225793)

    blocks = re.split(r"(?=^## SRC\d{6}$)", LEDGER.read_text(), flags=re.MULTILINE)[1:]
    remote_rows = list(csv.DictReader(REMOTE.open(newline="")))
    remote = {r["source_instance_id"]: r for r in remote_rows}
    assert len(blocks) == len(remote_rows) == len(remote) == 800
    prior_ids = {m["identity"] for m in parent["members"]}
    additions = []
    receipt_hashes = {}
    for block in blocks:
        sid = field(block, r"## (SRC\d{6})")
        identity = field(block, r"candidate: `([0-9a-f]{64})`")
        family = field(block, r"Family: `([^`]+)`")
        source_url = field(block, r"Publisher: (\S+)")
        raw_sha = field(block, r"RAW SHA-256: `([0-9a-f]{64})`")
        size = int(field(block, r"retained receipt bytes: (\d+)"))
        raw_path = field(block, r"Local: `([^`]+)`")
        remote_path = field(block, r"Remote: `([^`]+)`")
        acquisition_path = Path(field(block, r"Acquisition receipt: `([^`]+)`"))
        acquisition_sha = field(block, r"Acquisition receipt: `[^`]+`; expected SHA-256 `([0-9a-f]{64})`")
        receipt_path = Path(field(block, r"Remote receipt: `([^`]+)`"))
        receipt_sha = field(block, r"Remote receipt: `[^`]+`; SHA-256 `([0-9a-f]{64})`")
        assert identity not in prior_ids
        assert digest(acquisition_path) == acquisition_sha
        assert digest(receipt_path) == receipt_sha
        acquisition = json.loads(acquisition_path.read_bytes())
        receipt = json.loads(receipt_path.read_bytes())
        assert (acquisition["status"], acquisition["sha256"], acquisition["bytes"], acquisition["requested_url"]) == ("COMPLETE", raw_sha, size, source_url)
        assert (receipt["status"], receipt["source_instance_id"], receipt["sha256"], receipt["bytes"], receipt["remote"]) == ("REMOTE_READBACK_SHA256_PASS", sid, raw_sha, size, remote_path)
        readback = remote[sid]
        assert (readback["presence"], readback["size_match"], readback["read_size_match"], readback["hash_status"], readback["current_sha256"], int(readback["read_bytes"])) == ("PRESENT", "True", "True", "HASH_MATCH", raw_sha, size)
        additions.append({"identity": identity, "holdout": False, "raw_path": raw_path,
                          "raw_sha256": raw_sha, "raw_bytes": size,
                          "source_instance_id": sid, "source_family": family,
                          "publisher_url": source_url, "remote_raw_path": remote_path,
                          "acquisition_receipt_path": str(acquisition_path),
                          "acquisition_receipt_sha256": acquisition_sha,
                          "remote_receipt_path": str(receipt_path),
                          "remote_receipt_sha256": receipt_sha,
                          "independent_remote_readback_at": readback["read_completed_at"]})
        receipt_hashes[sid] = receipt_sha
    assert len({m["identity"] for m in additions}) == len({m["source_instance_id"] for m in additions}) == 800
    assert Counter(m["source_family"] for m in additions) == {"NOAA_GSOD": 300, "WORLD_BANK_WDI": 400, "TREASURY_ANNUAL_XML": 100}
    assert sum(m["raw_bytes"] for m in additions) == 79225793

    manifest = {k: v for k, v in parent.items() if k != "outside_universe_policy"}
    manifest.update({"approval_reference": str(DECISION.relative_to(ROOT)),
                     "universe_version": "2", "member_count": 3821,
                     "parent_manifest_sha256": digest(PARENT),
                     "expansion": {"owner_decision_sha256": digest(DECISION),
                                   "retained_reference_sha256": digest(LEDGER),
                                   "independent_remote_readback_sha256": digest(REMOTE),
                                   "new_member_count": 800, "new_raw_bytes": 79225793,
                                   "raw_uploads": 0},
                     "members": sorted([*parent["members"], *additions], key=lambda m: m["identity"])})
    assert len({m["identity"] for m in manifest["members"]}) == 3821
    assert sum(m["holdout"] for m in manifest["members"]) == 41
    previous = json.loads(PRIOR_BINDINGS.read_bytes())
    previous_ids = {row["source_identity"] for row in previous}
    assert len(previous) == len(previous_ids) == 2000
    assert previous_ids <= prior_ids
    assert not previous_ids & {m["identity"] for m in additions}
    assert not previous_ids & {m["identity"] for m in parent["members"] if m["holdout"]}
    assert len({m["identity"] for m in manifest["members"] if not m["holdout"]} - previous_ids) == 1780
    ACTIVE.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if ACTIVE.exists() and ACTIVE.read_bytes() != data:
        raise ValueError("Active manifest already exists with different bytes")
    ACTIVE.write_bytes(data)
    evidence = {"schema": "EDP_DAY7_UNIVERSE_PUBLICATION_RECONCILIATION_V1",
                "status": "LOCAL_RECONCILED_PROTECTED_READBACK_PENDING",
                "manifest_sha256": digest(ACTIVE), "owner_decision_sha256": digest(DECISION),
                "parent_manifest_sha256": digest(PARENT), "retained_reference_sha256": digest(LEDGER),
                "independent_remote_readback_sha256": digest(REMOTE),
                "c2000_bindings_sha256": digest(PRIOR_BINDINGS),
                "receipt_count": len(receipt_hashes), "members": 3821, "holdouts": 41,
                "eligible_after_c2000": 1780, "new_raw_bytes": 79225793, "raw_uploads": 0}
    EVIDENCE.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n")
    return evidence


if __name__ == "__main__":
    print(json.dumps(publish(), sort_keys=True))
