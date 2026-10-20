"""Additional empty/partial-scan cases under unresolved NULL semantics."""

import pytest

from edp_lab.profiling import tools
from edp_lab.profiling.source_reader import read_synthetic


@pytest.mark.parametrize("raw", [b"a,b\n", b"a,b\n,\n ,NULL\n"])
def test_empty_and_blank_populations_keep_unknown_null_metrics(raw):
    table = read_synthetic(raw, delimiter=",", quote=None, null_tokens=None,
                           expected_header=("a", "b"), provenance={})
    assert table.parse_status == "PASS"
    result = tools.profile_column(table, "a")
    for name, metric in result["statistics"].items():
        if name != "sample":
            assert metric["computation_mode"] == "NOT_COMPUTED"
            assert metric["value"] is None
            assert metric["reason"]
    assert result["sample_selection"]["actual_size"] == len(table.rows)
    assert tools.find_duplicates(table)["excess_rows"]["value"] == 0


def test_partial_scan_retains_failure_line_and_occurrences():
    table = read_synthetic(b"a,b\n001,x\n002\n003,z\n", delimiter=",", quote=None,
                           null_tokens=None, expected_header=("a", "b"), provenance={})
    assert table.errors == ("INVALID_RECORD_WIDTH line=3",)
    assert table.rows == (("001", "x"),)
    result = tools.profile_table(table)
    assert result["parse_status"] == "FAIL"
    assert result["rows_scanned"]["value"] == 1
    assert result["population"]["accounting"] == {"HEADER": 1, "DATA": 1, "FOOTER": 0}
    assert result["row_count"] == {
        "value": None, "computation_mode": "NOT_COMPUTED", "reason": "PARSE_FAILED"}
