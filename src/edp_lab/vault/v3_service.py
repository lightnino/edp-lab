"""Root-owned Day 6 V3 socket: scoped attempt issuance and no-effect recovery.

Install this code into the protected runtime. The client supplies only an
action; it cannot choose a Job, request, source, grant, table or attempt ID.
"""

from __future__ import annotations

import argparse
import grp
import hashlib
import json
import os
import socket
import socketserver
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.operating.authority import canonical, file_digest, verified_document


def _imports():
    import owner_day6_v3_successor as successor
    from owner_day6_v3_one_shot import _owner, _pins, _signed_once, _targets, require
    from owner_setup_day6_vault_0a import admin_cli

    return successor, _owner, _pins, _signed_once, _targets, _service_target_absent, require, admin_cli


def _service_target_absent(full_name: str) -> None:
    """Read-only, SP-authenticated absence check; never sudo into Owner OAuth.

    The fixed approved schema is checked by a list read; CREATE TABLE remains
    exclusive-create, so a hidden existing table cannot be replaced.
    """
    import re

    from owner_setup_day6_vault_0a import admin_cli

    prefix = "workspace.edp_lab_day6_vault_proto."
    if (not isinstance(full_name, str)
            or not full_name.startswith(prefix)
            or re.fullmatch(r"[a-z][a-z0-9_]*", full_name[len(prefix):]) is None):
        raise RuntimeError("V3_TARGET_ABSENCE_SCOPE_INVALID")
    objects = admin_cli("tables", "list", "workspace", "edp_lab_day6_vault_proto")
    if not isinstance(objects, list):
        raise TypeError("V3_TARGET_LIST_UNVERIFIED")
    existing = {obj.get("name") for obj in objects}
    if not all(isinstance(name, str) for name in existing):
        raise RuntimeError("V3_TARGET_LIST_UNVERIFIED")
    if full_name[len(prefix):] in existing:
        raise RuntimeError("V3_TARGET_ALREADY_PRESENT:" + full_name)


def _no_effect_path(base: Path, number: int) -> Path:
    return base / f"receipts/day6-v3-attempt-{number}-no-effect.signed.json"


def _ready(root: Path, base: Path) -> None:
    if os.geteuid() != 0 or base.stat().st_uid != 0 or base.stat().st_mode & 0o022:
        raise RuntimeError("V3_PROTECTED_SERVICE_ROOT_REQUIRED")
    standing = verified_document(root, base / "trust/day6-v3-standing-v1.signed.json",
                                 base / "trust")
    original = base / "receipts/day6-v3-e2e-ready-v1.signed.json"
    upgrade = base / "receipts/day6-v3-e2e-ready-coverpage-fix-v3.signed.json"
    approval = base / "approvals/day6-v3-coverpage-fix-upgrade-v3.signed.json"
    initial = verified_document(root, original, base / "trust")
    smoke = verified_document(root, upgrade, base / "trust")
    authorized = verified_document(root, approval, base / "trust")
    installed_commit = _commit(base)
    reviewed_commit = authorized.get("reviewed_commit")
    failed_canary_receipt = (
        base / "receipts/day6-v3-13f-canary-2-no-effect.signed.json"
    )
    old_failure = verified_document(root, failed_canary_receipt, base / "trust")
    if (old_failure.get("schema") != "EDP_DAY6_V3_UPGRADE_CANARY_NO_EFFECT_V1"
            or old_failure.get("status") != "TERMINAL_NO_REMOTE_EFFECT"):
        raise RuntimeError("V3_PREVIOUS_CANARY_NO_EFFECT_NOT_SIGNED")
    from owner_day6_v3_one_shot import CURRENT_REQUEST_SHA256, DEPLOYMENT
    deployment = json.loads(DEPLOYMENT.read_bytes())
    if (standing.get("status") != "INSTALLED"
            or initial.get("status") != "VERIFIED"
            or initial.get("standing_sha256") != file_digest(
                base / "trust/day6-v3-standing-v1.signed.json")
            or authorized.get("schema") != "EDP_DAY6_V3_ARTIFACT_UPGRADE_V1"
            or authorized.get("status") != "APPROVED"
            or authorized.get("request_sha256") != CURRENT_REQUEST_SHA256
            or authorized.get("wheel_sha256") != deployment["artifact"]["sha256"]
            or authorized.get("original_e2e_sha256") != file_digest(original)
            or smoke.get("schema") != "EDP_VAULT_E2E_UPGRADE_V1"
            or smoke.get("status") != "VERIFIED"
            or smoke.get("approval_sha256") != file_digest(approval)
            or smoke.get("installed_reviewed_commit") != installed_commit
            or smoke.get("installed_reviewed_commit") != reviewed_commit
            or authorized.get("reviewed_commit") != installed_commit
            or authorized.get("failed_canary_no_effect_sha256") != file_digest(
                failed_canary_receipt)
            or smoke.get("failed_canary_no_effect_sha256") != file_digest(
                failed_canary_receipt)
            or smoke.get("request_sha256") != CURRENT_REQUEST_SHA256
            or smoke.get("wheel_sha256") != deployment["artifact"]["sha256"]
            or smoke.get("original_e2e_sha256") != file_digest(original)
            or smoke.get("standing_sha256") != file_digest(
                base / "trust/day6-v3-standing-v1.signed.json")):
        raise RuntimeError("V3_UPGRADED_STANDING_OR_E2E_NOT_VERIFIED")


def _commit(base: Path) -> str:
    path = base / "trust/day6-v3-installed-commit.txt"
    if path.stat().st_uid != 0 or path.stat().st_mode & 0o022:
        raise RuntimeError("V3_INSTALLED_COMMIT_UNPROTECTED")
    return path.read_text().strip()


def _next_attempt(root: Path, base: Path) -> tuple[int, str]:
    successor, *_ = _imports()
    for number in range(1, 10000001):
        successor.configure_attempt(number)
        if successor.SUBMISSION.exists() or successor.RESERVATION.exists():
            accepted = base / f"receipts/day6-v3-attempt-{number}-readback.signed.json"
            if accepted.exists():
                proof = verified_document(root, accepted, base / "trust")
                if proof.get("status") != "VERIFIED" or proof.get("attempt_number") != number:
                    raise RuntimeError("V3_ACCEPTED_RECEIPT_MISMATCH")
                return number, "V3_VERIFIED"
            receipt = _no_effect_path(base, number)
            if not receipt.exists():
                return number, "RECONCILIATION_REQUIRED"
            proof = verified_document(root, receipt, base / "trust")
            if (proof.get("status") != "TERMINAL_NO_REMOTE_EFFECT"
                    or proof.get("attempt_number") != number
                    or proof.get("submission_sha256") != file_digest(successor.SUBMISSION)):
                raise RuntimeError("V3_ATTEMPT_NO_EFFECT_RECEIPT_MISMATCH")
            continue
        if successor.SUCCESSOR_INSTALL.exists() or successor.SUCCESSOR_GRANT.exists():
            return number, "INSTALL_OR_GRANT_PARTIAL"
        return number, "READY_FOR_DISTINCT_ATTEMPT"
    raise RuntimeError("V3_STANDING_ATTEMPT_LIMIT_EXHAUSTED")


def status(root: Path, base: Path) -> dict:
    _ready(root, base)
    number, state = _next_attempt(root, base)
    return {"status": state, "next_attempt": number,
            "standing_sha256": file_digest(base / "trust/day6-v3-standing-v1.signed.json"),
            "e2e_sha256": file_digest(
                base / "receipts/day6-v3-e2e-ready-coverpage-fix-v3.signed.json")}


def audit(root: Path, base: Path) -> dict:
    """Run every fixed non-mutating V3 admission check; report all failures.

    This does not claim Job-create, workspace-import or Delta-write authority;
    these can only be proven by separately authorized live execution/canaries.
    """
    _ready(root, base)
    from owner_day6_v3_one_shot import (
        SERVICE_PRINCIPAL_ID,
        SOURCE_TABLES,
        _installed,
        _remote_digest,
        _source_rights,
        _workspace_absent,
        _workspace_access,
    )
    from owner_setup_day6_vault_0a import admin_sql

    successor, owner, pins, _, targets, _, require, cli = _imports()
    owner(_commit(base))
    number, state = _next_attempt(root, base)
    if state != "READY_FOR_DISTINCT_ATTEMPT":
        return {"status": "V3_CHECKPOINT_CHANGED", "attempt_number": number,
                "checkpoint_state": state}
    successor.configure_attempt(number)
    request, deployment = pins()
    results = {}

    def check(label: str, fn) -> None:
        try:
            fn()
        except (OSError, RuntimeError, KeyError, TypeError, ValueError,
                subprocess.CalledProcessError) as exc:
            results[label] = {"status": "BLOCKED", "reason": str(exc)[:240]}
        else:
            results[label] = {"status": "PASS"}

    def verify_identity() -> None:
        identity = cli("current-user", "me")
        require(str(identity.get("id")) == SERVICE_PRINCIPAL_ID,
                "V3_UNATTENDED_IDENTITY_CHANGED")

    def verify_jobs() -> None:
        jobs = cli("jobs", "list")
        require(isinstance(jobs, list), "V3_UNATTENDED_JOBS_LIST_FAILED")

    def verify_wheel() -> None:
        require(_remote_digest(deployment["artifact"]["workspace_target_proposed"])
                == deployment["artifact"]["sha256"], "V3_DEPLOYED_WHEEL_CHANGED")

    def verify_history() -> None:
        _installed(request, deployment)

    def verify_targets() -> None:
        targets(request)

    check("identity", verify_identity)
    check("owner_signed_workspace_scope", _workspace_access)
    check("source_table_metadata", _source_rights)
    check("installed_job_and_pins", verify_history)
    check("wheel_export", verify_wheel)
    check("historical_table_ids", verify_targets)
    # REMOTE_REQUEST is a Databricks Workspace file, not a UC/Delta table.
    # The existing service-context verifier uses the protected M2M profile
    # and fails closed unless the exact remote file is demonstrably absent.
    check("distinct_request_absent", lambda: _workspace_absent(successor.REMOTE_REQUEST))
    check("jobs_list", verify_jobs)

    # Fixed SELECT-only real M2M SQL calls: verify both shared warehouse CAN_USE
    # and effective per-table SELECT, not merely metadata or prior Owner proof.
    for name in SOURCE_TABLES:
        def select_source(name: str = name) -> None:
            reply = admin_sql("SELECT 1 AS access_probe FROM workspace.edp_lab."
                              + name + " LIMIT 0")
            require(reply.get("status", {}).get("state") == "SUCCEEDED",
                    "V3_SERVICE_SOURCE_SELECT_DENIED:" + name)
        check("sql_select:" + name, select_source)

    passed = all(value["status"] == "PASS" for value in results.values())
    return {"status": ("V3_UNATTENDED_ADMISSION_READS_VERIFIED"
                       if passed else "V3_RUNTIME_CAPABILITY_AUDIT_BLOCKED"),
            "attempt_number": number, "checks": results,
            "write_capabilities": "NOT_TESTED_NO_MUTATION",
            "checks_passed": sum(v["status"] == "PASS" for v in results.values()),
            "checks_total": len(results)}


def probe(root: Path, base: Path) -> dict:
    """A single read-only full capability audit, never first-error-only."""
    return audit(root, base)


def evidence(root: Path, base: Path) -> dict:
    """Expose only a verified, non-secret acceptance document to the agent."""
    _ready(root, base)
    number, state = _next_attempt(root, base)
    if state != "V3_VERIFIED":
        return {"status": state, "attempt_number": number}
    path = base / f"receipts/day6-v3-attempt-{number}-readback.signed.json"
    proof = verified_document(root, path, base / "trust")
    return {"status": "V3_VERIFIED", "attempt_number": number,
            "receipt_sha256": file_digest(path), "receipt": proof}


def run(root: Path, base: Path) -> dict:
    _ready(root, base)
    successor, owner, *_ = _imports()
    commit = _commit(base)
    owner(commit)
    preflight = audit(root, base)
    if preflight.get("status") != "V3_UNATTENDED_ADMISSION_READS_VERIFIED":
        return preflight
    number, state = _next_attempt(root, base)
    if state != "READY_FOR_DISTINCT_ATTEMPT":
        return {"status": state, "attempt_number": number}
    successor.configure_attempt(number)
    installed = successor.authorize(commit)
    submitted = successor.execute(commit)
    return {"status": submitted["status"], "attempt_number": number,
            "job_id": installed["job_id"], "run_id": submitted.get("run_id")}


def reconcile(root: Path, base: Path) -> dict:
    _ready(root, base)
    (successor, owner, pins, sign_once, targets, target_absent,
     require, admin_cli) = _imports()
    owner(_commit(base))
    number, state = _next_attempt(root, base)
    if state != "RECONCILIATION_REQUIRED":
        return {"status": state, "attempt_number": number}
    successor.configure_attempt(number)
    require(successor.SUBMISSION.exists(), "V3_ATTEMPT_RUN_ID_UNCERTAIN")
    install = verified_document(root, successor.SUCCESSOR_INSTALL, base / "trust")
    grant = verified_document(root, successor.SUCCESSOR_GRANT, base / "trust")
    reservation = json.loads(successor.RESERVATION.read_bytes())
    submission = json.loads(successor.SUBMISSION.read_bytes())
    require(install.get("job_id") == grant.get("job_id") == submission.get("job_id")
            and reservation.get("grant_sha256") == file_digest(successor.SUCCESSOR_GRANT)
            and submission.get("grant_sha256") == file_digest(successor.SUCCESSOR_GRANT),
            "V3_ATTEMPT_LEDGER_MISMATCH")
    run_id = submission["run_id"]
    run_record = admin_cli("jobs", "get-run", str(run_id))
    require(run_record.get("run_id") == run_id
            and run_record.get("job_id") == install["job_id"],
            "V3_ATTEMPT_REMOTE_JOB_MISMATCH")
    terminal = run_record.get("status", {}).get("state") == "TERMINATED"
    if not terminal:
        started = run_record.get("start_time")
        elapsed = ((datetime.now(UTC).timestamp() * 1000 - started) / 1000
                   if type(started) is int else None)
        state_name = run_record.get("status", {}).get("state")
        return {"status": ("STALLED_PENDING_DIAGNOSIS" if elapsed is not None
                           and elapsed > 3600 else "ACTIVE_OR_UNRESOLVED_REQUIRES_POLL"),
                "attempt_number": number, "run_id": run_id,
                "job_state": state_name, "elapsed_seconds": elapsed,
                "observed_at_utc": datetime.now(UTC).isoformat()}
    request, _ = pins()
    if run_record.get("state", {}).get("result_state") == "SUCCESS":
        return _verify_success(root, base, number, run_record, install, grant,
                               reservation, submission)
    baseline = targets(request)
    require(baseline == install["historical_table_ids"],
            "V3_HISTORICAL_BASELINE_CHANGED")
    for name in request["new_v3_table_allowlist"]:
        target_absent(request["target_namespace"] + "." + name)
    receipt = _no_effect_path(base, number)
    require(not receipt.exists(), "V3_ATTEMPT_ALREADY_RECONCILED")
    document = {
        "schema": "EDP_DAY6_V3_ATTEMPT_NO_EFFECT_V1",
        "authority": "protected-verifier-v1", "status": "TERMINAL_NO_REMOTE_EFFECT",
        "attempt_number": number, "job_id": install["job_id"], "run_id": run_id,
        "original_partial_receipt_sha256": file_digest(successor.PARTIAL_RECEIPT),
        "install_sha256": file_digest(successor.SUCCESSOR_INSTALL),
        "grant_sha256": file_digest(successor.SUCCESSOR_GRANT),
        "reservation_sha256": file_digest(successor.RESERVATION),
        "submission_sha256": file_digest(successor.SUBMISSION),
        "terminal_run_sha256": __import__("hashlib").sha256(
            canonical(run_record)).hexdigest(),
        "absent_targets": request["new_v3_table_allowlist"],
        "historical_table_ids": baseline,
        "verified_at_utc": datetime.now(UTC).isoformat(),
    }
    sign_once(document, "verifier.pem", receipt)
    return {"status": "TERMINAL_NO_REMOTE_EFFECT", "attempt_number": number,
            "receipt_sha256": file_digest(receipt)}


def _verify_success(root: Path, base: Path, number: int, run_record: dict,
                    install: dict, grant: dict, reservation: dict,
                    submission: dict) -> dict:
    (successor, _, pins, sign_once, _, _, require, admin_cli) = _imports()
    receipt = base / f"receipts/day6-v3-attempt-{number}-readback.signed.json"
    if receipt.exists():
        proof = verified_document(root, receipt, base / "trust")
        require(proof.get("status") == "VERIFIED" and proof.get("run_id") == submission["run_id"],
                "V3_SIGNED_READBACK_CHANGED")
        return {"status": "V3_VERIFIED", "attempt_number": number,
                "receipt_sha256": file_digest(receipt), "receipt_path": str(receipt)}
    request, deployment = pins()
    # The verifier Job is a separate read-only execution of the pinned mapper.
    # Its fixed files are written once; an uncertain response is reconciled,
    # never retried as if the first call were known absent.
    job_record = base / f"ledger/day6-v3-attempt-{number}-verify-job.json"
    run_reservation = base / f"ledger/day6-v3-attempt-{number}-verify-reservation.json"
    run_record_path = base / f"ledger/day6-v3-attempt-{number}-verify-run.json"
    parameters = ["--request", successor.REMOTE_REQUEST,
                  "--request-sha256", file_digest(successor.DERIVED),
                  "--selection", "/Workspace/Shared/edp-lab/day6-c2000-v3/selection.json",
                  "--negative-oracles",
                  "/Workspace/Shared/edp-lab/day6-c2000-v3/negative-oracles.json",
                  "--verify-only"]
    from owner_day6_v3_one_shot import _job_settings, _write_once

    from edp_lab.vault.v3_one_shot_gate import verify_saved_job

    if job_record.exists():
        verify_job_id = json.loads(job_record.read_bytes())["job_id"]
    else:
        require(not run_reservation.exists() and not run_record_path.exists(),
                "V3_VERIFY_JOB_CREATE_UNCERTAIN")
        settings = _job_settings(file_digest(successor.DERIVED), deployment)
        settings["name"] = f"day6-v3-attempt-{number}-readback"
        settings["tasks"][0]["python_wheel_task"]["parameters"] = parameters
        created = admin_cli("jobs", "create", "--json", json.dumps(settings))
        verify_job_id = created.get("job_id") if isinstance(created, dict) else None
        require(type(verify_job_id) is int and verify_job_id > 0,
                "V3_VERIFY_JOB_CREATE_UNCERTAIN")
        _write_once(job_record, {"job_id": verify_job_id, "attempt_number": number})
    saved = admin_cli("jobs", "get", str(verify_job_id))
    verify_saved_job(saved["settings"],
                     wheel_path=deployment["artifact"]["workspace_target_proposed"],
                     run_as={"service_principal_name": successor.APP_ID},
                     parameters=parameters)
    if run_record_path.exists():
        verify_run_id = json.loads(run_record_path.read_bytes())["run_id"]
    else:
        require(not run_reservation.exists(), "V3_VERIFY_RUN_UNCERTAIN")
        _write_once(run_reservation, {"job_id": verify_job_id,
                                      "attempt_number": number})
        response = admin_cli("jobs", "run-now", str(verify_job_id), "--no-wait",
                             "--idempotency-token",
                             hashlib.sha256(canonical({"readback": number,
                                                       "job_id": verify_job_id}))
                             .hexdigest()[:32])
        verify_run_id = response.get("run_id") if isinstance(response, dict) else None
        require(type(verify_run_id) is int and verify_run_id > 0,
                "V3_VERIFY_RUN_ID_UNCERTAIN")
        _write_once(run_record_path, {"job_id": verify_job_id, "run_id": verify_run_id})
    verified_run = admin_cli("jobs", "get-run", str(verify_run_id))
    require(verified_run.get("job_id") == verify_job_id
            and verified_run.get("run_id") == verify_run_id,
            "V3_VERIFY_RUN_ID_CHANGED")
    if verified_run.get("status", {}).get("state") != "TERMINATED":
        return {"status": "V3_INDEPENDENT_READBACK_RUNNING", "run_id": verify_run_id}
    require(verified_run.get("state", {}).get("result_state") == "SUCCESS"
            and len(verified_run.get("tasks", [])) == 1,
            "V3_INDEPENDENT_READBACK_FAILED")
    output = admin_cli("jobs", "get-run-output",
                       str(verified_run["tasks"][0]["run_id"]))
    logs = output.get("logs", "")
    candidates = []
    for line in logs.splitlines():
        if line.startswith("{") and '"INDEPENDENT_V3_READBACK_CANDIDATE"' in line:
            candidates.append(json.loads(line))
    require(len(candidates) == 1, "V3_VERIFIER_OUTPUT_UNAVAILABLE")
    candidate = candidates[0]
    tables = candidate["readback_candidate"]["tables"]
    selection = json.loads((root / request["selection"]["path"]).read_bytes())
    expected_sources = {
        sid: sum(member["selected_data_rows"] for member in source["members"].values())
        for sid, source in selection["sources"].items()
    }
    require(set(tables) == set(request["new_v3_table_allowlist"])
            and candidate["per_source"] == expected_sources
            and sum(candidate["per_source"].values()) == 2047
            and len(candidate["isolated_negative_oracles_passed"]) == 24,
            "V3_INDEPENDENT_SOURCE_COVERAGE_MISMATCH")
    from owner_setup_day6_vault_0a import admin_sql

    independent_tables = {}
    for name, item in tables.items():
        remote = admin_cli("tables", "get", request["target_namespace"] + "." + name)
        count = admin_sql("SELECT COUNT(*) FROM " + request["target_namespace"] + "." + name)
        rows = count.get("result", {}).get("data_array")
        require(remote.get("table_id") == item["uc_delta_id"]
                and remote.get("properties", {}).get("delta.lastUpdateVersion")
                == str(item["latest_version"])
                and isinstance(rows, list) and len(rows) == 1
                and str(rows[0][0]) == str(item["row_count"]),
                "V3_INDEPENDENT_TABLE_READBACK_MISMATCH:" + name)
        independent_tables[name] = {"uc_table_id": remote["table_id"],
                                    "delta_version": item["latest_version"],
                                    "row_count": item["row_count"],
                                    "exact_row_sha256": item["exact_row_sha256"]}
    historical = {}
    for name, table_id in install["historical_table_ids"].items():
        item = admin_cli("tables", "get", request["target_namespace"] + "." + name)
        require(item.get("table_id") == table_id, "V3_HISTORICAL_TABLE_CHANGED:" + name)
        historical[name] = table_id
    document = {
        "schema": "EDP_VAULT_V3_PROTOTYPE_READBACK_V1",
        "authority": "protected-verifier-v1", "status": "VERIFIED",
        "cohort": "C2000", "attempt_number": number,
        "job_id": install["job_id"], "run_id": submission["run_id"],
        "v3_request_sha256": file_digest(successor.REQUEST),
        "selected_data_rows": 2047, "negative_oracles_passed": 24,
        "historical_prototype_unchanged": True,
        "historical_table_ids": historical,
        "source_coverage": {sid: "VERIFIED" for sid in request["selection"]["source_ids"]},
        "source_occurrences": candidate["per_source"],
        "tables": independent_tables,
        "original_partial_receipt_sha256": file_digest(successor.PARTIAL_RECEIPT),
        "install_sha256": file_digest(successor.SUCCESSOR_INSTALL),
        "grant_sha256": file_digest(successor.SUCCESSOR_GRANT),
        "reservation_sha256": file_digest(successor.RESERVATION),
        "submission_sha256": file_digest(successor.SUBMISSION),
        "verifier_job_id": verify_job_id, "verifier_run_id": verify_run_id,
        "verifier_output_sha256": hashlib.sha256(canonical(output)).hexdigest(),
        "production_run_sha256": hashlib.sha256(canonical(run_record)).hexdigest(),
        "verified_at_utc": datetime.now(UTC).isoformat(),
    }
    sign_once(document, "verifier.pem", receipt)
    return {"status": "V3_VERIFIED", "attempt_number": number,
            "receipt_sha256": file_digest(receipt), "receipt_path": str(receipt)}


def freeze(root: Path, base: Path) -> dict:
    """Pin the accepted scoped result in Delta and sign independent readback."""
    _ready(root, base)
    (successor, owner, pins, sign_once, _, target_absent,
     require, admin_cli) = _imports()
    from owner_day6_v3_one_shot import _write_once
    from owner_setup_day6_vault_0a import admin_sql

    owner(_commit(base))
    number, state = _next_attempt(root, base)
    require(state == "V3_VERIFIED", "V9_V3_SIGNED_ACCEPTANCE_REQUIRED")
    v3_path = base / f"receipts/day6-v3-attempt-{number}-readback.signed.json"
    v3 = verified_document(root, v3_path, base / "trust")
    request, _ = pins()
    evidence = {}
    for stage in ("v4", "v5", "v6", "v8"):
        path = root / f"runs/day6-vault-scoped/{stage}.json"
        item = json.loads(path.read_bytes())
        require(item.get("status") == "PASS"
                and item.get("scope") == "FOUR_FAMILY_BOUNDED_PROTOTYPE"
                and item.get("v3_receipt_sha256") == file_digest(v3_path),
                "V9_SCOPED_PREREQUISITE_INVALID:" + stage)
        evidence[stage] = file_digest(path)
    live = {}
    for name, accepted in v3["tables"].items():
        full = request["target_namespace"] + "." + name
        item = admin_cli("tables", "get", full)
        count = admin_sql("SELECT COUNT(*) FROM " + full)
        rows = count.get("result", {}).get("data_array")
        require(item.get("table_id") == accepted["uc_table_id"]
                and item.get("properties", {}).get("delta.lastUpdateVersion")
                == str(accepted["delta_version"])
                and isinstance(rows, list) and len(rows) == 1
                and str(rows[0][0]) == str(accepted["row_count"]),
                "V9_LIVE_V3_TABLE_CHANGED:" + name)
        live[name] = {"table_id": item["table_id"],
                      "delta_version": accepted["delta_version"],
                      "row_count": accepted["row_count"]}
    for name, table_id in v3["historical_table_ids"].items():
        item = admin_cli("tables", "get", request["target_namespace"] + "." + name)
        require(item.get("table_id") == table_id, "V9_HISTORICAL_TABLE_CHANGED:" + name)
    payload = {"schema": "EDP_DAY6_SCOPED_VAULT_FREEZE_V1",
               "scope": "FOUR_FAMILY_BOUNDED_PROTOTYPE",
               "v3_receipt_sha256": file_digest(v3_path),
               "evidence_sha256": evidence, "tables": live,
               "source_coverage": v3["source_coverage"]}
    freeze_id = hashlib.sha256(canonical(payload)).hexdigest()
    full = request["target_namespace"] + ".v9_day6_scoped_freeze"
    reservation = base / "ledger/day6-v9-scoped-freeze-v1.json"
    signed = base / "receipts/day6-v9-scoped-freeze-v1.signed.json"
    if signed.exists():
        proof = verified_document(root, signed, base / "trust")
        require(proof.get("freeze_id") == freeze_id, "V9_EXISTING_FREEZE_CHANGED")
        return {"status": "V9_LIVE_FREEZE_VERIFIED", "receipt_path": str(signed),
                "receipt_sha256": file_digest(signed)}
    if not reservation.exists():
        target_absent(full)
        _write_once(reservation, {"freeze_id": freeze_id,
                                  "request_sha256": file_digest(successor.REQUEST),
                                  "reserved_at_utc": datetime.now(UTC).isoformat()})
        raw = canonical(payload).decode()
        def literal(value: str) -> str:
            return "'" + value.replace("'", "''") + "'"
        sql = (f"CREATE TABLE {full} USING DELTA AS SELECT "
               f"{literal(freeze_id)} AS freeze_id, "
               f"{literal(raw)} AS payload_json")
        admin_sql(sql)
    recorded = admin_cli("tables", "get", full)
    rows = admin_sql("SELECT freeze_id, payload_json FROM " + full)
    require(recorded.get("table_id") and recorded.get("data_source_format") == "DELTA"
            and rows.get("result", {}).get("data_array") == [[freeze_id, canonical(payload).decode()]],
            "V9_LIVE_FREEZE_READBACK_MISMATCH")
    document = {
        "schema": "EDP_VAULT_LIVE_FREEZE_RECEIPT_V1",
        "authority": "protected-verifier-v1", "cohort": "C2000",
        "status": "VERIFIED", "scope": "FOUR_FAMILY_BOUNDED_PROTOTYPE",
        "live_readback": True, "freeze_id": freeze_id,
        "freeze_table_id": recorded["table_id"],
        "delta_ids": {name: item["table_id"] for name, item in live.items()},
        "delta_versions": {name: item["delta_version"] for name, item in live.items()},
        "source_coverage": v3["source_coverage"],
        "v3_receipt_sha256": file_digest(v3_path),
        "evidence_sha256": evidence,
        "reservation_sha256": file_digest(reservation),
        "verified_at_utc": datetime.now(UTC).isoformat(),
    }
    sign_once(document, "verifier.pem", signed)
    return {"status": "V9_LIVE_FREEZE_VERIFIED", "receipt_path": str(signed),
            "receipt_sha256": file_digest(signed), "freeze_id": freeze_id}


def serve(root: Path, base: Path) -> None:
    os.environ["EDP_DAY6_REVIEWED_ROOT"] = str(root)
    os.environ["EDP_DAY6_V3_SERVICE_CONTEXT"] = "1"
    _ready(root, base)
    socket_path = base / "day6-v3.sock"
    if socket_path.exists():
        info = socket_path.lstat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != 0:
            raise RuntimeError("V3_SOCKET_UNTRUSTED")
        with socket.socket(socket.AF_UNIX) as existing_socket:
            existing_socket.settimeout(2)
            try:
                existing_socket.connect(str(socket_path))
            except ConnectionRefusedError:
                socket_path.unlink()
            else:
                raise RuntimeError("V3_SERVICE_ALREADY_RUNNING")

    class Handler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            try:
                request = json.loads(self.rfile.readline(4096))
                if request == {"action": "status"}:
                    response = status(root, base)
                elif request == {"action": "probe"}:
                    response = probe(root, base)
                elif request == {"action": "audit"}:
                    response = audit(root, base)
                elif request == {"action": "evidence"}:
                    response = evidence(root, base)
                elif request == {"action": "run"}:
                    response = run(root, base)
                elif request == {"action": "reconcile"}:
                    response = reconcile(root, base)
                elif request == {"action": "freeze"}:
                    response = freeze(root, base)
                else:
                    response = {"status": "DENIED", "reason": "V3_ACTION_OUT_OF_SCOPE"}
            except (OSError, RuntimeError, KeyError, TypeError, ValueError) as exc:
                response = {"status": "BLOCKED", "reason": str(exc)[:300]}
            self.wfile.write(canonical(response))

    with socketserver.UnixStreamServer(str(socket_path), Handler) as server:
        os.chown(socket_path, 0, grp.getgrnam("staff").gr_gid)
        os.chmod(socket_path, 0o660)
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("base", type=Path)
    args = parser.parse_args()
    serve(args.root, args.base)


if __name__ == "__main__":
    main()
