"""Read-only, bounded FSDS NUM occurrence/replay and payload-hash probe.

The hashes are proposed Day 6 contract examples, not approved Vault keys.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "metadata/freezes/C1500_v1/C1500.bindings.json"
LINES = {"SRC000054": (337467,),
         "SRC000064": (3723826, 3723836, 3723930, 3723931)}


def digest(domain: str, parts: tuple[str | None, ...]) -> str:
    """SHA-256 of domain-separated, ordered length-prefixed UTF-8 values."""
    data = bytearray(b"EDP_VAULT_PROPOSAL_V1\x00")
    for value in (domain, *parts):
        if value is None:
            data.extend((0xFFFFFFFF).to_bytes(4, "big"))
        else:
            encoded = value.encode("utf-8")
            if len(encoded) >= 0xFFFFFFFF:
                raise ValueError("PART_TOO_LONG")
            data.extend(len(encoded).to_bytes(4, "big"))
            data.extend(encoded)
    return hashlib.sha256(data).hexdigest()


def occurrence_key(source_id: str, member: str, offset: int, length: int) -> str:
    return digest("SOURCE_OCCURRENCE", (source_id, member, str(offset), str(length)))


def payload_hashdiff(names: list[str], fields: list[str]) -> str:
    if len(names) != len(fields):
        raise ValueError("FIELD_WIDTH_MISMATCH")
    parts = [str(len(fields))]
    for ordinal, (name, value) in enumerate(zip(names, fields, strict=True), 1):
        parts.extend((str(ordinal), name, "PRESENT_EMPTY" if value == "" else "PRESENT_TEXT", value))
    return digest("FSDS_NUM_LEXICAL_PAYLOAD", tuple(parts))


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def probe(raw_root: Path, registry: Path) -> dict:
    freeze = json.loads((ROOT / "metadata/freezes/C1500_v1/freeze.json").read_text())
    assert file_sha(ROSTER) == freeze["files_sha256"]["C1500.bindings.json"]
    roster = {row["source_instance_id"]: row for row in json.loads(ROSTER.read_text())}
    bindings = {row["source_instance_id"]: row for row in
                json.loads(registry.read_text())["bindings"]
                if row["archive_member"] == "num.txt"}
    result = {}
    for source_id, wanted in LINES.items():
        source, binding = roster[source_id], bindings[source_id]
        path = raw_root / source["raw_path"]
        assert file_sha(path) == source["raw_sha256"] == binding["raw_sha256"]
        captured = []
        member_sha = hashlib.sha256()
        offset = 0
        with zipfile.ZipFile(path) as archive, archive.open("num.txt") as stream:
            for line_no, raw in enumerate(stream, 1):
                member_sha.update(raw)
                if line_no in wanted:
                    fields = raw.removesuffix(b"\n").removesuffix(b"\r").decode("utf-8").split("\t")
                    row = {"source_line": line_no, "byte_offset": offset,
                                     "byte_length": len(raw), "record_sha256": hashlib.sha256(raw).hexdigest(),
                                     "occurrence_key": occurrence_key(source_id, "num.txt", offset, len(raw)),
                                     "literal_tab_fields": len(fields)}
                    if len(fields) == len(binding["expected_header"]):
                        row.update({"payload_hashdiff": payload_hashdiff(binding["expected_header"], fields),
                                    "adsh": fields[0], "tag": fields[1], "version": fields[2],
                                    "ddate": fields[3], "qtrs": fields[4], "uom": fields[5],
                                    "segments": fields[6], "coreg": fields[7], "value": fields[8],
                                    "footnote": fields[9]})
                    else:
                        row["payload_status"] = "WIDTH_MISMATCH_SIMPLE_SPLIT_USE_PINNED_M1"
                    captured.append(row)
                offset += len(raw)
        assert len(captured) == len(wanted)
        assert member_sha.hexdigest() == binding["member_sha256"]
        result[source_id] = {"raw_sha256": source["raw_sha256"],
                             "member_sha256": member_sha.hexdigest(), "observations": captured}
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    args = parser.parse_args()
    first, second = probe(args.raw_root, args.registry), probe(args.raw_root, args.registry)
    assert first == second, "REPLAY_CHANGED"
    print(json.dumps({"status": "BOUNDED_REPLAY_IDENTICAL", "run_ids_excluded_from_identity": True,
                      "scope": LINES, "sources": first}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
