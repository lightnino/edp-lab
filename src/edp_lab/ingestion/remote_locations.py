"""Resolve remote RAW locations by immutable source identity, never by filenames.

This is a read-only receipt index, not evidence that an object is currently
available. LIVE SHA readback is still mandatory before processing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _receipts(evidence):
    """Accept the existing N750 qualification document or normalized receipt rows."""
    if isinstance(evidence, list):
        return evidence
    if "remote_reuse" in evidence:
        return evidence["remote_reuse"]
    return evidence["receipts"]


def resolve(roster, evidence):
    """Return one explicit remote locator outcome per approved physical source.

    A receipt must identify the *same* source_identity, SHA and byte count.
    Only existing, explicitly SHA-verified receipts are accepted. File basenames,
    cohort names, SRC numbers, directory order and local paths never infer the
    remote location.
    """
    _require(isinstance(roster, list), "INVALID_ROSTER")
    by_id = {}
    for source in roster:
        identity = source["source_identity"]
        _require(identity not in by_id, "DUPLICATE_SOURCE_IDENTITY")
        _require(len(source["raw_sha256"]) == 64 and
                 type(source["bytes"]) is int and source["bytes"] >= 0,
                 "INVALID_SOURCE_METADATA")
        by_id[identity] = source

    found = {}
    for receipt in _receipts(evidence):
        identity = receipt.get("source_identity")
        if identity not in by_id:
            continue
        source = by_id[identity]
        _require(receipt.get("raw_sha256") == source["raw_sha256"] and
                 receipt.get("bytes") == source["bytes"],
                 "REMOTE_RECEIPT_IDENTITY_MISMATCH")

        # Existing Day 3/4/5 verified receipts carry this exact basis. Future
        # upload receipts may use explicit remote status + actual SHA instead.
        legacy_verified = (receipt.get("basis") == "REUSED_PRIOR_REMOTE_READBACK"
                           and receipt.get("receipt") and
                           receipt.get("verified_at_utc"))
        live_verified = (receipt.get("remote_status") == "EXACT_REMOTE_BYTES_PASS"
                         and receipt.get("actual_sha256") == source["raw_sha256"])
        _require(legacy_verified or live_verified,
                 "REMOTE_RECEIPT_NOT_SHA_VERIFIED")
        remote = receipt.get("remote")
        _require(isinstance(remote, str) and
                 remote.startswith("dbfs:/Volumes/") and
                 ".." not in remote.split("/"),
                 "INVALID_REMOTE_LOCATOR")
        found.setdefault(identity, {})[remote] = {
            "remote": remote,
            "receipt": receipt.get("receipt"),
            "verified_at_utc": receipt.get("verified_at_utc"),
        }

    results = []
    for source in roster:
        identity = source["source_identity"]
        candidates = list(found.get(identity, {}).values())
        results.append({
            "source_identity": identity,
            "raw_sha256": source["raw_sha256"],
            "bytes": source["bytes"],
            "status": "RECEIPT_LOCATION_FOUND" if candidates else "UNRESOLVED",
            "remote_locations": sorted(candidates, key=lambda x: x["remote"]),
        })
    return {
        "schema": "REMOTE_LOCATION_INDEX_V1",
        "meaning": "Historical verified receipt locations, not current remote SHA readback",
        "selected": len(roster),
        "located": sum(bool(row["remote_locations"]) for row in results),
        "unresolved": sum(not row["remote_locations"] for row in results),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster", type=Path, required=True,
                        help="Source identity/SHA/bytes roster")
    parser.add_argument("--evidence", type=Path, action="append", required=True,
                        help="Verified receipts or a qualification packet; repeatable")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-complete", action="store_true",
                        help="Reject missing locators; use before remote processing")
    args = parser.parse_args()
    roster = json.loads(args.roster.read_bytes())
    receipts = []
    for path in args.evidence:
        receipts.extend(_receipts(json.loads(path.read_bytes())))
    index = resolve(roster, receipts)
    if args.require_complete and index["unresolved"]:
        parser.exit(2, f"REMOTE_LOCATIONS_UNRESOLVED: {index['unresolved']}\n")
    # Explicit output, never update a cohort/owner artifact and never overwrite.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(index, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"REMOTE_LOCATION_INDEX located={index['located']} "
          f"unresolved={index['unresolved']} output={args.output}")


if __name__ == "__main__":
    main()
