"""Focused read-only accession inventory over frozen C1500 FSDS SUB members.

Usage: python scripts/day6_fsds_sub_accessions.py --raw-root /path/to/edp-lab \
  --registry /path/to/bindings.proposed.json
No RAW bytes are copied or written. Every ZIP and SUB member is SHA-verified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "metadata/freezes/C1500_v1/C1500.bindings.json"
FREEZE = ROOT / "metadata/freezes/C1500_v1/freeze.json"


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory(raw_root: Path, registry: Path) -> dict:
    frozen = json.loads(FREEZE.read_text())
    assert file_sha(ROSTER) == frozen["files_sha256"]["C1500.bindings.json"]
    roster = [row for row in json.loads(ROSTER.read_text())
              if "/sec_fsds/" in row["raw_path"]]
    bindings = {row["source_instance_id"]: row for row in
                json.loads(registry.read_text())["bindings"]
                if row["archive_member"] == "sub.txt"}
    assert len(roster) == len(bindings) == 60
    occurrences: dict[str, list[dict]] = defaultdict(list)
    source_counts: dict[str, int] = {}
    amendments = Counter()
    empty_adsh = 0
    for source in roster:
        sid = source["source_instance_id"]
        binding = bindings[sid]
        path = raw_root / source["raw_path"]
        assert file_sha(path) == source["raw_sha256"], sid + ": RAW SHA mismatch"
        assert binding["raw_sha256"] == source["raw_sha256"]
        member_sha = hashlib.sha256()
        with zipfile.ZipFile(path) as archive:
            assert archive.namelist().count("sub.txt") == 1, sid + ": ambiguous SUB member"
            with archive.open("sub.txt") as hash_stream:
                for block in iter(lambda: hash_stream.read(8 * 1024 * 1024), b""):
                    member_sha.update(block)
            assert member_sha.hexdigest() == binding["member_sha256"], sid + ": SUB SHA mismatch"
            member_sha = hashlib.sha256()
            stream = archive.open("sub.txt")
            with stream:
                header = stream.readline()
                member_sha.update(header)
                names = header.rstrip(b"\r\n").decode("utf-8").split("\t")
                assert names == binding["expected_header"]
                adsh_pos, form_pos = names.index("adsh"), names.index("form")
                count = 0
                for line_no, raw in enumerate(stream, 2):
                    member_sha.update(raw)
                    fields = raw.rstrip(b"\r\n").decode("utf-8").split("\t")
                    assert len(fields) == len(names), (sid, line_no)
                    adsh, form = fields[adsh_pos], fields[form_pos]
                    empty_adsh += not bool(adsh)
                    if form.endswith("/A"):
                        amendments[form] += 1
                    occurrences[adsh].append({"source_instance_id": sid, "source_line": line_no,
                                              "form": form})
                    count += 1
        assert member_sha.hexdigest() == binding["member_sha256"], sid + ": SUB SHA mismatch"
        source_counts[sid] = count
    repeated = {adsh: rows for adsh, rows in occurrences.items() if len(rows) > 1}
    cross = {adsh: rows for adsh, rows in repeated.items()
             if len({row["source_instance_id"] for row in rows}) > 1}
    return {"scope": "ALL_60_C1500_SEC_FSDS_SUB_MEMBERS", "sources": len(roster),
            "rows": sum(source_counts.values()), "distinct_adsh": len(occurrences),
            "empty_adsh": empty_adsh, "repeated_adsh_groups": len(repeated),
            "cross_delivery_adsh_groups": len(cross),
            "cross_delivery_witnesses": dict(sorted(cross.items())[:20]),
            "within_delivery_witnesses": dict(sorted(
                ((k, v) for k, v in repeated.items() if k not in cross))[:20]),
            "amendment_form_counts": dict(sorted(amendments.items())),
            "source_counts": source_counts,
            "source_roster_sha256": file_sha(ROSTER),
            "registry_sha256": file_sha(registry)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(inventory(args.raw_root, args.registry), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
