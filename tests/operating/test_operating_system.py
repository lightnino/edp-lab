import base64
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied, authorize, canonical, digest, load_grant
from edp_lab.operating.boundaries import _reserve, databricks_write, git_write
from edp_lab.operating.runner import _freeze_verified, applicable_controls, run


def signed_setup(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    trust = tmp_path / "trust"
    trust.mkdir()
    private = tmp_path / "owner-private.pem"
    public = trust / "owner_ed25519_public.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "Ed25519", "-out", str(private)], check=True)
    subprocess.run(["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)], check=True)
    (trust / "revoked_grants.json").write_text("[]\n")
    raw = root / "raw.txt"
    raw.write_text("immutable sample\n")
    registry = root / "metadata/operating/validation_registry_v1.json"
    registry.parent.mkdir(parents=True)
    registry.write_text('{"schema":"EDP_VALIDATION_REGISTRY_V1","version":1,"controls":[]}\n')
    queue = root / "queue.json"
    tasks = [{"id": "hash", "kind": "verify_file", "depends_on": [], "source": {
        "identity": "SRC_A", "path": str(raw), "sha256": digest(raw.read_bytes())}},
        {"id": "retry", "kind": "transient_probe", "depends_on": ["hash"]},
        {"id": "freeze", "kind": "freeze_verify", "depends_on": ["hash", "retry"],
         "simulated_receipt": True}]
    queue.write_bytes(canonical({"schema": "EDP_QUEUE_V1", "cohort": "C_TEST",
                                 "output": "test.output.v1", "tags": [], "tasks": tasks,
                                 "contracts": {**{name: {"version": version, "path": "raw.txt"}
                                                  for name, version in (("parser", "P1"),
                                                                        ("model", "M1"),
                                                                        ("rule", "R1"))},
                                               "registry": {"version": "V1",
                                                            "path": "metadata/operating/validation_registry_v1.json"}}}))
    statement = root / "statement.json"
    statement.write_text(json.dumps({"statement": "CREATE TABLE workspace.test.output AS SELECT 1"}))
    grant = {"schema": "EDP_SIGNED_GRANT_V1", "grant_id": "owner-test-v1",
             "authority": "owner-test", "issued_at": "2026-01-01T00:00:00Z",
             "expires_at": "2027-01-01T00:00:00Z", "revocation_id": "rev-owner-test-v1",
             "cohort": "C_TEST", "sources": {"SRC_A": digest(raw.read_bytes())},
             "contracts": {"queue": {"version": "EDP_QUEUE_V1", "sha256": digest(queue.read_bytes())},
                           "parser": {"version": "P1", "sha256": digest(raw.read_bytes())},
                           "model": {"version": "M1", "sha256": digest(raw.read_bytes())},
                           "rule": {"version": "R1", "sha256": digest(raw.read_bytes())},
                           "registry": {"version": "V1", "sha256": digest(registry.read_bytes())},
                           "statement": {"version": "S1", "sha256": digest(statement.read_bytes())}},
             "operations": ["verify_file", "transient_probe", "freeze_verify", "databricks_write",
                            "git_write"],
             "databricks_paths": ["/Volumes/workspace/test"],
             "databricks_tables": ["workspace.test.output"],
             "outputs": ["test.output.v1"], "git_operations": ["push"],
             "protected_branches": ["main"],
             "limits": {"runtime_seconds": 30, "compute_units": 10, "token_count": 1000,
                        "retries": 2, "operations": 5}}
    return root, trust, private, queue, statement, grant


def sign(tmp_path, private, grant):
    payload = tmp_path / "payload"
    signature = tmp_path / "signature"
    envelope = tmp_path / "grant.json"
    payload.write_bytes(canonical(grant))
    subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(private),
                    "-rawin", "-in", str(payload), "-out", str(signature)], check=True)
    envelope.write_text(json.dumps({"grant": grant,
                                    "signature_base64": base64.b64encode(signature.read_bytes()).decode()}))
    return envelope


def sign_document(tmp_path, private, document):
    payload = tmp_path / "receipt-payload"
    signature = tmp_path / "receipt-signature"
    envelope = tmp_path / "receipt.json"
    payload.write_bytes(canonical(document))
    subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(private),
                    "-rawin", "-in", str(payload), "-out", str(signature)], check=True)
    envelope.write_text(json.dumps({"document": document,
                                    "signature_base64": base64.b64encode(signature.read_bytes()).decode()}))
    return envelope


def request(root, raw):
    return {"operation": "verify_file", "cohort": "C_TEST", "output": "test.output.v1",
            "source": {"identity": "SRC_A", "path": str(raw), "sha256": digest(raw.read_bytes())},
            "contracts": {name: {"version": version, "path": "raw.txt"}
                          for name, version in (("parser", "P1"), ("model", "M1"),
                                                ("rule", "R1"))},
            "budget": {"operations": 1}}


def test_signed_authorization_denials(tmp_path):
    root, trust, private, _queue, _statement, grant = signed_setup(tmp_path)
    envelope = sign(tmp_path, private, grant)
    loaded = load_grant(root, envelope, trust, datetime(2026, 10, 23, tzinfo=UTC))
    raw = root / "raw.txt"
    basic = request(root, raw)
    authorize(loaded, basic, root=root)
    forged = json.loads(envelope.read_text())
    forged["grant"]["sources"]["SRC_B"] = "0" * 64
    envelope.write_text(json.dumps(forged))
    with pytest.raises(Denied, match="INVALID_SIGNATURE"):
        load_grant(root, envelope, trust)
    envelope = sign(tmp_path, private, grant)
    for change, reason in [({"cohort": "OTHER"}, "COHORT_OUT_OF_SCOPE"),
                           ({"source": {"identity": "SRC_B", "path": str(raw),
                                         "sha256": digest(raw.read_bytes())}}, "SOURCE_OUT_OF_SCOPE"),
                           ({"contracts": {"model": {"version": "M2", "path": "raw.txt"}}},
                            "CONTRACT_OUT_OF_SCOPE"),
                           ({"databricks_table": "workspace.other.table"},
                            "DATABRICKS_TABLE_OUT_OF_SCOPE"),
                           ({"databricks_path": "/Volumes/other"},
                            "DATABRICKS_PATH_OUT_OF_SCOPE")]:
        with pytest.raises(Denied, match=reason):
            authorize(loaded, dict(basic, **change), root=root)
    with pytest.raises(Denied, match="BUDGET_EXCEEDED"):
        authorize(loaded, basic, root=root, used={"operations": 5})
    raw.write_text("changed\n")
    with pytest.raises(Denied, match="SOURCE_OUT_OF_SCOPE"):
        authorize(loaded, request(root, raw), root=root)
    raw.write_text("immutable sample\n")
    (trust / "revoked_grants.json").write_text('["owner-test-v1"]')
    with pytest.raises(Denied, match="GRANT_REVOKED"):
        load_grant(root, envelope, trust)
    (trust / "revoked_grants.json").write_text("[]")
    with pytest.raises(Denied, match="GRANT_NOT_CURRENT"):
        load_grant(root, envelope, trust, datetime(2028, 1, 1, tzinfo=UTC))


def test_external_boundary_and_replay(tmp_path):
    root, trust, private, _queue, _statement, grant = signed_setup(tmp_path)
    loaded = load_grant(root, sign(tmp_path, private, grant), trust)
    write = {"operation": "databricks_write", "cohort": "C_TEST", "output": "test.output.v1",
             "databricks_table": "workspace.test.output", "databricks_path": "/Volumes/workspace/test",
             "contracts": {"statement": {"version": "S1", "path": "statement.json"},
                           **{name: {"version": version, "path": "raw.txt"}
                              for name, version in (("parser", "P1"), ("model", "M1"),
                                                    ("rule", "R1"))}},
             "statement_path": "statement.json", "operation_id": "once-001"}
    assert databricks_write(root, loaded, write, tmp_path / "ledger") == {
        "status": "AUTHORIZED_DRY_RUN"}
    with pytest.raises(Denied, match="DATABRICKS_TABLE_OUT_OF_SCOPE"):
        databricks_write(root, loaded, dict(write, databricks_table="workspace.test.other"),
                         tmp_path / "ledger")
    _reserve(tmp_path / "ledger", "once-001", write)
    with pytest.raises(Denied, match="OPERATION_REPLAY"):
        _reserve(tmp_path / "ledger", "once-001", write)
    git_request = {"operation": "git_write", "cohort": "C_TEST", "output": "test.output.v1",
                   "git_operation": "push", "branch": "feature/test", "operation_id": "push-001",
                   "argv": ["git", "push", "--force", "origin", "feature/test"]}
    with pytest.raises(Denied, match="GIT_COMMAND_OUT_OF_SCOPE"):
        git_write(root, loaded, git_request, tmp_path / "ledger")
    with pytest.raises(Denied, match="PROTECTED_BRANCH"):
        git_write(root, loaded, dict(git_request, branch="main"), tmp_path / "ledger")


def test_runner_recovers_and_resumes(tmp_path, monkeypatch):
    root, trust, private, queue, _statement, grant = signed_setup(tmp_path)
    envelope = sign(tmp_path, private, grant)
    monkeypatch.setenv("EDP_OWNER_TRUST_DIR", str(trust))
    state_dir = tmp_path / "state"
    first = run(root, queue, envelope, state_dir, dry_run=True, pause_after=1)
    assert first["summary"]["complete"] == 1
    second = run(root, queue, envelope, state_dir, dry_run=True)
    assert second["summary"] == {"complete": 3, "total": 3, "dry_run": True,
                                 "simulation_complete": True, "accepted": False}
    assert second["used"]["retries"] == 1
    again = run(root, queue, envelope, state_dir, dry_run=True)
    assert again["used"]["operations"] == 3
    assert (state_dir / "events.jsonl").read_text().count('"kind": "COMPLETE"') == 3


def test_registry_changed_source_applicability(tmp_path):
    root = Path(__file__).resolve().parents[2]
    assert {c["id"] for c in applicable_controls(root, ["RAW", "FSDS", "FIN"])} == {
        "LOSSLESS_1_TO_5_LOCAL_V1", "FIN_001_V1", "FIN_002_V1"}
    assert {c["id"] for c in applicable_controls(root, ["RAW", "TREASURY"])} == {
        "LOSSLESS_1_TO_5_LOCAL_V1", "TRY_001_V1", "TRY_002_V1", "TRY_003_V1", "TRY_004_V1"}


def test_changed_registry_denied_before_queue(tmp_path, monkeypatch):
    root, trust, private, queue, _statement, grant = signed_setup(tmp_path)
    envelope = sign(tmp_path, private, grant)
    monkeypatch.setenv("EDP_OWNER_TRUST_DIR", str(trust))
    (root / "metadata/operating/validation_registry_v1.json").write_text("{}")
    with pytest.raises(Denied, match="REGISTRY_HASH_CHANGED"):
        run(root, queue, envelope, tmp_path / "state", dry_run=True)


def test_live_freeze_needs_signed_complete_evidence(tmp_path, monkeypatch):
    root, trust, private, _queue, _statement, _grant = signed_setup(tmp_path)
    monkeypatch.setenv("EDP_OWNER_TRUST_DIR", str(trust))
    fields = ("delta_ids", "delta_history", "delta_properties", "row_counts",
              "source_lineage", "queryable_versions", "live_readback")
    document = {"schema": "EDP_LIVE_FREEZE_RECEIPT_V1", "output": "test.output.v1",
                "remote_receipt_sha256": "a" * 64, **dict.fromkeys(fields, "VERIFIED")}
    receipt = sign_document(tmp_path, private, document)
    assert _freeze_verified(root, receipt, "test.output.v1")
    unsigned_change = json.loads(receipt.read_text())
    unsigned_change["document"]["live_readback"] = "NOT_RUN"
    receipt.write_text(json.dumps(unsigned_change))
    with pytest.raises(Denied, match="INVALID_SIGNATURE"):
        _freeze_verified(root, receipt, "test.output.v1")


def test_runner_dispatches_guarded_write_dry_run(tmp_path, monkeypatch):
    root, trust, private, queue_path, _statement, grant = signed_setup(tmp_path)
    queue = json.loads(queue_path.read_text())
    queue["contracts"]["statement"] = {"version": "S1", "path": "statement.json"}
    queue["tasks"].insert(2, {"id": "write", "kind": "databricks_write",
                              "depends_on": ["hash", "retry"],
                              "operation_id": "write-001", "statement_path": "statement.json",
                              "databricks_table": "workspace.test.output",
                              "databricks_path": "/Volumes/workspace/test"})
    queue["tasks"][-1]["depends_on"].append("write")
    queue_path.write_bytes(canonical(queue))
    grant["contracts"]["queue"]["sha256"] = digest(queue_path.read_bytes())
    envelope = sign(tmp_path, private, grant)
    monkeypatch.setenv("EDP_OWNER_TRUST_DIR", str(trust))
    state = run(root, queue_path, envelope, tmp_path / "state", dry_run=True)
    assert state["summary"]["simulation_complete"]
    assert state["summary"]["accepted"] is False
    assert state["tasks"]["write"]["external"] == {"status": "AUTHORIZED_DRY_RUN"}
    assert state["used"]["operations"] == 4


def test_external_write_waits_for_readback_without_replay(tmp_path, monkeypatch):
    root, trust, private, queue_path, _statement, grant = signed_setup(tmp_path)
    queue = json.loads(queue_path.read_text())
    queue["contracts"]["statement"] = {"version": "S1", "path": "statement.json"}
    receipt = tmp_path / "external-receipt.json"
    freeze = tmp_path / "freeze-receipt.json"
    queue["tasks"].insert(2, {"id": "write", "kind": "databricks_write",
                              "depends_on": ["hash", "retry"],
                              "operation_id": "write-001", "statement_path": "statement.json",
                              "databricks_table": "workspace.test.output",
                              "databricks_path": "/Volumes/workspace/test",
                              "external_receipt": str(receipt)})
    queue["tasks"][-1]["depends_on"].append("write")
    queue["tasks"][-1]["receipt"] = str(freeze)
    queue_path.write_bytes(canonical(queue))
    grant["contracts"]["queue"]["sha256"] = digest(queue_path.read_bytes())
    envelope = sign(tmp_path, private, grant)
    monkeypatch.setenv("EDP_OWNER_TRUST_DIR", str(trust))
    monkeypatch.setenv("EDP_OWNER_LEDGER_DIR", str(tmp_path / "protected-ledger"))
    seen = []

    def fake_write(root_arg, grant_arg, request_arg, ledger_arg, *, execute):
        seen.append(request_arg)
        assert execute
        return {"status": "SUBMITTED_REQUIRES_READBACK",
                "statement_id": "statement-write-001"}

    monkeypatch.setattr("edp_lab.operating.runner.databricks_write", fake_write)
    first = run(root, queue_path, envelope, tmp_path / "state")
    assert first["tasks"]["write"]["status"] == "VALIDATING"
    assert not first["summary"]["accepted"]
    assert len(seen) == 1
    external_doc = {"schema": "EDP_EXTERNAL_OPERATION_RECEIPT_V1",
                    "operation_id": "write-001", "request_sha256": digest(canonical(seen[0])),
                    "status": "VERIFIED", "live_readback": True,
                    "statement_id": "statement-write-001",
                    "terminal_state": "SUCCEEDED", "table": "workspace.test.output",
                    "uc_table_id": "table-write-001",
                    "terminal_response_sha256": "a" * 64,
                    "uc_response_sha256": "b" * 64}
    signed = sign_document(tmp_path, private, external_doc)
    receipt.write_bytes(signed.read_bytes())
    fields = ("delta_ids", "delta_history", "delta_properties", "row_counts",
              "source_lineage", "queryable_versions", "live_readback")
    freeze_doc = {"schema": "EDP_LIVE_FREEZE_RECEIPT_V1", "output": "test.output.v1",
                  "remote_receipt_sha256": "a" * 64, **dict.fromkeys(fields, "VERIFIED")}
    freeze.write_bytes(sign_document(tmp_path, private, freeze_doc).read_bytes())
    resumed = run(root, queue_path, envelope, tmp_path / "state")
    assert resumed["summary"]["accepted"]
    assert len(seen) == 1


def test_jobs_submit_waits_for_exact_signed_run_terminal_receipt(tmp_path, monkeypatch):
    root, trust, private, queue_path, _statement, grant = signed_setup(tmp_path)
    (root / "job.json").write_text('{"fixed":"submission"}')
    (root / "deployed.json").write_text('{"fixed":"runtime"}')
    queue = json.loads(queue_path.read_text())
    queue["contracts"]["job_submit_full"] = {"version": "V1", "path": "job.json"}
    queue["contracts"]["deploy_full"] = {"version": "V1", "path": "deployed.json"}
    queue["tasks"].insert(2, {"id": "full-job", "kind": "databricks_job_submit",
                              "depends_on": ["hash", "retry"],
                              "operation_id": "fixed-full-job-001",
                              "submission_path": "job.json",
                              "deployment_path": "deployed.json",
                              "submission_contract": "job_submit_full",
                              "deployment_contract": "deploy_full",
                              "databricks_path": "/Shared/approved/job",
                              "external_receipt": str(tmp_path / "job-terminal.json")})
    queue["tasks"][-1]["depends_on"].append("full-job")
    queue["tasks"][-1]["receipt"] = str(tmp_path / "freeze-complete.json")
    queue_path.write_bytes(canonical(queue))
    grant["operations"].append("databricks_job_submit")
    grant["databricks_paths"].append("/Shared/approved/job")
    grant["contracts"]["queue"]["sha256"] = digest(queue_path.read_bytes())
    grant["contracts"]["job_submit_full"] = {
        "version": "V1", "sha256": digest((root / "job.json").read_bytes())}
    grant["contracts"]["deploy_full"] = {
        "version": "V1", "sha256": digest((root / "deployed.json").read_bytes())}
    envelope = sign(tmp_path, private, grant)
    monkeypatch.setenv("EDP_OWNER_TRUST_DIR", str(trust))
    monkeypatch.setenv("EDP_OWNER_LEDGER_DIR", str(tmp_path / "ledger"))
    seen = []

    def fake_submit(_root, _grant, request, _ledger, *, execute):
        assert execute
        seen.append(request)
        return {"status": "SUBMITTED_REQUIRES_READBACK", "run_id": 9001}

    monkeypatch.setattr("edp_lab.operating.runner.databricks_job_submit", fake_submit)
    first = run(root, queue_path, envelope, tmp_path / "state")
    assert first["tasks"]["full-job"]["status"] == "VALIDATING"
    assert first["tasks"]["freeze"]["status"] == "PLANNED"
    assert not first["summary"]["accepted"] and len(seen) == 1
    # A validly signed receipt for *another run* must never complete this task.
    common = {"schema": "EDP_EXTERNAL_OPERATION_RECEIPT_V1",
              "operation_id": "fixed-full-job-001",
              "request_sha256": digest(canonical(seen[0])),
              "status": "VERIFIED", "live_readback": True,
              "external_service": "DATABRICKS_JOBS", "terminal_state": "SUCCESS"}
    wrong = sign_document(tmp_path, private, {**common, "job_run_id": 9999})
    (tmp_path / "job-terminal.json").write_bytes(wrong.read_bytes())
    stalled = run(root, queue_path, envelope, tmp_path / "state")
    assert stalled["tasks"]["full-job"]["status"] == "VALIDATING"
    assert len(seen) == 1 and not stalled["summary"]["accepted"]
    signed = sign_document(tmp_path, private, {**common, "job_run_id": 9001})
    (tmp_path / "job-terminal.json").write_bytes(signed.read_bytes())
    fields = ("delta_ids", "delta_history", "delta_properties", "row_counts",
              "source_lineage", "queryable_versions", "live_readback")
    final_receipt = sign_document(
        tmp_path, private, {"schema": "EDP_LIVE_FREEZE_RECEIPT_V1",
                            "output": "test.output.v1", "remote_receipt_sha256": "a" * 64,
                            **dict.fromkeys(fields, "VERIFIED")})
    (tmp_path / "freeze-complete.json").write_bytes(final_receipt.read_bytes())
    finished = run(root, queue_path, envelope, tmp_path / "state")
    assert finished["summary"]["accepted"]
    assert len(seen) == 1
