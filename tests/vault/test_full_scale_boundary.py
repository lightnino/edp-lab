"""Focused fail-closed checks for proposed full-scale protected requests."""

import copy

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.vault.full_scale_boundary import validate_batch, validate_freeze_candidate
from edp_lab.vault.standing_v2 import NAMESPACE

SHA = "a" * 64


def _authority():
    return {"source_ids": ["SRC000005", "SRC000065"],
            "target_tables": ["h_filing", "r_source_occurrence"],
            "source_manifest_sha256": SHA, "runtime_sha256": SHA,
            "contracts": {"SEC_FSDS_NUM_V1": SHA},
            "max_data_rows": 1_000_000, "timeout_seconds": 3600}


def _batch():
    return {"schema": "EDP_VAULT_SPARK_BATCH_V1", "cohort": "C2000",
            "namespace": NAMESPACE, "source_ids": ["SRC000005"],
            "source_manifest_sha256": SHA, "contracts": {"SEC_FSDS_NUM_V1": SHA},
            "target_tables": ["h_filing", "r_source_occurrence"],
            "runtime_sha256": SHA, "batch_id": "c2000_batch_001",
            "max_data_rows": 500_000, "timeout_seconds": 1800,
            "max_retries": 0, "mode": "INSERT_ONLY"}


def test_batch_requires_exact_authorized_scope_and_zero_retry():
    request = _batch()
    validate_batch(request, _authority())
    mutations = [
        ("source_ids", ["SRC000006"]),
        ("target_tables", ["h_filing", "other_schema"]),
        ("max_data_rows", 1_000_001),
        ("max_retries", 1),
        ("runtime_sha256", "b" * 64),
        ("mode", "OVERWRITE"),
    ]
    for key, value in mutations:
        invalid = copy.deepcopy(request)
        invalid[key] = value
        with pytest.raises(Denied):
            validate_batch(invalid, _authority())


def test_freeze_requires_every_table_and_source_with_live_pins():
    table = {"uc_table_id": "uc-1", "delta_version": 1, "row_count": 10,
             "history_sha256": SHA, "readback_sha256": SHA}
    candidate = {"schema": "EDP_VAULT_FREEZE_CANDIDATE_V1", "cohort": "C2000",
                 "namespace": NAMESPACE, "source_manifest_sha256": SHA,
                 "contracts": {"SEC_FSDS_NUM_V1": SHA},
                 "tables": {"h_filing": table, "r_source_occurrence": table},
                 "source_coverage": {"SRC000005": "LOADED", "SRC000065": "UNSUPPORTED"},
                 "status": "LIVE_READBACK_COMPLETE"}
    validate_freeze_candidate(candidate, _authority())
    for field in ("tables", "source_coverage"):
        invalid = copy.deepcopy(candidate)
        invalid[field].pop(next(iter(invalid[field])))
        with pytest.raises(Denied):
            validate_freeze_candidate(invalid, _authority())
    invalid = copy.deepcopy(candidate)
    invalid["tables"]["h_filing"]["delta_version"] = -1
    with pytest.raises(Denied):
        validate_freeze_candidate(invalid, _authority())
