"""Ensure lexical forensic checks are read-only and version-pinned."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_day6_v3_diagnose_lexical as diagnosis


def test_rejects_unpinned_or_mutating_statement(monkeypatch):
    monkeypatch.setattr(
        diagnosis, "admin_sql", lambda *_args: pytest.fail("remote SQL is forbidden"))
    for sql in (
        "DELETE FROM workspace.edp_lab.records",
        "SELECT * FROM workspace.edp_lab.records",
        "WITH r AS (SELECT * FROM workspace.edp_lab.records) SELECT * FROM r",
        "CREATE TABLE workspace.edp_lab.test AS SELECT 1",
    ):
        with pytest.raises(RuntimeError, match="V3_DIAG_ONLY_VERSION_PINNED_C300_SELECT"):
            diagnosis.rows(sql)


def test_selected_rows_uses_same_rank_and_only_original_values(monkeypatch):
    calls = []

    def fake_query(sql):
        calls.append(sql)
        return {"result": {"data_array": [
            ["1", json.dumps([
                {"field_ordinal": 1, "original_name": "a", "lexical_value": " 001"},
                {"field_ordinal": 2, "original_name": "b", "lexical_value": ""},
            ]), "21", "3"],
            ["2", json.dumps([
                {"field_ordinal": 1, "original_name": "a", "lexical_value": "002"},
                {"field_ordinal": 2, "original_name": "b", "lexical_value": "\t"},
            ]), "38", "4"],
        ]}}

    monkeypatch.setattr(diagnosis, "admin_sql", fake_query)
    selected = diagnosis.selected_rows(
        "clean_c300_m1_records_main_recovery_20261021_v4_full",
        {"run_id": "m1-test", "binding_sha256": "a" * 64}, [1, 2],
    )
    assert len(calls) == 1
    assert "VERSION AS OF 0" in calls[0]
    assert "ROW_NUMBER() OVER" in calls[0]
    assert "ORDER BY byte_offset, source_line" in calls[0]
    assert "WHERE ordinal IN (1,2)" in calls[0]
    assert [r[0] for r in selected] == [1, 2]
    assert [item["lexical_value"] for item in selected[0][1]] == [" 001", ""]


def test_digest_exactly_matches_runtime_ordinal_and_lexical_layout():
    from edp_lab.vault.v3_spark_runtime import _digest

    rows = [[1, ["001", "", "\t"]], [2, ["002", "3", "2.0"]]]
    assert diagnosis._digest(rows) == _digest(rows)
    assert diagnosis._digest(rows) != diagnosis._digest([
        [1, ["001", "\t", ""]], [2, ["002", "3", "2.0"]]
    ])


def test_sql_identifier_values_must_be_safe():
    for bad in ("a';DROP TABLE x", "", "a\nx", "a x"):
        with pytest.raises(RuntimeError, match="V3_DIAG_UNSAFE_SQL_VALUE"):
            diagnosis.checked_sql_token(bad)
