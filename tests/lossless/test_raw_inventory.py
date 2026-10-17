"""Deterministic no-mutation tests, independent of user's real RAW files."""

import csv
import hashlib
from pathlib import Path

from edp_lab.ingestion.inventory import sha256_file, verify_inventory


def test_sha256_matches_exact_bytes(tmp_path: Path) -> None:
    source = tmp_path / "original.txt"
    source.write_bytes(b"identifier|value\nABC|123\n")
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    before = source.read_bytes()
    assert sha256_file(source) == expected
    assert source.read_bytes() == before


def test_inventory_rejects_byte_change(tmp_path: Path) -> None:
    raw = tmp_path / "raw" / "sample.txt"
    raw.parent.mkdir()
    raw.write_bytes(b"abc")
    expected = hashlib.sha256(b"abc").hexdigest()
    manifest = tmp_path / "inventory.csv"
    with manifest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["relative_path", "sha256"])
        writer.writeheader()
        writer.writerow({"relative_path": "raw/sample.txt", "sha256": expected})
    ok, _ = verify_inventory(tmp_path, manifest)
    assert ok
    raw.write_bytes(b"changed")
    ok, lines = verify_inventory(tmp_path, manifest)
    assert not ok
    assert any(line.startswith("MISMATCH") for line in lines)
