"""Versioned Day 2 parsing/profiling contract and read-only RAW parser probe.

This is NOT a production profiler, a semantic type inferencer, or an approved
business mapping. Profiles remain provisional pending local RAW validation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile

from edp_lab.ingestion.source_identity import verify_source_identity

CONVENTIONS = Path("metadata/profiling_conventions_v1.json")
LOGICAL_TABLES = Path("metadata/gold_set_logical_tables_v2.csv")
LOCK = Path("uv.lock")
PRECISION_CLASSES = {
    "EXACT_FULL_SCAN",
    "EXACT_SAMPLE",
    "APPROXIMATE",
    "NOT_COMPUTED",
}
REQUIRED_OPTIONS = {
    "source_format",
    "delimiter",
    "has_header",
    "quote",
    "escape",
    "encoding",
    "null_tokens",
    "column_names",
    "column_types",
    "date_formats",
    "timestamp_formats",
    "json_format",
    "json_max_depth",
    "error_handling",
    "metadata_record_policy",
    "validation_status",
}


def reference_count_metrics(values: Iterable[str | None]) -> dict[str, int | float | None]:
    """Small exact reference oracle; does not certify a production scan scope.

    NULL is Python None. Empty text and literal 'NULL' are non-NULL strings.
    Ratios with zero denominators are unavailable (None), never zero.
    """
    materialized = list(values)
    non_null = [value for value in materialized if value is not None]
    frequency = Counter(non_null)
    row_count = len(materialized)
    non_null_count = len(non_null)
    null_count = row_count - non_null_count
    return {
        "row_count": row_count,
        "null_count": null_count,
        "non_null_count": non_null_count,
        "distinct_non_null_count": len(frequency),
        "unique_count": sum(count == 1 for count in frequency.values()),
        "null_pct": null_count / row_count if row_count else None,
        "distinct_pct": (
            len(frequency) / non_null_count if non_null_count else None
        ),
    }


def schema_fingerprint(columns: list[tuple[str, str]]) -> str:
    """Versioned order-sensitive schema fingerprint; no semantic normalization."""
    data = {
        "version": "SCHEMA_SHA256_V1",
        "columns": [{"name": name, "type": kind} for name, kind in columns],
    }
    encoded = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_conventions(root: Path) -> tuple[dict, dict[tuple[str, str], dict]]:
    """CI-safe validation of frozen conventions and all 13 GOLD_V2 bindings."""
    root = root.resolve()
    with (root / CONVENTIONS).open(encoding="utf-8") as stream:
        config = json.load(stream)

    if config.get("contract_version") != "PARSING_PROFILING_CONTRACT_V1":
        raise ValueError("CONTRACT_VERSION_MISMATCH")
    if config.get("profiler_implementation_status") != "NOT_IMPLEMENTED":
        raise ValueError("UNSUPPORTED_PROFILER_IMPLEMENTATION_STATUS")
    if config.get("profiling_scope") != (
        "FULL_LOGICAL_TABLE_EXCLUDING_EXPLICITLY_ACCOUNTED_METADATA_RECORDS"
    ):
        raise ValueError("INVALID_PROFILING_SCOPE")
    if config.get("sampling_method") != "FULL_SCAN":
        raise ValueError("INVALID_DEFAULT_SAMPLING")
    if config.get("sampling_seed_if_applicable") is not None:
        raise ValueError("FULL_SCAN_MUST_NOT_SET_SEED")
    if set(config.get("precision_classes", [])) != PRECISION_CLASSES:
        raise ValueError("INVALID_PRECISION_CLASSES")
    if config.get("ratio_zero_denominator") != "NULL":
        raise ValueError("INVALID_ZERO_DENOMINATOR_POLICY")
    if config.get("fingerprint_version") != "SCHEMA_SHA256_V1":
        raise ValueError("INVALID_FINGERPRINT_VERSION")
    if config.get("canonicalization_version") != "RAW_HEADER_TEXT_V1":
        raise ValueError("INVALID_CANONICALIZATION_VERSION")

    lock = (root / LOCK).read_text(encoding="utf-8")
    match = re.search(r'(?m)^name = "duckdb"\nversion = "([^"]+)"', lock)
    if not match or not config["duckdb_version"].startswith(match.group(1) + " "):
        raise ValueError("DUCKDB_LOCK_VERSION_MISMATCH")

    profiles = config.get("profiles", {})
    for name, profile in profiles.items():
        if set(profile) != REQUIRED_OPTIONS:
            raise ValueError(f"INVALID_PARSER_PROFILE_SCHEMA {name}")
        if profile["source_format"] != "DELIMITED_TEXT":
            raise ValueError(f"UNSUPPORTED_SOURCE_FORMAT {name}")
        if len(profile["delimiter"]) != 1 or profile["delimiter"] in "\r\n":
            raise ValueError(f"INVALID_DELIMITER {name}")
        if profile["has_header"] is not True:
            raise ValueError(f"HEADER_REQUIRED {name}")
        if profile["quote"] is not None or profile["escape"] is not None:
            raise ValueError(f"UNREVIEWED_QUOTING {name}")
        if profile["encoding"] != "utf-8" or profile["null_tokens"]:
            raise ValueError(f"UNREVIEWED_DECODING_OR_NULL_TOKENS {name}")
        if profile["column_names"] != "SOURCE_HEADER_EXACT":
            raise ValueError(f"UNREVIEWED_COLUMN_NAMES {name}")
        if profile["column_types"] != "ALL_TEXT":
            raise ValueError(f"UNREVIEWED_TYPE_COERCION {name}")
        if profile["date_formats"] or profile["timestamp_formats"]:
            raise ValueError(f"UNREVIEWED_DATE_COERCION {name}")
        if profile["json_format"] is not None or profile["json_max_depth"] is not None:
            raise ValueError(f"JSON_NOT_APPLICABLE {name}")
        if profile["error_handling"] != "FAIL_CLOSED":
            raise ValueError(f"INVALID_ERROR_HANDLING {name}")
        if profile["metadata_record_policy"] not in {
            "NONE", "TRAILING_FILE_CREATION_TIME"
        }:
            raise ValueError(f"INVALID_METADATA_POLICY {name}")
        if profile["validation_status"] not in {"PROVISIONAL", "RAW_VERIFIED"}:
            raise ValueError(f"INVALID_VALIDATION_STATUS {name}")

    with (root / LOGICAL_TABLES).open(encoding="utf-8", newline="") as stream:
        expected = {
            (row["source_instance_id"], row["logical_table_name"]): row
            for row in csv.DictReader(stream)
        }
    mapped: dict[tuple[str, str], dict] = {}
    for item in config.get("assignments", []):
        key = item["source_instance_id"], item["logical_table_name"]
        if key in mapped or key not in expected:
            raise ValueError(f"INVALID_OR_DUPLICATE_PROFILE_BINDING {key}")
        name = item["profile_id"]
        if name not in profiles:
            raise ValueError(f"UNKNOWN_PROFILE {name}")
        mapped[key] = profiles[name]
    if set(mapped) != set(expected):
        raise ValueError("GOLD_V2_PROFILE_COVERAGE_MISMATCH")
    if len(mapped) != 13:
        raise ValueError("GOLD_V2_EXPECTED_13_LOGICAL_TABLES")
    return config, mapped


def probe_raw_parsers(root: Path) -> list[str]:
    """Read-only full-width/fidelity probe of all 13 local RAW logical tables.

    This checks selected conservative parser assumptions, not semantic correctness
    or completed baseline profiling. It never auto-promotes provisional profiles.
    """
    root = root.resolve()
    verify_source_identity(root, check_raw=True)
    config, mapped = load_conventions(root)
    del config
    with (root / LOGICAL_TABLES).open(encoding="utf-8", newline="") as stream:
        logical_rows = list(csv.DictReader(stream))
    output: list[str] = []
    for item in logical_rows:
        key = item["source_instance_id"], item["logical_table_name"]
        profile = mapped[key]
        path = root / item["raw_path"]
        with ExitStack() as stack:
            if item["archive_member"]:
                archive = stack.enter_context(ZipFile(path))
                binary = stack.enter_context(archive.open(item["archive_member"]))
            else:
                binary = stack.enter_context(path.open("rb"))
            stream = stack.enter_context(
                io.TextIOWrapper(binary, encoding=profile["encoding"], errors="strict",
                                 newline="")
            )
            reader = csv.reader(
                stream, delimiter=profile["delimiter"],
                quotechar=None, escapechar=None,
                quoting=csv.QUOTE_NONE, strict=True,
            )
            try:
                header = next(reader)
            except StopIteration as exc:
                raise ValueError(f"EMPTY_SOURCE {key}") from exc
            if not header or any(not name for name in header):
                raise ValueError(f"INVALID_SOURCE_HEADER {key}")
            if len(set(header)) != len(header):
                raise ValueError(f"DUPLICATE_SOURCE_HEADERS {key}")
            data_rows = 0
            metadata_rows = 0
            for row in reader:
                if (profile["metadata_record_policy"] == "TRAILING_FILE_CREATION_TIME"
                        and row and row[0].startswith("File Creation Time:")):
                    if metadata_rows:
                        raise ValueError(f"MULTIPLE_FOOTER_ROWS {key}")
                    metadata_rows += 1
                    continue
                if metadata_rows:
                    raise ValueError(f"DATA_AFTER_FOOTER {key}")
                if len(row) != len(header):
                    raise ValueError(
                        f"ROW_WIDTH_MISMATCH {key}: row={data_rows + 1} "
                        f"expected={len(header)} actual={len(row)}"
                    )
                data_rows += 1
            if (profile["metadata_record_policy"] == "TRAILING_FILE_CREATION_TIME"
                    and metadata_rows != 1):
                raise ValueError(f"EXPECTED_METADATA_FOOTER {key}")
            output.append(
                f"PROBE PASS {key[0]} {key[1]}: {len(header)} columns, "
                f"{data_rows} data rows, {metadata_rows} accounted metadata rows; "
                f"profile status={profile['validation_status']}"
            )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check-raw", action="store_true")
    args = parser.parse_args()
    try:
        config, mapped = load_conventions(args.root)
        print(
            f"PASS {config['contract_version']}: {len(mapped)} GOLD_V2 profiles bound; "
            f"DuckDB lock {config['duckdb_version']}"
        )
        print("NOT IMPLEMENTED: production profiler; parser profiles remain provisional")
        if args.check_raw:
            print("\n".join(probe_raw_parsers(args.root)))
    except (OSError, ValueError, csv.Error, UnicodeError) as exc:
        parser.exit(1, f"FAIL {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
