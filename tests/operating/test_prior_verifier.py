"""A protected prior-cohort receipt requires pinned bytes and live readback."""

import json
import subprocess

import pytest

from edp_lab.operating import prior_verifier as verifier
from edp_lab.operating.authority import Denied, file_digest, verified_document


def setup(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    frozen = root / "metadata/freezes/C1500_v1"
    result = root / "metadata/freezes/O_C1500_M2_v1"
    frozen.mkdir(parents=True)
    result.mkdir(parents=True)
    (frozen / "C1500.bindings.json").write_text(json.dumps([
        {"source_identity": f"id-{n}", "source_instance_id": f"SRC{n:06d}"}
        for n in range(1500)]))
    (result / "databricks_result_freeze_v2.json").write_text('{"status":"FROZEN"}')
    monkeypatch.setattr(verifier, "EXPECTED_ROSTER_SHA",
                        file_digest(frozen / "C1500.bindings.json"))
    monkeypatch.setattr(verifier, "EXPECTED_FREEZE_SHA",
                        file_digest(result / "databricks_result_freeze_v2.json"))
    trust = tmp_path / "trust"
    trust.mkdir()
    key = trust / "verifier.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "Ed25519", "-out", str(key)],
                   check=True)
    subprocess.run(["openssl", "pkey", "-in", str(key), "-pubout", "-out",
                    str(trust / "verifier_ed25519_public.pem")], check=True)
    return root, trust, key


def test_protected_verifier_attests_own_live_readback(tmp_path, monkeypatch):
    root, trust, key = setup(tmp_path, monkeypatch)

    def live(_user, method, *args):
        if method == "get":
            return {"full_name": verifier.VIEW, "table_type": "VIEW",
                    "table_id": verifier.EXPECTED_VIEW_ID,
                    "properties": {"edp.freeze.status": "SOURCE_PRESERVING_VERIFIED",
                                   "edp.freeze.source_roster_sha256": verifier.EXPECTED_ROSTER_SHA,
                                   "edp.freeze.physical_sources": "1500",
                                   "edp.freeze.version": "O_C1500_M2_DATABRICKS_V2"}}
        return {"status": {"state": "SUCCEEDED"}, "statement_id": "live-statement",
                "result": {"data_array": [["OLD_C750_RECORD", "SRC000000"]]}}

    monkeypatch.setattr(verifier, "_databricks", live)
    output = trust / "prior.json"
    result = verifier.attest(root, trust, key, output, "test-user")
    assert result["status"] == "VERIFIED"
    document = verified_document(root, output, trust)
    assert document["cohort"] == "C1500" and len(document["identities"]) == 1500
    assert document["live_statement_id"] == "live-statement"
    with pytest.raises(FileExistsError):
        verifier.attest(root, trust, key, output, "test-user")


def test_protected_verifier_rejects_out_of_roster_sample(tmp_path, monkeypatch):
    root, trust, key = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(verifier, "_databricks", lambda _user, method, *args: (
        {"full_name": verifier.VIEW, "table_type": "VIEW",
         "table_id": verifier.EXPECTED_VIEW_ID,
         "properties": {"edp.freeze.status": "SOURCE_PRESERVING_VERIFIED",
                        "edp.freeze.source_roster_sha256": verifier.EXPECTED_ROSTER_SHA,
                        "edp.freeze.physical_sources": "1500",
                        "edp.freeze.version": "O_C1500_M2_DATABRICKS_V2"}}
        if method == "get" else
        {"status": {"state": "SUCCEEDED"}, "statement_id": "live-statement",
         "result": {"data_array": [["OLD_C750_RECORD", "SRC999999"]]}}))
    with pytest.raises(Denied, match="LIVE_PRIOR_SAMPLE_OUT_OF_ROSTER"):
        verifier.attest(root, trust, key, trust / "prior.json", "test-user")
    assert not (trust / "prior.json").exists()
