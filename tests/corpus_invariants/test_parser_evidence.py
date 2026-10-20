"""Mechanical evidence collection preserves lexical distinctions and hash gate."""

import csv
from pathlib import Path

import pytest

from edp_lab.profiling import parser_evidence as evidence


def test_integrity_failure_precedes_member_reads(tmp_path, monkeypatch):
    def reject(*args, **kwargs):
        raise ValueError("RAW_SHA256_MISMATCH")

    monkeypatch.setattr(evidence, "verify_source_identity", reject)
    with pytest.raises(ValueError, match="RAW_SHA256_MISMATCH"):
        evidence.investigate(tmp_path)


def test_lexical_evidence_keeps_quotes_null_like_text_and_precision(tmp_path, monkeypatch):
    raw = tmp_path / "source.txt"
    raw.write_bytes(
        b'ID|Text|Value\r\n001|"a""b"|1.2300\r\n002|NULL|\r\n'
        b'File Creation Time: 1015202603:03||\r\n'
    )
    registry = tmp_path / "tables.csv"
    with registry.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "source_instance_id", "logical_table_name", "raw_path",
            "raw_sha256", "archive_member",
        ])
        writer.writeheader()
        writer.writerow({"source_instance_id": "fixture", "logical_table_name": "source.txt",
                         "raw_path": "source.txt", "raw_sha256": "fixture", "archive_member": ""})
    monkeypatch.setattr(evidence, "LOGICAL_TABLES", Path("tables.csv"))
    monkeypatch.setattr(evidence, "verify_source_identity", lambda *a, **kw: [])
    monkeypatch.setattr(evidence, "load_conventions", lambda root: ({}, {
        ("fixture", "source.txt"): {
            "delimiter": "|", "metadata_record_policy": "TRAILING_FILE_CREATION_TIME",
        },
    }))
    result, = evidence.investigate(tmp_path)
    assert result["physical_lines"] == 4
    assert result["crlf"] == 4
    assert result["lexical_counts"]["data_rows"] == 2
    assert result["empty_by_column"] == {"Value": 1}
    witnesses = result["first_witnesses"]
    assert witnesses["double_quote"]["value"] == '"a""b"'
    assert witnesses["leading_zero"]["value"] == "001"
    assert witnesses["decimal"]["value"] == "1.2300"
    assert result["candidate_tokens"] == [{"column": "Text", "text": "NULL", "count": 1}]
    assert result["footer"][0]["line"] == 4
