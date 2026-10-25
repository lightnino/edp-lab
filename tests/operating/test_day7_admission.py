"""Generic incremental admission: exact identity, pinned frozen inputs, no RAW writes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from edp_lab.ingestion.universe import ACTIVE_AUTHORITY_PATH
from edp_lab.operating import cohort_admission as admission
from edp_lab.operating.authority import Denied, file_digest


def setup(tmp_path: Path, monkeypatch):
    root = tmp_path
    (root / "metadata/freezes").mkdir(parents=True)
    (root / "metadata/cohorts").mkdir(parents=True)
    (root / "inputs").mkdir()
    (root / "protected/trust").mkdir(parents=True)
    (root / "protected/receipts").mkdir()
    source_index_path = root / "protected/source_evidence_index.json"
    source_index_path.write_text("{}")
    source_index_sha = file_digest(source_index_path)
    old = [{"source_instance_id": "SRC001", "source_identity": "original",
            "raw_sha256": "a" * 64, "raw_path": "raw/original"}]
    new = [{"source_instance_id": "SRC002", "source_identity": "fresh",
            "raw_sha256": "b" * 64, "raw_path": "raw/fresh",
            "remote_raw_path": "dbfs:/Volume/verified/fresh"}]
    old_path = root / "inputs/previous.json"
    old_path.write_text(json.dumps(old))
    new_path = root / "inputs/new.json"
    receipt = root / "protected/receipts/day7-u10-fresh.json"
    receipt.write_text(json.dumps({"test": "not used as owner authority"}))
    new[0].update(raw_handoff_receipt_path=str(receipt),
                  raw_handoff_receipt_sha256=file_digest(receipt))
    new_path.write_text(json.dumps(new))
    freeze_path = root / "inputs/frozen.json"
    freeze_path.write_text(json.dumps({"status": "FROZEN"}))
    manifest = {"schema": "SOURCE_UNIVERSE_AUTHORITY_V1",
                "universe_version": "active", "approval_reference": "approval.json",
                "inventory_reference": "inventory.json",
                "inventory_sha256": "0" * 64,
                "members": [
                    {"identity": "original", "raw_sha256": "a" * 64,
                     "raw_path": "raw/original", "holdout": False},
                    {"identity": "fresh", "raw_sha256": "b" * 64,
                     "raw_path": "raw/fresh", "holdout": False,
                     "source_instance_id": "SRC002", "raw_bytes": 123,
                     "remote_raw_path": "dbfs:/Volume/verified/fresh",
                     "remote_receipt_sha256": "e" * 64},
                    {"identity": "reserved", "raw_sha256": "c" * 64,
                     "raw_path": "raw/reserved", "holdout": True},
                ], "member_count": 3,
                "expansion": {"independent_remote_readback_sha256": "f" * 64}}
    active = root / ACTIVE_AUTHORITY_PATH
    active.parent.mkdir(parents=True)
    active.write_text(json.dumps(manifest))
    universe_sha = file_digest(active)
    approval = root / "approval.json"
    approval.write_text(json.dumps({"status": "APPROVED",
                                   "manifest_sha256": universe_sha}))
    approval_sha = file_digest(approval)
    candidate = {"schema": "EDP_INCREMENTAL_COHORT_CANDIDATE_V1",
                 "status": "PREPARED_NOT_ADMITTED",
                 "previous_cohort": "C1", "cohort": "C2",
                 "expected_increment": 1,
                 "previous_bindings_path": "inputs/previous.json",
                 "previous_bindings_sha256": file_digest(old_path),
                 "new_bindings_path": "inputs/new.json",
                 "new_bindings_sha256": file_digest(new_path),
                 "previous_freeze_path": "inputs/frozen.json",
                 "previous_freeze_sha256": file_digest(freeze_path),
                 "universe_sha256": universe_sha,
                 "universe_approval_sha256": approval_sha}
    candidate_path = root / "inputs/candidate.json"
    candidate_path.write_text(json.dumps(candidate))
    queue_path = root / "inputs/queue.json"
    queue_path.write_text(json.dumps({"cohort": "C2"}))
    queue = {"raw_mode": "VERIFIED_READ_ONLY", "previous_cohort": "C1",
             "tasks": [{"kind": "cohort_admit"}],
             "sources": [{"identity": "fresh", "sha256": "b" * 64,
                          "remote_raw_path": "dbfs:/Volume/verified/fresh"}],
             "contracts": {"universe": {"path": str(ACTIVE_AUTHORITY_PATH),
                                        "sha256": universe_sha}}}
    grant = {"contracts": {"universe": {"sha256": universe_sha},
                           "universe_approval": {"sha256": approval_sha},
                           "source_evidence_index": {"sha256": source_index_sha}}}
    request = {"cohort": "C2", "operation_id": "day7-c2-admit",
               "contracts": {"queue": {"path": "inputs/queue.json"}}}
    monkeypatch.setattr(admission, "protected_trust_dir", lambda _: root / "protected/trust")
    monkeypatch.setattr("edp_lab.operating.day7_protected.verified_document", lambda *_: {
        "schema": "EDP_U10_RAW_HANDOFF_RECEIPT_V1",
        "authority": "protected-verifier-v1", "status": "VERIFIED",
        "readback_mode": "CURRENT_FULL_HASH",
        "live_readback": True, "physical_identity": "fresh",
        "source_instance_id": "SRC002", "remote_sha256": "b" * 64,
        "remote_bytes": 123, "remote_path": "dbfs:/Volume/verified/fresh",
        "remote_receipt_sha256": "e" * 64,
        "historical_independent_readback_sha256": "f" * 64,
        "manifest_sha256": universe_sha,
        "source_evidence_index_sha256": source_index_sha,
    })
    monkeypatch.setattr(admission, "_reserve", lambda *_: None)
    return root, grant, request, queue, candidate_path, candidate


def test_new_cohort_publication_reuses_accepted_old(tmp_path, monkeypatch):
    root, grant, request, queue, candidate_path, candidate = setup(tmp_path, monkeypatch)
    dry = admission._admit_incremental(
        root, grant, request, root / "protected/ledger",
        queue, candidate_path, candidate, execute=False)
    assert dry["status"] == "AUTHORIZED_DRY_RUN"
    assert not (root / "metadata/freezes/C2").exists()
    live = admission._admit_incremental(
        root, grant, request, root / "protected/ledger",
        queue, candidate_path, candidate, execute=True)
    freeze = json.loads((root / "metadata/freezes/C2/freeze.json").read_text())
    assert freeze["status"] == "FROZEN_INPUT_NOT_RESULT"
    assert freeze["old_count"] == 1 and freeze["new_count"] == 1
    assert freeze["combined_count"] == 2 and freeze["raw_write_operations"] == 0
    assert live["status"] == "PUBLISHED_REQUIRES_INDEPENDENT_READBACK"
    assert (root / "metadata/cohorts/C2.csv").exists()
    assert json.loads((root / "metadata/freezes/C2/C2.bindings.json").read_text()) == [
        *json.loads((root / "inputs/previous.json").read_text()),
        *json.loads((root / "inputs/new.json").read_text()),
    ]


def test_queue_source_cannot_differ_from_candidate(tmp_path, monkeypatch):
    root, grant, request, queue, candidate_path, candidate = setup(tmp_path, monkeypatch)
    queue["sources"][0]["sha256"] = "f" * 64
    with pytest.raises(Denied, match="INCREMENT_QUEUE_SOURCE_MISMATCH"):
        admission._admit_incremental(root, grant, request,
                                     root / "protected/ledger", queue,
                                     candidate_path, candidate, execute=False)


def test_owner_approval_must_be_pinned_by_broker(tmp_path, monkeypatch):
    root, grant, request, queue, candidate_path, candidate = setup(tmp_path, monkeypatch)
    grant["contracts"].pop("universe_approval")
    with pytest.raises(Denied, match="ACTIVE_UNIVERSE_APPROVAL_NOT_PINNED"):
        admission._admit_incremental(root, grant, request,
                                     root / "protected/ledger", queue,
                                     candidate_path, candidate, execute=False)
