"""Day 7 evidence bridge fails closed on absent or changed RAW proof."""

import json
from pathlib import Path

import pytest

from edp_lab.operating import day7_protected as day7
from edp_lab.operating.authority import Denied, file_digest

ROOT = Path(__file__).resolve().parents[2]
READBACK = Path("/Users/lightnino/Projects/edp-lab-incident/docs/incidents/evidence/"
                "800_remote_verification/objects.csv")


def test_active_universe_and_all_800_existing_receipts():
    if not READBACK.is_file():
        pytest.skip("Owner-host historical receipts are unavailable in CI")
    document = day7._active(ROOT, {
        "universe_sha256": day7.MANIFEST_SHA,
        "contracts": {"universe_approval": {"sha256": day7.DECISION_SHA}},
    })
    additions, readback_sha = day7._source_evidence(document)
    assert len(additions) == 800
    assert readback_sha == document["expansion"]["independent_remote_readback_sha256"]
    assert file_digest(ROOT / "metadata/source_universes/approved/manifest.json") == day7.MANIFEST_SHA


def test_unverified_original_has_no_u10_handoff(monkeypatch, tmp_path):
    monkeypatch.setattr(day7, "_policy", lambda *_: {
        "universe_sha256": day7.MANIFEST_SHA,
        "contracts": {"universe_approval": {"sha256": day7.DECISION_SHA}},
    })
    monkeypatch.setattr(day7, "_source_evidence", lambda _: ({}, "f" * 64))
    with pytest.raises(Denied, match="RAW_HANDOFF_REFERENCE_UNAVAILABLE"):
        day7.attest_handoff(ROOT, tmp_path / "policy", tmp_path / "trust",
                            tmp_path / "key", "0" * 64)


def test_live_handoff_refuses_changed_remote_bytes(monkeypatch, tmp_path):
    monkeypatch.setattr(day7, "_policy", lambda *_: {
        "universe_sha256": day7.MANIFEST_SHA,
        "contracts": {"universe_approval": {"sha256": day7.DECISION_SHA}},
    })
    member = next(row for row in json.loads((ROOT / "metadata/source_universes/approved/"
                                             "manifest.json").read_bytes())["members"]
                  if "remote_raw_path" in row)
    identity = member["identity"]
    monkeypatch.setattr(day7, "_source_evidence",
                        lambda _: ({identity: member}, "f" * 64))
    monkeypatch.setattr(day7, "_current_remote_bytes", lambda _: b"changed")
    with pytest.raises(Denied, match="DAY7_RAW_CANARY_HASH_MISMATCH"):
        day7.attest_handoff(ROOT, tmp_path / "policy", tmp_path / "trust",
                            tmp_path / "key", identity, live_canary=True)


def test_u10_receipt_cannot_change_remote_identity_or_hash(monkeypatch, tmp_path):
    manifest = json.loads((ROOT / "metadata/source_universes/approved/manifest.json").read_bytes())
    member = next(row for row in manifest["members"] if "remote_raw_path" in row)
    trust = tmp_path / "trust"
    receipts = tmp_path / "receipts"
    trust.mkdir()
    receipts.mkdir()
    path = receipts / f"day7-u10-{member['identity']}.json"
    path.write_bytes(b"signed receipt bytes")
    source = {"raw_handoff_receipt_path": str(path),
              "raw_handoff_receipt_sha256": file_digest(path),
              "remote_raw_path": member["remote_raw_path"]}
    proof = {"schema": "EDP_U10_RAW_HANDOFF_RECEIPT_V1",
             "authority": "protected-verifier-v1", "status": "VERIFIED",
             "readback_mode": "PINNED_HISTORICAL_FULL_HASH", "live_readback": False,
             "physical_identity": member["identity"],
             "source_instance_id": member["source_instance_id"],
             "remote_sha256": member["raw_sha256"],
             "remote_bytes": member["raw_bytes"],
             "remote_path": member["remote_raw_path"],
             "manifest_sha256": day7.MANIFEST_SHA,
             "historical_independent_readback_sha256": manifest["expansion"][
                 "independent_remote_readback_sha256"],
             "remote_receipt_sha256": member["remote_receipt_sha256"]}
    monkeypatch.setattr(day7, "verified_document", lambda *_: proof)
    assert day7.verify_handoff_receipt(ROOT, trust, member, source, manifest) == file_digest(path)
    proof["remote_sha256"] = "0" * 64
    with pytest.raises(Denied, match="RAW_HANDOFF_EVIDENCE_INVALID"):
        day7.verify_handoff_receipt(ROOT, trust, member, source, manifest)
    proof["remote_sha256"] = member["raw_sha256"]
    source["raw_handoff_receipt_sha256"] = "0" * 64
    with pytest.raises(Denied, match="RAW_HANDOFF_RECEIPT_NOT_PINNED"):
        day7.verify_handoff_receipt(ROOT, trust, member, source, manifest)
