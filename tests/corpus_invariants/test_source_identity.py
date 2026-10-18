"""Synthetic source-identity checks plus frozen-metadata baseline invariants."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from zipfile import ZipFile

import pytest

from edp_lab.ingestion.gold_set import HEADERS
from edp_lab.ingestion.source_identity import (
    LOGICAL_FIELDS,
    LOGICAL_TABLES,
    MANIFEST,
    verify_source_identity,
)

PROJECT = Path(__file__).resolve().parents[2]
FROZEN = PROJECT / "tests/fixtures/gold_v2_manifest_snapshot.csv"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fixture(tmp_path: Path) -> tuple[dict[str, str], dict[str, str]]:
    raw_path = tmp_path / "data/raw/source.zip"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(raw_path, "w") as archive:
        archive.writestr("table.tsv", b"key\tvalue\n001\t2\n")
    digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    source = {
        "source_instance_id": "SRC000001",
        "source_family": "FIXTURE",
        "admitted_at_utc": "2026-10-18T05:11:35Z",
        "introduced_cohort": "GOLD_V1",
        "raw_path": "data/raw/source.zip",
        "raw_sha256": digest,
        "real_or_controlled": "REAL",
        "variant_type": "",
        "parent_source_id": "",
        "ground_truth_available": "FALSE",
        "schema_fingerprint": "",
        "status": "ADMITTED",
    }
    logical = {
        "source_instance_id": "SRC000001",
        "source_family": "FIXTURE",
        "source_dataset": "FIXTURE_DATASET",
        "source_file": "source.zip",
        "raw_path": source["raw_path"],
        "raw_sha256": digest,
        "source_documentation": "FIXTURE_DOC",
        "logical_table_name": "table.tsv",
        "archive_member": "table.tsv",
        "profiling_status": "PENDING_DEEP_PROFILE",
    }
    _write(tmp_path / MANIFEST, HEADERS, [source])
    _write(tmp_path / LOGICAL_TABLES, LOGICAL_FIELDS, [logical])
    return source, logical


def test_frozen_gold_v2_rows_are_unchanged_and_future_append_is_possible() -> None:
    frozen = FROZEN.read_text(encoding="utf-8").splitlines(keepends=True)
    current = (PROJECT / MANIFEST).read_text(encoding="utf-8").splitlines(
        keepends=True
    )
    assert len(frozen) == 5
    assert current[:len(frozen)] == frozen


def test_registered_identity_structure_passes_without_raw_files() -> None:
    results = verify_source_identity(PROJECT)
    assert any("4 distinct instances" in line for line in results)
    assert any("13 registered logical tables" in line for line in results)
    assert "NOT_CHECKED RAW bytes (metadata-only validation)" in results


def test_exact_raw_bytes_and_member_validation(tmp_path: Path) -> None:
    _fixture(tmp_path)
    assert any("PASS RAW bytes and archive members" in s for s in
               verify_source_identity(tmp_path, check_raw=True))


@pytest.mark.parametrize(
    ("field", "bad", "error"),
    [
        ("source_instance_id", "SRC000001", "DUPLICATE_SOURCE_ID"),
        ("raw_path", "data/raw/source.zip", "RAW_PATH_REUSED"),
        ("raw_path", "data/raw/../other.zip", "INVALID_RAW_PATH"),
        ("raw_sha256", "abc", "INVALID_RAW_SHA256"),
    ],
)
def test_bad_new_identity_rejected(
    tmp_path: Path, field: str, bad: str, error: str
) -> None:
    source, _ = _fixture(tmp_path)
    duplicate = source.copy()
    duplicate["source_instance_id"] = "SRC000002"
    duplicate["raw_path"] = "data/raw/another.zip"
    duplicate[field] = bad
    _write(tmp_path / MANIFEST, HEADERS, [source, duplicate])
    with pytest.raises(ValueError, match=error):
        verify_source_identity(tmp_path)


def test_identical_hash_with_distinct_delivery_paths_requires_review(
    tmp_path: Path,
) -> None:
    source, _ = _fixture(tmp_path)
    second = source.copy()
    second["source_instance_id"] = "SRC000002"
    second["raw_path"] = "data/raw/second_delivery.zip"
    _write(tmp_path / MANIFEST, HEADERS, [source, second])
    results = verify_source_identity(tmp_path)
    assert any("REVIEW_REQUIRED identical RAW SHA-256" in s for s in results)


def test_controlled_variant_requires_real_parent_and_type(tmp_path: Path) -> None:
    source, _ = _fixture(tmp_path)
    bad = source.copy()
    bad.update(
        source_instance_id="SRC000002",
        raw_path="data/raw/variant.zip",
        real_or_controlled="CONTROLLED",
        parent_source_id="",
        variant_type="NULL_INJECTION",
    )
    _write(tmp_path / MANIFEST, HEADERS, [source, bad])
    with pytest.raises(ValueError, match="CONTROLLED_MISSING_PARENT"):
        verify_source_identity(tmp_path)
    bad["parent_source_id"] = "SRC999999"
    _write(tmp_path / MANIFEST, HEADERS, [source, bad])
    with pytest.raises(ValueError, match="UNKNOWN_CONTROLLED_PARENT"):
        verify_source_identity(tmp_path)
    bad["parent_source_id"] = "SRC000001"
    _write(tmp_path / MANIFEST, HEADERS, [source, bad])
    assert any("2 distinct instances" in s for s in verify_source_identity(tmp_path))


def test_archive_member_must_have_exact_parent_lineage(tmp_path: Path) -> None:
    _, logical = _fixture(tmp_path)
    bad = logical.copy()
    bad["archive_member"] = "other.tsv"
    _write(tmp_path / LOGICAL_TABLES, LOGICAL_FIELDS, [bad])
    with pytest.raises(ValueError, match="INVALID_ARCHIVE_MEMBER"):
        verify_source_identity(tmp_path)
    bad["logical_table_name"] = "other.tsv"
    _write(tmp_path / LOGICAL_TABLES, LOGICAL_FIELDS, [bad])
    with pytest.raises(ValueError, match="MISSING_ARCHIVE_MEMBER"):
        verify_source_identity(tmp_path, check_raw=True)


def test_changed_source_bytes_are_not_silently_accepted(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / "data/raw/source.zip").write_bytes(b"changed source")
    with pytest.raises(ValueError, match="RAW_SHA256_MISMATCH"):
        verify_source_identity(tmp_path, check_raw=True)
