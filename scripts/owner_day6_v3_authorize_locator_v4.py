"""Owner-only signed no-effect disposition and exact V4 locator upgrade approval.

This performs read-only remote checks, then writes two additive protected signed
documents. It does not upload a wheel, create/run a Job, or alter any old pin.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

from owner_day6_v3_one_shot import BASE, ROOT, _signed_once, require
from owner_setup_day6_vault_0a import admin_cli

from edp_lab.operating.authority import file_digest, verified_document

REQUEST = ROOT / "metadata/operating/day6_c2000_vault_v3_bounded_request_locator_fix_v1.json"
DEPLOYMENT = ROOT / "metadata/operating/day6_c2000_vault_v3_deployment_v6.json"
PRIOR_REQUEST = ROOT / "metadata/operating/day6_c2000_vault_v3_bounded_request_coverpage_quote_fix_v1.json"
PRIOR_DEPLOYMENT = ROOT / "metadata/operating/day6_c2000_vault_v3_deployment_v5.json"
NO_EFFECT = BASE / "receipts/day6-v3-canary-3-no-effect.signed.json"
APPROVAL = BASE / "approvals/day6-v3-edgar-locator-upgrade-v4.signed.json"
INSTALL = BASE / "receipts/day6-v3-install-v1.signed.json"
STANDING = BASE / "trust/day6-v3-standing-v1.signed.json"
E2E = BASE / "receipts/day6-v3-e2e-ready-coverpage-fix-v3.signed.json"
WHEEL_SHA = "0b26e3319bd453fc1a460d09d81326ee12abc22422cb41d268d5068f4cbcd88e"
JOB_ID = 389618471873606
RUN_ID = 588435072660254
TASK_ID = 105664983922870
EXPECTED_HISTORICAL_VERSION = "0"


def git(*args: str) -> bytes:
    return subprocess.run(["/usr/bin/git", "-c", f"safe.directory={ROOT}",
                           "-C", str(ROOT), *args], check=True,
                          capture_output=True, timeout=60).stdout


def _function(source: bytes, name: str) -> str:
    node = next(item for item in ast.parse(source).body
                if isinstance(item, ast.FunctionDef) and item.name == name)
    return ast.dump(node, include_attributes=False)


def preflight(commit: str) -> tuple[dict, dict]:
    require(os.geteuid() == 0, "V4_OWNER_ROOT_REQUIRED")
    require(git("rev-parse", "HEAD").decode().strip() == commit
            and not git("status", "--porcelain", "--untracked-files=no").strip(),
            "V4_REVIEWED_COMMIT_OR_TREE_CHANGED")
    for path in (REQUEST, DEPLOYMENT, PRIOR_REQUEST, PRIOR_DEPLOYMENT):
        require(path.read_bytes() == git("show", f"{commit}:{path.relative_to(ROOT)}"),
                "V4_REVIEWED_PIN_CHANGED:" + path.name)
    request = json.loads(REQUEST.read_bytes())
    deployment = json.loads(DEPLOYMENT.read_bytes())
    prior = json.loads(PRIOR_REQUEST.read_bytes())
    require({k: v for k, v in request.items() if k != "execution"} ==
            {k: v for k, v in prior.items() if k != "execution"},
            "V4_SOURCE_OR_SEMANTIC_SCOPE_CHANGED")
    altered = {k for k in request["execution"]
               if request["execution"][k] != prior["execution"][k]}
    require(altered == {"runtime_artifact_sha256", "deployment_sha256"}
            and request["execution"]["runtime_artifact_sha256"] == WHEEL_SHA
            and request["execution"]["deployment_sha256"] == file_digest(DEPLOYMENT),
            "V4_REQUEST_SCOPE_CHANGED")
    artifact = deployment["artifact"]
    wheel = Path(artifact["local_build_output_uncommitted"])
    require(artifact["sha256"] == file_digest(wheel) == WHEEL_SHA
            and artifact["workspace_target_proposed"] ==
            "/Workspace/Shared/edp-lab/day6-c2000-v3-edgar-locator-fix-v4/edp_lab-0.1.0-py3-none-any.whl",
            "V4_WHEEL_OR_PATH_CHANGED")
    with ZipFile(wheel) as archive, ZipFile(Path(json.loads(PRIOR_DEPLOYMENT.read_bytes())
                                           ["artifact"]["local_build_output_uncommitted"])) as old:
        for name in ("v3_keys.py", "v3_mapping.py", "v3_input.py",
                     "v3_spark_runtime.py", "v3_ddl.py", "v3_oracles.py",
                     "v3_readback.py"):
            member = "edp_lab/vault/" + name
            require(archive.read(member) == git("show", f"{commit}:src/edp_lab/vault/{name}"),
                    "V4_WHEEL_SOURCE_MISMATCH:" + name)
        for name in ("v3_ddl.py", "v3_oracles.py", "v3_readback.py"):
            require(archive.read("edp_lab/vault/" + name) ==
                    old.read("edp_lab/vault/" + name),
                    "V4_WRITE_OR_VERIFIER_CHANGED:" + name)
        require(_function(archive.read("edp_lab/vault/v3_spark_runtime.py"), "_write_once") ==
                _function(old.read("edp_lab/vault/v3_spark_runtime.py"), "_write_once"),
                "V4_PERSISTED_WRITE_PATH_CHANGED")
    for path in (STANDING, E2E, INSTALL):
        proof = verified_document(ROOT, path, BASE / "trust")
        require(proof.get("status") in {"INSTALLED", "VERIFIED", "INSTALLED_NOT_GRANTED"},
                "V4_PRIOR_SIGNED_TRUST_INVALID")
    return request, deployment


def reconcile(request: dict) -> dict:
    job = admin_cli("jobs", "get", str(JOB_ID))
    run = admin_cli("jobs", "get-run", str(RUN_ID))
    require(job.get("job_id") == JOB_ID
            and run.get("job_id") == JOB_ID
            and run.get("run_id") == RUN_ID
            and run.get("state", {}).get("result_state") == "FAILED"
            and run.get("status", {}).get("state") == "TERMINATED"
            and len(run.get("tasks", [])) == 1
            and run["tasks"][0].get("run_id") == TASK_ID,
            "V4_CANARY_3_NOT_TERMINAL_FAILED")
    params = run["tasks"][0]["python_wheel_task"]["parameters"]
    require("--execute" not in params and "--verify-only" not in params,
            "V4_CANARY_3_NOT_READ_ONLY")
    output = admin_cli("jobs", "get-run-output", str(TASK_ID))
    require(output.get("error") == "ValueError: INVALID_OCCURRENCE_LOCATOR"
            and "_prepare_rows" in output.get("error_trace", "")
            and "_write_once" not in output.get("error_trace", ""),
            "V4_CANARY_3_FAILURE_CLASS_CHANGED")
    listed = admin_cli("tables", "list", "workspace", "edp_lab_day6_vault_proto")
    require(isinstance(listed, list), "V4_REMOTE_TABLE_LIST_UNVERIFIED")
    by_name = {item["name"]: item for item in listed}
    historical = verified_document(ROOT, INSTALL, BASE / "trust")["historical_table_ids"]
    allowed = set(historical) | {"v0a_day6_e2e_20261025"}
    require(set(by_name) == allowed
            and not set(request["new_v3_table_allowlist"]) & set(by_name),
            "V4_CANARY_3_TARGET_OR_HISTORICAL_SET_CHANGED")
    for name, table_id in historical.items():
        item = by_name[name]
        require(item.get("table_id") == table_id
                and item.get("data_source_format") == "DELTA"
                and item.get("properties", {}).get("delta.lastUpdateVersion") ==
                EXPECTED_HISTORICAL_VERSION,
                "V4_HISTORICAL_DELTA_CHANGED:" + name)
    return {"schema": "EDP_DAY6_V3_CANARY_3_NO_EFFECT_V1",
            "authority": "protected-verifier-v1",
            "status": "TERMINAL_NO_REMOTE_EFFECT",
            "job_id": JOB_ID, "run_id": RUN_ID, "task_id": TASK_ID,
            "read_only_parameters_verified": True,
            "failure_code": "INVALID_OCCURRENCE_LOCATOR",
            "target_absent_count": 23,
            "historical_table_ids": historical,
            "historical_delta_versions": {name: EXPECTED_HISTORICAL_VERSION
                                          for name in historical},
            "run_sha256": hashlib.sha256(json.dumps(run, sort_keys=True).encode()).hexdigest(),
            "verified_at_utc": datetime.now(UTC).isoformat()}


def authorize(commit: str) -> dict:
    request, deployment = preflight(commit)
    proof = reconcile(request)
    if NO_EFFECT.exists():
        saved = verified_document(ROOT, NO_EFFECT, BASE / "trust")
        require(all(saved.get(k) == v for k, v in proof.items()
                    if k != "verified_at_utc"), "V4_SIGNED_NO_EFFECT_CHANGED")
    else:
        _signed_once(proof, "verifier.pem", NO_EFFECT)
    approval = {"schema": "EDP_DAY6_V3_ARTIFACT_UPGRADE_V4",
                "authority": "owner-v3-artifact-upgrade-v4",
                "status": "APPROVED",
                "reviewed_commit": commit,
                "request_sha256": file_digest(REQUEST),
                "deployment_sha256": file_digest(DEPLOYMENT),
                "wheel_sha256": WHEEL_SHA,
                "wheel_workspace_path": deployment["artifact"]["workspace_target_proposed"],
                "canary_3_no_effect_sha256": file_digest(NO_EFFECT),
                "standing_sha256": file_digest(STANDING),
                "prior_e2e_sha256": file_digest(E2E),
                "allowed_operation": "DISTINCT_READ_ONLY_CANARY_V4_THEN_EXISTING_SCOPE_V3",
                "canary_job_submissions_max": 1,
                "automatic_retries_max": 0,
                "target_namespace": request["target_namespace"],
                "source_ids": request["selection"]["source_ids"],
                "table_allowlist": request["new_v3_table_allowlist"],
                "issued_at_utc": datetime.now(UTC).isoformat()}
    if APPROVAL.exists():
        saved = verified_document(ROOT, APPROVAL, BASE / "trust")
        require(all(saved.get(k) == v for k, v in approval.items()
                    if k != "issued_at_utc"), "V4_SIGNED_APPROVAL_CHANGED")
    else:
        _signed_once(approval, "owner.pem", APPROVAL)
    return {"status": "V4_APPROVED_NOT_DEPLOYED",
            "no_effect_sha256": file_digest(NO_EFFECT),
            "approval_sha256": file_digest(APPROVAL),
            "request_sha256": file_digest(REQUEST),
            "wheel_sha256": WHEEL_SHA,
            "remote_job_submissions": 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reviewed_commit")
    args = parser.parse_args()
    print(json.dumps(authorize(args.reviewed_commit), sort_keys=True))


if __name__ == "__main__":
    main()
