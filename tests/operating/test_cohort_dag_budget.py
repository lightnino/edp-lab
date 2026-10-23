"""Deterministic DAG compiler, C3.4 budget and signed receipt runner tests.

No Databricks/Git/Codex production calls or owner signing credentials are used.
"""

import base64
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied, canonical, digest
from edp_lab.operating.budget import compare_phase, load_policy, verify_phase_receipt
from edp_lab.operating.dag import STAGES, compile_dag
from edp_lab.operating.runner import run


def _keys(tmp_path):
    trust = tmp_path / "trust"
    trust.mkdir()
    secret = tmp_path / "secret.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "Ed25519",
                    "-out", str(secret)], check=True)
    subprocess.run(["openssl", "pkey", "-in", str(secret), "-pubout",
                    "-out", str(trust / "owner_ed25519_public.pem")], check=True)
    (trust / "revoked_grants.json").write_text("[]\n")
    return trust, secret


def _signed(tmp_path, secret, document, label, *, grant=False):
    payload = tmp_path / (label + ".payload")
    signature = tmp_path / (label + ".sig")
    envelope = tmp_path / (label + ".json")
    payload.write_bytes(canonical(document))
    subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(secret),
                    "-rawin", "-in", str(payload), "-out", str(signature)], check=True)
    key = "grant" if grant else "document"
    envelope.write_text(json.dumps({key: document,
                                    "signature_base64": base64.b64encode(
                                        signature.read_bytes()).decode()}))
    return envelope


def _policy(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    source = (Path(__file__).resolve().parents[2]
              / "metadata/operating/edp_lab_pilot_c3_4_budget_v1.json")
    policy = root / "pilot.json"
    policy.write_bytes(source.read_bytes())
    return root, policy


def test_project_budget_exact_edges(tmp_path):
    _root, policy_path = _policy(tmp_path)
    policy = load_policy(policy_path)
    phase = "sql_table_creation"
    baseline = 55.145
    assert compare_phase(policy, phase, baseline * 5)["status"] == "PASS"
    assert compare_phase(policy, phase, baseline * 7)["status"] == (
        "PASS_WITH_PERFORMANCE_WARNING")
    assert compare_phase(policy, phase, baseline * 10)["status"] == (
        "PASS_WITH_PERFORMANCE_WARNING")
    assert compare_phase(policy, phase, baseline * 10.001)["status"] == (
        "C3_4_BLOCKED_NEEDS_HUMAN_APPROVAL")
    assert compare_phase(policy, "new_unmeasured_stage", 20)["status"] == (
        "BASELINE_OR_MEASUREMENT_UNRESOLVED")
    for invalid in (float("nan"), float("inf"), -1, True):
        with pytest.raises(Denied, match="C3_4_TIMING_INVALID"):
            compare_phase(policy, phase, invalid)


def test_budget_config_tamper_denied(tmp_path):
    _root, path = _policy(tmp_path)
    value = json.loads(path.read_text())
    value["phase_limits"][0]["block_above_seconds"] = 999999
    path.write_text(json.dumps(value))
    with pytest.raises(Denied, match="C3_4_THRESHOLDS_CHANGED"):
        load_policy(path)


def test_signed_phase_receipt_and_negative_cases(tmp_path):
    root, policy = _policy(tmp_path)
    trust, secret = _keys(tmp_path)
    row = next(p for p in load_policy(policy)["phase_limits"]
               if p["id"] == "sql_table_creation")
    document = {"schema": "EDP_PHASE_TIMING_RECEIPT_V1", "cohort": "C2000",
                "output": "o.c2000.m2.v1", "phase_id": row["id"],
                "policy_sha256": digest(policy.read_bytes()), "observed_live": True,
                "elapsed_seconds": row["baseline_observed_seconds"] * 6,
                "timing_method": row["metric"], "phase_comparable": True,
                "measurement_receipt_sha256": "f" * 64}
    receipt = _signed(tmp_path, secret, document, "timing")
    args = {"cohort": "C2000", "output": "o.c2000.m2.v1",
            "phase_id": row["id"], "trust_dir": trust}
    assert verify_phase_receipt(root, policy, receipt, **args)["status"] == (
        "PASS_WITH_PERFORMANCE_WARNING")
    altered = json.loads(receipt.read_text())
    altered["document"]["elapsed_seconds"] = 0
    receipt.write_text(json.dumps(altered))
    with pytest.raises(Denied, match="INVALID_SIGNATURE"):
        verify_phase_receipt(root, policy, receipt, **args)
    document["phase_comparable"] = False
    receipt = _signed(tmp_path, secret, document, "timing-notcomparable")
    with pytest.raises(Denied, match="C3_4_PHASE_NOT_COMPARABLE"):
        verify_phase_receipt(root, policy, receipt, **args)


def _fixture(tmp_path, monkeypatch, *, elapsed_factor=6, simulation=False):
    root, policy_path = _policy(tmp_path)
    trust, secret = _keys(tmp_path)
    monkeypatch.setenv("EDP_OWNER_TRUST_DIR", str(trust))
    raw = root / "raw.txt"
    raw.write_text("source preserving original\n")
    registry = root / "registry.json"
    registry.write_text('{"schema":"EDP_VALIDATION_REGISTRY_V1","version":1,'
                        '"controls":[]}\n')
    raw_sha = digest(raw.read_bytes())
    contracts = {key: {"version": "V1", "path": "raw.txt"}
                 for key in ("parser", "model", "rule")}
    contracts.update({"registry": {"version": "V1", "path": "registry.json"},
                      "budget_policy": {"version": "V1", "path": "pilot.json"}})
    stage = {"id": "stage", "kind": "stage_gate", "depends_on": [],
             "stage": "P8", "receipt": str(tmp_path / "stage.json")}
    budget = {"id": "budget", "kind": "budget_gate", "depends_on": ["stage"],
              "phase_id": "sql_table_creation",
              "receipt": str(tmp_path / "timing.json")}
    freeze = {"id": "freeze", "kind": "freeze_verify",
              "depends_on": ["stage", "budget"],
              "receipt": str(tmp_path / "freeze.json")}
    if simulation:
        stage["simulated_receipt"] = True
        budget["simulated_measurement"] = True
        freeze["simulated_receipt"] = True
    queue = {"schema": "EDP_QUEUE_V1", "cohort": "C2000", "output": "o.c2000.m2.v1",
             "tags": [], "contracts": contracts, "tasks": [stage, budget, freeze],
             "simulation_only": simulation}
    queue_path = root / "queue.json"
    queue_path.write_bytes(canonical(queue))
    now = datetime.now(UTC)
    grant = {"schema": "EDP_SIGNED_GRANT_V1", "grant_id": "budgetpilot-v1",
             "authority": "fixture", "issued_at": (now - timedelta(hours=1)).isoformat(),
             "expires_at": (now + timedelta(hours=1)).isoformat(),
             "revocation_id": "rev-budgetpilot-v1", "cohort": "C2000",
             "sources": {}, "contracts": {"queue": {"version": "EDP_QUEUE_V1",
                                                  "sha256": digest(queue_path.read_bytes())},
                                         **{k: {"version": v["version"],
                                                "sha256": digest((root / v["path"]).read_bytes())}
                                            for k, v in contracts.items()}},
             "operations": ["stage_gate", "budget_gate", "freeze_verify"],
             "databricks_paths": [], "databricks_tables": [],
             "outputs": [queue["output"]], "git_operations": [],
             "protected_branches": ["main"],
             "limits": {"runtime_seconds": 120, "compute_units": 10, "token_count": 500,
                        "retries": 1, "operations": 4}}
    envelope = _signed(tmp_path, secret, grant, "grant", grant=True)
    if not simulation:
        _signed(tmp_path, secret, {"schema": "EDP_STAGE_RECEIPT_V1",
                                  "cohort": "C2000", "output": queue["output"],
                                  "stage": "P8", "queue_sha256": digest(queue_path.read_bytes()),
                                  "status": "VERIFIED", "independent_verifier": True,
                                  "evidence_sha256": raw_sha, "execution_kind": "LIVE"}, "stage"
                ).replace(tmp_path / "stage.json")
        row = next(p for p in load_policy(policy_path)["phase_limits"]
                   if p["id"] == "sql_table_creation")
        _signed(tmp_path, secret, {"schema": "EDP_PHASE_TIMING_RECEIPT_V1",
                                  "cohort": "C2000", "output": queue["output"],
                                  "phase_id": row["id"], "policy_sha256": digest(
                                      policy_path.read_bytes()),
                                  "observed_live": True,
                                  "elapsed_seconds": row["baseline_observed_seconds"] * elapsed_factor,
                                  "timing_method": row["metric"], "phase_comparable": True,
                                  "measurement_receipt_sha256": "f" * 64}, "timing"
                ).replace(tmp_path / "timing.json")
        _signed(tmp_path, secret, {
            "schema": "EDP_LIVE_FREEZE_RECEIPT_V1", "output": queue["output"],
            "remote_receipt_sha256": "a" * 64,
            **dict.fromkeys(("delta_ids", "delta_history", "delta_properties",
                             "row_counts", "source_lineage", "queryable_versions",
                             "live_readback"), "VERIFIED")}, "freeze").replace(
                                 tmp_path / "freeze.json")
    return root, queue_path, envelope


def test_runner_budget_warn_continue_and_freeze_gate(tmp_path, monkeypatch):
    root, queue, grant = _fixture(tmp_path, monkeypatch)
    state = run(root, queue, grant, tmp_path / "state")
    assert state["summary"]["accepted"]
    assert state["tasks"]["budget"]["budget_outcome"]["status"] == (
        "PASS_WITH_PERFORMANCE_WARNING")
    assert "PERFORMANCE_WARNING" in (tmp_path / "state/events.jsonl").read_text()
    again = run(root, queue, grant, tmp_path / "state")
    assert again["used"]["operations"] == 3


def test_runner_budget_block_is_sticky(tmp_path, monkeypatch):
    root, queue, grant = _fixture(tmp_path, monkeypatch, elapsed_factor=11)
    state = run(root, queue, grant, tmp_path / "state")
    assert not state["summary"]["accepted"]
    assert state["tasks"]["budget"]["status"] == "NEEDS_HUMAN_DECISION"
    assert state["tasks"]["freeze"]["status"] == "PLANNED"
    with pytest.raises(Denied, match="PAUSED_REQUIRES_OWNER_DISPOSITION"):
        run(root, queue, grant, tmp_path / "state")


def test_runner_simulation_never_accepted_live(tmp_path, monkeypatch):
    root, queue, grant = _fixture(tmp_path, monkeypatch, simulation=True)
    with pytest.raises(Denied, match="SIMULATION_QUEUE_CANNOT_RUN_LIVE"):
        run(root, queue, grant, tmp_path / "state")
    state = run(root, queue, grant, tmp_path / "state", dry_run=True)
    assert state["summary"]["simulation_complete"]
    assert not state["summary"]["accepted"]


def test_compiler_branches_and_deps(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    import hashlib

    policy = repo / "metadata/operating/edp_lab_pilot_c3_4_budget_v1.json"
    registry = repo / "metadata/operating/validation_registry_v1.json"
    original = repo / "AGENTS.md"
    pins = {"parser": {"version": "P1", "path": "AGENTS.md"},
            "model": {"version": "M1", "path": "AGENTS.md"},
            "rule": {"version": "R1", "path": "AGENTS.md"},
            "registry": {"version": "V1",
                         "path": "metadata/operating/validation_registry_v1.json",
                         "sha256": hashlib.sha256(registry.read_bytes()).hexdigest()},
            "budget_policy": {"version": "V1",
                              "path": "metadata/operating/edp_lab_pilot_c3_4_budget_v1.json",
                              "sha256": hashlib.sha256(policy.read_bytes()).hexdigest()}}
    assert original.is_file()
    plan = {"schema": "EDP_COHORT_DAG_PLAN_V1", "route": "CORPUS_ONLY",
            "cohort": "C2000", "output": "workspace.edp_lab.o_c2000",
            "contracts": pins, "tags": ["RAW"],
            "source_families": ["FSDS", "TREASURY"],
            "stage_receipts": {stage: str(tmp_path / (stage + ".json")) for stage in STAGES},
            "budget_phases": [{"phase_id": "sql_table_creation",
                               "receipt": str(tmp_path / "elapsed.json")}],
            "freeze_receipt": str(tmp_path / "freeze.json"), "simulation_only": True}
    queue = compile_dag(repo, plan)
    assert queue["schema"] == "EDP_QUEUE_V1"
    assert queue["route"] == "CORPUS_ONLY"
    assert queue["tasks"][-1]["kind"] == "freeze_verify"
    assert len(queue["tasks"][-1]["depends_on"]) == len(queue["tasks"]) - 1
    ids = next(t["control_ids"] for t in queue["tasks"] if t["id"] == "P9_controls")
    assert {"FIN_001_V1", "FIN_002_V1", "TRY_001_V1"} <= set(ids)
    assert all(t.get("simulated_receipt") for t in queue["tasks"]
               if t["kind"] in ("stage_gate", "freeze_verify"))
    for wrong in ("UNRESOLVED", "UNKNOWN"):
        with pytest.raises(Denied, match="MODEL_ROUTE_NOT_APPROVED"):
            compile_dag(repo, dict(plan, route=wrong))
    with pytest.raises(Denied, match="MISSING_STAGE_RECEIPTS"):
        compile_dag(repo, dict(plan, stage_receipts={"P0": "x"}))
    # P8 may invoke exactly the existing signed/ledgered guarded CREATE TABLE adapter.
    guarded = {"operation_id": "create-c2000-once",
               "databricks_path": "/Volumes/workspace/edp_lab/approved",
               "databricks_table": "workspace.edp_lab.o_c2000_candidate_v1",
               "statement_path": "AGENTS.md",
               "external_receipt": str(tmp_path / "db-readback.json")}
    with pytest.raises(Denied, match="GUARDED_WRITE_STATEMENT_NOT_PINNED"):
        compile_dag(repo, dict(plan, guarded_create_table=guarded))
    updated = dict(plan, contracts={**pins, "statement": {
        "version": "S1", "path": "AGENTS.md"}},
        guarded_create_table=guarded)
    with_write = compile_dag(repo, updated)
    write = next(t for t in with_write["tasks"]
                 if t["id"] == "P8_guarded_create_table")
    assert write["depends_on"] == ["P7"]
    p8 = next(t for t in with_write["tasks"] if t["id"] == "P8")
    assert p8["depends_on"] == ["P8_guarded_create_table"]
    with pytest.raises(Denied, match="INVALID_GUARDED_WRITE"):
        compile_dag(repo, dict(updated, guarded_create_table={
            **guarded, "not_approved": True}))
