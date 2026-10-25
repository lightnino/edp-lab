"""Read-only RAW-vs-C300 lexical forensics for frozen SRC000065/COVERPAGE.tsv.

Use exact original latin-1 csv.reader selected by the frozen V3 manifest and
the accepted M1 Delta VERSION AS OF 0. Never mutate RAW, manifests, protected
state or Databricks; never print source lexical values.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import zipfile
from collections import Counter
from pathlib import Path

from owner_day6_v3_diagnose_lexical import SELECTION, bindings, selected_rows
from owner_day6_v3_one_shot import ROOT, require

from edp_lab.vault.v3_spark_runtime import _digest, _ordinals

SOURCE_ID = "SRC000065"
MEMBER = "COVERPAGE.tsv"
FROZEN_BINDINGS = ROOT / "metadata/freezes/C2000_v1/C2000.bindings.json"
EXPECTED_FROZEN_BINDING_SHA = (
    "2a72b8f8483e2181a3112a26b5d68d702b92308def6e74978838b155cfd85312"
)
EXPECTED_SELECTION_SHA = (
    "5b84f0a1dc088affc51f631bc34c66f0053b871b67efff13e770021a19a33259"
)


def _candidate_paths(raw_path: Path) -> list[Path]:
    """Locate a physical RAW delivery without copying it into the prototype.

    The C2000 freeze is authoritative for identity; these are *locations only*.
    A candidate is never trusted or opened as source evidence until SHA matches.
    """
    override = os.environ.get("EDP_DAY6_FROZEN_RAW_ZIP")
    if override:
        explicit = Path(override).expanduser()
        require(explicit.is_absolute(), "COVERPAGE_RAW_OVERRIDE_NOT_ABSOLUTE")
        return [explicit]

    filename = raw_path.name
    locations = [ROOT / raw_path]
    # Other local edp-lab checkouts may contain the original large RAW corpus.
    for sibling in sorted(ROOT.parent.iterdir()):
        if not sibling.is_dir() or not sibling.name.startswith("edp-lab"):
            continue
        locations.extend((
            sibling / raw_path,
            sibling / "data/raw/sec" / filename,
            sibling / "data/raw/sec/sec_13f" / filename,
        ))
        # Frozen deliveries can be stored under their source-identity
        # directory or re-homed; scan only the SEC 13F RAW subtree.
        root13f = sibling / "data/raw/sec/sec_13f"
        if root13f.is_dir():
            locations.extend(sorted(root13f.glob("*/" + filename)))
    # sudo runs as root; derive the Owner home from the reviewed project
    # location rather than accidentally looking in /var/root/Downloads.
    downloads = ROOT.parent.parent / "Downloads"
    locations.append(downloads / filename)
    return list(dict.fromkeys(locations))


def _verified_source_location(raw_path: Path, expected_sha: str) -> Path:
    candidates = _candidate_paths(raw_path)
    seen = 0
    for path in candidates:
        if not path.is_file():
            continue
        seen += 1
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() == expected_sha:
                return path
    if os.environ.get("EDP_DAY6_FROZEN_RAW_ZIP"):
        raise RuntimeError("COVERPAGE_EXPLICIT_RAW_SHA_OR_LOCATION_INVALID")
    raise RuntimeError(
        "COVERPAGE_VERIFIED_LOCAL_RAW_NOT_FOUND:"
        f"matching_candidates=0 scanned_existing_files={seen};"
        " original source ZIP must be located or restored unchanged;"
        " set EDP_DAY6_FROZEN_RAW_ZIP=/absolute/path/2013q3_form13f.zip"
        " only for a SHA-matching original"
    )


def source_path() -> tuple[Path, str]:
    require(hashlib.sha256(FROZEN_BINDINGS.read_bytes()).hexdigest() ==
            EXPECTED_FROZEN_BINDING_SHA, "COVERPAGE_FROZEN_BINDINGS_CHANGED")
    frozen = json.loads(FROZEN_BINDINGS.read_bytes())
    matches = [x for x in frozen if x["source_instance_id"] == SOURCE_ID]
    require(len(matches) == 1, "COVERPAGE_FROZEN_SOURCE_BINDING_COUNT_CHANGED")
    binding = matches[0]
    raw_path = Path(binding["raw_path"])
    require(not raw_path.is_absolute() and ".." not in raw_path.parts
            and "data" in raw_path.parts and "raw" in raw_path.parts
            and raw_path.name == "2013q3_form13f.zip",
            "COVERPAGE_FROZEN_RAW_PATH_UNEXPECTED")
    path = _verified_source_location(raw_path, binding["raw_sha256"])
    return path, binding["raw_sha256"]


def raw_selected(path: Path, expected_ordinals: list[int]) -> tuple[list[str], list[tuple[int, list[str]]]]:
    # Byte-exact same CSV decoding used in the original frozen selection generator.
    require(expected_ordinals == list(range(1, 17)),
            "COVERPAGE_SELECTION_ORDINALS_CHANGED")
    with zipfile.ZipFile(path) as archive, archive.open(MEMBER) as stream:
        reader = csv.reader(io.TextIOWrapper(
            stream, encoding="latin-1", newline=""), delimiter="\t")
        header = next(reader)
        raw_rows = [(ordinal, row) for ordinal, row in zip(
            expected_ordinals, (next(reader) for _ in expected_ordinals), strict=True)]
    require(len(raw_rows) == 16
            and all(len(fields) == len(header) for _, fields in raw_rows),
            "COVERPAGE_RAW_WIDTH_OR_COUNT_CHANGED")
    return header, raw_rows


def classified_change(raw: str, c300: str) -> str:
    """Shape-only diagnosis; never returns user data."""
    if raw == c300:
        return "MATCH"
    if raw.strip() == c300.strip():
        return "SURROUNDING_WHITESPACE"
    if raw.replace("\r\n", "\n").replace("\r", "\n") == (
        c300.replace("\r\n", "\n").replace("\r", "\n")
    ):
        return "LINE_ENDINGS"
    if raw.replace('"', "") == c300.replace('"', ""):
        return "QUOTE_CHARACTERS"
    if raw.replace("\t", " ") == c300.replace("\t", " "):
        return "TAB_VS_SPACE"
    if raw == '"' + c300 + '"' or c300 == '"' + raw + '"':
        return "EXTERNAL_QUOTE_WRAPPING"
    return "OTHER_LEXICAL_DIFFERENCE"


def _quoted_csv_cell_equivalent(raw: str, physical: str) -> bool:
    """Exact semantic test, not quote stripping or a normalization policy.

    Require a single, physically quoted TSV cell whose standard CSV decoding
    yields exactly the independently verified frozen RAW csv.reader value.
    """
    if (not isinstance(raw, str) or not isinstance(physical, str)
            or len(physical) < 2
            or not physical.startswith('"') or not physical.endswith('"')
            or '""' not in physical or "\t" in physical
            or "\n" in physical or "\r" in physical):
        return False
    try:
        parsed = list(csv.reader([physical], delimiter="\t", strict=True))
    except csv.Error:
        return False
    return (len(parsed) == 1 and len(parsed[0]) == 1
            and parsed[0][0] == raw)


def quote_equivalence(
    headers: list[str],
    raw_rows: list[tuple[int, list[str]]],
    c300_rows: list[tuple[int, list[dict], int, int]],
) -> dict:
    """Classify only the 7th-row/21st-field difference without exposing data."""
    differences = []
    for (ordinal, original), (observed_ordinal, fields, _, _) in zip(
        raw_rows, c300_rows, strict=True
    ):
        require(ordinal == observed_ordinal
                and len(original) == len(fields) == 21
                and len(headers) == 21,
                "COVERPAGE_CSV_PROOF_SHAPE_CHANGED")
        for index, (raw, field) in enumerate(zip(original, fields, strict=True), 1):
            c300 = field["lexical_value"]
            if raw != c300:
                differences.append((ordinal, index, raw, c300))
    exact_only = len(differences) == 1 and differences[0][:2] == (7, 21)
    equivalent = (
        exact_only
        and headers[20] == "ADDITIONALINFORMATION"
        and _quoted_csv_cell_equivalent(differences[0][2], differences[0][3])
    )
    return {
        "only_difference_is_coverpage_row7_field21": exact_only,
        "physical_quoted_field_csv_decode_equals_frozen_raw": bool(equivalent),
        "normalization_scope": "SRC000065/COVERPAGE.tsv/row7/field21",
        "no_frozen_hash_or_c300_record_mutated": True,
    }


def diff_summary(
    headers: list[str],
    raw_rows: list[tuple[int, list[str]]],
    c300_rows: list[tuple[int, list[dict], int, int]],
) -> dict:
    """Compare every ordinal and field, return metadata only, never raw values."""
    require([r[0] for r in raw_rows] == [r[0] for r in c300_rows],
            "COVERPAGE_RAW_M1_ORDINALS_CHANGED")
    require(len(raw_rows) == len(c300_rows) == 16,
            "COVERPAGE_ROW_COUNT_CHANGED")
    require(all([field["original_name"] for field in fields] == headers
                and [field["field_ordinal"] for field in fields] ==
                list(range(1, len(headers) + 1))
                for _, fields, _, _ in c300_rows),
            "COVERPAGE_M1_HEADER_OR_FIELD_ORDINAL_CHANGED")
    classes = Counter()
    columns = Counter()
    ordinals = Counter()
    examples = []
    for (ordinal, original), (_, converted, _, _) in zip(
        raw_rows, c300_rows, strict=True
    ):
        require(len(original) == len(converted) == len(headers),
                "COVERPAGE_FIELDS_WIDTH_CHANGED")
        for index, (left, field) in enumerate(zip(
            original, converted, strict=True
        )):
            right = field["lexical_value"]
            require(isinstance(right, str), "COVERPAGE_NONLEXICAL_VALUE")
            if left == right:
                continue
            kind = classified_change(left, right)
            classes[kind] += 1
            columns[index + 1] += 1
            ordinals[ordinal] += 1
            if len(examples) < 24:
                examples.append({
                    "row_ordinal": ordinal,
                    "field_ordinal": index + 1,
                    "column_name": headers[index],
                    "difference_kind": kind,
                    "raw_length": len(left),
                    "c300_length": len(right),
                    "raw_quotation_marks": left.count('"'),
                    "c300_quotation_marks": right.count('"'),
                    "raw_newlines": left.count("\n"),
                    "c300_newlines": right.count("\n"),
                })
    return {
        "differing_cells": sum(classes.values()),
        "differing_rows": len(ordinals),
        "classes": dict(sorted(classes.items())),
        "mismatch_count_by_column_ordinal": dict(sorted(columns.items())),
        "mismatch_count_by_row_ordinal": dict(sorted(ordinals.items())),
        "first_24_metadata_only_differences": examples,
    }


def diagnose() -> None:
    require(hashlib.sha256(SELECTION.read_bytes()).hexdigest() ==
            EXPECTED_SELECTION_SHA, "COVERPAGE_SELECTION_SHA_CHANGED")
    selection = json.loads(SELECTION.read_bytes())
    spec = selection["sources"][SOURCE_ID]["members"][MEMBER]
    ordinals = _ordinals(spec)
    path, actual_raw_sha = source_path()
    require(actual_raw_sha == selection["sources"][SOURCE_ID]["raw_sha256"],
            "COVERPAGE_RAW_VS_SELECTION_SHA_CHANGED")
    header, original = raw_selected(path, ordinals)
    expected = spec["selected_lexical_sha256"]
    raw_sha = _digest([[ordinal, values] for ordinal, values in original])
    require(raw_sha == expected, "COVERPAGE_FROZEN_SELECTION_NOT_REPRODUCIBLE")
    require(_digest(header) == spec["header_sha256"],
            "COVERPAGE_FROZEN_HEADER_NOT_REPRODUCIBLE")
    found = bindings(selection)
    table, binding = found[SOURCE_ID, MEMBER]
    remote = selected_rows(table, binding, ordinals)
    actual = _digest([[ordinal, [f["lexical_value"] for f in fields]]
                      for ordinal, fields, _, _ in remote])
    summary = diff_summary(header, original, remote)
    equivalence = quote_equivalence(header, original, remote)
    require(actual != expected, "COVERPAGE_NO_LONGER_MISMATCHED_REASSESS_RECOVERY")
    require(summary["differing_cells"] > 0,
            "COVERPAGE_M1_LEXICAL_DIGEST_CHANGED_WITH_EQUAL_FIELD_VALUES")
    print("=== COVERPAGE EXACT RAW VS ACCEPTED M1 (READ ONLY) ===")
    print("SOURCE=SRC000065 MEMBER=COVERPAGE.tsv ROWS=16 FIELDS=21")
    print("FROZEN_RAW_SHA256_VERIFIED=True")
    print("RAW_CSV_REPRODUCES_FROZEN_SELECTION=True")
    print("FROZEN_SELECTED_LEXICAL_SHA256=" + expected)
    print("ACCEPTED_M1_SELECTED_LEXICAL_SHA256=" + actual)
    print("DIFFERENCE_SUMMARY=" + json.dumps(summary, sort_keys=True))
    print("CSV_QUOTE_EQUIVALENCE=" + json.dumps(equivalence, sort_keys=True))
    print("NO_RAW_CONTENT_PRINTED_NO_DELTA_WRITE_NO_CANARY_RETRY")


if __name__ == "__main__":
    diagnose()
