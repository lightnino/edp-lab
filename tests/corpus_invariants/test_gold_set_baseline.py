"""Synthetic tests for the Gold Set baseline validator (no real RAW files in CI)."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from edp_lab.ingestion.gold_set import (
    COHORT_ID,
    HEADERS,
    MANIFEST,
    ROSTER,
    RawSource,
    verify,
)


def test_gold_set_detects_mutation_and_freezes_membership(tmp_path: Path) -> None:
    raw = tmp_path / "data/raw/source.txt"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"00123,5000\n")
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    item = RawSource("SRC000001", "FIXTURE", "data/raw/source.txt", digest)

    manifest = tmp_path / MANIFEST
    manifest.parent.mkdir(parents=True)
    with manifest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerow(
            {
                "source_instance_id": item.source_instance_id,
                "source_family": item.source_family,
                "admitted_at_utc": "2026-10-18T05:00:00Z",
                "introduced_cohort": COHORT_ID,
                "raw_path": item.raw_path,
                "raw_sha256": digest,
                "real_or_controlled": "REAL",
                "variant_type": "",
                "parent_source_id": "",
                "ground_truth_available": "FALSE",
                "schema_fingerprint": "",
                "status": "ADMITTED",
            }
        )
    roster = tmp_path / ROSTER
    roster.parent.mkdir(parents=True)
    roster.write_text("source_instance_id\nSRC000001\n", encoding="utf-8")

    assert any("SHA256=" in line for line in verify(tmp_path, (item,), check_report=False))
    raw.write_bytes(b"00123,5001\n")
    with pytest.raises(ValueError, match="SHA-256 FAIL"):
        verify(tmp_path, (item,), check_report=False)


def test_gold_set_rejects_an_unadmitted_record(tmp_path: Path) -> None:
    manifest = tmp_path / MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.write_text(",".join(HEADERS) + "\n", encoding="utf-8")
    roster = tmp_path / ROSTER
    roster.parent.mkdir(parents=True)
    roster.write_text("source_instance_id\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Gold Set membership mismatch"):
        verify(
            tmp_path,
            (RawSource("SRC000001", "X", "data/raw/a.txt", "0" * 64),),
            check_report=False,
        )
