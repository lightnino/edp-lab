"""Hash-verified physical-schema inventory and bounded D1-D5 candidate probes.

Reads frozen RAW bytes only. It never chooses a business key or writes Delta.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree


def _family(path: str) -> str | None:
    for marker, family in (("/sec_edgar_daily_master/", "SEC_EDGAR_DAILY_MASTER"),
                           ("/sec_13f/", "SEC_13F"),
                           ("/treasury_annual_xml/", "TREASURY_ANNUAL_XML")):
        if marker in path:
            return family
    return None


def _verified_path(raw_root: Path, binding: dict) -> Path:
    path = Path(binding["raw_path"])
    path = path if path.is_absolute() else raw_root / path
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != binding["raw_sha256"]:
        raise ValueError("RAW_HASH_CHANGED:" + binding["source_instance_id"])
    return path


def _edgar(path: Path) -> dict:
    header = None
    rows = 0
    bad_width = 0
    duplicate_rows = 0
    repeated_paths = 0
    seen_rows = set()
    paths = Counter()
    example = None
    # Latin-1 is a reversible byte display here; no source character-set
    # semantics or cleansing decision is made by this structural probe.
    with path.open(encoding="latin-1") as stream:
        for line in stream:
            value = line.rstrip("\r\n")
            if header is None:
                if value.startswith("CIK|"):
                    header = value.split("|")
                continue
            if value.startswith("-") or not value:
                continue
            fields = value.split("|")
            rows += 1
            bad_width += len(fields) != len(header)
            duplicate_rows += value in seen_rows
            seen_rows.add(value)
            if len(fields) == len(header):
                paths[fields[-1]] += 1
                if example is None:
                    example = fields
    if header is None:
        raise ValueError("EDGAR_HEADER_MISSING")
    repeated_paths = sum(count > 1 for count in paths.values())
    return {"header": header, "profile_decode": "LATIN1_BYTE_PRESERVING",
            "data_rows": rows, "bad_width": bad_width,
            "exact_duplicate_rows_within_file": duplicate_rows,
            "repeated_file_paths_within_file": repeated_paths,
            "example": example}


def _tsv_header(archive: zipfile.ZipFile, member: str) -> list[str]:
    with archive.open(member) as stream:
        return stream.readline().decode("utf-8-sig").rstrip("\r\n").split("\t")


def _thirteen_f(path: Path, *, deep: bool) -> dict:
    with zipfile.ZipFile(path) as archive:
        members = {name: _tsv_header(archive, name) for name in archive.namelist()
                   if name.upper().endswith(".TSV")}
        result = {"member_headers": members, "deep_profile": None}
        if not deep:
            return result
        for name in ("SUBMISSION.tsv", "INFOTABLE.tsv"):
            if name not in members:
                raise ValueError("13F_MEMBER_MISSING:" + name)
        with archive.open("SUBMISSION.tsv") as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""),
                                    delimiter="\t")
            submissions = Counter(row["ACCESSION_NUMBER"] for row in reader)
        facts = Counter()
        sks = set()
        duplicate_sk = 0
        blank_figi = 0
        rows = 0
        with archive.open("INFOTABLE.tsv") as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""),
                                    delimiter="\t")
            for row in reader:
                rows += 1
                facts[row["ACCESSION_NUMBER"]] += 1
                sk = row["INFOTABLE_SK"]
                duplicate_sk += sk in sks
                sks.add(sk)
                blank_figi += row["FIGI"] == ""
        result["deep_profile"] = {
            "submission_rows": sum(submissions.values()), "infotable_rows": rows,
            "duplicate_submission_accessions": sum(n > 1 for n in submissions.values()),
            "duplicate_infottable_sk_within_zip": duplicate_sk,
            "infotable_accessions_without_submission": len(set(facts) - set(submissions)),
            "max_infottable_rows_per_accession": max(facts.values(), default=0),
            "blank_figi_rows": blank_figi}
        return result


def _treasury(path: Path) -> dict:
    root = ElementTree.parse(path).getroot()
    entries = [node for node in root if node.tag.endswith("entry")]
    dates = Counter()
    fields = Counter()
    empty_cells = Counter()
    first = None
    date_field = None
    for entry in entries:
        properties = next((node for node in entry.iter()
                           if node.tag.rsplit("}", 1)[-1] == "properties"), None)
        if properties is None:
            raise ValueError("TREASURY_PROPERTIES_MISSING")
        values = {node.tag.rsplit("}", 1)[-1]: node.text
                  for node in properties if len(node) == 0}
        if date_field is None:
            date_field = next((name for name in ("NEW_DATE", "INDEX_DATE", "QUOTE_DATE")
                               if name in values), None)
        if first is None:
            first = values
        dates[values.get(date_field)] += 1
        fields.update(values.keys())
        empty_cells.update(key for key, value in values.items() if value in {None, ""})
    return {"entry_rows": len(entries), "fields": sorted(fields),
            "field_presence_counts": dict(sorted(fields.items())),
            "date_field": date_field,
            "duplicate_date_values_within_file": sum(n > 1 for n in dates.values()),
            "missing_date_rows": dates.get(None, 0) + dates.get("", 0),
            "missing_or_empty_cells_by_field": {
                key: len(entries) - count + empty_cells[key]
                for key, count in sorted(fields.items())
                if len(entries) - count + empty_cells[key]},
            "example": first}


def profile(bindings_path: Path, raw_root: Path) -> dict:
    bindings = json.loads(bindings_path.read_bytes())
    relevant = [item for item in bindings if _family(item["raw_path"])]
    thirteen = [item["source_instance_id"] for item in relevant
                if _family(item["raw_path"]) == "SEC_13F"]
    deep_13f = {thirteen[0], thirteen[len(thirteen) // 2], thirteen[-1]}
    sources = {}
    for binding in relevant:
        source_id = binding["source_instance_id"]
        family = _family(binding["raw_path"])
        path = _verified_path(raw_root, binding)
        observed = (_edgar(path) if family == "SEC_EDGAR_DAILY_MASTER" else
                    _thirteen_f(path, deep=source_id in deep_13f) if family == "SEC_13F" else
                    _treasury(path))
        sources[source_id] = {"family": family, "raw_sha256": binding["raw_sha256"],
                              "raw_path": binding["raw_path"], "observed": observed}
    if len(sources) != 1940:
        raise ValueError("SOURCE_SCOPE_CHANGED")
    families = Counter(row["family"] for row in sources.values())
    edgar = [row["observed"] for row in sources.values()
             if row["family"] == "SEC_EDGAR_DAILY_MASTER"]
    return {"schema": "EDP_VAULT_FAMILY_D1_D5_PROFILE_V2",
            "scope": "1940_FROZEN_NON_FSDS_SOURCES_HASH_VERIFIED_ALL_PHYSICAL_SCHEMAS",
            "bindings_sha256": hashlib.sha256(bindings_path.read_bytes()).hexdigest(),
            "family_counts": dict(families),
            "edgar_aggregate": {key: sum(row[key] for row in edgar) for key in
                                ("data_rows", "bad_width", "exact_duplicate_rows_within_file",
                                 "repeated_file_paths_within_file")},
            "deep_13f_source_ids": sorted(deep_13f), "sources": sources}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bindings", type=Path)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    value = profile(args.bindings, args.raw_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and json.loads(args.output.read_bytes()) != value:
        raise ValueError("PROFILE_EVIDENCE_CHANGED")
    args.output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "family_counts": value["family_counts"],
                      "edgar_aggregate": value["edgar_aggregate"],
                      "deep_13f_source_ids": value["deep_13f_source_ids"]}, sort_keys=True))


if __name__ == "__main__":
    main()
