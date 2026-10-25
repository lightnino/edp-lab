"""Installer canary checkpoints make restart idempotent."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/owner_install_day7.py"
SPEC = importlib.util.spec_from_file_location("owner_install_day7", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def test_canary_submit_restart_reuses_checkpoint(tmp_path, monkeypatch):
    base = tmp_path / "protected"
    (base / "ledger").mkdir(parents=True)
    monkeypatch.setattr(installer, "BASE", base)
    calls = []

    def service(*args):
        calls.append(args)
        return {"run_id": 123456789}

    monkeypatch.setattr(installer, "service", service)
    payload = {"idempotency_token": "stable-day7-canary"}
    assert installer.submit_canary_once(payload, "a" * 64) == "123456789"
    assert installer.submit_canary_once(payload, "a" * 64) == "123456789"
    assert len(calls) == 1
    with pytest.raises(RuntimeError, match="DAY7_CANARY_RESTART_INTENT_CHANGED"):
        installer.submit_canary_once(payload, "b" * 64)
    intent = json.loads((base / "ledger/canary-submit-intent.json").read_text())
    assert intent == {"payload": payload, "source_sha256": "a" * 64}


def test_canary_uncertain_submit_retry_uses_same_idempotency_token(tmp_path, monkeypatch):
    base = tmp_path / "protected"
    (base / "ledger").mkdir(parents=True)
    monkeypatch.setattr(installer, "BASE", base)
    tokens = []

    def service(*args):
        payload = json.loads(args[3])
        tokens.append(payload["idempotency_token"])
        if len(tokens) == 1:
            raise TimeoutError("response lost after remote submit")
        return {"run_id": 7654321}

    monkeypatch.setattr(installer, "service", service)
    payload = {"idempotency_token": "stable-day7-canary"}
    with pytest.raises(TimeoutError):
        installer.submit_canary_once(payload, "c" * 64)
    assert installer.submit_canary_once(payload, "c" * 64) == "7654321"
    assert tokens == ["stable-day7-canary", "stable-day7-canary"]
