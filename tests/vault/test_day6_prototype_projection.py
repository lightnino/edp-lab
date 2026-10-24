"""Synthetic controls for the bounded, pinned M1-to-Vault adapter."""
from __future__ import annotations

from copy import deepcopy

import pytest

from edp_lab.vault.prototype import HEADER, project, validate_batch

SID = "SRC000064"
APPROVED = {SID: {"run_id": "num_recovery_20261021_v1_recovery",
                  "raw_sha256": "a" * 64, "member_sha256": "b" * 64,
                  "binding_sha256": "c" * 64,
                  "parser_profile_id": "C300_FSDS_NUM_QUOTE_BOUNDARY_V1",
                  "parser_version": "C300_FSDS_NUM_QUOTE_BOUNDARY_V1",
                  "model_version": "M1_LEXICAL_V1",
                  "rule_version": "C300_FSDS_NUM_QUOTE_BOUNDARY_V1"}}
VALUES = ("0001918712-25-000092", "DerivativeAssetNotionalAmount", "us-gaap/2025",
          "20241231", "0", "AUD", "axis=member;", "", "12458000.0000", "")


def source_row(offset=551554342, values=VALUES):
    return {"source_instance_id": SID, "run_id": APPROVED[SID]["run_id"],
            "raw_path": "data/raw/approved.zip", "raw_sha256": "a" * 64,
            "archive_member": "num.txt", "member_sha256": "b" * 64,
            "binding_sha256": "c" * 64, "source_line": 3723930,
            "byte_offset": offset, "byte_length": 168,
            "m1_fields": [{"field_ordinal": i, "original_name": name,
                           "lexical_value": value, "disposition": "DIRECT_MAP"}
                          for i, (name, value) in enumerate(zip(HEADER, values, strict=True), 1)]}


def test_two_physical_occurrences_remain_distinct_at_same_slot():
    left = project(source_row(), APPROVED)
    right = project(source_row(551554510), APPROVED)
    assert left["fact_slot_hk"] == right["fact_slot_hk"]
    assert left["payload_hashdiff"] == right["payload_hashdiff"]
    assert left["occurrence_hk"] != right["occurrence_hk"]
    assert left["assertion_hk"] != right["assertion_hk"]
    validate_batch([left, right])


def test_payload_drift_does_not_change_business_slot():
    values = (*VALUES[:8], "18133000.0000", VALUES[9])
    before = project(source_row(), APPROVED)
    after = project(source_row(values=values), APPROVED)
    assert before["fact_slot_hk"] == after["fact_slot_hk"]
    assert before["occurrence_hk"] == after["occurrence_hk"]
    assert before["payload_hashdiff"] != after["payload_hashdiff"]
    with pytest.raises(ValueError, match="DUPLICATE_OR_DRIFTED_OCCURRENCE"):
        validate_batch([before, after])


@pytest.mark.parametrize("mutation,reason", [
    (lambda x: x["m1_fields"].reverse(), "FIELD_ORDER_OR_WIDTH"),
    (lambda x: x["m1_fields"][0].update(lexical_value=""), "MISSING_BUSINESS_KEY"),
    (lambda x: x.update(member_sha256="d" * 64), "UNAPPROVED_SOURCE_OR_BINDING"),
    (lambda x: x.update(archive_member="sub.txt"), "UNAPPROVED_MEMBER"),
])
def test_reject_unpromotable_input(mutation, reason):
    row = deepcopy(source_row())
    mutation(row)
    with pytest.raises(ValueError, match=reason):
        project(row, APPROVED)


def test_blank_m2_is_additive_and_lexical():
    row = source_row(values=(*VALUES[:8], "", VALUES[9]))
    projected = project(row, APPROVED)
    assert projected["m2_outcome"] == "BLANK"
    assert projected["m2_decimal"] is None
    assert projected["value_lexical"] == ""
