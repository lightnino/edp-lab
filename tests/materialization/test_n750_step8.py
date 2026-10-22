"""Focused guards for the approved N750 lexical and M2 source boundary."""

import hashlib

import pytest

from edp_lab.materialization.n750_step8 import parse_sec, parse_treasury


def source(raw, sid):
    return {"source_instance_id": sid, "source_identity": "a" * 64,
            "raw_sha256": hashlib.sha256(raw).hexdigest()}


def test_sec_preserves_framing_and_equal_looking_occurrences():
    prefix = (b"Description: sample\nLast Data Received: sample\nComments: sample\n"
              b"Anonymous FTP: sample\n \nCIK|Company Name|Form Type|Date Filed|File Name\n" +
              b"-" * 80 + b"\n")
    line = b"1|A|10-K|20250101|edgar/data/1/x\n"
    raw = prefix + line + line
    rows = parse_sec(raw, source(raw, "SRC010456"))
    assert len(rows) == 9
    assert [r["record_kind"] for r in rows[:7]] == [
        "METADATA", "METADATA", "METADATA", "METADATA", "METADATA", "HEADER", "METADATA"]
    assert rows[7]["fields"] == rows[8]["fields"]
    assert rows[7]["byte_offset"] != rows[8]["byte_offset"]
    assert rows[7]["line_sha256"] == rows[8]["line_sha256"]
    assert b"".join(raw[r["byte_offset"]:r["byte_offset"] + r["byte_length"]]
                    for r in rows) == raw


def test_treasury_repeats_present_empty_and_missing_are_distinct():
    raw = (b'<feed xmlns="http://www.w3.org/2005/Atom" '
           b'xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" '
           b'xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">'
           b'<entry><content><m:properties><d:RATE>4.45</d:RATE>'
           b'<d:RATE></d:RATE></m:properties></content></entry>'
           b'<entry><content><m:properties></m:properties></content></entry></feed>')
    lexical, typed, entries = parse_treasury(raw, source(raw, "SRC010453"))
    assert entries == 2 and len(lexical) == 2 and len(typed) == 3
    assert [r["conversion_outcome"] for r in typed] == ["VALID", "BLANK", "MISSING"]
    assert [r["present"] for r in typed] == [True, True, False]
    assert typed[1]["lexical_value"] == "" and typed[2]["lexical_value"] is None
    assert typed[0]["property_ordinal"] != typed[1]["property_ordinal"]
    assert typed[2]["byte_offset"] is None


def test_changed_raw_is_rejected_before_parsing():
    raw = b"not the sealed source"
    binding = source(raw, "SRC010453")
    with pytest.raises(AssertionError):
        parse_treasury(raw + b"!", binding)
