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
    monkeypatch.setattr(day7, "_source_index", lambda *_: ({"original_sources": []}, "e" * 64))
    with pytest.raises(Denied, match="RAW_HANDOFF_INCOMPLETE"):
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
    monkeypatch.setattr(day7, "_source_index", lambda *_: ({"original_sources": []}, "e" * 64))
    monkeypatch.setattr(day7, "_current_remote_bytes", lambda _: b"changed")
    with pytest.raises(Denied, match="RAW_HANDOFF_INCOMPLETE"):
        day7.attest_handoff(ROOT, tmp_path / "policy", tmp_path / "trust",
                            tmp_path / "key", identity, live_canary=True)


def test_u10_receipt_cannot_change_remote_identity_or_hash(monkeypatch, tmp_path):
    manifest = json.loads((ROOT / "metadata/source_universes/approved/manifest.json").read_bytes())
    member = next(row for row in manifest["members"] if "remote_raw_path" in row)
    trust = tmp_path / "trust"
    receipts = tmp_path / "receipts"
    trust.mkdir()
    receipts.mkdir()
    index_path = tmp_path / "source_evidence_index.json"
    index_path.write_text("{}")
    index_sha = file_digest(index_path)
    path = receipts / f"day7-u10-{member['identity']}.json"
    path.write_bytes(b"signed receipt bytes")
    source = {"raw_handoff_receipt_path": str(path),
              "raw_handoff_receipt_sha256": file_digest(path),
              "remote_raw_path": member["remote_raw_path"]}
    proof = {"schema": "EDP_U10_RAW_HANDOFF_RECEIPT_V1",
             "authority": "protected-verifier-v1", "status": "VERIFIED",
             "readback_mode": "CURRENT_FULL_HASH", "live_readback": True,
             "physical_identity": member["identity"],
             "source_instance_id": member["source_instance_id"],
             "remote_sha256": member["raw_sha256"],
             "remote_bytes": member["raw_bytes"],
             "remote_path": member["remote_raw_path"],
             "manifest_sha256": day7.MANIFEST_SHA,
             "source_evidence_index_sha256": index_sha,
             "historical_independent_readback_sha256": manifest["expansion"][
                 "independent_remote_readback_sha256"],
             "remote_receipt_sha256": member["remote_receipt_sha256"]}
    monkeypatch.setattr(day7, "verified_document", lambda *_: proof)
    assert day7.verify_handoff_receipt(ROOT, trust, member, source, manifest,
                                      index_sha) == file_digest(path)
    proof["remote_sha256"] = "0" * 64
    with pytest.raises(Denied, match="RAW_HANDOFF_EVIDENCE_INVALID"):
        day7.verify_handoff_receipt(ROOT, trust, member, source, manifest, index_sha)
    proof["remote_sha256"] = member["raw_sha256"]
    source["raw_handoff_receipt_sha256"] = "0" * 64
    with pytest.raises(Denied, match="RAW_HANDOFF_RECEIPT_NOT_PINNED"):
        day7.verify_handoff_receipt(ROOT, trust, member, source, manifest, index_sha)


def test_original_locator_index_requires_exact_identity_sha_and_bytes():
    identity = "original-physical-id"
    source = {"physical_identity": identity, "source_instance_id": None,
              "raw_sha256": "a" * 64, "raw_bytes": 42,
              "raw_path": "/original/source.zip"}
    index = {"historical_remote_receipts": [
        {"source_instance_id": identity, "sha256": "a" * 64, "bytes": 41,
         "remote_path": "dbfs:/wrong-bytes"},
        {"source_instance_id": identity, "sha256": "b" * 64, "bytes": 42,
         "remote_path": "dbfs:/wrong-hash"}],
        "known_original_locators": [
            {"physical_identity": identity, "sha256": "a" * 64, "bytes": 42,
             "remote_path": "dbfs:/exact"}],
        "historical_locator_roots": []}
    assert day7._candidate_original_locators(index, source) == [
        ("dbfs:/exact", "PINNED_HISTORICAL_LOCATOR")]


def test_original_u10_verification_uses_pinned_index_and_exact_handoff(tmp_path, monkeypatch):
    manifest = json.loads((ROOT / "metadata/source_universes/approved/manifest.json").read_bytes())
    identity = "original-physical-id"
    index = {"schema": "EDP_DAY7_SOURCE_EVIDENCE_INDEX_V1",
             "status": "PINNED_DISCOVERY_INPUTS_NOT_U10_VERIFIED",
             "original_sources": [{"physical_identity": identity,
                                   "source_instance_id": None, "raw_bytes": 42}]}
    trust = tmp_path / "trust"
    receipts = tmp_path / "receipts"
    trust.mkdir()
    receipts.mkdir()
    index_path = trust.parent / "source_evidence_index.json"
    index_path.write_text(json.dumps(index))
    index_sha = file_digest(index_path)
    receipt = receipts / f"day7-u10-{identity}.json"
    receipt.write_bytes(b"signed")
    source = {"raw_handoff_receipt_path": str(receipt),
              "raw_handoff_receipt_sha256": file_digest(receipt),
              "remote_raw_path": "dbfs:/existing/original.zip"}
    member = {"identity": identity, "raw_sha256": "a" * 64,
              "raw_path": "/original/source.zip", "holdout": False}
    proof = {"schema": "EDP_U10_RAW_HANDOFF_RECEIPT_V1",
             "authority": "protected-verifier-v1", "status": "VERIFIED",
             "readback_mode": "CURRENT_FULL_HASH", "live_readback": True,
             "physical_identity": identity, "source_instance_id": identity,
             "remote_sha256": "a" * 64, "remote_bytes": 42,
             "remote_path": source["remote_raw_path"],
             "manifest_sha256": day7.MANIFEST_SHA,
             "source_evidence_index_sha256": index_sha,
             "evidence_provenance": "PINNED_SOURCE_EVIDENCE_INDEX"}
    monkeypatch.setattr(day7, "verified_document", lambda *_: proof)
    assert day7.verify_handoff_receipt(ROOT, trust, member, source, manifest,
                                       index_sha) == file_digest(receipt)
    proof["remote_bytes"] = 41
    with pytest.raises(Denied, match="RAW_HANDOFF_EVIDENCE_INVALID"):
        day7.verify_handoff_receipt(ROOT, trust, member, source, manifest, index_sha)
