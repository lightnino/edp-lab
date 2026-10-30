"""Pinned approved semantics and bounded V3 request remain distinct from grants."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(relative):
    return json.loads((ROOT / relative).read_bytes())


def _sha(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def test_unsigned_owner_document_pins_all_contracts_and_no_execution_grant():
    request = _load("metadata/authorizations/day6_c2000_full_semantics_owner_decision_v1.unsigned.json")
    assert request["signature_status"] == "PENDING_OWNER_CONTROLLED_SIGNATURE"
    assert "signature_base64" not in request
    document = request["document"]
    assert document["status"] == "APPROVED"
    assert len(document["contract_pins"]) == 5
    for pin in document["contract_pins"]:
        assert _sha(pin["path"]) == pin["sha256"]
    assert "new Delta writes" in document["exclusions"]


def test_v3_selection_and_authority_boundary_are_exact():
    plan = _load("metadata/operating/day6_c2000_vault_v3_bounded_request.json")
    selected = plan["selection"]
    assert _sha(selected["path"]) == selected["sha256"]
    manifest = _load(selected["path"])
    assert manifest["selected_data_rows"] == 2047
    assert sorted(manifest["sources"]) == sorted(selected["source_ids"])
    assert manifest["accepted_fsds_num_prototype_reused_data_rows"] == 127
    parents = manifest["sources"]["SRC000065"]["members"]["SUBMISSION.tsv"]
    assert parents["selected_data_rows"] == 46
    assert parents["selected_child_accessions"] == 30
    assert _sha(plan["negative_oracles"]["path"]) == plan["negative_oracles"]["sha256"]
    assert len(_load(plan["negative_oracles"]["path"])["rules"]) == 24
    assert len(plan["new_v3_table_allowlist"]) == 23
    assert len(set(plan["new_v3_table_allowlist"])) == 23
    assert all(name.startswith("v3_") for name in plan["new_v3_table_allowlist"])
    assert plan["execution"]["automatic_retries_max"] == 0
    assert plan["execution"]["job_submissions_max"] == 10000000
    deployment = "metadata/operating/day6_c2000_vault_v3_deployment_v2.json"
    assert _sha(deployment) == plan["execution"]["deployment_sha256"]
    assert (_load(deployment)["artifact"]["sha256"] ==
            plan["execution"]["runtime_artifact_sha256"])
    assert _sha(plan["target_ddl"]["path"]) == plan["target_ddl"]["sha256"]
    assert _sha(plan["resource_proposal"]["path"]) == plan["resource_proposal"]["sha256"]
    assert plan["execution"]["protected_grant_id"] is None
