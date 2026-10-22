"""Synthetic checks for reusable additive cohort publication (no RAW/network writes)."""
import json

import pytest

from edp_lab.ingestion import cohort_publication as c
from edp_lab.ingestion.gold_set import HEADERS
from edp_lab.ingestion.c300_admission import csv_bytes, encoded
from edp_lab.ingestion.universe import ScopeDenied, sha


class FakeGate:
    @classmethod
    def load(cls, root):
        return cls()

    def verify_inventory(self, root):
        return None

    def check(self, identity, digest, path):
        if path != "/approved/" + identity or digest not in {"c" * 64, "d" * 64}:
            raise ScopeDenied("IDENTITY_EVIDENCE_MISMATCH")
        return {"physical_identity": identity}

    def scope_reference(self):
        return {"universe_version": "1", "universe_id": "TEST"}


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "UniverseGate", FakeGate)
    baseline = [
        dict(zip(HEADERS, (f"SRC{i:06d}", "TEST", "2026-10-21T00:00:00Z", "C2",
                           f"data/raw/old{i}", "a" * 64 if i == 1 else "b" * 64,
                           "REAL", "", "", "FALSE", "", "ADMITTED"), strict=True))
        for i in (1, 2)
    ]
    old_bindings = [
        {"source_identity": f"old{i}", "source_instance_id": f"SRC{i:06d}",
         "raw_path": f"data/raw/old{i}", "raw_sha256": baseline[i - 1]["raw_sha256"]}
        for i in (1, 2)
    ]
    filenames = {
        "baseline_roster": "metadata/freezes/C2_v1/C2.csv",
        "baseline_bindings": "metadata/freezes/C2_v1/C2.bindings.json",
        "baseline_manifest": "metadata/freezes/C2_v1/corpus_manifest_v4.csv",
        "baseline_freeze": "metadata/freezes/C2_v1/freeze.json",
    }
    values = {
        "baseline_roster": csv_bytes(("source_instance_id",), [
            {"source_instance_id": f"SRC{i:06d}"} for i in (1, 2)]),
        "baseline_bindings": encoded(old_bindings),
        "baseline_manifest": csv_bytes(HEADERS, baseline),
        "baseline_freeze": encoded({"status": "FROZEN"}),
    }
    for key, value in values.items():
        dest = tmp_path / filenames[key]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(value)
    base = {
        "version": "COHORT_ADDITIVE_V1", "baseline": "C2",
        "increment": "N1", "combined": "C3",
        "baseline_roster": filenames["baseline_roster"],
        "baseline_bindings": filenames["baseline_bindings"],
        "baseline_manifest": filenames["baseline_manifest"],
        "baseline_freeze": filenames["baseline_freeze"],
        "baseline_sha256": {k: sha(v) for k, v in values.items()},
        "baseline_count": 2, "increment_count": 1, "combined_count": 3,
        "manifest_version": 4, "admission_path": "metadata/admissions/N1_v1",
        "freeze_path": "metadata/freezes/C3_v1",
        "admitted_at_utc": "2026-10-22T10:00:00Z",
        "selected": [{
            "source_identity": "phy1", "source_instance_id": "SRC000003",
            "physical_raw_path": "/approved/phy1", "raw_path": "data/raw/new1",
            "raw_sha256": "c" * 64, "family": "TEST",
        }],
    }
    return tmp_path, base, filenames


def approval(root, plan):
    plan_raw = encoded(plan)
    bundles = c.prepare(root, plan)
    grant = {
        "status": "OWNER_APPROVED", "plan_sha256": sha(plan_raw),
        "scopes": {
            a: {"cohort": plan["increment" if a == "admission" else "combined"],
                "destination": plan["admission_path" if a == "admission" else "freeze_path"],
                "files_sha256": {k: sha(v) for k, v in bundles[a].items()}}
            for a in ("admission", "freeze")
        },
    }
    grant_raw = encoded(grant)
    return plan_raw, grant_raw, sha(grant_raw)


def test_publication_readback_and_no_overwrite(world):
    root, plan, paths = world
    before = {k: (root / p).read_bytes() for k, p in paths.items()}
    plan_raw, grant_raw, trusted = approval(root, plan)
    assert c.publish(root, plan_raw, grant_raw, trusted, "admission")["status"] == "PUBLISHED"
    result = c.publish(root, plan_raw, grant_raw, trusted, "freeze")
    assert result["cohort"] == "C3"
    assert len(c.read_csv((root / plan["freeze_path"] / "C3.csv").read_bytes())) == 3
    assert len(c.read_csv((root / plan["admission_path"] /
                           "corpus_manifest_v5.csv").read_bytes())) == 3
    assert all((root / p).read_bytes() == before[k] for k, p in paths.items())
    with pytest.raises(ScopeDenied, match="PUBLICATION_ALREADY_EXISTS"):
        c.publish(root, plan_raw, grant_raw, trusted, "admission")


def test_uninstalled_or_changed_owner_grant_denied(world):
    root, plan, _ = world
    p, g, trusted = approval(root, plan)
    with pytest.raises(ScopeDenied, match="TRUSTED_GRANT_NOT_INSTALLED"):
        c.publish(root, p, g, "", "admission")
    with pytest.raises(ScopeDenied, match="OWNER_GRANT_PIN_MISMATCH"):
        c.publish(root, p, g, "0" * 64, "admission")
    altered = json.loads(g)
    altered["scopes"]["admission"]["destination"] = "metadata/admissions/attacker"
    with pytest.raises(ScopeDenied, match="OWNER_GRANT_PIN_MISMATCH"):
        c.publish(root, p, encoded(altered), trusted, "admission")
    with pytest.raises(ScopeDenied, match="ACTION_NOT_AUTHORIZED"):
        c.publish(root, p, encoded(altered), sha(encoded(altered)), "admission")


def test_membership_and_hash_changes_denied(world):
    root, plan, _ = world
    p, g, trusted = approval(root, plan)
    altered = json.loads(p)
    altered["selected"][0]["raw_sha256"] = "d" * 64
    with pytest.raises(ScopeDenied, match="OWNER_SCOPE_MISMATCH"):
        c.publish(root, encoded(altered), g, trusted, "admission")
    with pytest.raises(ScopeDenied, match="INVALID_COHORT_ACTION"):
        c.publish(root, p, g, trusted, "unapproved")


def test_freeze_requires_exact_actual_admission(world):
    root, plan, _ = world
    p, g, trusted = approval(root, plan)
    with pytest.raises(ScopeDenied, match="ADMISSION_NOT_PUBLISHED"):
        c.publish(root, p, g, trusted, "freeze")
    c.publish(root, p, g, trusted, "admission")
    (root / plan["admission_path"] / "bindings.json").write_text("[]")
    with pytest.raises(ScopeDenied, match="ADMISSION_BYTES_CHANGED"):
        c.publish(root, p, g, trusted, "freeze")


def test_different_cohort_size_same_code(world):
    root, plan, _ = world
    plan["increment"] = "N2"
    plan["combined"] = "C4"
    plan["increment_count"] = 2
    plan["combined_count"] = 4
    plan["admission_path"] = "metadata/admissions/N2_v1"
    plan["freeze_path"] = "metadata/freezes/C4_v1"
    plan["selected"].append({
        "source_identity": "phy2", "source_instance_id": "SRC000004",
        "physical_raw_path": "/approved/phy2", "raw_path": "data/raw/new2",
        "raw_sha256": "d" * 64, "family": "TEST",
    })
    p, g, trusted = approval(root, plan)
    c.publish(root, p, g, trusted, "admission")
    c.publish(root, p, g, trusted, "freeze")
    assert len(c.read_csv((root / plan["freeze_path"] / "C4.csv").read_bytes())) == 4


def test_destination_escape_denied(world):
    root, plan, _ = world
    plan["admission_path"] = "metadata/admissions/../../unsafe"
    with pytest.raises(ScopeDenied, match="COHORT_DESTINATION_MISMATCH"):
        c.prepare(root, plan)
