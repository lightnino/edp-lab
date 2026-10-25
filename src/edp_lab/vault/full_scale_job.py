"""Candidate protected Spark Jobs and Delta freeze operations.

The installed Vault V2 service does not expose these actions. This adapter is
for an independently installed, owner-authorized protected service only; it
has no credential, signature or policy issuer and cannot run by itself.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from edp_lab.operating.authority import Denied, canonical, digest
from edp_lab.operating.boundaries import _reserve
from edp_lab.vault.full_scale_boundary import validate_batch, validate_freeze_candidate
from edp_lab.vault.standing_v2 import NAMESPACE


class JobsTransport(Protocol):
    def submit(self, payload: dict) -> dict: ...

    def get_run(self, run_id: int) -> dict: ...


class FreezeReader(Protocol):
    def table(self, namespace: str, name: str) -> dict: ...

    def source_coverage(self, namespace: str, source_ids: list[str]) -> dict: ...


def submit_batch(request: dict, authority: dict, repo_root: Path, ledger: Path,
                 transport: JobsTransport) -> dict:
    """Reserve once, then submit an exact pinned runtime with no retry.

    The caller must independently verify the owner-signed authority, the
    deployed runtime SHA-256 and the source manifest before invoking this.
    """
    validate_batch(request, authority)
    if not authority.get("trusted_signature_verified"):
        raise Denied("VAULT_OWNER_AUTHORITY_UNVERIFIED")
    if not authority.get("deployment_sha256_verified"):
        raise Denied("VAULT_REMOTE_DEPLOYMENT_UNVERIFIED")
    if not authority.get("source_manifest_verified"):
        raise Denied("VAULT_SOURCE_MANIFEST_UNVERIFIED")
    if ledger.resolve().is_relative_to(repo_root.resolve()):
        raise Denied("VAULT_LEDGER_MUST_BE_PROTECTED")
    # Protected caller supplies ledger outside the worktree. Reservation is
    # durable before the external call; uncertain outcomes require readback.
    record = _reserve(ledger, request["batch_id"], request)
    payload = {"run_name": request["batch_id"],
               "idempotency_token": digest(canonical(request))[:32],
               "timeout_seconds": request["timeout_seconds"],
               "tasks": [{"task_key": "vault_batch",
                          "timeout_seconds": request["timeout_seconds"],
                          "max_retries": 0,
                          "notebook_task": {
                              "notebook_path": authority["notebook_path"],
                              "source": "WORKSPACE",
                              "base_parameters": {
                                  "request_sha256": digest(canonical(request)),
                                  "manifest_sha256": request["source_manifest_sha256"],
                                  "batch_id": request["batch_id"]}}}]}
    try:
        response = transport.submit(payload)
        run_id = response.get("run_id")
        if type(run_id) is not int or run_id <= 0:
            raise ValueError("missing run id")
        outcome = {"status": "SUBMITTED_REQUIRES_READBACK", "run_id": run_id,
                   "request_sha256": digest(canonical(request))}
    except (OSError, ValueError, TimeoutError):
        outcome = {"status": "UNCERTAIN_REQUIRES_READBACK",
                   "request_sha256": digest(canonical(request))}
    with record.open("w") as stream:
        stream.write(json.dumps(outcome, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return outcome


def readback_batch(request: dict, repo_root: Path, ledger: Path,
                   transport: JobsTransport) -> dict:
    """Read one known Jobs ID; success still requires persisted Delta checks."""
    if ledger.resolve().is_relative_to(repo_root.resolve()):
        raise Denied("VAULT_LEDGER_MUST_BE_PROTECTED")
    record = json.loads((ledger / (request["batch_id"] + ".json")).read_bytes())
    if record.get("request_sha256") != digest(canonical(request)):
        raise Denied("VAULT_BATCH_LEDGER_MISMATCH")
    if record.get("status") != "SUBMITTED_REQUIRES_READBACK":
        raise Denied("VAULT_BATCH_UNCERTAIN_RECONCILE_EXTERNALLY")
    run_id = record["run_id"]
    live = transport.get_run(run_id)
    if live.get("run_id") != run_id:
        raise Denied("VAULT_BATCH_REMOTE_RUN_MISMATCH")
    state = live.get("state", {})
    return {"run_id": run_id, "request_sha256": record["request_sha256"],
            "remote_state": state, "remote_response_sha256": digest(canonical(live)),
            "status": ("JOB_TERMINAL_SUCCESS_DELTA_READBACK_REQUIRED"
                       if state.get("life_cycle_state") == "TERMINATED"
                       and state.get("result_state") == "SUCCESS"
                       else "NOT_VERIFIED")}


def read_freeze_candidate(authority: dict, reader: FreezeReader) -> dict:
    """Collect live pins and complete source dispositions, unsigned.

    A protected verifier must independently validate table history, data and
    lineage predicates and sign a distinct receipt after this candidate.
    """
    if not authority.get("trusted_signature_verified"):
        raise Denied("VAULT_OWNER_AUTHORITY_UNVERIFIED")
    names = sorted(authority["target_tables"])
    sources = sorted(authority["source_ids"])
    candidate = {"schema": "EDP_VAULT_FREEZE_CANDIDATE_V1", "cohort": "C2000",
                 "namespace": NAMESPACE,
                 "source_manifest_sha256": authority["source_manifest_sha256"],
                 "contracts": authority["contracts"],
                 "tables": {name: reader.table(NAMESPACE, name) for name in names},
                 "source_coverage": reader.source_coverage(NAMESPACE, sources),
                 "status": "LIVE_READBACK_COMPLETE"}
    validate_freeze_candidate(candidate, authority)
    return candidate
