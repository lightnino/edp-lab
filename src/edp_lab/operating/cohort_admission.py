"""Exclusive C2000 input publication after 500 independently verified RAW readbacks."""

import json
import os
import shutil
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    authorize,
    canonical,
    digest,
    file_digest,
    load_grant,
    protected_trust_dir,
    verified_document,
)
from edp_lab.operating.boundaries import _reserve
from edp_lab.operating.runner import task_request


def cohort_admit(root: Path, grant: dict, request: dict, ledger: Path,
                 *, execute: bool = False) -> dict:
    """Copy immutable candidate bytes into a new freeze, never rewrite a prior cohort."""
    root = root.resolve()
    if request["operation"] != "cohort_admit" or request["cohort"] != "C2000":
        raise Denied("COHORT_ADMISSION_SCOPE_INVALID")
    if ledger.resolve().is_relative_to(root):
        raise Denied("LEDGER_MUST_BE_OUTSIDE_WORKTREE")
    if execute:
        fresh = load_grant(root, Path(request["grant_path"]), protected_trust_dir(root))
        if fresh != grant:
            raise Denied("GRANT_CHANGED_AT_ADMISSION_BOUNDARY")
    authorize(grant, request, root=root)
    queue_path = (root / request["contracts"]["queue"]["path"]).resolve(strict=True)
    queue = json.loads(queue_path.read_bytes())
    candidate_path = (root / request["candidate_path"]).resolve(strict=True)
    if (not candidate_path.is_relative_to(root)
            or request["candidate_path"] != queue["contracts"]["candidate"]["path"]
            or file_digest(candidate_path) != grant["contracts"]["candidate"]["sha256"]):
        raise Denied("ADMISSION_CANDIDATE_CHANGED")
    candidate = json.loads(candidate_path.read_bytes())
    base = candidate_path.parent
    if (candidate.get("status") != "PREPARED_NOT_ADMITTED_REMOTE_READBACK_PENDING"
            or candidate["new_count"] != 500 or candidate["combined_count"] != 2000):
        raise Denied("ADMISSION_CANDIDATE_INVALID")
    for name, expected in candidate["outputs_sha256"].items():
        if file_digest(base / name) != expected:
            raise Denied("ADMISSION_INPUT_HASH_CHANGED")
    new = json.loads((base / "N500.bindings.json").read_bytes())
    if ({(row["source_identity"], row["raw_sha256"], row["raw_path"])
         for row in new} != {(row["identity"], row["sha256"], row["path"])
                         for row in queue["sources"]} or len(new) != 500):
        raise Denied("ADMISSION_ROSTER_MISMATCH")
    stage_tasks = [task for task in queue["tasks"] if task["kind"] == "raw_stage"]
    if len(stage_tasks) != 500 or {task["source"]["identity"] for task in stage_tasks} != {
            row["source_identity"] for row in new}:
        raise Denied("RAW_STAGE_COVERAGE_INCOMPLETE")
    trust = protected_trust_dir(root)
    receipt_hashes = {}
    for task in stage_tasks:
        receipt_path = Path(task["external_receipt"])
        if receipt_path.parent.resolve() != (trust.parent / "receipts").resolve():
            raise Denied("RAW_RECEIPT_OUTSIDE_PROTECTED_STORE")
        proof = verified_document(root, receipt_path, trust)
        exact = task_request(root, queue, queue_path, task, Path(request["grant_path"]))
        if (proof.get("authority") != "protected-verifier-v1"
                or proof.get("schema") != "EDP_EXTERNAL_OPERATION_RECEIPT_V1"
                or proof.get("operation_id") != task["operation_id"]
                or proof.get("request_sha256") != digest(canonical(exact))
                or proof.get("remote_sha256") != task["source"]["sha256"]
                or proof.get("remote_path") != task["databricks_path"]
                or proof.get("status") != "VERIFIED" or proof.get("live_readback") is not True):
            raise Denied("RAW_RECEIPT_NOT_VERIFIED")
        receipt_hashes[task["source"]["identity"]] = file_digest(receipt_path)
    target = root / "metadata/freezes/C2000_v1"
    alias = root / "metadata/cohorts/C2000.csv"
    if target.exists() or alias.exists():
        raise Denied("COHORT_DESTINATION_ALREADY_EXISTS")
    if not execute:
        return {"status": "AUTHORIZED_DRY_RUN", "sources": 500}
    _reserve(ledger, request["operation_id"], request)
    target.mkdir(exist_ok=False)
    for name in ("N500.bindings.json", "C2000.bindings.json", "N500.csv", "C2000.csv"):
        shutil.copyfile(base / name, target / name)
    freeze = {"schema": "C2000_INPUT_FREEZE_V1", "status": "FROZEN_INPUT_NOT_RESULT",
              "cohort": "C2000", "previous_cohort": "C1500",
              "candidate_sha256": file_digest(candidate_path),
              "queue_sha256": file_digest(queue_path),
              "raw_receipts_sha256": receipt_hashes,
              "files_sha256": {name: file_digest(target / name) for name in (
                  "N500.bindings.json", "C2000.bindings.json", "N500.csv", "C2000.csv")}}
    with (target / "freeze.json").open("x") as stream:
        stream.write(json.dumps(freeze, sort_keys=True, indent=2) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    with alias.open("xb") as stream:
        stream.write((target / "C2000.csv").read_bytes())
        stream.flush()
        os.fsync(stream.fileno())
    return {"status": "PUBLISHED_REQUIRES_INDEPENDENT_READBACK",
            "freeze_sha256": file_digest(target / "freeze.json"),
            "cohort_csv_sha256": file_digest(alias)}
