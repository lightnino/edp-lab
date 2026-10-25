"""Day 7 runtime boundaries: one pinned active universe and read-only RAW."""

from __future__ import annotations

import json

import pytest

from edp_lab.ingestion.universe import ACTIVE_AUTHORITY_PATH, ScopeDenied, UniverseGate, sha
from edp_lab.operating.authority import Denied
from edp_lab.operating.runner import _validate_raw_mode


def _installed(tmp_path):
    manifest = {
        "schema": "SOURCE_UNIVERSE_AUTHORITY_V1",
        "universe_id": "TEST",
        "universe_version": "current",
        "approval_reference": "owner-approval.json",
        "inventory_reference": "inventory.json",
        "inventory_sha256": "0" * 64,
        "member_count": 2,
        "members": [
            {"identity": "eligible", "raw_sha256": "a" * 64,
             "raw_path": "raw/eligible", "holdout": False},
            {"identity": "reserved", "raw_sha256": "b" * 64,
             "raw_path": "raw/reserved", "holdout": True},
        ],
    }
    path = tmp_path / ACTIVE_AUTHORITY_PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(manifest))
    pin = sha(path.read_bytes())
    approval = {"status": "APPROVED", "manifest_sha256": pin}
    approved_path = tmp_path / "owner-approval.json"
    approved_path.write_text(json.dumps(approval))
    return pin, sha(approved_path.read_bytes())


def test_single_active_manifest_pinned_to_owner_approval(tmp_path):
    manifest_sha, approval_sha = _installed(tmp_path)
    gate = UniverseGate.load_active(tmp_path, manifest_sha256=manifest_sha,
                                    approval_sha256=approval_sha)
    assert gate.check("eligible", "a" * 64, "raw/eligible")["identity"] == "eligible"
    with pytest.raises(ScopeDenied, match="RESERVED_HOLDOUT"):
        gate.check("reserved", "b" * 64, "raw/reserved")


def test_auto_loader_uses_one_active_manifest_and_cannot_fall_back(tmp_path, monkeypatch):
    from edp_lab.ingestion import universe as u

    manifest_sha, approval_sha = _installed(tmp_path)
    # An installed active file without a protected deployment pin must stop.
    with pytest.raises(ScopeDenied, match="ACTIVE_UNIVERSE_DEPLOYMENT_PIN_MISSING"):
        UniverseGate.load(tmp_path)
    monkeypatch.setattr(u, "_protected_active_pin", lambda _: (manifest_sha, approval_sha))
    assert UniverseGate.load(tmp_path).check(
        "eligible", "a" * 64, "raw/eligible")["identity"] == "eligible"
    (tmp_path / ACTIVE_AUTHORITY_PATH).write_text("mutated")
    with pytest.raises(ScopeDenied, match="AUTHORITY_PIN_MISMATCH"):
        UniverseGate.load(tmp_path)


def test_active_manifest_cannot_follow_unpinned_latest(tmp_path):
    manifest_sha, approval_sha = _installed(tmp_path)
    path = tmp_path / ACTIVE_AUTHORITY_PATH
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ScopeDenied, match="AUTHORITY_PIN_MISMATCH"):
        UniverseGate.load_active(tmp_path, manifest_sha256=manifest_sha,
                                 approval_sha256=approval_sha)


def test_active_owner_approval_cannot_be_changed(tmp_path):
    manifest_sha, approval_sha = _installed(tmp_path)
    (tmp_path / "owner-approval.json").write_text('{"status":"APPROVED"}')
    with pytest.raises(ScopeDenied, match="INVALID_OWNER_OR_COHORT_EVIDENCE"):
        UniverseGate.load_active(tmp_path, manifest_sha256=manifest_sha,
                                 approval_sha256=approval_sha)


def test_published_day7_manifest_binds_exact_owner_decision():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    manifest_path = root / ACTIVE_AUTHORITY_PATH
    decision_path = root / "metadata/authorizations/day7_universe_expansion_800_owner_decision.json"
    gate = UniverseGate.load_active(root, manifest_sha256=sha(manifest_path.read_bytes()),
                                    approval_sha256=sha(decision_path.read_bytes()))
    members = gate.document()["members"]
    assert len(members) == 3821
    assert sum(member["holdout"] for member in members) == 41
    assert sum("remote_raw_path" in member for member in members) == 800
    with pytest.raises(ScopeDenied, match="INVALID_OWNER_OR_COHORT_EVIDENCE"):
        UniverseGate.load_active(root, manifest_sha256=sha(manifest_path.read_bytes()),
                                 approval_sha256="0" * 64)


def test_active_universe_rejects_missing_install(tmp_path):
    with pytest.raises(ScopeDenied, match="MISSING_ACTIVE_UNIVERSE"):
        UniverseGate.load_active(tmp_path, manifest_sha256="a" * 64,
                                 approval_sha256="b" * 64)


def _queue():
    return {"raw_mode": "VERIFIED_READ_ONLY", "previous_cohort": "C2000",
            "sources": [{"identity": "fresh", "remote_raw_path": "dbfs:/verified/raw",
                         "raw_handoff_receipt_sha256": "d" * 64}]}


def test_runner_accepts_read_only_queue():
    _validate_raw_mode(_queue(), [{"kind": "cohort_admit"}])


def test_runner_denies_raw_write_even_when_queue_calls_it_recovery():
    with pytest.raises(Denied, match="COHORT_RAW_WRITE_FORBIDDEN"):
        _validate_raw_mode(_queue(), [{"kind": "raw_stage"}])


def test_runner_requires_verified_raw_handoff():
    queue = _queue()
    queue["sources"][0].pop("remote_raw_path")
    with pytest.raises(Denied, match="INCREMENT_RAW_HANDOFF_REQUIRED"):
        _validate_raw_mode(queue, [{"kind": "cohort_admit"}])


def test_invalid_raw_mode_denied():
    queue = _queue()
    queue["raw_mode"] = "WRITE_RAW"
    with pytest.raises(Denied, match="INVALID_RAW_MODE"):
        _validate_raw_mode(queue, [])
