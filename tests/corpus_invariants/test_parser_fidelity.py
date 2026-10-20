"""Synthetic fidelity tests; success establishes mechanics, not source semantics."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from edp_lab.profiling import parser_fidelity as fidelity

ROOT = Path(__file__).resolve().parents[2]


def spec(header=None, footer=None, name="fixture.txt"):
    return {"expected_header": header or ["ID", "Text"], "footer": footer,
            "logical_table_name": name}


def parse(raw, table=None):
    return list(fidelity.literal_records(raw, table or spec(), {"delimiter": "|"}))


@pytest.mark.parametrize("raw,error", [
    (b"", "EMPTY_SOURCE"),
    (b"\xef\xbb\xbfID|Text\n1|a\n", "UTF8_BOM_REJECTED"),
    (b"ID|Text\n1|\xff\n", "utf-8"),
    (b"Text|ID\n1|a\n", "ORDERED_HEADER_MISMATCH"),
    (b"ID|Other\n1|a\n", "ORDERED_HEADER_MISMATCH"),
    (b"id|Text\n1|a\n", "ORDERED_HEADER_MISMATCH"),
    (b" ID|Text\n1|a\n", "ORDERED_HEADER_MISMATCH"),
    (b"ID|ID\n1|a\n", "ORDERED_HEADER_MISMATCH"),
    (b"ID|\n1|a\n", "ORDERED_HEADER_MISMATCH"),
    (b"ID|Text\n1\n", "INVALID_RECORD_WIDTH"),
    (b"ID|Text\n1|a|b\n", "INVALID_RECORD_WIDTH"),
    (b"ID|Text\n\n1|a\n", "BLANK_PHYSICAL_RECORD"),
    (b"ID|Text\r\n1|a\r\n\r\n", "BLANK_PHYSICAL_RECORD"),
    (b"ID|Text\r1|a\r", "UNSUPPORTED_RECORD_TERMINATOR"),
    (b"ID|Text\nFile Creation Time: 1015202603:03|\n", "UNEXPECTED_FOOTER"),
])
def test_bad_records_fail_closed(raw, error):
    with pytest.raises(ValueError, match=error):
        parse(raw)


@pytest.mark.parametrize("ending", [b"\n", b"\r\n", b""])
def test_exact_text_and_duplicate_occurrences_survive(ending):
    values = ["001", " padded ", "+1.2300", "-0.0000", "2010-05-07 13:14:00.0",
              "31-MAY-2013", "NULL", "N/A", "NA", "NAN", "NONE", "-", ".", "",
              "   ", '"a""b"', "a\\b", "Å", "\u2028"]
    header = [f"C{i}" for i in range(len(values))]
    row = "|".join(values).encode()
    raw = "|".join(header).encode() + b"\n" + row + b"\n" + row + ending
    records = parse(raw, spec(header=header))
    assert records[0][3] == header
    assert [r[3] for r in records[1:]] == [values, values]
    assert b"".join(r[2] for r in records) == raw
    assert records[2][1] == len(records[0][2]) + len(records[1][2])


def test_delimited_empty_fields_are_not_blank_physical_records():
    assert parse(b"ID|Text\n|\n")[1][3] == ["", ""]


@pytest.mark.parametrize("pipes", [6, 7])
def test_footer_bytes_locator_and_accounting(pipes):
    footer = {"first_field": "File Creation Time: 1015202603:03",
              "trailing_empty_fields": pipes}
    table = spec(footer=footer)
    prefix = b"ID|Text\r\n001|a\r\n"
    raw_footer = footer["first_field"].encode() + b"|" * pipes + b"\r\n"
    result = fidelity.validate_bytes(prefix + raw_footer, table, {"delimiter": "|"})
    assert result["record_accounting"] == {"HEADER": 1, "DATA": 1, "FOOTER": 1,
                                           "physical_records": 3}
    assert result["footer_evidence"] == [{"source_line": 3, "byte_offset": len(prefix),
                                          "raw_bytes_hex": raw_footer.hex()}]


@pytest.mark.parametrize("pipes", [6, 7])
@pytest.mark.parametrize("mutation,error", [
    ("absent", "ABSENT_FOOTER"),
    ("duplicate", "DUPLICATE_FOOTER"),
    ("nonfinal", "NONFINAL_FOOTER"),
    ("wrong_width", "MALFORMED"),
    ("nonempty_tail", "MALFORMED"),
    ("wrong_timestamp_shape", "MALFORMED"),
    ("changed_snapshot_timestamp", "MALFORMED"),
    ("bad_prefix", "INVALID_RECORD_WIDTH"),
    ("blank_after", "BLANK_PHYSICAL_RECORD"),
])
def test_footer_failures(pipes, mutation, error):
    first = "File Creation Time: 1015202603:03"
    footer = (first + "|" * pipes + "\n").encode()
    variants = {
        "absent": b"", "duplicate": footer * 2, "nonfinal": footer + b"2|b\n",
        "wrong_width": (first + "|" * (pipes - 1) + "\n").encode(),
        "nonempty_tail": footer[:-1] + b"X\n",
        "wrong_timestamp_shape": footer.replace(b"1015202603:03", b"2026-10-15 03:03"),
        "changed_snapshot_timestamp": footer.replace(b"1015202603:03", b"1016202603:03"),
        "bad_prefix": footer.replace(b"File Creation Time:", b"FILE CREATION TIME:"),
        "blank_after": footer + b"\n",
    }
    table = spec(footer={"first_field": first, "trailing_empty_fields": pipes})
    with pytest.raises(ValueError, match=error):
        parse(b"ID|Text\n1|a\n" + variants[mutation], table)


def test_lexical_counts_and_semantic_metrics_are_separate():
    raw = b"ID|plabel\n001|\n002| \n003|NA\n003|NA\n004|NULL\n"
    result = fidelity.validate_bytes(raw, spec(["ID", "plabel"], name="pre.txt"),
                                     {"delimiter": "|"})
    assert result["lexical_blank_counts_by_column"]["plabel"] == {
        "empty_fields": 1, "whitespace_only_fields": 1}
    assert result["lexical_candidate_tokens"] == [
        {"column_name": "plabel", "literal_value": "NA", "count": 2},
        {"column_name": "plabel", "literal_value": "NULL", "count": 1}]
    assert result["documented_inconsistencies"][0]["source_line"] == 2
    for metric in ("null_count", "null_pct"):
        assert result["semantic_metrics"][metric] == {
            "status": "NOT_COMPUTED", "reason": fidelity.NULL_REASON}


def test_quote_hypothesis_cannot_change_validated_values():
    raw = b'ID|Text\n001|"a""b\\c"\n'
    result = fidelity.validate_bytes(raw, spec(), {"delimiter": "|"})
    comparison, = result["quote_comparisons"]
    assert comparison == {"source_line": 2, "column_name": "Text",
                          "literal_value": '"a""b\\c"',
                          "proposed_decoded_value": 'a"b\\c',
                          "status": "EVIDENCE_ONLY_NOT_APPROVED"}
    assert parse(raw)[1][3][1] == comparison["literal_value"]
    assert fidelity.quote_comparison('"unclosed')["status"] == "HYPOTHESIS_PARSE_FAILED"


def test_candidate_is_inactive_and_covers_exact_snapshot_schemas():
    config = fidelity.load_candidate(ROOT)
    assert config["activation_status"] == "INACTIVE"
    assert len(config["profiles"]) == 3
    assert len(config["tables"]) == 13
    assert {p["validation_status"] for p in config["profiles"].values()} == {"PROVISIONAL"}


@pytest.mark.parametrize("mutation,error", [
    ("activate", "UNSUPPORTED_CANDIDATE_CONFIG"),
    ("dialect", "UNSUPPORTED_CANDIDATE_DIALECT"),
    ("unknown_option", "UNSUPPORTED_CANDIDATE_CONFIG"),
    ("coverage", "CANDIDATE_COVERAGE_MISMATCH"),
    ("duplicate", "UNSUPPORTED_TABLE_BINDING"),
    ("source", "SNAPSHOT_SCOPE_MISMATCH"),
    ("profile", "UNSUPPORTED_TABLE_PROFILE"),
    ("header", "INVALID_EXPECTED_HEADER"),
    ("footer", "UNSUPPORTED_FOOTER_CONFIG"),
])
def test_unsupported_config_has_no_fallback(tmp_path, monkeypatch, mutation, error):
    config = copy.deepcopy(fidelity.load_candidate(ROOT))
    if mutation == "activate":
        config["activation_status"] = "ACTIVE"
    elif mutation == "dialect":
        next(iter(config["profiles"].values()))["quote"] = '"'
    elif mutation == "unknown_option":
        config["fallback"] = True
    elif mutation == "coverage":
        config["tables"].pop()
    elif mutation == "duplicate":
        config["tables"].append(config["tables"][0])
    elif mutation == "source":
        config["tables"][0]["raw_sha256"] = "0" * 64
    elif mutation == "profile":
        config["tables"][0]["profile_id"] = "UNKNOWN"
    elif mutation == "header":
        config["tables"][0]["expected_header"] = ["A", "A"]
    elif mutation == "footer":
        next(t for t in config["tables"] if t["footer"])["footer"]["trailing_empty_fields"] = 8
    # Use real frozen metadata but replace only the candidate file location.
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(config))
    monkeypatch.setattr(fidelity, "CANDIDATE", path)
    with pytest.raises(ValueError, match=error):
        fidelity.load_candidate(ROOT)


def test_hash_failure_precedes_read_and_changed_member_is_rejected(monkeypatch):
    config = fidelity.load_candidate(ROOT)
    monkeypatch.setattr(fidelity, "load_candidate", lambda root: config)

    def reject(*args, **kwargs):
        raise ValueError("RAW_SHA256_MISMATCH")

    def forbidden(*args):
        pytest.fail("member read before integrity gate")

    monkeypatch.setattr(fidelity, "verify_source_identity", reject)
    monkeypatch.setattr(fidelity, "read_member", forbidden)
    with pytest.raises(ValueError, match="RAW_SHA256_MISMATCH"):
        fidelity.validate_candidate(ROOT)
    monkeypatch.setattr(fidelity, "verify_source_identity", lambda *a, **kw: [])
    monkeypatch.setattr(fidelity, "read_member", lambda *a: b"changed")
    assert hashlib.sha256(b"changed").hexdigest() != config["tables"][0]["member_sha256"]
    with pytest.raises(ValueError, match="MEMBER_SHA256_MISMATCH"):
        fidelity.validate_candidate(ROOT)
