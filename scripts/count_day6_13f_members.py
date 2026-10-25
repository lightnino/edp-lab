"""Count hash-verified 13F physical member rows for Vault resource planning."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path


def count(bindings_path: Path, raw_root: Path) -> dict:
    bindings = json.loads(bindings_path.read_bytes())
    sources = {}
    totals = Counter()
    for binding in bindings:
        if "/sec_13f/" not in binding["raw_path"]:
            continue
        path = Path(binding["raw_path"])
        path = path if path.is_absolute() else raw_root / path
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != binding["raw_sha256"]:
                raise ValueError("13F_RAW_HASH_CHANGED:" + binding["source_instance_id"])
        member_rows = {}
        with zipfile.ZipFile(path) as archive:
            for member in sorted(name for name in archive.namelist()
                                 if name.upper().endswith(".TSV")):
                with archive.open(member) as raw:
                    reader = csv.reader(io.TextIOWrapper(raw, encoding="latin-1", newline=""),
                                        delimiter="\t")
                    header = next(reader)
                    rows = 0
                    bad_width = 0
                    for row in reader:
                        rows += 1
                        bad_width += len(row) != len(header)
                member_rows[member] = {"rows": rows, "bad_width": bad_width,
                                       "field_count": len(header)}
                totals[member] += rows
        sources[binding["source_instance_id"]] = {
            "raw_sha256": binding["raw_sha256"], "members": member_rows}
    if len(sources) != 42:
        raise ValueError("13F_SOURCE_COUNT_CHANGED")
    return {"schema": "EDP_VAULT_13F_MEMBER_COUNTS_V1", "source_count": 42,
            "bindings_sha256": hashlib.sha256(bindings_path.read_bytes()).hexdigest(),
            "member_rows": dict(sorted(totals.items())), "sources": sources}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bindings", type=Path)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = count(args.bindings, args.raw_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and json.loads(args.output.read_bytes()) != result:
        raise ValueError("13F_COUNT_EVIDENCE_CHANGED")
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "member_rows": result["member_rows"]}, sort_keys=True))


if __name__ == "__main__":
    main()
