"""Remote location mapping never depends on SRC IDs or folder basenames."""
import json
from pathlib import Path

import pytest

from edp_lab.ingestion.remote_locations import resolve

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "proposals/n750-step1-v3"


def test_current_selected_sources_reuse_receipts_without_filename_guessing():
    roster = json.loads((PACKET / "roster.json").read_bytes())
    qualification = json.loads((PACKET / "qualification.json").read_bytes())
    index = resolve(roster, qualification)
    assert index["selected"] == 750
    assert index["located"] == 450
    assert index["unresolved"] == 300
    located = [r for r in index["results"] if r["remote_locations"]]
    assert all(row["status"] == "RECEIPT_LOCATION_FOUND" for row in located)
    assert all(loc["remote"].startswith("dbfs:/Volumes/")
               for row in located for loc in row["remote_locations"])


def test_new_receipt_resolves_independently_of_filename_and_cohort():
    source = {"source_identity": "physical-a", "raw_sha256": "a" * 64, "bytes": 7}
    receipt = {
        **source, "remote": "dbfs:/Volumes/workspace/edp_lab/raw/legacy/random-name.bin",
        "remote_status": "EXACT_REMOTE_BYTES_PASS", "actual_sha256": "a" * 64,
        "verified_at_utc": "2026-10-22T00:00:00Z",
    }
    result = resolve([source], [receipt])
    assert result["located"] == 1
    assert result["results"][0]["remote_locations"][0]["remote"] == receipt["remote"]


def test_unmatched_receipts_are_not_treated_as_locations():
    source = {"source_identity": "physical-a", "raw_sha256": "a" * 64, "bytes": 7}
    another = {**source, "source_identity": "not-selected"}
    receipt = {**another, "remote": "dbfs:/Volumes/somewhere/file",
               "remote_status": "EXACT_REMOTE_BYTES_PASS",
               "actual_sha256": "a" * 64}
    assert resolve([source], [receipt])["unresolved"] == 1


def test_conflicting_source_sha_or_bytes_rejected():
    source = {"source_identity": "physical-a", "raw_sha256": "a" * 64, "bytes": 7}
    receipt = {**source, "raw_sha256": "b" * 64,
               "remote": "dbfs:/Volumes/workspace/x",
               "remote_status": "EXACT_REMOTE_BYTES_PASS",
               "actual_sha256": "b" * 64}
    with pytest.raises(ValueError, match="REMOTE_RECEIPT_IDENTITY_MISMATCH"):
        resolve([source], [receipt])
    receipt["raw_sha256"] = "a" * 64
    receipt["bytes"] = 8
    with pytest.raises(ValueError, match="REMOTE_RECEIPT_IDENTITY_MISMATCH"):
        resolve([source], [receipt])


def test_unverified_and_unsafe_locations_cannot_pass():
    source = {"source_identity": "physical-a", "raw_sha256": "a" * 64, "bytes": 7}
    receipt = {**source, "remote": "dbfs:/Volumes/workspace/x"}
    with pytest.raises(ValueError, match="REMOTE_RECEIPT_NOT_SHA_VERIFIED"):
        resolve([source], [receipt])
    receipt.update(remote_status="EXACT_REMOTE_BYTES_PASS", actual_sha256="a" * 64)
    receipt["remote"] = "dbfs:/Volumes/workspace/../x"
    with pytest.raises(ValueError, match="INVALID_REMOTE_LOCATOR"):
        resolve([source], [receipt])


def test_duplicate_selected_physical_identity_denied():
    source = {"source_identity": "physical-a", "raw_sha256": "a" * 64, "bytes": 7}
    with pytest.raises(ValueError, match="DUPLICATE_SOURCE_IDENTITY"):
        resolve([source, source], [])
