"""Synthetic metrics and physical-format diagnostic tests. No user RAW required."""

from __future__ import annotations

import hashlib

import pytest

from edp_lab.profiling.metrics_contract import FieldCounts, source_schema_fingerprint
from edp_lab.profiling.source_format_probe import inspect_member


def test_explicit_fraction_denominators_and_all_null_behavior() -> None:
    profile = FieldCounts(row_count=10, null_count=2, distinct_non_null_count=4).as_profile()
    assert profile["non_null_count"] == 8
    assert profile["null_pct"] == 0.2
    assert profile["distinct_pct"] == 0.5
    assert FieldCounts(0, 0, 0).as_profile()["null_pct"] is None
    assert FieldCounts(2, 2, 0).as_profile()["distinct_pct"] is None


@pytest.mark.parametrize(
    "data",
    [
        (3, 4, 1),
        (3, 1, 3),
        (-1, 0, 0),
        (True, 0, 0),
        (3.5, 0, 0),
    ],
)
def test_invalid_exact_counts_rejected(data: tuple[object, ...]) -> None:
    with pytest.raises(ValueError):
        FieldCounts(*data).as_profile()


def test_approximation_cannot_be_silently_used() -> None:
    with pytest.raises(ValueError, match="APPROXIMATE"):
        FieldCounts(10, 0, 7, count_mode="APPROXIMATE").as_profile()


def test_order_and_parser_configuration_affect_schema_fingerprint() -> None:
    first = source_schema_fingerprint(["CUSIP", "VALUE"], parser_profile_sha256="0" * 64)
    assert first == source_schema_fingerprint(
        ["CUSIP", "VALUE"], parser_profile_sha256="0" * 64
    )
    assert len(first) == 64
    assert first != source_schema_fingerprint(
        ["VALUE", "CUSIP"], parser_profile_sha256="0" * 64
    )
    assert first != source_schema_fingerprint(
        ["CUSIP", "VALUE"], parser_profile_sha256="1" * 64
    )
    assert first != source_schema_fingerprint(
        ["CUSIP", "value"], parser_profile_sha256="0" * 64
    )


def test_probe_does_not_strip_footer_or_leading_zeros() -> None:
    payload = b"symbol|value\r\n00123|0000\r\nFile Creation Time: 20261015\r\n"
    evidence = inspect_member(payload)
    assert evidence["member_sha256"] == hashlib.sha256(payload).hexdigest()
    assert evidence["newline_counts"] == {"crlf": 3, "lf_only": 0, "cr_only": 0}
    assert evidence["first_line_pipe_separator_count"] == 1
    assert evidence["last_line_pipe_separator_count"] == 0
    assert "00123" not in evidence["first_nonempty_line_bytes"]
    assert evidence["physical_line_count_diagnostic"] == 3


def test_probe_reports_non_utf8_as_evidence_not_as_failed_parse() -> None:
    evidence = inspect_member(b"a\tdata\nX\t\xff\n")
    assert evidence["utf8_decodable"] is False
    assert evidence["first_line_tab_separator_count"] == 1
