"""Verify frozen FSDS ZIP bytes, then inspect only each NUM physical header."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path


def probe(bindings_path: Path, raw_root: Path) -> dict:
    bindings = json.loads(bindings_path.read_bytes())
    sources = {}
    for binding in bindings:
        if "/sec_fsds/" not in binding["raw_path"]:
            continue
        path = Path(binding["raw_path"])
        path = path if path.is_absolute() else raw_root / path
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != binding["raw_sha256"]:
            raise ValueError("FSDS_RAW_HASH_CHANGED:" + binding["source_instance_id"])
        with zipfile.ZipFile(path) as archive:
            member = next((name for name in archive.namelist()
                           if name.rsplit("/", 1)[-1].lower() == "num.txt"), None)
            if member is None:
                raise ValueError("FSDS_NUM_MISSING:" + binding["source_instance_id"])
            with archive.open(member) as stream:
                header = stream.readline().decode("utf-8-sig").rstrip("\r\n").split("\t")
        sources[binding["source_instance_id"]] = {
            "raw_sha256": actual, "num_member": member, "physical_header": header}
    if len(sources) != 60:
        raise ValueError("FSDS_SOURCE_COUNT_CHANGED")
    patterns = Counter("\t".join(item["physical_header"]) for item in sources.values())
    return {"schema": "EDP_VAULT_FSDS_NUM_HEADER_PROBE_V1",
            "bindings_sha256": hashlib.sha256(bindings_path.read_bytes()).hexdigest(),
            "source_count": 60, "header_patterns": dict(patterns), "sources": sources}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bindings", type=Path)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = probe(args.bindings, args.raw_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and json.loads(args.output.read_bytes()) != result:
        raise ValueError("FSDS_HEADER_EVIDENCE_CHANGED")
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "patterns": result["header_patterns"]}, sort_keys=True))


if __name__ == "__main__":
    main()
