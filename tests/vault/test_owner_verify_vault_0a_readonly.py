"""The acceptance probe must not invoke Executor if its lock is unsafe."""
from __future__ import annotations

import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_verify_vault_0a_readonly as verify


@pytest.mark.parametrize("case", ["absent", "directory", "symlink", "wrong_owner"])
def test_invalid_namespace_lock_never_contacts_executor(tmp_path, monkeypatch, case):
    ledger = tmp_path / "ledger"
    ledger.mkdir()
    lock = ledger / "namespace.lock"
    if case == "directory":
        lock.mkdir()
    elif case == "symlink":
        target = tmp_path / "target"
        target.touch()
        lock.symlink_to(target)
    elif case == "wrong_owner":
        lock.touch()
        monkeypatch.setattr(verify.Path, "lstat", lambda self: SimpleNamespace(
            st_mode=stat.S_IFREG | 0o600, st_uid=12345))

    def unexpected_rpc(*_args):
        pytest.fail("Executor must not be contacted")

    monkeypatch.setattr(verify, "_rpc", unexpected_rpc)
    with pytest.raises(RuntimeError, match="NAMESPACE_LOCK_MISSING_OR_INVALID"):
        verify.executor_negative_probe(tmp_path, tmp_path / "forged.json")
    if case == "absent":
        assert not lock.exists()
