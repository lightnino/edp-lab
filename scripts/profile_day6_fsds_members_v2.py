"""Hash-verified FSDS physical-member/header inventory, without reprocessing rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


def profile(bindings_path: Path, raw_root: Path) -> dict:
    bindings = json.loads(bindings_path.read_bytes())
    sources = {}
    patterns: dict[str, Counter[str]] = defaultdict(Counter)
    for binding in bindings:
        if "/sec_fsds/" not in binding["raw_path"]:
            continue
        path = Path(binding["raw_path"])
        path = path if path.is_absolute() else raw_root / path
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != binding["raw_sha256"]:
                raise ValueError("FSDS_RAW_HASH_CHANGED:" + binding["source_instance_id"])
        members = {}
        with zipfile.ZipFile(path) as archive:
            for name in sorted(archive.namelist()):
                if not name.lower().endswith(".txt"):
                    continue
                with archive.open(name) as stream:
                    header = stream.readline().decode("utf-8-sig").rstrip("\r\n").split("\t")
                members[name] = {"header": header,
                                 "uncompressed_bytes": archive.getinfo(name).file_size}
                patterns[name]["\t".join(header)] += 1
        sources[binding["source_instance_id"]] = {
            "raw_sha256": binding["raw_sha256"], "members": members}
    if len(sources) != 60:
        raise ValueError("FSDS_SOURCE_COUNT_CHANGED")
    return {"schema": "EDP_VAULT_FSDS_MEMBER_INVENTORY_V2", "source_count": 60,
            "bindings_sha256": hashlib.sha256(bindings_path.read_bytes()).hexdigest(),
            "header_patterns": {name: dict(counts) for name, counts in sorted(patterns.items())},
            "sources": sources}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bindings", type=Path)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    value = profile(args.bindings, args.raw_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and json.loads(args.output.read_bytes()) != value:
        raise ValueError("FSDS_MEMBER_EVIDENCE_CHANGED")
    args.output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "member_header_variants": {
        name: len(counts) for name, counts in value["header_patterns"].items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
