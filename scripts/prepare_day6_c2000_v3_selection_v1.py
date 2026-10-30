"""Prepare exact read-only V3 row selection from frozen hash-verified RAW.

This is a selection manifest, not a parser approval, signed grant or load.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

FSDS = ("SRC000005", "SRC000054", "SRC000064")
THIRTEEN_F = "SRC000065"
EDGAR = "SRC000107"
TREASURY = ("SRC010451", "SRC010452", "SRC010453", "SRC010454", "SRC010455")
LIMIT = 16


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                                     ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()


def _zip_selection(path: Path, members: tuple[str, ...]) -> dict:
    result = {}
    with zipfile.ZipFile(path) as archive:
        for member in members:
            with archive.open(member) as raw:
                reader = csv.reader(io.TextIOWrapper(raw, encoding="latin-1", newline=""),
                                    delimiter="\t")
                header = next(reader)
                selected = []
                for ordinal, row in enumerate(reader, 1):
                    if ordinal > LIMIT:
                        break
                    selected.append([ordinal, row])
            if len(selected) != LIMIT:
                raise ValueError("INSUFFICIENT_MEMBER_ROWS:" + member)
            result[member] = {"data_row_ordinals": [1, LIMIT],
                              "selection_kind": "INCLUSIVE_FIRST_N_DATA_ROWS",
                              "selected_data_rows": LIMIT, "header_sha256": _digest(header),
                              "selected_lexical_sha256": _digest(selected)}
    return result


def _with_13f_parents(path: Path, result: dict) -> dict:
    """Include the unique source-native Submission parent of each child row."""
    child_accessions = set()
    with zipfile.ZipFile(path) as archive:
        for member in result:
            if member == "SUBMISSION.tsv":
                continue
            with archive.open(member) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="latin-1", newline=""),
                                        delimiter="\t")
                for _, row in zip(range(LIMIT), reader):
                    child_accessions.add(row["ACCESSION_NUMBER"])
        with archive.open("SUBMISSION.tsv") as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="latin-1", newline=""),
                                    delimiter="\t")
            selected = []
            matched = {}
            for ordinal, row in enumerate(reader, 1):
                if ordinal <= LIMIT or row["ACCESSION_NUMBER"] in child_accessions:
                    selected.append([ordinal, list(row.values())])
                if row["ACCESSION_NUMBER"] in child_accessions:
                    matched[row["ACCESSION_NUMBER"]] = matched.get(row["ACCESSION_NUMBER"], 0) + 1
    if set(matched) != child_accessions or any(count != 1 for count in matched.values()):
        raise ValueError("THIRTEEN_F_SUBMISSION_PARENT_MISSING_OR_AMBIGUOUS")
    result["SUBMISSION.tsv"] = {
        "data_row_ordinals": [item[0] for item in selected],
        "selection_kind": "FIRST_N_PLUS_EXACT_CHILD_ACCESSION_PARENTS",
        "selected_data_rows": len(selected),
        "header_sha256": result["SUBMISSION.tsv"]["header_sha256"],
        "selected_lexical_sha256": _digest(selected),
        "selected_child_accessions": len(child_accessions),
    }
    return result


def _edgar_selection(path: Path) -> dict:
    rows = []
    seen = {}
    pair = None
    with path.open(encoding="latin-1") as stream:
        header_seen = False
        for line in stream:
            value = line.rstrip("\r\n")
            if not header_seen:
                if value.startswith("CIK|"):
                    header_seen = True
                continue
            if not value or value.startswith("-"):
                continue
            ordinal = len(rows) + 1
            rows.append(value)
            if value in seen and pair is None:
                pair = [seen[value], ordinal]
            seen.setdefault(value, ordinal)
    if pair is None:
        raise ValueError("EDGAR_DUPLICATE_WITNESS_MISSING")
    ordinals = sorted(set(range(1, LIMIT + 1)) | set(pair))
    selected = [[n, rows[n - 1]] for n in ordinals]
    return {"daily_master.idx": {"data_row_ordinals": ordinals,
                                  "duplicate_witness_pair": pair,
                                  "selected_data_rows": len(ordinals),
                                  "selected_lexical_sha256": _digest(selected),
                                  "profile_decode": "LATIN1_REVERSIBLE_BYTE_DISPLAY"}}


def _treasury_selection(path: Path) -> dict:
    root = ElementTree.parse(path).getroot()
    identity = [child.text.strip() for child in root
                if child.tag.endswith("}id") and child.text]
    if len(identity) != 1:
        raise ValueError("TREASURY_FEED_ID_AMBIGUOUS")
    entries = [element for element in root if element.tag.endswith("}entry")]
    if not entries:
        raise ValueError("TREASURY_ENTRIES_MISSING")
    payload = [[n, ElementTree.tostring(entry, encoding="unicode")]
               for n, entry in enumerate(entries, 1)]
    return {"atom.entry": {"data_row_ordinals": [1, len(entries)],
                           "selection_kind": "ALL_FROZEN_XML_ENTRIES",
                           "selected_data_rows": len(entries),
                           "selected_lexical_sha256": _digest(payload),
                           "feed_id": identity[0]}}


def prepare(bindings_path: Path, raw_root: Path) -> dict:
    bindings_raw = bindings_path.read_bytes()
    bindings = {item["source_instance_id"]: item for item in json.loads(bindings_raw)}
    selected_ids = (*FSDS, THIRTEEN_F, EDGAR, *TREASURY)
    result = {}
    for sid in selected_ids:
        binding = bindings[sid]
        path = raw_root / binding["raw_path"]
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != binding["raw_sha256"]:
                raise ValueError("FROZEN_RAW_HASH_CHANGED:" + sid)
        if sid in FSDS:
            members = _zip_selection(path, ("sub.txt", "tag.txt", "pre.txt"))
        elif sid == THIRTEEN_F:
            with zipfile.ZipFile(path) as archive:
                names = tuple(sorted(n for n in archive.namelist()
                                     if n.upper().endswith(".TSV")))
            if len(names) != 7:
                raise ValueError("THIRTEEN_F_MEMBER_COUNT_CHANGED")
            members = _with_13f_parents(path, _zip_selection(path, names))
        elif sid == EDGAR:
            members = _edgar_selection(path)
        else:
            members = _treasury_selection(path)
        result[sid] = {"raw_sha256": binding["raw_sha256"], "members": members}
    total = sum(item["selected_data_rows"] for source in result.values()
                for item in source["members"].values())
    if len(result) != 10 or total != 2047:
        raise ValueError("V3_SELECTION_LIMIT_CHANGED")
    return {"schema": "EDP_C2000_VAULT_V3_SELECTION_V1",
            "status": "PREPARED_NO_WRITE_AUTHORITY",
            "frozen_bindings_sha256": hashlib.sha256(bindings_raw).hexdigest(),
            "selected_source_count": len(result), "selected_data_rows": total,
            "accepted_fsds_num_prototype_reused_data_rows": 127,
            "sources": result}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bindings", type=Path)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    value = prepare(args.bindings, args.raw_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and json.loads(args.output.read_bytes()) != value:
        raise ValueError("V3_SELECTION_CHANGED")
    args.output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"sources": value["selected_source_count"],
                      "data_rows": value["selected_data_rows"]}))


if __name__ == "__main__":
    main()
