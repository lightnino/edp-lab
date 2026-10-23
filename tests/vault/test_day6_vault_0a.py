"""Negative authority and deterministic load-plan controls; no live writes."""
from __future__ import annotations

import copy
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.vault.load_plan import NAMESPACE, render
from edp_lab.vault.protected_readback import _expected, _normalized
from edp_lab.vault.protected_sql import _reserve_statement_budget
from edp_lab.vault.raw_verify import verify_selected
from edp_lab.vault.standing_authority import signed_policy, validate_policy

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = json.loads((ROOT / "metadata/operating/day6_vault_dev_policy_proposal_v1.json").read_text())


@pytest.mark.parametrize("change", [
    {"namespace": "workspace.edp_lab"},
    {"source_ids": ["SRC000005", "SRC000054", "SRC000065"]},
    {"tables": [*PROPOSAL["tables"], "day5_table"]},
    {"max_data_occurrences": 1000},
    {"max_sql_statements": 10000},
    {"day5_resources_allowed": True},
    {"c2000_integration_allowed": True},
    {"requires_independent_readback_receipts": False},
])
def test_policy_scope_expansion_denied_before_file_access(change):
    policy = {**PROPOSAL, **change}
    with pytest.raises(Denied, match="VAULT_POLICY_SCOPE_CHANGED"):
        validate_policy(ROOT, policy, ROOT / "missing-sample", ROOT / "missing-projection",
                        ROOT / "missing-plan")


def projected_rows():
    base = {"filing_hk": "f" * 64, "concept_hk": "c" * 64,
            "fact_slot_hk": "s" * 64, "adsh": "0001", "tag": "ExactTag",
            "version": "us-gaap/2025", "context_json": "{}",
            "source_instance_id": "SRC000064", "archive_member": "num.txt",
            "member_sha256": "a" * 64, "byte_offset": 10, "byte_length": 20,
            "source_line": 2, "raw_path": "data/raw/approved.zip",
            "raw_sha256": "b" * 64, "binding_sha256": "c" * 64,
            "run_id": "pinned", "fields_json": "[]",
            "parser_contract_version": "C300_FSDS_NUM_QUOTE_BOUNDARY_V1",
            "parser_profile_id": "C300_FSDS_NUM_QUOTE_BOUNDARY_V1",
            "m1_model_version": "M1_LEXICAL_V1",
            "m1_rule_version": "C300_FSDS_NUM_QUOTE_BOUNDARY_V1",
            "payload_hashdiff": "d" * 64, "value_lexical": "9.0000",
            "footnote_lexical": "quote ' and UTF-8 雪",
            "m2_source_rule_version": "FSDS_NUM_VALUE_SCOPE_V1",
            "m2_model_version": "M2_ADDITIVE_TYPED_NUMERIC_V1",
            "m2_rule_version": "EXACT_DECIMAL_38_4_V1", "m2_decimal": "9.0000",
            "m2_outcome": "VALID", "m2_reason": "EXACT_PROJECTION"}
    return [{**base, "occurrence_hk": f"{i:064x}", "assertion_hk": f"{i + 127:064x}",
             "byte_offset": 10 + i * 20, "source_line": i + 2} for i in range(127)]


def test_plan_is_fixed_target_insert_only_and_utf8_lossless():
    rows = projected_rows()
    plan = render(rows)
    assert len(plan["stages"]) == 9
    assert plan == render(copy.deepcopy(rows))
    assert {stage["table"].split(".")[-1] for stage in plan["stages"]} == set(
        PROPOSAL["tables"])
    for stage in plan["stages"]:
        assert stage["statement"].startswith("MERGE INTO " + NAMESPACE)
        assert "WHEN NOT MATCHED THEN INSERT" in stage["statement"]
        assert "WHEN MATCHED THEN" not in stage["statement"]
        assert "<=>" in stage["precheck"]
        assert "quote ' and UTF-8 雪" not in stage["statement"]
    assert "71756f7465202720616e64205554462d3820e99baa" in plan["stages"][4]["statement"]
    with pytest.raises(ValueError, match="PINNED_SAMPLE_SIZE"):
        render(rows[:-1])
    expected = _expected(rows)
    assert len(expected["r_source_occurrence"]) == 127
    assert len(expected["s_fact_assertion"]) == 127
    assert len(expected["r_load_event"]) == 254
    assert len(expected["vault_reject_quarantine"]) == 6


def test_protected_raw_verifier_checks_every_selected_locator(tmp_path):
    groups = {"SRC000005": 42, "SRC000054": 42, "SRC000064": 43}
    rows = []
    for sid, count in groups.items():
        relative = Path("data/raw") / f"{sid}.zip"
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        member = b"header\n" + b"".join(f"{sid}-{i}\n".encode() for i in range(count))
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("num.txt", member)
        raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        member_hash = hashlib.sha256(member).hexdigest()
        offset = len(b"header\n")
        for index in range(count):
            line = f"{sid}-{index}\n".encode()
            rows.append({"source_instance_id": sid, "raw_path": str(relative),
                         "raw_sha256": raw_hash, "archive_member": "num.txt",
                         "member_sha256": member_hash, "source_line": index + 2,
                         "byte_offset": offset, "byte_length": len(line)})
            offset += len(line)
    result = verify_selected(tmp_path, rows)
    assert sum(item["selected_locators_verified"] for item in result.values()) == 127
    changed = copy.deepcopy(rows)
    changed[0]["byte_offset"] += 1
    with pytest.raises(ValueError, match="SELECTED_BYTE_LOCATOR_MISSING"):
        verify_selected(tmp_path, changed)


def test_sql_statement_budget_is_durable_and_fails_closed(tmp_path):
    base = tmp_path / "protected"
    (base / "trust").mkdir(parents=True)
    (base / "ledger").mkdir()
    (base / "trust/policy.signed.json").write_text(json.dumps({
        "document": {"max_sql_statements": 2, "max_runtime_seconds": 60}}))
    _reserve_statement_budget(base)
    _reserve_statement_budget(base)
    with pytest.raises(Denied, match="VAULT_SQL_STATEMENT_CAP_EXHAUSTED"):
        _reserve_statement_budget(base)
    assert json.loads((base / "ledger/sql_statement_budget.json").read_text())["used"] == 2


def test_agent_writable_trust_cannot_activate_owner_policy(tmp_path):
    trust = tmp_path / "trust"
    trust.mkdir()
    policy = trust / "policy.signed.json"
    policy.write_text("{}")
    with pytest.raises(Denied, match="VAULT_OWNER_CONTROL_NOT_ESTABLISHED"):
        signed_policy(ROOT, policy, trust)


def test_delta_boolean_readback_matches_lexical_expected():
    assert _normalized([[True, False, None]]) == _normalized([["true", "false", None]])
