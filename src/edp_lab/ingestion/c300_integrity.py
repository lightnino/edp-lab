"""Read-only integrity checks for an authorized C300 freeze and future expansion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from edp_lab.ingestion.c300_admission import (
    require,
    sealed,
    verify_nested,
    verify_registry,
)
from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.ingestion.source_identity import _csv_rows


def verify_freeze(root: Path, directory: Path, *, check_raw=False, expansion=None):
    root = root.resolve()
    directory = directory.resolve()
    lock = json.loads((directory / "freeze.json").read_bytes())
    require(lock["status"] == "FROZEN", "Missing completed freeze")
    require(set(lock["files"]) == {
        "C300.csv", "corpus_manifest_v3.csv", "review.json", "authorization.json"
    }, "Unexpected frozen file set")
    for name, digest in lock["files"].items():
        sealed(directory / name, digest)
    packet_path = directory / "review.json"
    packet = json.loads(packet_path.read_bytes())
    authority = json.loads((directory / "authorization.json").read_bytes())
    require(authority["admit_and_freeze"] is True, "Missing final authority")
    require(authority["packet_sha256"] == file_sha256(packet_path), "Approval packet mismatch")
    roster_path = directory / "C300.csv"
    require(file_sha256(roster_path) == packet["proposed_roster_sha256"]
            == authority["roster_sha256"], "Approved roster mismatch")
    ids = [r["source_instance_id"] for r in _csv_rows(roster_path, ("source_instance_id",))]
    members = packet["members"]
    require(len(ids) == len(set(ids)) == len(members) == 300, "C300 size mismatch")
    require(ids == [m["source_instance_id"] for m in members], "C300 membership changed")
    manifest = directory / "corpus_manifest_v3.csv"
    rows = verify_registry(root, manifest, check_raw=check_raw)
    by_id = {r["source_instance_id"]: r for r in rows}
    require(len(rows) == 304, "Unexpected admitted population")
    require({r["source_instance_id"] for r in rows if r["introduced_cohort"] == "C300"}
            == set(ids), "C300 introduction scope mismatch")
    for member in members:
        row = by_id[member["source_instance_id"]]
        require(row["raw_path"] == member["raw_path"]
                and row["raw_sha256"] == member["raw_sha256"]
                and row["source_family"] == member["family"]
                and row["admitted_at_utc"] == lock["frozen_at_utc"],
                "Frozen member identity mismatch")
    for rel, digest in packet["evidence"].items():
        sealed(root / rel, digest)
    active = json.loads((root / "runs/whole_lab/active-inventory.json").read_bytes())
    review = json.loads(Path(active["review_inventory"]).read_bytes())
    candidates = [m["candidate_id"] for m in members]
    require(review["candidate_selections"]["C300"]["candidate_ids"] == candidates,
            "Future draft replaced C300")
    verify_nested(review["candidate_selections"], candidates)
    if expansion is not None:
        verify_registry(root, expansion, check_raw=check_raw, frozen=manifest)
    return {"admission": "ADMITTED", "freeze": "FROZEN", "members": len(ids),
            "manifest_rows": len(rows), "raw_hashes": "PASS" if check_raw else "NOT_CHECKED",
            "evidence": "PASS", "nested_drafts": "PASS", "gold_preservation": "PASS",
            "frozen_at_utc": lock["frozen_at_utc"],
            "manifest_sha256": file_sha256(manifest),
            "roster_sha256": file_sha256(roster_path),
            "freeze_record_sha256": file_sha256(directory / "freeze.json")}


def verify_persisted_freeze(root: Path):
    """Verify canonical Git metadata without requiring local RAW or operational runs."""
    root = root.resolve()
    base = root / "metadata/freezes/C300_v1"
    refs = json.loads((base / "references.json").read_bytes())
    lock_path = sealed(base / "freeze.json", refs["freeze_sha256"])
    lock = json.loads(lock_path.read_bytes())
    require(lock["status"] == "FROZEN", "Canonical freeze incomplete")
    require(refs["canonical_files"] == {
        "C300.csv": "metadata/cohorts/C300.csv",
        "corpus_manifest_v3.csv": "metadata/corpus_manifest_v3.csv",
        "freeze.json": "metadata/freezes/C300_v1/freeze.json",
        "authorization.json": "metadata/freezes/C300_v1/authorization.json",
    }, "Unexpected canonical references")
    for name, rel in refs["canonical_files"].items():
        if name != "freeze.json":
            sealed(root / rel, lock["files"][name])
    require(refs["review_packet"]["sha256"] == lock["files"]["review.json"],
            "Review evidence reference changed")
    authority = json.loads((base / "authorization.json").read_bytes())
    require(authority["admit_and_freeze"] is True
            and authority["packet_sha256"] == lock["files"]["review.json"]
            and authority["roster_sha256"] == lock["files"]["C300.csv"],
            "Canonical authority mismatch")
    roster = _csv_rows(root / "metadata/cohorts/C300.csv", ("source_instance_id",))
    ids = [r["source_instance_id"] for r in roster]
    require(len(ids) == len(set(ids)) == 300, "Canonical C300 size changed")
    rows = verify_registry(root, root / "metadata/corpus_manifest_v3.csv")
    admitted = [r for r in rows if r["introduced_cohort"] == "C300"]
    require(len(rows) == 304 and [r["source_instance_id"] for r in admitted] == ids,
            "Canonical manifest/roster mismatch")
    require(all(r["admitted_at_utc"] == lock["frozen_at_utc"] for r in admitted),
            "Canonical admission time changed")
    return {"members": 300, "status": "FROZEN", "metadata": "PASS",
            "raw_hashes": "NOT_CHECKED", "operational_evidence": "REFERENCED_BY_HASH"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--directory", type=Path, default=Path("runs/c300/frozen-v1"))
    parser.add_argument("--check-raw", action="store_true")
    parser.add_argument("--expansion", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_freeze(args.root, args.directory, check_raw=args.check_raw,
                                   expansion=args.expansion), indent=2))


if __name__ == "__main__":
    main()
