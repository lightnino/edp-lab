"""Join already verified source profiles into exact per-source candidate coverage.

No RAW reads or Databricks operations are performed. Input evidence hashes are
checked against explicit arguments so changed profiles cannot be used silently.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def _pinned(path: Path, sha: str) -> dict:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError("PROFILE_HASH_CHANGED:" + str(path))
    return json.loads(raw)


def assemble(root: Path) -> dict:
    run = root / "runs/day6-vault-pilot"
    model = _pinned(run / "model-fit-2000.json",
                    "f0db94486c7f5b3dd5db02133ee0c37e04a50f2438c1888ede660c66dc74f9be")
    family = _pinned(run / "family-d1-d5-profile-v2.json",
                     "356bf90e9fd0c230918fb6e30b6bbb3cb489abfa766772ca8a204d74f1834a50")
    fsds = _pinned(run / "fsds-other-member-counts-v1.json",
                   "9902a600301c372f4bb88c04b713c0a935194b793a6e0d9da0328c6cd5ba0ef7")
    thirteen = _pinned(run / "13f-member-counts-v1.json",
                       "2e497f0a431a906ab0a6e92a72dbd151a25d5e4e919fb9aad106bd00895300af")
    baseline_path = root / "metadata/baselines/O_C750_M2_v1.json"
    baseline = json.loads(baseline_path.read_bytes())
    num = {row["source_instance_id"]: row["records_data"]
           for row in baseline["scope"]["inventory"]}
    sources = {}
    totals = Counter()
    for sid, fit in sorted(model["sources"].items()):
        family_name = fit["family"]
        if family_name == "SEC_FSDS":
            members = {member: item["rows"] for member, item in
                       fsds["sources"][sid]["members"].items()}
            members["num.txt"] = num[sid]
            approved = ["num.txt"]
        elif family_name == "SEC_13F":
            members = {member: item["rows"] for member, item in
                       thirteen["sources"][sid]["members"].items()}
            approved = []
        elif family_name == "SEC_EDGAR_DAILY_MASTER":
            members = {"daily_master.idx":
                       family["sources"][sid]["observed"]["data_rows"]}
            approved = []
        elif family_name == "TREASURY_ANNUAL_XML":
            members = {"atom.entry":
                       family["sources"][sid]["observed"]["entry_rows"]}
            approved = []
        else:
            raise ValueError("UNEXPECTED_FAMILY:" + sid)
        for member, count in members.items():
            totals[family_name + "/" + member] += count
        sources[sid] = {
            "family": family_name, "raw_sha256": fit["raw_sha256"],
            "member_data_rows": dict(sorted(members.items())),
            "approved_business_members": approved,
            "other_members_status": "CANDIDATE_SEMANTICS_OWNER_REVIEW",
            "prototype_loaded_data_rows": {"SRC000005": 10, "SRC000054": 9,
                                           "SRC000064": 108}.get(sid, 0),
        }
    if len(sources) != 2000 or sum(totals.values()) != 321_150_341:
        raise ValueError("C2000_SOURCE_OR_DATA_TOTAL_CHANGED")
    return {"schema": "EDP_C2000_VAULT_FULL_SOURCE_COVERAGE_V2",
            "status": "CANDIDATE_MODEL_FIT_NOT_LOAD_AUTHORITY",
            "source_count": len(sources), "data_rows": sum(totals.values()),
            "member_totals": dict(sorted(totals.items())), "sources": sources,
            "input_sha256": {"model_fit": "f0db94486c7f5b3dd5db02133ee0c37e04a50f2438c1888ede660c66dc74f9be",
                             "family_profile": "356bf90e9fd0c230918fb6e30b6bbb3cb489abfa766772ca8a204d74f1834a50",
                             "fsds_other_counts": "9902a600301c372f4bb88c04b713c0a935194b793a6e0d9da0328c6cd5ba0ef7",
                             "13f_member_counts": "2e497f0a431a906ab0a6e92a72dbd151a25d5e4e919fb9aad106bd00895300af",
                             "num_baseline": hashlib.sha256(baseline_path.read_bytes()).hexdigest()}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    value = assemble(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and json.loads(args.output.read_bytes()) != value:
        raise ValueError("COVERAGE_ARTIFACT_CHANGED")
    args.output.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"sources": value["source_count"], "data_rows": value["data_rows"]}))


if __name__ == "__main__":
    main()
