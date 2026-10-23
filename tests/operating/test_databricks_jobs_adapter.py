"""No-network tests for the fixed-workload Databricks Jobs adapter."""

import base64
import json
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied, digest
from edp_lab.operating.databricks_jobs import databricks_job_submit


def fixture(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    for name in ("parser", "model", "rule"):
        (root / (name + ".txt")).write_text(name)
    notebook = b"# exact reviewed notebook\n"
    runtime = b"exact immutable zip bytes"
    remote_path = "dbfs:/Volumes/workspace/edp_lab/raw/test/v1/runtime.zip"
    nb_path = "/Shared/edp-lab/approved/runtime"
    payload = {"run_name": "day5-n500-v1", "timeout_seconds": 3600,
               "idempotency_token": "day5-n500-v1-full",
               "tasks": [{"task_key": "full", "timeout_seconds": 3600, "max_retries": 0,
                          "notebook_task": {"notebook_path": nb_path,
                                            "source": "WORKSPACE",
                                            "base_parameters": {"phase": "full"}}}]}
    (root / "submit.json").write_text(json.dumps(payload))
    deployment = {"schema": "EDP_DATABRICKS_DEPLOYMENT_V1",
                  "notebook_path": nb_path, "notebook_sha256": digest(notebook),
                  "submission_sha256": digest((root / "submit.json").read_bytes()),
                  "files": [{"uri": remote_path, "sha256": digest(runtime)}]}
    (root / "deployment.json").write_text(json.dumps(deployment))
    grant = {"cohort": "C2000", "operations": ["databricks_job_submit"],
             "sources": {}, "contracts": {
                 **{name: {"version": "V1", "sha256": digest(
                     (root / (name + ".txt")).read_bytes())}
                    for name in ("parser", "model", "rule")},
                 "submit_phase": {"version": "V1",
                                  "sha256": digest((root / "submit.json").read_bytes())},
                 "deployment_phase": {"version": "V1",
                                      "sha256": digest((root / "deployment.json").read_bytes())}},
             "databricks_paths": [nb_path, remote_path],
             "databricks_tables": [], "outputs": ["o.c2000"],
             "git_operations": [], "protected_branches": ["main"],
             "limits": {"runtime_seconds": 4000, "operations": 4,
                        "compute_units": 10, "token_count": 100, "retries": 1}}
    request = {"operation": "databricks_job_submit", "cohort": "C2000",
               "output": "o.c2000", "operation_id": "day5-job-001",
               "submission_path": "submit.json", "deployment_path": "deployment.json",
               "submission_contract": "submit_phase", "deployment_contract": "deployment_phase",
               "databricks_path": nb_path,
               "contracts": {name: {"version": pin["version"],
                                    "path": (name + ".txt" if name in ("parser", "model", "rule")
                                             else "submit.json" if name == "submit_phase"
                                             else "deployment.json")}
                             for name, pin in grant["contracts"].items()}}
    return root, grant, request, notebook, runtime, remote_path


def test_verified_remote_then_exact_submit_once(tmp_path, monkeypatch):
    root, grant, request, nb, runtime, remote = fixture(tmp_path)
    calls = []

    def fake(*argv, timeout):
        calls.append(argv)
        if argv[:2] == ("workspace", "export"):
            return json.dumps({"content": base64.b64encode(nb).decode()}).encode()
        if argv[:2] == ("fs", "cat"):
            assert argv[2] == remote
            return runtime
        if argv[:2] == ("jobs", "submit"):
            assert "--no-wait" in argv and "@" + str(root / "submit.json") in argv
            return b'{"run_id":314159}'
        pytest.fail("Unexpected Databricks command")

    monkeypatch.setattr("edp_lab.operating.databricks_jobs._cli", fake)
    monkeypatch.setattr("edp_lab.operating.databricks_jobs.load_grant",
                        lambda *args: grant)
    monkeypatch.setattr("edp_lab.operating.databricks_jobs.protected_trust_dir",
                        lambda *args: tmp_path / "trust")
    request["grant_path"] = str(tmp_path / "signed.json")
    ledger = tmp_path / "ledger"
    assert databricks_job_submit(root, grant, request, ledger) == {
        "status": "AUTHORIZED_DRY_RUN_REMOTE_UNVERIFIED"}
    assert not calls
    result = databricks_job_submit(root, grant, request, ledger, execute=True)
    assert result["status"] == "SUBMITTED_REQUIRES_READBACK"
    assert result["run_id"] == 314159
    assert [c[0] for c in calls] == ["workspace", "fs", "jobs"]
    with pytest.raises(Denied, match="OPERATION_REPLAY_OR_UNCERTAIN_RESULT"):
        databricks_job_submit(root, grant, request, ledger, execute=True)
    assert [c[0] for c in calls].count("jobs") == 1


def test_changed_remote_notebook_or_runtime_denied(tmp_path, monkeypatch):
    root, grant, request, nb, runtime, remote = fixture(tmp_path)
    monkeypatch.setattr("edp_lab.operating.databricks_jobs.load_grant",
                        lambda *args: grant)
    monkeypatch.setattr("edp_lab.operating.databricks_jobs.protected_trust_dir",
                        lambda *args: tmp_path)
    request["grant_path"] = str(tmp_path / "signed.json")
    def bad_notebook(*argv, timeout):
        if argv[:2] == ("workspace", "export"):
            return json.dumps({"content": base64.b64encode(b"modified notebook").decode()}).encode()
        pytest.fail("Must never submit")
    monkeypatch.setattr("edp_lab.operating.databricks_jobs._cli", bad_notebook)
    with pytest.raises(Denied, match="REMOTE_NOTEBOOK_HASH_CHANGED"):
        databricks_job_submit(root, grant, request, tmp_path / "ledger", execute=True)
    def bad_runtime(*argv, timeout):
        if argv[:2] == ("workspace", "export"):
            return json.dumps({"content": base64.b64encode(nb).decode()}).encode()
        if argv[:2] == ("fs", "cat"):
            return b"changed runtime"
        pytest.fail("Must never submit")
    monkeypatch.setattr("edp_lab.operating.databricks_jobs._cli", bad_runtime)
    with pytest.raises(Denied, match="REMOTE_DEPLOYMENT_HASH_CHANGED"):
        databricks_job_submit(root, grant, request, tmp_path / "ledger", execute=True)


@pytest.mark.parametrize("edit,reason", [
    ("extra_task", "JOB_TASK_COUNT_OUT_OF_SCOPE"),
    ("retry", "JOB_TASK_LIMITS_INVALID"),
    ("timeout", "JOB_TIMEOUT_OUT_OF_SCOPE"),
    ("parameters", "JOB_PARAMETERS_OUT_OF_SCOPE"),
    ("different_notebook", "JOB_NOTEBOOK_OUT_OF_SCOPE"),
])
def test_submitted_payload_is_exact_and_bounded(tmp_path, edit, reason):
    root, grant, request, _nb, _runtime, _remote = fixture(tmp_path)
    data = json.loads((root / "submit.json").read_text())
    if edit == "extra_task":
        data["tasks"].append(data["tasks"][0])
    elif edit == "retry":
        data["tasks"][0]["max_retries"] = 1
    elif edit == "timeout":
        data["timeout_seconds"] = 9999
    elif edit == "parameters":
        data["tasks"][0]["notebook_task"]["base_parameters"]["rogue"] = "x"
    elif edit == "different_notebook":
        data["tasks"][0]["notebook_task"]["notebook_path"] = "/Shared/evil"
    (root / "submit.json").write_text(json.dumps(data))
    grant["contracts"]["submit_phase"]["sha256"] = digest((root / "submit.json").read_bytes())
    deployment = json.loads((root / "deployment.json").read_text())
    deployment["submission_sha256"] = digest((root / "submit.json").read_bytes())
    (root / "deployment.json").write_text(json.dumps(deployment))
    grant["contracts"]["deployment_phase"]["sha256"] = digest(
        (root / "deployment.json").read_bytes())
    with pytest.raises(Denied, match=reason):
        databricks_job_submit(root, grant, request, tmp_path / "ledger")


def test_local_contract_tamper_and_forbidden_remote_path(tmp_path):
    root, grant, request, *_ = fixture(tmp_path)
    original = (root / "submit.json").read_text()
    (root / "submit.json").write_text("{}")
    with pytest.raises(Denied, match="CONTRACT_HASH_CHANGED|JOB_OR_DEPLOYMENT_CONTRACT_CHANGED"):
        databricks_job_submit(root, grant, request, tmp_path / "ledger")
    # Restore the original bytes so the next assertion isolates scope denial.
    (root / "submit.json").write_text(original)
    request["databricks_path"] = "/Shared/unauthorized"
    with pytest.raises(Denied, match="DATABRICKS_PATH_OUT_OF_SCOPE"):
        databricks_job_submit(root, grant, request, tmp_path / "ledger")
