"""Fixed V3 selection, isolated negative controls and readback boundaries."""

import json
from pathlib import Path

import pytest

from edp_lab.vault.v3_ddl import TABLES, plan
from edp_lab.vault.v3_oracles import evaluate
from edp_lab.vault.v3_readback import _rows_digest
from edp_lab.vault.v3_spark_runtime import _ordinals

ROOT = Path(__file__).resolve().parents[2]


def test_all_pinned_isolated_oracles_pass_without_delta():
    spec = json.loads((ROOT / "metadata/evaluations/"
                       "day6_c2000_vault_v3_negative_oracles_v1.json").read_bytes())
    assert set(evaluate()) == {rule["id"] for rule in spec["rules"]}


def test_edgar_and_parent_ordinals_are_exact():
    selected = json.loads((ROOT / "metadata/evaluations/"
                           "day6_c2000_vault_v3_selection_v1.json").read_bytes())
    sources = selected["sources"]
    edgar = sources["SRC000107"]["members"]["daily_master.idx"]
    assert _ordinals(edgar) == list(range(1, 17)) + [437, 438]
    submission = sources["SRC000065"]["members"]["SUBMISSION.tsv"]
    assert len(_ordinals(submission)) == 46
    with pytest.raises(ValueError, match="V3_ROW_ORDINALS_INVALID"):
        _ordinals({"data_row_ordinals": [1, 1], "selected_data_rows": 2,
                   "duplicate_witness_pair": [1, 1]})


def test_ddl_exact_table_allowlist():
    request = json.loads((ROOT / "metadata/operating/"
                          "day6_c2000_vault_v3_bounded_request_v1.json").read_bytes())
    assert tuple(request["new_v3_table_allowlist"]) == TABLES
    assert len(plan(request["new_v3_table_allowlist"])["tables"]) == 23
    with pytest.raises(ValueError, match="V3_TABLE_ALLOWLIST_CHANGED"):
        plan(list(TABLES[:-1]) + ["v3_wrong_table"])


def test_readback_digest_is_order_invariant_and_payload_sensitive():
    row = {"hk": "a", "occurrence_hk": "b", "source_instance_id": "SRC000005",
           "archive_member": "pre.txt", "source_line": 2, "byte_offset": 4,
           "byte_length": 5, "raw_sha256": "a" * 64, "member_sha256": "b" * 64,
           "contract_version": "FSDS_OTHER_V1", "payload_json": '{"x":"1"}'}
    other = dict(row, hk="c")
    assert _rows_digest([row, other]) == _rows_digest([other, row])
    assert _rows_digest([row]) != _rows_digest([dict(row, payload_json='{"x":"2"}')])
