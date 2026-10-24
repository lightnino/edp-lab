"""Negative authority and deterministic load-plan controls; no live writes."""
from __future__ import annotations

import copy
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.vault.load_plan import NAMESPACE, TABLES, render_v2
from edp_lab.vault.protected_readback import _normalized
from edp_lab.vault.protected_sql import _reserve_statement_budget
from edp_lab.vault.raw_verify import verify_selected
from edp_lab.vault.standing_authority import signed_policy

ROOT = Path(__file__).resolve().parents[2]
def test_withdrawn_c1500_has_no_active_authorization():
    assert not (ROOT / "metadata/authorizations/day6_vault_c1500_prototype_exception_v1.json").exists()
    assert not (ROOT / "metadata/operating/day6_vault_dev_policy_proposal_v1.json").exists()
    assert json.loads((ROOT / "metadata/operating/day6_vault_step2_pause_v1.json").read_text())[
        "status"] == "WITHDRAWN_UNEXERCISED"


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


def test_v2_renderer_uses_synthetic_rows_without_local_manifests():
    rows = projected_rows()
    counts = {name: 0 for name in TABLES}
    counts.update({"h_filing": 1, "h_concept": 1, "l_fact_slot": 1,
                   "r_source_occurrence": 127, "s_fact_assertion": 127,
                   "s_num_m2_value": 127, "vault_reject_quarantine": 6})
    plan = render_v2(rows, cohort_id="SYNTHETIC_TEST", input_manifest_sha256="a" * 64,
                     expected_table_counts=counts, synthetic_negatives=True)
    assert plan["schema"] == "EDP_VAULT_LOAD_PLAN_V2"
    assert plan["data_occurrences"] == 127
    assert plan["synthetic_rows"] == 6
    assert plan["expected_tables"]["r_load_event"]["rows"] == []
    assert all(stage["table"] != f"{NAMESPACE}.r_load_event" for stage in plan["stages"])
    assert all(stage["statement"].startswith("MERGE INTO " + NAMESPACE)
               and "WHEN NOT MATCHED THEN INSERT" in stage["statement"]
               and "WHEN MATCHED THEN" not in stage["statement"] for stage in plan["stages"])


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
