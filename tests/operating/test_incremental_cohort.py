"""Cohort growth stays source-disjoint without RAW uploads or old rewrites."""

from __future__ import annotations

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.operating.incremental_cohort import plan_increment


def fixture():
    members = [
        {"identity": "old", "raw_sha256": "a" * 64,
         "raw_path": "raw/old", "holdout": False},
        {"identity": "fresh", "raw_sha256": "b" * 64,
         "raw_path": "raw/fresh", "holdout": False},
        {"identity": "held", "raw_sha256": "c" * 64,
         "raw_path": "raw/held", "holdout": True},
    ]
    old = [{"source_identity": "old", "source_instance_id": "SRC001"}]
    incoming = [{"source_identity": "fresh", "source_instance_id": "SRC002",
                 "raw_sha256": "b" * 64, "raw_path": "raw/fresh",
                 "remote_raw_path": "dbfs:/Volumes/verified/raw/fresh",
                 "raw_handoff_receipt_sha256": "d" * 64}]
    return old, incoming, members


def invoke(old=None, incoming=None, members=None, *, expected_increment=1):
    original_old, original_incoming, original_members = fixture()
    return plan_increment(
        original_old if old is None else old,
        original_incoming if incoming is None else incoming,
        original_members if members is None else members,
        previous_cohort=f"C{len(original_old if old is None else old)}",
        new_cohort=f"C{len(original_old if old is None else old) + len(original_incoming if incoming is None else incoming)}",
        expected_increment=expected_increment, pinned_universe_sha256="e" * 64,
    )


def test_minimal_increment_reuses_history_without_raw_writes():
    plan = invoke()
    assert (plan["old_count"], plan["new_count"], plan["combined_count"]) == (1, 1, 2)
    assert plan["raw_write_operations"] == 0
    assert plan["historical_result_rewrite"] is False
    assert plan["status"] == "PREPARED_NOT_ADMITTED"


@pytest.mark.parametrize("change,reason", [
    ({"source_identity": "old"}, "INCREMENT_OVERLAP"),
    ({"source_instance_id": "SRC001"}, "INCREMENT_OVERLAP"),
    ({"source_identity": "held", "raw_sha256": "c" * 64,
      "raw_path": "raw/held"}, "INCREMENT_NOT_APPROVED_OR_HOLDOUT"),
    ({"source_identity": "not-approved"}, "INCREMENT_NOT_APPROVED_OR_HOLDOUT"),
    ({"raw_sha256": "0" * 64}, "INCREMENT_RAW_IDENTITY_MISMATCH"),
    ({"raw_path": "wrong-location"}, "INCREMENT_RAW_IDENTITY_MISMATCH"),
    ({"remote_raw_path": ""}, "RAW_HANDOFF_MISSING"),
    ({"raw_handoff_receipt_sha256": ""}, "INVALID_SOURCE_SHA256"),
])
def test_failed_admission_invariant(change, reason):
    old, incoming, members = fixture()
    incoming[0].update(change)
    with pytest.raises(Denied, match=reason):
        invoke(old, incoming, members)


def test_requires_exact_increment_count():
    with pytest.raises(Denied, match="INCREMENT_COUNT_MISMATCH"):
        invoke(expected_increment=2)


def test_duplicate_in_increment():
    old, incoming, members = fixture()
    duplicate = {**incoming[0], "source_instance_id": "SRC003"}
    with pytest.raises(Denied, match="INCREMENT_OVERLAP"):
        invoke(old, incoming + [duplicate], members, expected_increment=2)


def test_duplicate_old_baseline():
    old, incoming, members = fixture()
    with pytest.raises(Denied, match="PRIOR_COHORT_NOT_UNIQUE"):
        invoke(old + old, incoming, members)


def test_source_identity_must_be_explicit():
    old, incoming, members = fixture()
    del incoming[0]["source_identity"]
    with pytest.raises(Denied, match="MISSING_PHYSICAL_IDENTITY"):
        invoke(old, incoming, members)
