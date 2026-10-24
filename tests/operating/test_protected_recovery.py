"""The stopped RAW task is recoverable only before reservation and remote write."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from edp_lab.operating.authority import Denied, canonical, file_digest
from edp_lab.operating.protected_recovery import recover_pre_submission_raw


def setup(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    protected = tmp_path / "protected"
    trust = protected / "trust"
    trust.mkdir(parents=True)
    (protected / "ledger").mkdir()
    (protected / "receipts").mkdir()
    key = protected / "verifier.pem"
    key.write_text("test-only key placeholder")
    raw = root / "master.idx"
    raw.write_bytes(b"RAW")
    queue = root / "queue.json"
    queue.write_bytes(canonical({"cohort": "C2000", "tasks": [
        {"id": "P5"}, {"id": "raw-001", "operation_id": "first-raw",
                      "databricks_path": "dbfs:/Volumes/workspace/edp_lab/raw/day5/identity/master.idx",
                      "source": {"path": str(raw)}}]}))
    state_dir = protected / "state"
    state_dir.mkdir()
    checkpoint = state_dir / "checkpoint.json"
    checkpoint.write_bytes(canonical({"queue_sha256": file_digest(queue),
                                      "grant_id": "broker-test",
                                      "tasks": {"P5": {"status": "COMPLETE"},
                                                "raw-001": {"status": "FAILED_INTEGRITY",
                                                            "reason": "RAW_PARENT_CREATION_UNCERTAIN"}}}))
    monkeypatch.setattr("edp_lab.operating.protected_recovery.load_grant",
                        lambda *_args: {"authority": "policy-broker-v1",
                                        "grant_id": "broker-test",
                                        "contracts": {"queue": {"sha256": file_digest(queue)}}})
    monkeypatch.setattr("edp_lab.operating.protected_recovery._sign",
                        lambda document, _key, output: output.write_bytes(canonical(document)))
    return root, queue, protected, trust, key, checkpoint


def test_no_ledger_no_remote_object_allows_exact_reset(tmp_path, monkeypatch):
    root, queue, protected, trust, key, checkpoint = setup(tmp_path, monkeypatch)
    monkeypatch.setattr("edp_lab.operating.protected_recovery.databricks_argv",
                        lambda *args: list(args))
    monkeypatch.setattr("edp_lab.operating.protected_recovery.subprocess.run",
                        lambda *_args, **_kwargs: SimpleNamespace(
                            returncode=1, stderr="Error: no such directory", stdout=""))
    result = recover_pre_submission_raw(root, queue, protected / "grant.json",
                                        checkpoint, trust, key)
    assert result["status"] == "VERIFIED_PRE_SUBMISSION_RECOVERY"
    assert json.loads(checkpoint.read_bytes())["tasks"]["raw-001"]["status"] == "PLANNED"
    assert (protected / "receipts/recovery-raw-001.json").exists()


def test_existing_ledger_reservation_blocks_reset(tmp_path, monkeypatch):
    root, queue, protected, trust, key, checkpoint = setup(tmp_path, monkeypatch)
    (protected / "ledger/first-raw.json").write_text("reserved")
    with pytest.raises(Denied, match="RECOVERY_LEDGER_RESERVATION_EXISTS"):
        recover_pre_submission_raw(root, queue, protected / "grant.json",
                                   checkpoint, trust, key)
    assert json.loads(checkpoint.read_bytes())["tasks"]["raw-001"][
        "status"] == "FAILED_INTEGRITY"
