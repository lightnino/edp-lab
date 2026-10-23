"""Focused negative controls for the approved source-scoped Vault contract."""

from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.day6_vault_contract_v1 import (
    assertion_key,
    concept_key,
    fact_slot_key,
    filing_key,
    lexical_hashdiff,
    occurrence_key,
    validate_lossless,
)

HEADER = ("adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg",
          "value", "footnote")
OLD_HEADER = tuple(x for x in HEADER if x != "segments")
ROW = dict(zip(HEADER, ("0001918712-25-000092", "DerivativeAssetNotionalAmount",
                        "us-gaap/2025", "20241231", "0", "AUD", "axis=member;", "",
                        "12458000.0000", ""), strict=True))
MEMBER_SHA = "a" * 64


def fields(row=ROW):
    return tuple((i, name, "PRESENT", row[name]) for i, name in enumerate(HEADER, 1))


def test_filing_and_concept_namespace_and_exact_version():
    assert filing_key("0001") != filing_key("00001")
    assert concept_key("Tag", "us-gaap/2024") != concept_key("Tag", "us-gaap/2025")
    assert concept_key("Tag", "custom-adsh") != concept_key("tag", "custom-adsh")
    with pytest.raises(ValueError, match="MISSING_ADSH"):
        filing_key("")
    with pytest.raises(ValueError, match="MISSING_CONCEPT_COMPONENT"):
        concept_key("Tag", "")


def test_complete_context_and_historical_schema_state():
    base = fact_slot_key(ROW, HEADER)
    for field in ("ddate", "qtrs", "uom", "coreg", "segments"):
        changed = {**ROW, field: "different"}
        assert fact_slot_key(changed, HEADER) != base
    assert fact_slot_key({**ROW, "segments": ""}, HEADER) != base
    absent = {k: v for k, v in ROW.items() if k != "segments"}
    assert fact_slot_key(absent, OLD_HEADER) != fact_slot_key(
        {**absent, "segments": ""}, HEADER
    )
    assert fact_slot_key({**ROW, "segments": None}, HEADER) != fact_slot_key(
        {**ROW, "segments": ""}, HEADER
    )
    with pytest.raises(ValueError, match="PRESENT_FIELD_NOT_PARSED"):
        fact_slot_key(absent, HEADER)


def test_conflicting_and_identical_assertions_both_survive():
    slot = fact_slot_key(ROW, HEADER)
    other_value = {**ROW, "value": "18133000.0000"}
    assert fact_slot_key(other_value, HEADER) == slot
    left = occurrence_key("SRC000064", "num.txt", MEMBER_SHA, 551554342, 168)
    right = occurrence_key("SRC000064", "num.txt", MEMBER_SHA, 551554510, 168)
    assert assertion_key(slot, left, "M1_V1") != assertion_key(slot, right, "M1_V1")
    assert lexical_hashdiff(fields()) != lexical_hashdiff(fields(other_value))
    # Even an exact-equal payload at another byte interval is a separate child.
    assert lexical_hashdiff(fields()) == lexical_hashdiff(fields(deepcopy(ROW)))
    assert left != right


def test_replay_and_hashdiff_are_stable_but_detect_payload_drift():
    slot = fact_slot_key(ROW, HEADER)
    first = occurrence_key("SRC000064", "num.txt", MEMBER_SHA, 551554342, 168)
    assert first == occurrence_key("SRC000064", "num.txt", MEMBER_SHA, 551554342, 168)
    assert assertion_key(slot, first, "M1_V1") == assertion_key(slot, first, "M1_V1")
    assert first != occurrence_key("SRC000065", "num.txt", MEMBER_SHA, 551554342, 168)
    assert first != occurrence_key("SRC000064", "num.txt", "b" * 64, 551554342, 168)
    base = lexical_hashdiff(fields())
    assert base != lexical_hashdiff(fields({**ROW, "value": "12458000.0001"}))
    assert base != lexical_hashdiff(fields({**ROW, "footnote": "text"}))
    with pytest.raises(ValueError, match="INVALID_FIELD_STATE_OR_ORDER"):
        lexical_hashdiff(((2, "value", "PRESENT", "1"),))


def test_lossless_counts_lineage_and_replay_conflict():
    slot = fact_slot_key(ROW, HEADER)
    occurrence = occurrence_key("SRC000064", "num.txt", MEMBER_SHA, 100, 80)
    record = {"occurrence_hk": occurrence, "source_instance_id": "SRC000064",
              "source_line": 2, "byte_offset": 100,
              "byte_length": 80, "raw_sha256": "c" * 64, "member_sha256": MEMBER_SHA,
              "binding_sha256": "d" * 64, "raw_path": "raw.zip",
              "archive_member": "num.txt", "payload_hashdiff": lexical_hashdiff(fields()),
              "record_kind": "DATA", "fields": fields(), "fact_slot_hk": slot}
    validate_lossless((record,), 1, len(HEADER))
    # Separate load attempts validate the same source occurrence at its original grain.
    validate_lossless(({**record, "run_id": "replay"},), 1, len(HEADER))
    with pytest.raises(ValueError, match="DUPLICATE_OCCURRENCE_IN_BATCH"):
        validate_lossless((record, {**record, "run_id": "replay"}),
                          2, 2 * len(HEADER))
    with pytest.raises(ValueError, match="REPLAY_DRIFT"):
        changed = fields({**ROW, "value": "18133000.0000"})
        validate_lossless((record, {**record, "fields": changed,
                                    "payload_hashdiff": lexical_hashdiff(changed)}),
                          2, 2 * len(HEADER))
    with pytest.raises(ValueError, match="MISSING_LINEAGE"):
        validate_lossless(({**record, "binding_sha256": None},), 1, len(HEADER))
    with pytest.raises(ValueError, match="LOSSLESS_COUNT_MISMATCH"):
        validate_lossless((record,), 2, 2 * len(HEADER))
    with pytest.raises(ValueError, match="FIELD_ORDER_MISMATCH"):
        validate_lossless(({**record, "fields": fields()[::-1]},), 1, len(HEADER))


def test_approved_m1_m2_contracts_are_only_referenced():
    # This scope test intentionally reads no RAW or Delta table and writes nothing.
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    contract = (root / "docs/vault_load_contract_v1.md").read_text()
    assert "VERSION AS OF 0" in contract
    assert "M2_ADDITIVE_TYPED_NUMERIC_V1" in contract
    assert "EXACT_DECIMAL_38_4_V1" in contract
    assert "FSDS_NUM_VALUE_SCOPE_V1" in contract
    assert "M3 versions require separately established applicability" in contract
