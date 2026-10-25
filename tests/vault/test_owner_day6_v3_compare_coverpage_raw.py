"""No-content RAW/C300 comparators for frozen 13F COVERPAGE lexical incident."""

from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_day6_v3_compare_coverpage_raw as probe


def test_frozen_13f_coverpage_member_reading_uses_csv_quote_handling(tmp_path):
    path = tmp_path / "13f.zip"
    content = io.StringIO(newline="")
    writer = csv.writer(content, delimiter="\t")
    writer.writerow(["ID", "VALUE"])
    for i in range(1, 17):
        writer.writerow([str(i), f'text "{i}"\twith comma, tabs'])
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("COVERPAGE.tsv", content.getvalue().encode("latin-1"))
    header, selected = probe.raw_selected(path, list(range(1, 17)))
    assert header == ["ID", "VALUE"]
    assert [ordinal for ordinal, _ in selected] == list(range(1, 17))
    assert selected[0][1] == ["1", 'text "1"\twith comma, tabs']


def test_equal_frozen_cells_no_differences():
    header = ["ID", "VALUE"]
    originals = [(n, [str(n), "A"]) for n in range(1, 17)]
    remote = [
        (n, [
            {"original_name": key, "field_ordinal": i + 1,
             "lexical_value": value}
            for i, (key, value) in enumerate(zip(header, cells, strict=True))
        ], 10 * n, n + 1)
        for n, cells in originals
    ]
    result = probe.diff_summary(header, originals, remote)
    assert result["differing_cells"] == 0
    assert result["differing_rows"] == 0


def test_cell_differences_return_metadata_only():
    header = ["ID", "NAME"]
    originals = [(n, [str(n), "SENSITIVE_RAW_IDENTIFIER"])
                 for n in range(1, 17)]
    remote = [
        (n, [
            {"original_name": "ID", "field_ordinal": 1,
             "lexical_value": str(n)},
            {"original_name": "NAME", "field_ordinal": 2,
             "lexical_value": (
                 "SENSITIVE_RAW_IDENTIFIER" if n != 1
                 else "SENSITIVE_C300_IDENTIFIER"
             )},
        ], n * 3, n + 1)
        for n, _ in originals
    ]
    summary = probe.diff_summary(header, originals, remote)
    assert summary["differing_cells"] == 1
    assert summary["differing_rows"] == 1
    assert summary["mismatch_count_by_column_ordinal"] == {2: 1}
    assert summary["mismatch_count_by_row_ordinal"] == {1: 1}
    public = json.dumps(summary)
    assert "SENSITIVE_RAW_IDENTIFIER" not in public
    assert "SENSITIVE_C300_IDENTIFIER" not in public
    assert summary["first_24_metadata_only_differences"][0]["difference_kind"] == (
        "OTHER_LEXICAL_DIFFERENCE"
    )


def test_common_nonidentity_transformations_do_not_silently_pass():
    assert probe.classified_change(" 123", "123") == "SURROUNDING_WHITESPACE"
    assert probe.classified_change("X\r\nY", "X\nY") == "LINE_ENDINGS"
    assert probe.classified_change('X"Y', "XY") == "QUOTE_CHARACTERS"
    assert probe.classified_change("a\tb", "a b") == "TAB_VS_SPACE"
    assert probe.classified_change(" 123", " 123") == "MATCH"


def test_frozen_raw_missing_is_nonmutating(monkeypatch, tmp_path):
    path = tmp_path / "frozen.json"
    path.write_text(json.dumps([{
        "source_instance_id": "SRC000065",
        "raw_path": "data/raw/sec/does-not-exist.zip",
        "raw_sha256": "a" * 64,
    }]))
    import hashlib

    monkeypatch.setattr(probe, "FROZEN_BINDINGS", path)
    monkeypatch.setattr(probe, "EXPECTED_FROZEN_BINDING_SHA",
                        hashlib.sha256(path.read_bytes()).hexdigest())
    monkeypatch.setattr(probe, "_candidate_paths", lambda _: [
        tmp_path / "no-physical-raw.zip"
    ])
    with pytest.raises(RuntimeError, match="COVERPAGE_VERIFIED_LOCAL_RAW_NOT_FOUND"):
        probe.source_path()



def test_other_edp_lab_checkout_located_by_exact_frozen_sha(tmp_path, monkeypatch):
    import hashlib

    root = tmp_path / "edp-lab-day6-vault-prototype"
    root.mkdir()
    sibling = tmp_path / "edp-lab"
    raw = Path("data/raw/sec/sec_13f/hash-abc/2013q3_form13f.zip")
    candidate = sibling / raw
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"original-verified-raw")
    decoy = root / raw
    decoy.parent.mkdir(parents=True)
    decoy.write_bytes(b"bad-unverified-raw")
    monkeypatch.setattr(probe, "ROOT", root)
    monkeypatch.delenv("EDP_DAY6_FROZEN_RAW_ZIP", raising=False)

    discovered = probe._candidate_paths(raw)
    assert decoy in discovered
    assert candidate in discovered
    expected = hashlib.sha256(candidate.read_bytes()).hexdigest()
    assert probe._verified_source_location(raw, expected) == candidate

    with pytest.raises(RuntimeError, match="COVERPAGE_VERIFIED_LOCAL_RAW_NOT_FOUND"):
        probe._verified_source_location(raw, "0" * 64)


def test_explicit_original_raw_path_requires_exact_sha(tmp_path, monkeypatch):
    import hashlib

    path = tmp_path / "2013q3_form13f.zip"
    path.write_bytes(b"byte-preserved")
    monkeypatch.setenv("EDP_DAY6_FROZEN_RAW_ZIP", str(path))
    raw = Path("data/raw/sec/sec_13f/freeze/2013q3_form13f.zip")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert probe._verified_source_location(raw, digest) == path
    with pytest.raises(RuntimeError, match="COVERPAGE_EXPLICIT_RAW_SHA_OR_LOCATION_INVALID"):
        probe._verified_source_location(raw, "f" * 64)
