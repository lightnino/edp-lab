"""Offline C300 review and explicitly authorized, exclusive versioned publication."""

from __future__ import annotations

import argparse
import csv
import io
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.ingestion.gold_set import HEADERS, file_sha256
from edp_lab.ingestion.source_identity import MANIFEST, _csv_rows, verify_source_identity
from edp_lab.ingestion.whole_lab import capture_body, load_plan

VERSION = "C300_ADMISSION_V1"


def verify_registry(root, manifest, *, check_raw=False, frozen=None):
    """Validate additive REAL admissions; CONTROLLED requires a future reviewed version."""
    from edp_lab.ingestion.source_identity import ID_RE, SHA_RE, _safe_path

    rows = _csv_rows(manifest, HEADERS)
    old = _csv_rows(root / MANIFEST, HEADERS)
    require(rows[:len(old)] == old, "Historical GOLD rows changed")
    require(len({r["source_instance_id"] for r in rows}) == len(rows), "Duplicate source ID")
    require(len({r["raw_path"] for r in rows}) == len(rows), "Duplicate RAW path")
    for row in rows:
        require(ID_RE.fullmatch(row["source_instance_id"]), "Invalid source ID")
        require(SHA_RE.fullmatch(row["raw_sha256"]), "Invalid SHA-256")
        require(_safe_path(row["raw_path"]), "Invalid RAW path")
        require(row["status"] == "ADMITTED" and row["source_family"]
                and row["introduced_cohort"], "Missing admission scope")
        stamp = datetime.fromisoformat(row["admitted_at_utc"])
        require(row["admitted_at_utc"].endswith("Z") and stamp.utcoffset().total_seconds() == 0,
                "Invalid admission UTC")
        require(row["real_or_controlled"] == "REAL" and not row["variant_type"]
                and not row["parent_source_id"] and row["ground_truth_available"] == "FALSE",
                "Unsupported admission policy")
        if check_raw:
            path = (root / row["raw_path"]).resolve()
            require(path.is_relative_to((root / "data/raw").resolve()), "RAW escape")
            sealed(path, row["raw_sha256"])
    if frozen:
        protected = _csv_rows(frozen, HEADERS)
        indexed = {r["source_instance_id"]: r for r in rows}
        require(all(indexed.get(r["source_instance_id"]) == r for r in protected),
                "Frozen source replaced or changed")
    return rows



def require(condition, message):
    if not condition:
        raise ValueError(message)


def sealed(path, expected):
    require(file_sha256(path) == expected, f"Evidence hash mismatch: {path}")
    return path


def csv_bytes(fields, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def verify_nested(selections, selected):
    previous = selected
    for size in (700, 1500, 2000, 3000):
        current = selections[f"C{size}"]["candidate_ids"]
        require(len(current) == len(set(current)) == size, f"Invalid C{size} size")
        require(current[:len(previous)] == previous, f"Nested membership changed: C{size}")
        previous = current


def prepare(root: Path, output: Path):
    """Verify existing draft bytes and evidence; reserve IDs without admitting them."""
    root = root.resolve()
    active_path = root / "runs/whole_lab/active-inventory.json"
    active = json.loads(active_path.read_bytes())
    inventory_path = sealed(Path(active["inventory"]), active["inventory_sha256"])
    review_path = sealed(Path(active["review_inventory"]), active["review_inventory_sha256"])
    sealed(Path(active["mapping"]), active["mapping_sha256"])
    review = json.loads(review_path.read_bytes())
    directory = review_path.parent
    plan = load_plan(directory)
    require(plan["plan_sha256"] == review["plan_sha256"], "Review/plan mismatch")
    inventory = list(csv.DictReader(io.StringIO(inventory_path.read_text())))
    require(len(inventory) == 3021, "Active inventory size changed")
    by_delivery = {r["inventory_id"]: r for r in inventory}
    require(len(by_delivery) == len(inventory), "Duplicate inventory identity")
    entries = {r["inventory_id"]: r for r in review["entries"]}
    selected = review["candidate_selections"]["C300"]["candidate_ids"]
    require(len(selected) == len(set(selected)) == 300, "C300 must contain exactly 300")
    verify_nested(review["candidate_selections"], selected)
    verify_source_identity(root, check_raw=True)
    old = _csv_rows(root / MANIFEST, HEADERS)
    next_id = max(int(r["source_instance_id"][3:]) for r in old) + 1
    evidence = {str(p.relative_to(root)): file_sha256(p) for p in (
        active_path, inventory_path, review_path, Path(active["mapping"]),
        directory / "candidates.json", root / MANIFEST,
        root / "metadata/cohorts/GOLD_V1.csv", root / "metadata/cohorts/GOLD_V2.csv",
        root / "metadata/parsing_profiling_freeze_v2.json",
        root / "metadata/gold_set_logical_tables_v2.csv",
        root / "docs/source_instance_identity.md", root / "docs/corpus_admission_policy.md",
        root / "docs/evaluation_contract.md", Path(__file__).resolve())}
    members = []
    candidates = {c["candidate_id"]: c for c in plan["candidates"]}
    for index, candidate_id in enumerate(selected):
        entry = entries[candidate_id]
        require(entry["origin"] == "ACQUIRED", "Historical provenance needs review")
        record = entry["record"]
        candidate = record["candidate"]
        require(candidate == candidates[candidate_id], "Candidate/plan mismatch")
        require(record["plan_sha256"] == plan["plan_sha256"], "Delivery/plan mismatch")
        physical = by_delivery[entry["delivery_candidate_id"]]
        require(physical["status"] == "VERIFIED_CANDIDATE_FOR_ADMISSION_REVIEW",
                "Unresolved physical eligibility")
        body = capture_body(directory, record["capture"], candidate["url"])
        require(body == Path(physical["final_path"]), "Active path mismatch")
        require(body.is_relative_to(root / "data/raw"), "Not existing RAW")
        require(file_sha256(body) == physical["sha256"], "RAW hash mismatch")
        receipt_path = directory / record["capture"]["receipt"]
        receipt = json.loads(receipt_path.read_bytes())
        require(receipt.get("started_at_utc") and receipt.get("finished_at_utc"),
                "Missing retrieval time")
        require(record["inspection"].get("container_status",
                record["inspection"].get("physical_format_check")) == "PASS", "Inspection failed")
        require(physical["publisher_url"] == candidate["url"]
                and physical["publisher"] == candidate["publisher"]
                and physical["family"] == candidate["family"], "Publisher linkage mismatch")
        for p in (receipt_path, directory / f"delivery-{candidate_id}.json"):
            require(p.is_file(), f"Missing evidence: {p}")
            evidence[str(p.relative_to(root))] = file_sha256(p)
            if p.name.startswith("delivery-"):
                require(json.loads(p.read_bytes()) == record, "Retained delivery evidence changed")
        members.append({"source_instance_id": f"SRC{next_id + index:06d}",
                        "candidate_id": candidate_id, "delivery_id": entry["delivery_candidate_id"],
                        "publisher": candidate["publisher"], "family": candidate["family"],
                        "edition": candidate["edition"], "publisher_url": candidate["url"],
                        "raw_path": str(body.relative_to(root)), "raw_sha256": physical["sha256"],
                        "receipt": str(receipt_path.relative_to(root)),
                        "receipt_sha256": file_sha256(receipt_path),
                        "real_or_controlled": "REAL", "eligibility": "PASS"})
    for field in ("raw_path", "raw_sha256", "delivery_id", "publisher_url"):
        require(len({m[field] for m in members}) == 300, f"Equal/reused {field}: review required")
    require(not ({m['raw_path'] for m in members} & {r['raw_path'] for r in old}),
            "Existing admitted delivery requires ID reuse")
    all_hashes = Counter(r["sha256"] for r in inventory)
    require(all(all_hashes[m["raw_sha256"]] == 1 for m in members),
            "Equal hash elsewhere in Whole Lab: review required")
    for folder in (directory / "relocations", directory / "publisher-relocations"):
        for path in folder.glob("*.json"):
            evidence[str(path.relative_to(root))] = file_sha256(path)
    for capture in plan["captures"].values():
        for field in ("body", "receipt"):
            path = directory / capture[field]
            evidence[str(path.relative_to(root))] = file_sha256(path)
    template = list(old)
    for member in members:
        template.append(dict(zip(HEADERS, (member["source_instance_id"], member["family"],
            "PENDING_FINAL_AUTHORIZATION", "C300", member["raw_path"], member["raw_sha256"],
            "REAL", "", "", "FALSE", "", "PROPOSED"), strict=True)))
    write_new(output / "corpus_manifest_v3.proposed.csv", csv_bytes(HEADERS, template))
    roster = csv_bytes(("source_instance_id",),
                       [{"source_instance_id": m["source_instance_id"]} for m in members])
    write_new(output / "C300.proposed.csv", roster)
    write_new(output / "members.csv", csv_bytes(tuple(members[0]), members))
    packet = {"version": VERSION, "admission": "BLOCKED_PENDING_FINAL_AUTHORIZATION",
              "freeze": "NOT_FROZEN", "members": members, "evidence": evidence,
              "source_id_allocation": "Existing draft order, after maximum preserved GOLD ID",
              "publisher_counts": dict(Counter(m["publisher"] for m in members)),
              "family_counts": dict(Counter(m["family"] for m in members)),
              "REAL": 300, "CONTROLLED": 0, "unresolved_evidence": [],
              "nested_checks": {f"C{s}": "PASS" for s in (700, 1500, 2000, 3000)},
              "proposed_roster_sha256": file_sha256(output / "C300.proposed.csv"),
              "manifest_template": "Old rows unchanged; members REAL/FALSE, C300; actual UTC at admission",
              "proposed_manifest_sha256": file_sha256(output / "corpus_manifest_v3.proposed.csv"),
              "final_manifest_sha256": None}
    write_new(output / "review.json", encoded(packet))
    return packet


def freeze(root: Path, packet_path: Path, authorization: Path, output: Path):
    """Publish only against explicit authority naming the exact reviewed packet hash."""
    packet = json.loads(packet_path.read_bytes())
    authority = json.loads(authorization.read_bytes())
    require(authority.get("packet_sha256") == file_sha256(packet_path), "Authority scope mismatch")
    require(authority.get("admit_and_freeze") is True and authority.get("approved_by")
            and authority.get("authorization_text") and authority.get("authorized_at_utc"),
            "Explicit final authorization required")
    require(packet["version"] == VERSION and not packet["unresolved_evidence"], "Blocked packet")
    for rel, digest in packet["evidence"].items():
        sealed(root / rel, digest)
    members = packet["members"]
    require(len(members) == len({m['source_instance_id'] for m in members}) == 300,
            "Invalid reviewed membership")
    stamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    old = _csv_rows(root / MANIFEST, HEADERS)
    rows = list(old)
    for member in members:
        sealed(root / member["raw_path"], member["raw_sha256"])
        rows.append(dict(zip(HEADERS, (member["source_instance_id"], member["family"], stamp,
                                      "C300", member["raw_path"], member["raw_sha256"],
                                      "REAL", "", "", "FALSE", "", "ADMITTED"), strict=True)))
    require(len({r['source_instance_id'] for r in rows}) == len(rows), "Source ID collision")
    require(len({r['raw_path'] for r in rows}) == len(rows), "RAW path collision")
    require(not output.exists(), "Freeze destination already exists")
    output.mkdir(parents=True)
    write_new(output / "corpus_manifest_v3.csv", csv_bytes(HEADERS, rows))
    write_new(output / "C300.csv", csv_bytes(("source_instance_id",), [
        {"source_instance_id": m["source_instance_id"]} for m in members]))
    write_new(output / "review.json", packet_path.read_bytes())
    write_new(output / "authorization.json", authorization.read_bytes())
    verify_registry(root, output / "corpus_manifest_v3.csv", check_raw=True)
    lock = {"version": VERSION, "status": "FROZEN", "frozen_at_utc": stamp,
            "files": {p.name: file_sha256(p) for p in output.iterdir()},
            "expansion_rule": "Every expansion must retain all C300 IDs and exact manifest rows"}
    write_new(output / "freeze.json", encoded(lock))
    return lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "freeze"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--authorization", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.root, args.output)
        else:
            require(args.packet and args.authorization, "Packet and authorization required")
            result = freeze(args.root, args.packet, args.authorization, args.output)
        print(json.dumps({k: v for k, v in result.items() if k not in {"members", "evidence"}},
                         indent=2))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"FAIL {exc}\n")


if __name__ == "__main__":
    main()
