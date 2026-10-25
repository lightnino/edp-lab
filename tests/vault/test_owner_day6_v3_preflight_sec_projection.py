"""Read-only M1 SEC projection preflight never acquires write authority."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_day6_v3_preflight_sec_projection as probe


def test_member_literal_must_be_safe_and_preserve_real_standalone_empty():
    assert probe._physical_literal("") == "''"
    assert probe._physical_literal("COVERPAGE.tsv") == "'COVERPAGE.tsv'"
    with pytest.raises(RuntimeError, match="V3_DIAG_UNSAFE_SQL_VALUE"):
        probe._physical_literal("x' OR 1=1 --")


def test_selected_records_use_only_version_zero_read_with_fixed_row_number(
        monkeypatch):
    calls = []

    def remote(sql):
        calls.append(sql)
        return [[
            "1", "SRC000107", "m1-run", "a" * 64,
            "2", "50", "20", (
                '[{"original_name":"CIK","field_ordinal":1,'
                '"disposition":"DIRECT_MAP","lexical_value":"0001"}]'
            )
        ]]

    monkeypatch.setattr(probe, "rows", remote)
    value = probe._data_rows({
        "source_instance_id": "SRC000107",
        "records_table": "clean_c300_m1_records_main_recovery_20261021_v4_full",
        "run_id": "m1-run",
        "binding_sha256": "a" * 64,
    }, [1])
    assert len(value) == 1
    assert value[0][0] == 1
    assert value[0][1]["byte_offset"] == 50
    assert value[0][1]["byte_length"] == 20
    assert value[0][1]["fields"][0]["lexical_value"] == "0001"
    assert len(calls) == 1
    assert "VERSION AS OF 0" in calls[0]
    assert "ROW_NUMBER()" in calls[0]
    assert "WHERE ordinal IN (1)" in calls[0]
    assert "CREATE " not in calls[0].upper()
    assert "MERGE " not in calls[0].upper()


def test_preflight_binding_lookup_cannot_adopt_missing_member_hash(monkeypatch):
    fake = {
        ("SRC000107", "daily_master.idx"): (
            "clean_c300_m1_records_main_recovery_20261021_v4_full",
            {"run_id": "m1-run", "binding_sha256": "a" * 64, "physical": ""},
        )
    }
    monkeypatch.setattr(probe, "rows", lambda *_: [])
    with pytest.raises(RuntimeError, match="V3_SEC_PREFLIGHT_MEMBER_SHA_UNVERIFIED"):
        probe._full_bindings(fake)
