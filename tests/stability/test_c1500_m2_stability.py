"""Permanent independent Step 9 controls for frozen membership and M2 values."""
from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_n750_m2_oracle", ROOT / "scripts/check_n750_m2_oracle.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_oracle_preserves_scale_and_rejects_silent_coercion():
    assert MODULE.oracle("+0007.120", True, False) == (
        "VALID", "EXACT_PROJECTION", Decimal("7.1200"))
    assert MODULE.oracle("7.12000", True, False)[:2] == (
        "SCALE_EXCEEDED", "FRACTIONAL_DIGITS_GT_4")
    assert MODULE.oracle("1e2", True, False)[:2] == (
        "INVALID", "LEXICAL_GRAMMAR")
    assert MODULE.oracle("", True, False)[:2] == ("BLANK", "EMPTY_TEXT")
    assert MODULE.oracle(None, False, False)[:2] == (
        "MISSING", "SOURCE_FIELD_ABSENT")
    assert MODULE.oracle("", True, True)[:2] == (
        "NULL_UNRESOLVED", "SOURCE_NULL_MARKER_UNINTERPRETED")


def test_c1500_freeze_and_n750_persisted_oracle():
    if not (ROOT / "runs/n750/step8-v1/clean/treasury-m2-projections.parquet").exists():
        import pytest

        pytest.skip("retained Step 8 local outputs unavailable")
    MODULE.main()


def test_combined_sql_is_read_only_source_preserving_and_pinned():
    sql = (ROOT / "sql/stability/c1500_m2_v1/combined_candidate.sql").read_text().upper()
    assert sql.count("UNION ALL") == 3
    assert "SELECT DISTINCT" not in sql
    for token in ("O_C750_M2_RECORDS_HISTORICAL_20261022_V1",
                  "CLEAN_N750_M1_SEC_RECORDS_STEP8_V1 VERSION AS OF 0",
                  "CLEAN_N750_M1_TREASURY_PROPERTIES_STEP8_V1 VERSION AS OF 0",
                  "CLEAN_N750_M2_TREASURY_RATES_STEP8_V1 VERSION AS OF 0"):
        assert token in sql
    assert "TO_JSON(STRUCT(" in sql
    assert sql.count("IGNORENULLFIELDS") == 4
    for verb in ("CREATE ", "REPLACE ", "INSERT ", "MERGE ", "DELETE ", "UPDATE "):
        assert verb not in sql
