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


def source_path() -> tuple[Path, str]:
    require(hashlib.sha256(FROZEN_BINDINGS.read_bytes()).hexdigest() ==
            EXPECTED_FROZEN_BINDING_SHA, "COVERPAGE_FROZEN_BINDINGS_CHANGED")
    frozen = json.loads(FROZEN_BINDINGS.read_bytes())
    matches = [x for x in frozen if x["source_instance_id"] == SOURCE_ID]
    require(len(matches) == 1, "COVERPAGE_FROZEN_SOURCE_BINDING_COUNT_CHANGED")
    binding = matches[0]
    raw_path = Path(binding["raw_path"])
    require(not raw_path.is_absolute() and ".." not in raw_path.parts
            and "data" in raw_path.parts and "raw" in raw_path.parts,
            "COVERPAGE_FROZEN_RAW_PATH_UNEXPECTED")
    path = ROOT / raw_path
    require(path.is_file(), "COVERPAGE_LOCAL_FROZEN_RAW_MISSING:" + str(path))
    with path.open("rb") as stream:
        require(hashlib.file_digest(stream, "sha256").hexdigest() ==
                binding["raw_sha256"], "COVERPAGE_FROZEN_RAW_SHA_CHANGED")
    return path, binding["raw_sha256"]


def raw_selected(path: Path, expected_ordinals: list[int]) -> tuple[list[str], list[tuple[int, list[str]]]]:
    # Byte-exact same CSV decoding used in the original frozen selection generator.
    require(expected_ordinals == list(range(1, 17)),
            "COVERPAGE_SELECTION_ORDINALS_CHANGED")
    with zipfile.ZipFile(path) as archive:
        with archive.open(MEMBER) as stream:
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
    print("NO_RAW_CONTENT_PRINTED_NO_DELTA_WRITE_NO_CANARY_RETRY")


if __name__ == "__main__":
    diagnose()
