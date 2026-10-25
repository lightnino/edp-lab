"""Regression: SRC canonical physical identity and protected Broker V4 resume."""

from __future__ import annotations

import importlib.util
import inspect
import json
import socket
import sys
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.operating import policy_broker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "owner_recover_day7_broker_v4", ROOT / "scripts/owner_recover_day7_broker_v4.py")
assert SPEC and SPEC.loader
v4 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v4)


class FakeSocket:
    sent: bytes = b""

    def __init__(self, *_args, **_kwargs):
        self.result = {"status": "VERIFIED",
                       "result": {"physical_identity": "SRC000002"}}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def settimeout(self, _timeout):
        return None

    def connect(self, _path):
        return None

    def sendall(self, data):
        self.sent = data
        FakeSocket.sent = data

    def shutdown(self, _direction):
        return None

    def recv(self, _limit):
        return json.dumps(self.result).encode()


def test_broker_accepts_canonical_day7_id_without_dropping_legacy_hash(monkeypatch):
    monkeypatch.setattr(socket, "socket", FakeSocket)
    assert policy_broker.resolve_handoff(
        Path("/private/root-only.sock"), "SRC000002") == {
            "physical_identity": "SRC000002"}
    assert json.loads(FakeSocket.sent)["identity"] == "SRC000002"
    assert policy_broker.resolve_handoff(
        Path("/private/root-only.sock"), "a" * 64)["physical_identity"] == "SRC000002"
    assert json.loads(FakeSocket.sent)["identity"] == "a" * 64


@pytest.mark.parametrize("invalid", [
    "SRC", "SRC00002", "SRC000002/", "../SRC000002", "src000002",
    "SRC000002\n", "a" * 63, "A" * 64, "", None, 123,
])
def test_broker_rejects_invalid_physical_identity_before_socket_use(
        monkeypatch, invalid):
    def prohibited(*_args, **_kwargs):
        pytest.fail("invalid physical identity must not reach Unix socket")
    monkeypatch.setattr(socket, "socket", prohibited)
    with pytest.raises(Denied, match="INVALID_PHYSICAL_IDENTITY"):
        policy_broker.resolve_handoff(Path("/tmp/untrusted.sock"), invalid)


def test_successor_is_pinned_and_excludes_old_deployment_write_paths():
    assert v4.OLD_COMMIT == "6b6e18fb1bb4adc709271ffb3a6af94342287f12"
    assert v4.SP_ID == "78491734320299"
    assert v4.CANARY_RUN_ID == "771002586635696"
    assert v4.ALLOWED_DIFF == {
        v4.BROKER_REL,
        "scripts/owner_recover_day7_broker_v4.py",
        "tests/operating/test_day7_broker_v4.py",
    }
    source = inspect.getsource(v4.execute)
    assert "owner._save_json(RECOVERY_INTENT" in source
    assert source.index("owner._save_json(RECOVERY_INTENT") < source.index(
        "_protected_atomic_replace(new_bytes, BROKER_INSTALLED)")
    assert source.index("_live_u10(u10)") < source.index(
        'owner._mark("broker"')
    assert source.index('owner._mark("broker"') < source.index(
        'owner._mark("deployment"')
    assert "owner.canary(" not in source
    assert "owner.publication(" not in source
    assert "GRANT SELECT" not in source
    assert "service-principal-secrets-proxy" not in source
    assert "jobs submit" not in source


def test_read_only_checks_prohibit_existing_upgrade_marker():
    source = inspect.getsource(v4.check)
    assert "DAY7_V4_RECOVERY_ALREADY_ATTEMPTED" in source
    assert "DAY7_V4_PREVIOUS_JOURNAL_COMMIT_MISMATCH" in source
    assert "DAY7_V4_PROTECTED_BROKER_MODULE_DRIFT" in source
    assert "DAY7_V4_PRIOR_TABLE_GRANT_INTENT_CHANGED" in source
    assert "DAY7_V4_PUBLISHED_RECEIPTS_DRIFT" in source
    assert "broker_health()" in source
    assert "owner_table_read()" in source
    assert 'owner.service("jobs", "get-run", CANARY_RUN_ID)' in source


def test_broker_invalid_health_response_fails_closed(monkeypatch, tmp_path):
    sock = tmp_path / "broker.sock"
    sock.write_bytes(b"untrusted")
    monkeypatch.setattr(v4.owner, "BASE", tmp_path)
    with pytest.raises(RuntimeError, match="DAY7_V4_BROKER_SOCKET_CHANGED"):
        v4.broker_health()


def test_v4_checks_before_any_broker_runtime_write(monkeypatch, tmp_path):
    """Mock exact old receipts and persistent Job; no rerun of old stages."""
    base = tmp_path / "protected"
    (base / "ledger").mkdir(parents=True)
    (base / "receipts").mkdir()
    (base / "runtime/src/edp_lab/operating").mkdir(parents=True)
    original = base / "runtime/src/edp_lab/operating/policy_broker.py"
    original.write_text("old-broker-module")
    reviewed = tmp_path / "reviewed-policy-broker.py"
    reviewed.write_text("new-broker-module")
    marker = base / "ledger/recovery.json"
    backup = base / "ledger/old-broker.py"
    temp = base / "runtime/src/edp_lab/operating/policy_broker.py.new"

    monkeypatch.setattr(v4, "BROKER_INSTALLED", original)
    monkeypatch.setattr(v4, "BROKER_REVIEWED", reviewed)
    monkeypatch.setattr(v4, "RECOVERY_INTENT", marker)
    monkeypatch.setattr(v4, "BROKER_BACKUP", backup)
    monkeypatch.setattr(v4, "BROKER_TEMP", temp)
    monkeypatch.setattr(v4.owner, "BASE", base)
    monkeypatch.setattr(v4.owner, "JOURNAL", base / "ledger/day7-install.json")
    stages = {}
    journal = {"reviewed_commit": v4.OLD_COMMIT, "completed": stages}
    receipts = (
        {"status": "UNIVERSE_PUBLISHED_AND_VERIFIED", "receipt_sha256": "u"},
        {"status": "VERIFIED", "receipt_sha256": "p"},
        {"status": "VERIFIED", "receipt_sha256": "h",
         "physical_identity": "SRC000002", "source_instance_id": "SRC000002",
         "raw_sha256": "1d3656", "raw_bytes": 349417,
         "remote_raw_path": "dbfs:/valid"},
    )
    job = {"job_run_id": v4.CANARY_RUN_ID, "task_run_id": "321",
           "table": v4.owner.CANARY_TABLE, "table_id": "table-id",
           "notebook_sha256": "note", "result": "DAY7_PROTECTED_CANARY_PASS",
           "independent_readback": "OWNER_SQL_EXACT_ONE_ROW"}
    monkeypatch.setattr(v4, "check", lambda _sha: (journal, receipts, job))
    actions = []

    def save(path, obj):
        actions.append("save:" + path.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj))

    monkeypatch.setattr(v4.owner, "_save_json", save)
    monkeypatch.setattr(v4.owner, "file_digest",
                        lambda path: "hash-" + path.name)
    monkeypatch.setattr(v4, "_protected_atomic_replace",
                        lambda blob, target: actions.append("replaced-module"))
    monkeypatch.setattr(v4.owner, "run", lambda *args: actions.append(
        "restart-broker") or "")
    monkeypatch.setattr(v4, "_live_u10",
                        lambda receipt: actions.append("verified-live-u10"))
    monkeypatch.setattr(v4.owner, "_mark", lambda stage, data: actions.append(
        "mark:" + stage))
    monkeypatch.setattr(v4.owner, "_read_json", lambda path: {
        "application_id": "app-uuid"})
    from edp_lab.operating import authority, protected_verifier

    monkeypatch.setattr(protected_verifier, "_sign",
                        lambda receipt, _key, path: path.write_text(json.dumps(
                            receipt)))
    monkeypatch.setattr(authority, "verified_document",
                        lambda _root, path, _trust: json.loads(path.read_text()))

    result = v4.execute("reviewed-new-commit")
    assert result["status"] == "RUNNER_DEPLOYED_AND_VERIFIED"
    assert actions == [
        "save:recovery.json", "replaced-module", "restart-broker",
        "verified-live-u10", "save:day7-install.json", "mark:broker",
        "mark:deployment",
    ]
    assert journal["reviewed_commit"] == "reviewed-new-commit"
    assert not any("jobs submit" in x for x in actions)
