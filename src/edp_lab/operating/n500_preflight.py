"""Fail-closed, *proposal-only* N500 -> C2000 membership preflight.

Verifies signed-off historical metadata and Universe membership, NOT physical
RAW or remote Databricks readback. It cannot issue owner approvals, sign grants,
create a cohort freeze or select a roster on its own.
"""

import argparse
import csv
import io
import json
import re
from pathlib import Path

from edp_lab.operating.authority import Denied, canonical, digest, file_digest

_HEX = re.compile(r"[0-9a-f]{64}\Z")
_SRC = re.compile(r"SRC[0-9]{6}\Z")
_V1 = "metadata/source_universes/approved_v1"
_OLD = "metadata/freezes/C1500_v1"


def _file(root: Path, rel: str) -> Path:
    path = (root / rel).resolve(strict=True)
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise Denied("PREFLIGHT_EVIDENCE_OUTSIDE_REPO")
    return path


def _json(root: Path, rel: str):
    return json.loads(_file(root, rel).read_bytes())


def _members(path: Path) -> list[str]:
    reader = csv.reader(io.StringIO(path.read_text(encoding="utf-8")))
    rows = list(reader)
    if not rows or rows[0] != ["source_instance_id"]:
        raise Denied("C1500_CSV_FORMAT_INVALID")
    result = [row[0] for row in rows[1:] if len(row) == 1]
    if len(result) != len(rows) - 1 or len(set(result)) != len(result):
        raise Denied("C1500_CSV_MEMBERSHIP_INVALID")
    return result


def _raw_path_matches(authority: str, proposed: str) -> bool:
    """An old relative repository RAW path may match pinned absolute inventory."""
    if not isinstance(authority, str) or not isinstance(proposed, str):
        return False
    if ".." in Path(proposed).parts or ".." in Path(authority).parts:
        return False
    return authority == proposed or (
        not Path(proposed).is_absolute() and authority.endswith("/" + proposed))


def _binding(item, universe, *, exclude, used_ids):
    expected = {"source_instance_id", "source_identity", "raw_sha256", "raw_path"}
    if not isinstance(item, dict) or set(item) != expected:
        raise Denied("INVALID_BINDING_SCHEMA")
    sid, identity, sha, raw_path = (
        item["source_instance_id"], item["source_identity"],
        item["raw_sha256"], item["raw_path"])
    if (not isinstance(sid, str) or not _SRC.fullmatch(sid)
            or not isinstance(identity, str) or not _HEX.fullmatch(identity)
            or not isinstance(sha, str) or not _HEX.fullmatch(sha)):
        raise Denied("INVALID_SOURCE_IDENTITY")
    if sid in used_ids:
        raise Denied("DUPLICATE_REGISTERED_SOURCE_ID")
    if identity in exclude:
        raise Denied("DUPLICATE_PHYSICAL_SOURCE")
    member = universe.get(identity)
    if member is None:
        raise Denied("OUT_OF_UNIVERSE_SOURCE")
    if member["holdout"]:
        raise Denied("PROTECTED_HOLDOUT_SOURCE")
    if sha != member["raw_sha256"] or not _raw_path_matches(member["raw_path"], raw_path):
        raise Denied("UNIVERSE_RAW_BINDING_MISMATCH")
    used_ids.add(sid)
    exclude.add(identity)
    return item


def prepare_n500_review(root: Path, candidate_bindings: list, *,
                        baseline_count: int = 1500, increment_count: int = 500) -> dict:
    """Generate a reproducible review packet, NEVER an admission or grant."""
    root = root.resolve()
    unipath = f"{_V1}/manifest.json"
    approved = _json(root, unipath)
    owner = _json(root, f"{_V1}/owner_authorization.json")
    universe_sha = file_digest(_file(root, unipath))
    if (approved.get("schema") != "SOURCE_UNIVERSE_AUTHORITY_V1"
            or approved.get("universe_version") != "1"
            or approved.get("member_count") != len(approved.get("members", []))
            or owner.get("schema") != "SOURCE_UNIVERSE_OWNER_APPROVAL_V1"
            or owner.get("status") != "APPROVED"
            or owner.get("manifest_sha256") != universe_sha
            or approved.get("approval_reference") != f"{_V1}/owner_authorization.json"):
        raise Denied("UNIVERSE_APPROVAL_MISMATCH")
    members = approved["members"]
    univ = {m["identity"]: m for m in members}
    if len(univ) != len(members):
        raise Denied("UNIVERSE_IDENTITY_DUPLICATE")
    if approved["member_count"] != 3021:
        raise Denied("UNIVERSE_BASELINE_CHANGED")
    freeze = _json(root, f"{_OLD}/freeze.json")
    old_csv = f"{_OLD}/C1500.csv"
    old_bindings = f"{_OLD}/C1500.bindings.json"
    if (freeze.get("schema") != "COMBINED_COHORT_FREEZE_V1"
            or freeze.get("status") != "FROZEN"
            or freeze.get("cohort") != "C1500"
            or freeze.get("universe", {}).get("universe_manifest_sha256") != universe_sha
            or freeze.get("files_sha256", {}).get("C1500.csv") != file_digest(
                _file(root, old_csv))
            or freeze.get("files_sha256", {}).get("C1500.bindings.json") != file_digest(
                _file(root, old_bindings))):
        raise Denied("PRIOR_COHORT_FREEZE_INVALID")
    old_ids = _members(_file(root, old_csv))
    old = _json(root, old_bindings)
    if (not isinstance(old, list) or len(old) != baseline_count
            or len(old_ids) != baseline_count
            or [o.get("source_instance_id") for o in old] != old_ids):
        raise Denied("PRIOR_COHORT_ROSTER_MISMATCH")
    used_ids, physical = set(), set()
    for item in old:
        _binding(item, univ, exclude=physical, used_ids=used_ids)
    if not isinstance(candidate_bindings, list) or len(candidate_bindings) != increment_count:
        raise Denied("N500_EXACT_COUNT_REQUIRED")
    proposed = []
    for item in candidate_bindings:
        proposed.append(_binding(item, univ, exclude=physical, used_ids=used_ids))
    combined_ids = old_ids + [item["source_instance_id"] for item in proposed]
    if len(set(combined_ids)) != baseline_count + increment_count:
        raise Denied("C2000_SOURCE_ID_DUPLICATE")
    return {
        "schema": "EDP_N500_C2000_OWNER_REVIEW_PACKET_V1",
        "status": "PROPOSED_NOT_AUTHORIZED",
        "prior_cohort": "C1500",
        "proposed_cohort": "C2000",
        "existing_count": baseline_count,
        "additional_count": increment_count,
        "combined_count": len(combined_ids),
        "universe_manifest_sha256": universe_sha,
        "universe_approval_sha256": file_digest(_file(root, f"{_V1}/owner_authorization.json")),
        "frozen_c1500_members_sha256": file_digest(_file(root, old_csv)),
        "frozen_c1500_bindings_sha256": file_digest(_file(root, old_bindings)),
        "n500_binding_sha256": digest(canonical(candidate_bindings)),
        "combined_membership_sha256": digest(canonical(combined_ids)),
        "source_families": "NOT_DETERMINED_BY_THIS_PREFLIGHT",
        "authorization": "NOT_GRANTED",
        "raw_bytes_verified": False,
        "databricks_raw_readback_verified": False,
        "processing_contract_reviewed": False,
        "unresolved_next_gates": [
            "INDEPENDENT_LOCAL_AND_REMOTE_RAW_SHA_READBACK",
            "COMPLETE_REGISTERED_SOURCE_IDENTITY_EVIDENCE",
            "B1_MODEL_ROUTE_AND_PARSER_RULE_REVIEW",
            "OWNER_COHORT_ADMISSION_AND_FREEZE",
            "EXTERNAL_SIGNED_WORKFLOW_GRANT",
            "DATABRICKS_RUNTIME_AND_RESULT_VERIFICATION",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_bindings", type=Path,
                        help="exact reviewed N500 source bindings JSON; never auto-generated")
    parser.add_argument("output", type=Path, help="exclusive proposal report path")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    bindings = json.loads(args.candidate_bindings.read_bytes())
    review = prepare_n500_review(root, bindings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as output:
        output.write(canonical(review))
    print(json.dumps({"status": review["status"],
                      "proposed_members": review["additional_count"],
                      "review_packet": str(args.output)}))


if __name__ == "__main__":
    main()
