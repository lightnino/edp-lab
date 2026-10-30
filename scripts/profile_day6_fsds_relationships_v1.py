"""Bounded, hash-verified FSDS PRE/TAG/SUB relationship candidate probe."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

SOURCES = ("SRC000005", "SRC000054", "SRC000064")


def _rows(archive: zipfile.ZipFile, member: str):
    with archive.open(member) as raw:
        yield from csv.DictReader(io.TextIOWrapper(raw, encoding="latin-1", newline=""),
                                  delimiter="\t")


def profile(bindings_path: Path, raw_root: Path) -> dict:
    bindings = json.loads(bindings_path.read_bytes())
    lookup = {item["source_instance_id"]: item for item in bindings}
    sources = {}
    for sid in SOURCES:
        binding = lookup[sid]
        raw_path = raw_root / binding["raw_path"]
        with raw_path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != binding["raw_sha256"]:
                raise ValueError("FSDS_RAW_HASH_CHANGED:" + sid)
        with zipfile.ZipFile(raw_path) as archive:
            subs = Counter(row["adsh"] for row in _rows(archive, "sub.txt"))
            tags = Counter((row["tag"], row["version"])
                           for row in _rows(archive, "tag.txt"))
            contexts = Counter()
            pre_rows = 0
            orphan_adsh = 0
            orphan_tag = 0
            example_collision = None
            for row in _rows(archive, "pre.txt"):
                pre_rows += 1
                orphan_adsh += row["adsh"] not in subs
                orphan_tag += (row["tag"], row["version"]) not in tags
                context = tuple(row[field] for field in
                                ("adsh", "tag", "version", "report", "line",
                                 "stmt", "inpth", "rfile"))
                contexts[context] += 1
                if contexts[context] == 2 and example_collision is None:
                    example_collision = dict(row)
        sources[sid] = {
            "raw_sha256": binding["raw_sha256"],
            "sub_rows": sum(subs.values()), "duplicate_sub_adsh":
                sum(n - 1 for n in subs.values() if n > 1),
            "tag_rows": sum(tags.values()), "duplicate_tag_version":
                sum(n - 1 for n in tags.values() if n > 1),
            "pre_rows": pre_rows,
            "pre_orphan_adsh_rows": orphan_adsh,
            "pre_orphan_tag_version_rows": orphan_tag,
            "pre_full_context_collision_groups": sum(n > 1 for n in contexts.values()),
            "pre_full_context_extra_rows": sum(n - 1 for n in contexts.values()),
            "example_context_collision": example_collision,
        }
    return {"schema": "EDP_VAULT_FSDS_RELATIONSHIP_PROBE_V1",
            "scope": "THREE_ALREADY_ACCEPTED_PROTOTYPE_SOURCES_ONLY",
            "bindings_sha256": hashlib.sha256(bindings_path.read_bytes()).hexdigest(),
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
        raise ValueError("FSDS_RELATIONSHIP_EVIDENCE_CHANGED")
    args.output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    print(json.dumps({sid: {k: v for k, v in source.items()
                            if isinstance(v, int)}
                      for sid, source in value["sources"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
