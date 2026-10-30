"""Count hash-verified FSDS SUB/PRE/TAG rows without re-reading NUM records."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

MEMBERS = ("sub.txt", "pre.txt", "tag.txt")


def count(bindings_path: Path, raw_root: Path) -> dict:
    bindings = json.loads(bindings_path.read_bytes())
    totals = Counter()
    bad_widths = Counter()
    sources = {}
    for binding in bindings:
        if "/sec_fsds/" not in binding["raw_path"]:
            continue
        path = Path(binding["raw_path"])
        path = path if path.is_absolute() else raw_root / path
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != binding["raw_sha256"]:
                raise ValueError("FSDS_RAW_HASH_CHANGED:" + binding["source_instance_id"])
        counts = {}
        with zipfile.ZipFile(path) as archive:
            for member in MEMBERS:
                with archive.open(member) as raw:
                    reader = csv.reader(io.TextIOWrapper(raw, encoding="latin-1", newline=""),
                                        delimiter="\t")
                    header = next(reader)
                    rows = 0
                    bad = 0
                    for row in reader:
                        rows += 1
                        bad += len(row) != len(header)
                counts[member] = {"rows": rows, "bad_width": bad}
                totals[member] += rows
                bad_widths[member] += bad
        sources[binding["source_instance_id"]] = {
            "raw_sha256": binding["raw_sha256"], "members": counts}
    if len(sources) != 60:
        raise ValueError("FSDS_SOURCE_COUNT_CHANGED")
    return {"schema": "EDP_VAULT_FSDS_OTHER_MEMBER_COUNTS_V1",
            "bindings_sha256": hashlib.sha256(bindings_path.read_bytes()).hexdigest(),
            "source_count": 60, "member_rows": dict(sorted(totals.items())),
            "bad_width": dict(sorted(bad_widths.items())), "sources": sources}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bindings", type=Path)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    value = count(args.bindings, args.raw_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and json.loads(args.output.read_bytes()) != value:
        raise ValueError("FSDS_COUNT_EVIDENCE_CHANGED")
    args.output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "member_rows": value["member_rows"],
                      "bad_width": value["bad_width"]}, sort_keys=True))


if __name__ == "__main__":
    main()
