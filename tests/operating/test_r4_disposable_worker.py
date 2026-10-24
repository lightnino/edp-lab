"""The reviewed R4 worker can only exercise an isolated noop Queue."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts/r4_disposable_worker.py"
_SPEC = importlib.util.spec_from_file_location("r4_disposable_worker", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
run_fixture = _MODULE.run_fixture


def fixture_root(tmp_path: Path) -> tuple[Path, str, str]:
    for name in ("queue", "ledger", "state"):
        (tmp_path / name).mkdir()
    queue = tmp_path / "queue/no_write_queue.json"
    queue.write_text(json.dumps({
        "schema": "EDP_R4_NO_WRITE_FIXTURE_QUEUE_V1",
        "tasks": [{"id": "fixture-noop", "kind": "noop"}],
        "external_operations": []}))
    ledger = tmp_path / "ledger/operations.json"
    ledger.write_text(json.dumps({"operations": []}))
    return (tmp_path, hashlib.sha256(queue.read_bytes()).hexdigest(),
            hashlib.sha256(ledger.read_bytes()).hexdigest())


@pytest.mark.parametrize(("mode", "code", "status"), [
    ("normal", 0, "COMPLETE"),
    ("blocked", 2, "PAUSED_WITH_DECISION_PACKET"),
    ("unexpected", 2, "PAUSED_WITH_DECISION_PACKET"),
])
def test_no_write_terminal_modes_preserve_ledger(
        tmp_path: Path, monkeypatch, mode, code, status) -> None:
    for name in ("DATABRICKS_CONFIG_FILE", "DATABRICKS_TOKEN",
                 "EDP_POLICY_BROKER_SOCKET", "EDP_OWNER_TRUST_DIR"):
        monkeypatch.delenv(name, raising=False)
    root, queue_sha, ledger_sha = fixture_root(tmp_path)
    ledger = root / "ledger/operations.json"
    before = ledger.read_bytes()
    assert run_fixture(root, queue_sha, ledger_sha, mode) == code
    assert ledger.read_bytes() == before
    observed = json.loads((root / "state/supervisor_status.json").read_text())
    assert observed["status"] == status
    assert observed["replay_authorized"] is False


def test_external_operation_queue_or_credential_env_is_rejected(
        tmp_path: Path, monkeypatch) -> None:
    root, queue_sha, ledger_sha = fixture_root(tmp_path)
    monkeypatch.setenv("DATABRICKS_TOKEN", "fixture-token")
    with pytest.raises(ValueError, match="FIXTURE_CREDENTIAL_ENV_PRESENT"):
        run_fixture(root, queue_sha, ledger_sha, "normal")
    monkeypatch.delenv("DATABRICKS_TOKEN")
    queue = root / "queue/no_write_queue.json"
    bad = json.loads(queue.read_text())
    bad["external_operations"] = ["sql"]
    queue.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="FIXTURE_SCOPE_INVALID"):
        run_fixture(root, hashlib.sha256(queue.read_bytes()).hexdigest(),
                    ledger_sha, "normal")
