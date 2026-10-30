"""Read-only, hash-verified structural witnesses for new C2000 Vault families."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree


def _resolve(raw_root: Path, binding: dict) -> Path:
    path = Path(binding["raw_path"])
    path = path if path.is_absolute() else raw_root / path
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != binding["raw_sha256"]:
        raise ValueError("RAW_SHA256_CHANGED:" + binding["source_instance_id"])
    return path


def _edgar(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        lines = stream.read().splitlines()
    header = "CIK|Company Name|Form Type|Date Filed|File Name"
    if lines[5] != header:
        raise ValueError("EDGAR_HEADER_CHANGED")
    rows = [line.split("|") for line in lines[7:] if line]
    if any(len(row) != 5 for row in rows):
        raise ValueError("EDGAR_WIDTH_CHANGED")
    paths = Counter(row[4] for row in rows)
    return {"header": header.split("|"), "data_rows": len(rows),
            "exact_duplicate_rows": len(rows) - len(set(map(tuple, rows))),
            "repeated_file_paths": sum(count > 1 for count in paths.values()),
            "blank_cik": sum(not row[0] for row in rows),
            "sample": rows[0] if rows else None}


def _tsv(archive: zipfile.ZipFile, name: str) -> tuple[list[str], list[list[str]], str]:
    payload = archive.read(name)
    records = list(csv.reader(payload.decode("utf-8-sig").splitlines(), delimiter="\t"))
    if not records:
        raise ValueError("EMPTY_MEMBER:" + name)
    return records[0], records[1:], hashlib.sha256(payload).hexdigest()


def _thirteen_f(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        sub_header, submissions, sub_sha = _tsv(archive, "SUBMISSION.tsv")
        info_header, facts, info_sha = _tsv(archive, "INFOTABLE.tsv")
    if ("ACCESSION_NUMBER" not in sub_header or "ACCESSION_NUMBER" not in info_header
            or "INFOTABLE_SK" not in info_header):
        raise ValueError("13F_REQUIRED_FIELDS_MISSING")
    sub_accessions = Counter(row[sub_header.index("ACCESSION_NUMBER")] for row in submissions)
    fact_accessions = Counter(row[info_header.index("ACCESSION_NUMBER")] for row in facts)
    sks = Counter(row[info_header.index("INFOTABLE_SK")] for row in facts)
    figi = info_header.index("FIGI")
    return {"members": {"SUBMISSION.tsv": sub_sha, "INFOTABLE.tsv": info_sha},
            "submission_header": sub_header, "infotable_header": info_header,
            "submission_rows": len(submissions), "infotable_rows": len(facts),
            "duplicate_submission_accessions": sum(n > 1 for n in sub_accessions.values()),
            "duplicate_infottable_sk_values": sum(n > 1 for n in sks.values()),
            "fact_accessions_without_submission": sorted(set(fact_accessions) - set(sub_accessions))[:10],
            "max_infottable_rows_per_accession": max(fact_accessions.values(), default=0),
            "blank_figi_rows": sum(not row[figi] for row in facts),
            "sample_submission": submissions[0] if submissions else None}


def _treasury(path: Path) -> dict:
    root = ElementTree.parse(path).getroot()
    entries = [item for item in root if item.tag.endswith("entry")]
    observed = []
    for entry in entries:
        fields = {child.tag.rsplit("}", 1)[-1]: child.text
                  for child in entry.iter() if child.tag.rsplit("}", 1)[-1].startswith(("NEW_DATE", "BC_"))}
        observed.append(fields)
    dates = Counter(row.get("NEW_DATE") for row in observed)
    fields = sorted(set().union(*(row.keys() for row in observed))) if observed else []
    return {"entry_rows": len(entries), "fields": fields,
            "duplicate_new_date_values": sum(n > 1 for n in dates.values()),
            "missing_new_date_rows": sum(not row.get("NEW_DATE") for row in observed),
            "missing_tenor_cells": sum(field not in row or row[field] in {None, ""}
                                       for row in observed for field in fields if field.startswith("BC_")),
            "sample": observed[0] if observed else None}


def probe(bindings_path: Path, raw_root: Path) -> dict:
    bindings = {item["source_instance_id"]: item for item in json.loads(bindings_path.read_bytes())}
    result = {}
    for source_id, inspect in (("SRC000065", _thirteen_f),
                               ("SRC000107", _edgar),
                               ("SRC010451", _treasury)):
        binding = bindings[source_id]
        result[source_id] = {"raw_sha256": binding["raw_sha256"],
                             "raw_path": binding["raw_path"],
                             "observation": inspect(_resolve(raw_root, binding))}
    return {"schema": "EDP_VAULT_FAMILY_STRUCTURAL_PROBE_V1",
            "scope": "THREE_HASH_VERIFIED_REPRESENTATIVES_ONLY", "sources": result}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bindings", type=Path)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = probe(args.bindings, args.raw_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and json.loads(args.output.read_bytes()) != result:
        raise ValueError("EXISTING_PROBE_CONFLICT")
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "sources": list(result["sources"])}, sort_keys=True))


if __name__ == "__main__":
    main()
