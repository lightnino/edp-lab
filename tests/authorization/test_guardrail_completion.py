"""Offline real-entrypoint checks. No RAW parsing, network, or processing jobs."""

import csv
import hashlib
import io
import json
from pathlib import Path

import pytest

from edp_lab.agents.c300_shallow_v0 import inspect
from edp_lab.ingestion import universe as u
from edp_lab.ingestion.c300_admission import freeze, prepare, verify_registry

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.usefixtures("owner_evidence")
def test_exact_owner_authority_and_frozen_compatibility():
    gate = u.UniverseGate.load(ROOT)
    gate.verify_inventory(ROOT)
    doc = gate.document()
    assert len(doc["members"]) == 3021
    assert sum(m["holdout"] for m in doc["members"]) == 41
    bulk = [m for m in doc["members"] if "qualification" in m]
    assert len(bulk) == 2
    assert all(
        m["qualification"]["disposition"] == "QUALIFIED — OWNER_ATTESTED_PROVENANCE" for m in bulk
    )
    approval = json.loads((ROOT / doc["approval_reference"]).read_bytes())
    assert approval["manifest_sha256"] == gate.fingerprint
    assert len(verify_registry(ROOT, ROOT / "metadata/corpus_manifest_v3.csv")) == 304
    assert gate.feasibility(300, "C300") == 300
    with pytest.raises(u.ScopeDenied, match="INSUFFICIENT_AUTHORIZED_SOURCES") as exc:
        gate.feasibility(301, "C300")
    assert exc.value.outcome["route"] == "Human Review"


def registry_with_extra(tmp_path, family):
    text = (ROOT / "metadata/corpus_manifest.csv").read_text()
    rows = list(csv.DictReader(io.StringIO(text)))
    extra = dict(
        rows[0],
        source_instance_id="SRC999999",
        source_family=family,
        raw_path=f"data/raw/{family}/retained.csv",
        raw_sha256="a" * 64,
        introduced_cohort="C300",
    )
    path = tmp_path / "registry.csv"
    with path.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows([*rows, extra])
    return path


@pytest.mark.parametrize("family", ["NOAA", "WDI", "TREASURY_NEW"])
@pytest.mark.usefixtures("owner_evidence")
def test_actual_registry_rejects_retained_outside_universe(tmp_path, family):
    with pytest.raises(u.ScopeDenied, match="NOT_IN_APPROVED_UNIVERSE"):
        verify_registry(ROOT, registry_with_extra(tmp_path, family))


@pytest.mark.usefixtures("owner_evidence")
def test_actual_inspection_rejects_enlarged_physical_input_before_parser(monkeypatch):
    rows = list(csv.DictReader((ROOT / "metadata/corpus_manifest_v3.csv").open()))
    allowed = rows[4]
    unexpected = dict(allowed, source_instance_id="SRC999999")

    def forbidden(*args):
        pytest.fail("parser/RAW access reached before complete input authorization")

    monkeypatch.setattr("edp_lab.agents.c300_shallow_v0.require_activation", forbidden)
    with pytest.raises(u.ScopeDenied, match="NOT_IN_APPROVED_UNIVERSE"):
        inspect(ROOT, {"bindings": [allowed, unexpected]}, None)
    # An original approved GOLD source is still outside the selected C300 run.
    with pytest.raises(u.ScopeDenied, match="NOT_IN_PINNED_COHORT"):
        inspect(ROOT, {"bindings": [rows[0]]}, None)
    holdout = next(m for m in u.UniverseGate.load(ROOT).document()["members"] if m["holdout"])
    with pytest.raises(u.ScopeDenied, match="RESERVED_HOLDOUT"):
        inspect(
            ROOT,
            {
                "bindings": [
                    {
                        "source_instance_id": holdout["identity"],
                        "raw_path": holdout["raw_path"],
                        "raw_sha256": holdout["raw_sha256"],
                    }
                ]
            },
            None,
        )


def test_missing_cohort_blocks_actual_preparation_without_acquisition(tmp_path, monkeypatch):
    doc = {
        "schema": "SOURCE_UNIVERSE_AUTHORITY_V1",
        "universe_version": "TEST_ONLY",
        "approval_reference": "TEST_ONLY",
        "inventory_reference": "inventory",
        "inventory_sha256": u.sha(b"inventory"),
        "members": [],
        "member_count": 0,
    }
    path = tmp_path / u.AUTHORITY_PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(doc))
    (tmp_path / "inventory").write_bytes(b"inventory")
    monkeypatch.setattr(u, "APPROVED_AUTHORITY_SHA256", u.sha(path.read_bytes()))
    with pytest.raises(u.ScopeDenied, match="INSUFFICIENT_AUTHORIZED_SOURCES"):
        prepare(tmp_path, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.usefixtures("owner_evidence")
def test_agent_cannot_inject_freeze_approval(tmp_path):
    packet = tmp_path / "packet.json"
    packet.write_text("{}")
    authority = tmp_path / "self_approved.json"
    authority.write_text(
        json.dumps(
            {
                "packet_sha256": hashlib.sha256(packet.read_bytes()).hexdigest(),
                "admit_and_freeze": True,
                "approved_by": "Agent",
                "authorization_text": "approve",
                "authorized_at_utc": "2026-10-21T00:00:00Z",
            }
        )
    )
    with pytest.raises(ValueError, match="UNTRUSTED_FREEZE_AUTHORIZATION"):
        freeze(ROOT, packet, authority, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.usefixtures("owner_evidence")
def test_c300_inspection_scope_accepts_original_binding_before_parser_approval():
    rows = list(csv.DictReader((ROOT / "metadata/corpus_manifest_v3.csv").open()))
    # This reaches the independent parser approval boundary, without processing RAW.
    with pytest.raises(PermissionError, match="SCOPED_HUMAN_APPROVAL"):
        inspect(ROOT, {"bindings": [rows[4]]}, None)


@pytest.mark.usefixtures("owner_evidence")
def test_future_host_approved_version_can_use_retained_raw_at_actual_entrypoint(
    tmp_path, monkeypatch
):
    # Test-only deployment pin; this cannot approve real Universe v2.
    candidate = tmp_path / "data/raw/retained.csv"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"x\n1\n")
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    original = (ROOT / u.AUTHORITY_PATH).read_bytes()
    doc = {
        "schema": "SOURCE_UNIVERSE_AUTHORITY_V1",
        "universe_id": "TEST_ONLY",
        "universe_version": "future-test",
        "approval_reference": "TEST_ONLY_OWNER",
        "inventory_reference": "inventory",
        "inventory_sha256": u.sha(b"inventory"),
        "members": [
            {
                "identity": "SRC999999",
                "raw_sha256": digest,
                "raw_path": "data/raw/retained.csv",
                "holdout": False,
            }
        ],
        "member_count": 1,
        "cohorts": {"future-test": {"identities": ["SRC999999"]}},
    }
    location = tmp_path / u.AUTHORITY_PATH
    location.parent.mkdir(parents=True)
    location.write_text(json.dumps(doc))
    (tmp_path / "inventory").write_bytes(b"inventory")
    binding = {
        "source_instance_id": "SRC999999",
        "raw_sha256": digest,
        "raw_path": "data/raw/retained.csv",
    }
    with pytest.raises(u.ScopeDenied):
        u.processing(ROOT, binding, "C300")
    monkeypatch.setattr(u, "APPROVED_AUTHORITY_SHA256", u.sha(location.read_bytes()))
    assert u.processing(tmp_path, binding, "future-test")["universe_version"] == "future-test"
    with pytest.raises(u.ScopeDenied, match="NOT_IN_PINNED_COHORT"):
        u.processing(tmp_path, binding, "C300")
    assert candidate.read_bytes() == b"x\n1\n"
    assert (ROOT / u.AUTHORITY_PATH).read_bytes() == original


def test_actual_load_rejects_agent_manifest_or_approval_replacement(tmp_path):
    location = tmp_path / u.AUTHORITY_PATH
    location.parent.mkdir(parents=True)
    location.write_bytes((ROOT / u.AUTHORITY_PATH).read_bytes() + b" ")
    with pytest.raises(u.ScopeDenied, match="AUTHORITY_PIN_MISMATCH"):
        u.UniverseGate.load(tmp_path)
    location.write_bytes((ROOT / u.AUTHORITY_PATH).read_bytes())
    (location.parent / "owner_authorization.json").write_text('{"approved_by":"Agent"}')
    with pytest.raises(u.ScopeDenied, match="INVALID_OWNER_OR_COHORT_EVIDENCE"):
        u.UniverseGate.load(tmp_path)
