"""Reusable Vault standing-authority negatives; no live Databricks writes."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.vault.broker_v2 import (
    _prepare_socket,
    _protected,
    _reserve_grant_budget,
    verify_grant_envelope,
)
from edp_lab.vault.credential_rotation import _rotate_file, rotate_config
from edp_lab.vault.eligibility_v2 import receipt_from_owner_approval
from edp_lab.vault.executor_v2 import _audit_sql
from edp_lab.vault.load_plan import render, render_v2
from edp_lab.vault.protected_sql import _reserve_statement_budget
from edp_lab.vault.standing_v2 import (
    NAMESPACE,
    TABLES,
    authorize_stage,
    grant_for_run,
    pinned_path,
    validate_cohort_receipt,
    validate_run,
    validate_standing_policy,
)
from edp_lab.vault.verifier_v2 import COLS, _where
from edp_lab.vault.verifier_v2 import _expected as expected_readback

ROOT = Path(__file__).resolve().parents[2]
POLICY = json.loads((ROOT / "metadata/operating/vault_standing_policy_v2_proposal.json").read_text())
NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)


def _pin(root: Path, name: str) -> dict:
    path = root / name
    path.write_text(name)
    return {"path": name, "sha256": hashlib.sha256(name.encode()).hexdigest()}


def _receipt(root: Path, cohort: str) -> dict:
    for pin in (*POLICY["contracts"], *POLICY["mapping_rules"]):
        target = root / pin["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / pin["path"]).read_bytes())
    pins = {name: _pin(root, f"{cohort}-{name}.json") for name in
            ("freeze", "source_manifest", "approval", "input_manifest", "load_plan")}
    return {"schema": "EDP_VAULT_COHORT_ELIGIBILITY_V1",
            "authority": "protected-verifier-v1", "status": "VERIFIED_FROZEN",
            "cohort_id": cohort, "namespace": NAMESPACE, "tables": list(TABLES),
            "workload_kind": "BOUNDED_PROTOTYPE",
            "contract": POLICY["contracts"][0], "mapping_rule": POLICY["mapping_rules"][0],
            "issued_at": NOW.isoformat(),
            "expires_at": (NOW + timedelta(days=30)).isoformat(),
            "data_occurrence_limit": 200, "synthetic_row_limit": 6,
            "independent_freeze_receipt_sha256": "f" * 64,
            "sources": {f"SRC-{cohort}": "a" * 64}, **pins,
            "input_manifest_sha256": pins["input_manifest"]["sha256"],
            "load_plan_sha256": pins["load_plan"]["sha256"]}


def _run(receipt: dict, run_id: str) -> dict:
    return {"schema": "EDP_VAULT_RUN_REQUEST_V1", "cohort_id": receipt["cohort_id"],
            "workload_kind": receipt["workload_kind"],
            "run_id": run_id, "event_kind": "ADMITTED",
            "namespace": NAMESPACE, "tables": list(TABLES),
            "contract": receipt["contract"], "mapping_rule": receipt["mapping_rule"],
            "sources": receipt["sources"],
            "input_manifest_sha256": receipt["input_manifest_sha256"],
            "load_plan_sha256": receipt["load_plan_sha256"],
            "data_occurrences": 127, "synthetic_rows": 6,
            "max_statements": 60, "max_runtime_seconds": 3600}


def test_policy_is_cohort_neutral_and_two_cohorts_need_no_reinstall(tmp_path):
    validate_standing_policy(POLICY, now=NOW)
    assert "C1500" not in json.dumps(POLICY)
    assert POLICY["expires_at"] != "2026-11-01T00:00:00+00:00"
    grants = []
    for cohort in ("C1500", "FUTURE_APPROVED"):
        receipt = _receipt(tmp_path, cohort)
        validate_cohort_receipt(POLICY, receipt, tmp_path, now=NOW)
        run = _run(receipt, f"vault-run-{cohort}")
        grants.append(grant_for_run(POLICY, receipt, run, now=NOW))
    assert grants[0]["grant_id"] != grants[1]["grant_id"]
    assert all(datetime.fromisoformat(g["expires_at"]) <= NOW + timedelta(hours=1)
               for g in grants)


@pytest.mark.parametrize("change", [
    {"namespace": "workspace.edp_lab"},
    {"tables": [*TABLES, "day5_queue"]},
    {"day5_resources_allowed": True},
    {"raw_writes_allowed": True},
    {"c2000_full_integration_allowed": True},
    {"destructive_sql_allowed": True},
    {"max_run_statements": 10000},
    {"max_retries_per_statement": 1},
    {"contracts": [{"version": "UNAPPROVED", "path": "docs/new.md", "sha256": "a" * 64}]},
])
def test_standing_boundary_denials(change):
    proposal = {**POLICY, **change}
    if "contracts" in change:
        validate_standing_policy(proposal, now=NOW)
        assert proposal["contracts"] != POLICY["contracts"]
    else:
        with pytest.raises(Denied):
            validate_standing_policy(proposal, now=NOW)


def test_unapproved_or_changed_cohort_denied(tmp_path):
    receipt = _receipt(tmp_path, "C1500")
    for field, value in (("status", "UNVERIFIED"), ("namespace", "workspace.edp_lab"),
                         ("contract", {"version": "UNAPPROVED", "path": "docs/new.md",
                                       "sha256": "b" * 64}),
                         ("mapping_rule", {"version": "NEW", "path": "docs/new.md",
                                           "sha256": "c" * 64})):
        changed = {**receipt, field: value}
        with pytest.raises(Denied):
            validate_cohort_receipt(POLICY, changed, tmp_path, now=NOW)
    (tmp_path / receipt["freeze"]["path"]).write_text("changed")
    with pytest.raises(Denied, match="VAULT_COHORT_PIN_CHANGED"):
        validate_cohort_receipt(POLICY, receipt, tmp_path, now=NOW)


def test_full_integration_requires_owner_policy_expansion(tmp_path):
    receipt = _receipt(tmp_path, "C2000")
    receipt["workload_kind"] = "FULL_INTEGRATION"
    with pytest.raises(Denied, match="VAULT_COHORT_RECEIPT_SCOPE_INVALID"):
        validate_cohort_receipt(POLICY, receipt, tmp_path, now=NOW)


@pytest.mark.parametrize("name", ["protected:../plan.json", "protected:/plan.json",
                                        "protected:plan/other.json", "protected:plan.txt"])
def test_protected_artifact_path_rejects_escape_or_wrong_type(tmp_path, name):
    with pytest.raises(Denied, match="VAULT_PROTECTED_ARTIFACT_PATH_INVALID"):
        pinned_path(tmp_path, name, tmp_path / "protected")


def test_run_drift_and_budget_denied(tmp_path):
    receipt = _receipt(tmp_path, "C1500")
    run = _run(receipt, "vault-run-c1500")
    for field, value in (("cohort_id", "C2000"), ("sources", {"SRC-X": "a" * 64}),
                         ("max_statements", 101), ("data_occurrences", 1001),
                         ("load_plan_sha256", "0" * 64)):
        changed = {**run, field: value}
        with pytest.raises(Denied, match="VAULT_RUN_OUT_OF_SCOPE"):
            validate_run(POLICY, receipt, changed)


def test_stage_sql_and_uncertain_replay_denied(tmp_path):
    receipt = _receipt(tmp_path, "C1500")
    grant = grant_for_run(POLICY, receipt, _run(receipt, "vault-run-c1500"), now=NOW)
    sql = f"MERGE INTO {NAMESPACE}.h_filing AS t\nUSING source AS s\nON t.id=s.id\nWHEN NOT MATCHED THEN INSERT *"
    stage = {"operation_id": "vault-run-c1500-stage1", "kind": "MERGE_INSERT_ONLY",
             "table": f"{NAMESPACE}.h_filing", "statement": sql,
             "statement_sha256": hashlib.sha256(sql.encode()).hexdigest(),
             "load_plan_sha256": grant["load_plan_sha256"]}
    authorize_stage(grant, stage, used_statements=0, uncertain_operation_ids=set())
    for mutation in ({"table": "workspace.edp_lab.day5_queue"},
                     {"statement": "DROP TABLE workspace.edp_lab.day5_queue"},
                     {"statement": sql + "; DELETE FROM x"}):
        with pytest.raises(Denied):
            authorize_stage(grant, {**stage, **mutation}, used_statements=0,
                            uncertain_operation_ids=set())
    with pytest.raises(Denied, match="VAULT_UNCERTAIN_WRITE_REPLAY_DENIED"):
        authorize_stage(grant, stage, used_statements=0,
                        uncertain_operation_ids={stage["operation_id"]})
    with pytest.raises(Denied, match="VAULT_STAGE_OUT_OF_SCOPE"):
        authorize_stage(grant, stage, used_statements=grant["max_statements"],
                        uncertain_operation_ids=set())
    wrong_read = "SELECT * FROM workspace.edp_lab.day5_queue"
    with pytest.raises(Denied, match="VAULT_SQL_UNAUTHORIZED"):
        authorize_stage(grant, {**stage, "kind": "READBACK", "statement": wrong_read,
                                "statement_sha256": hashlib.sha256(
                                    wrong_read.encode()).hexdigest()},
                        used_statements=0, uncertain_operation_ids=set())


def test_grant_expiry_and_receipt_expiry(tmp_path):
    receipt = _receipt(tmp_path, "C1500")
    run = _run(receipt, "vault-run-c1500")
    expired = copy.deepcopy(receipt)
    expired["expires_at"] = (NOW - timedelta(seconds=1)).isoformat()
    with pytest.raises(Denied, match="VAULT_COHORT_RECEIPT_EXPIRED"):
        validate_cohort_receipt(POLICY, expired, tmp_path, now=NOW)
    with pytest.raises(Denied, match="VAULT_GRANT_WINDOW_EXHAUSTED"):
        grant_for_run(POLICY, expired, run, now=NOW)


def test_forged_expired_and_revoked_grants_denied(tmp_path):
    receipt = _receipt(tmp_path, "C1500")
    grant = grant_for_run(POLICY, receipt, _run(receipt, "vault-run-c1500"), now=NOW)
    private, public = tmp_path / "broker.pem", tmp_path / "broker.pub"
    subprocess.run(["openssl", "genpkey", "-algorithm", "Ed25519", "-out", str(private)],
                   check=True, capture_output=True)
    subprocess.run(["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)],
                   check=True, capture_output=True)
    message = tmp_path / "message"
    signature = tmp_path / "signature"
    message.write_bytes(json.dumps(grant, sort_keys=True, separators=(",", ":"),
                                  ensure_ascii=False).encode() + b"\n")
    subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(private), "-rawin",
                    "-in", str(message), "-out", str(signature)],
                   check=True, capture_output=True)
    envelope = {"grant": grant,
                "signature_base64": base64.b64encode(signature.read_bytes()).decode()}
    assert verify_grant_envelope(envelope, public, [], now=NOW) == grant
    forged = copy.deepcopy(envelope)
    forged["grant"]["namespace"] = "workspace.edp_lab"
    with pytest.raises(Denied, match="INVALID_SIGNATURE"):
        verify_grant_envelope(forged, public, [], now=NOW)
    with pytest.raises(Denied, match="VAULT_GRANT_EXPIRED_OR_INVALID"):
        verify_grant_envelope(envelope, public, [], now=NOW + timedelta(hours=1))
    with pytest.raises(Denied, match="VAULT_GRANT_REVOKED"):
        verify_grant_envelope(envelope, public, [grant["grant_id"]], now=NOW)


def test_stale_socket_restart_cannot_replace_live_service():
    with tempfile.TemporaryDirectory(prefix="v", dir="/tmp") as short:
        path = Path(short) / "broker.sock"
        with socket.socket(socket.AF_UNIX) as server:
            server.bind(str(path))
            server.listen()
            with pytest.raises(Denied, match="VAULT_BROKER_ALREADY_RUNNING"):
                _prepare_socket(path, owner_uid=os.getuid())
        _prepare_socket(path, owner_uid=os.getuid())
        assert not path.exists()
        path.write_text("forged")
        with pytest.raises(Denied, match="VAULT_BROKER_SOCKET_UNTRUSTED"):
            _prepare_socket(path, owner_uid=os.getuid())


def test_credential_rotation_preserves_old_secret_on_failed_probe(tmp_path):
    config = tmp_path / "databrickscfg"
    original = "[vault-dev]\nclient_secret = OLD\n"
    replacement = "[vault-dev]\nclient_secret = NEW\n"
    config.write_text(original)
    with pytest.raises(Denied, match="VAULT_NEW_CREDENTIAL_PROBE_FAILED"):
        _rotate_file(config, replacement, lambda staged: False)
    assert config.read_text() == original
    _rotate_file(config, replacement, lambda staged: staged.read_text() == replacement)
    assert config.read_text() == replacement
    with pytest.raises(Denied, match="VAULT_CREDENTIAL_BOUNDARY_REQUIRED"):
        rotate_config(config, original, lambda staged: True)


def test_successive_run_audits_have_distinct_execution_identity(tmp_path):
    receipt = _receipt(tmp_path, "C1500")
    first = _run(receipt, "vault-run-first")
    second = {**first, "run_id": "vault-run-replay", "event_kind": "REPLAY"}
    grants = [grant_for_run(POLICY, receipt, run, now=NOW) for run in (first, second)]
    plan = {"expected_tables": {"r_source_occurrence": {
        "rows": [["a" * 64], ["b" * 64]]}}}
    for grant in grants:
        grant["data_occurrences"] = 2
    first_sql = _audit_sql(plan, grants[0])
    second_sql = _audit_sql(plan, grants[1])
    assert first_sql[3] == second_sql[3] == 2
    assert first_sql[1] != second_sql[1]
    assert "WHEN NOT MATCHED THEN INSERT" in first_sql[1]
    assert "WHEN MATCHED THEN" not in second_sql[1]


def test_v2_sql_budget_is_per_run_and_durable(tmp_path):
    base = tmp_path / "protected"
    (base / "trust").mkdir(parents=True)
    (base / "ledger").mkdir()
    (base / "trust/policy.signed.json").write_text(json.dumps({"document": POLICY}))
    first = {"run_sha256": "a" * 64, "max_statements": 2,
             "max_runtime_seconds": 60}
    second = {**first, "run_sha256": "b" * 64}
    _reserve_statement_budget(base, first)
    _reserve_statement_budget(base, first)
    with pytest.raises(Denied, match="VAULT_SQL_STATEMENT_CAP_EXHAUSTED"):
        _reserve_statement_budget(base, first)
    _reserve_statement_budget(base, second)
    assert len(list((base / "ledger").glob("sql-*.json"))) == 2
    with pytest.raises(Denied, match="VAULT_RUN_SQL_BUDGET_INVALID"):
        _reserve_statement_budget(base, {**first, "run_sha256": "../bad"})


def test_standing_grant_and_sql_caps_are_durable(tmp_path):
    base = tmp_path / "protected"
    (base / "trust").mkdir(parents=True)
    (base / "ledger").mkdir()
    policy = {**POLICY, "max_total_sql_statements": 2}
    (base / "trust/policy.signed.json").write_text(json.dumps({"document": policy}))
    _reserve_grant_budget(base, 2)
    _reserve_grant_budget(base, 2)
    with pytest.raises(Denied, match="VAULT_STANDING_GRANT_CAP_EXHAUSTED"):
        _reserve_grant_budget(base, 2)
    for run_hash in ("a" * 64, "b" * 64):
        _reserve_statement_budget(base, {"run_sha256": run_hash,
                                         "max_statements": 1,
                                         "max_runtime_seconds": 60})
    with pytest.raises(Denied, match="VAULT_STANDING_SQL_CAP_EXHAUSTED"):
        _reserve_statement_budget(base, {"run_sha256": "c" * 64,
                                         "max_statements": 1,
                                         "max_runtime_seconds": 60})


def test_agent_owned_directory_cannot_host_v2_trust(tmp_path):
    with pytest.raises(Denied, match="VAULT_0A_PROTECTED_ROOT_REQUIRED"):
        _protected(ROOT, tmp_path)


def test_owner_installer_denies_unprivileged_invocation():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/owner_setup_vault_0a_v2.py"),
         "0" * 40, "0" * 64], capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode != 0
    assert "OWNER_ROOT_TERMINAL_AND_WORKTREE_REQUIRED" in result.stderr


def test_v2_client_rejects_absolute_run_path_before_socket_access():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/vault_0a_v2_client.py"),
         "grant", "/tmp/forged.json"],
        capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode != 0
    assert "VAULT_RUN_PATH_INVALID" in result.stderr


def test_owner_approved_cohort_registers_once_for_multiple_runs(tmp_path):
    receipt = _receipt(tmp_path, "C1500")
    approval = {**receipt, "schema": "EDP_VAULT_COHORT_SCOPE_APPROVAL_V1",
                "authority": "requesting-owner-vault-dev-v2", "status": "APPROVED"}
    transferred = receipt_from_owner_approval(POLICY, approval, now=NOW)
    validate_cohort_receipt(POLICY, transferred, tmp_path, now=NOW)
    assert grant_for_run(POLICY, transferred, _run(transferred, "vault-run-first"),
                         now=NOW)["run_id"] == "vault-run-first"
    assert grant_for_run(POLICY, transferred, _run(transferred, "vault-run-replay"),
                         now=NOW)["run_id"] == "vault-run-replay"
    with pytest.raises(Denied, match="VAULT_COHORT_OWNER_APPROVAL_INVALID"):
        receipt_from_owner_approval(POLICY, {**approval, "status": "PROPOSED"}, now=NOW)


def test_independent_readback_requires_exact_table_keys_and_multiplicity():
    plan = {"expected_tables": {name: {"columns": list(COLS[name]),
                                        "rows": [] if name in {"s_num_m2_value",
                                                                  "r_load_event",
                                                                  "vault_reject_quarantine"}
                                        else [["a" * 64] + ["value"] * (len(COLS[name]) - 1)]}
                                for name in TABLES}}
    expected = expected_readback(plan)
    assert expected["r_source_occurrence"][0][0] == "a" * 64
    predicate = _where("h_filing", expected["h_filing"])
    assert "filing_hk <=> decode(unhex(" in predicate
    changed = copy.deepcopy(plan)
    changed["expected_tables"]["h_filing"]["rows"].append(
        changed["expected_tables"]["h_filing"]["rows"][0])
    with pytest.raises(Denied, match="VAULT_EXPECTED_KEY_DUPLICATE"):
        expected_readback(changed)


def test_v1_pinned_plan_unchanged_and_v2_renderer_is_cohort_neutral():
    projection = ROOT / "runs/day6-vault-prototype/projected-manifest.json"
    plan_path = ROOT / "runs/day6-vault-prototype/load-plan.json"
    if not projection.exists() or not plan_path.exists():
        pytest.skip("pinned local prototype manifests are intentionally ignored by Git")
    rows = json.loads(projection.read_bytes())["rows"]
    retained = json.loads(plan_path.read_bytes())
    assert render(rows) == retained
    counts = {name: 0 for name in TABLES}
    counts.update({"h_filing": 20, "h_concept": 24, "l_fact_slot": 76,
                   "r_source_occurrence": 127, "s_fact_assertion": 127,
                   "s_num_m2_value": 127, "vault_reject_quarantine": 6})
    plan = render_v2(rows, cohort_id="C1500", input_manifest_sha256="a" * 64,
                     expected_table_counts=counts, synthetic_negatives=True)
    assert plan["schema"] == "EDP_VAULT_LOAD_PLAN_V2"
    assert plan["data_occurrences"] == 127
    assert plan["synthetic_rows"] == 6
    assert plan["expected_tables"]["r_load_event"]["rows"] == []
    assert all(stage["table"] != f"{NAMESPACE}.r_load_event" for stage in plan["stages"])
