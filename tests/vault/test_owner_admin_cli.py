"""CLI response contracts for Owner-only installation commands."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import owner_setup_day6_vault_0a as setup


@pytest.mark.parametrize("stdout", ["", " \n"])
def test_explicit_empty_response_is_accepted(monkeypatch, stdout):
    monkeypatch.setattr(setup, "run", lambda *_args, **_kwargs:
                        subprocess.CompletedProcess([], 0, stdout, ""))
    assert setup.admin_cli("workspace", "mkdirs", "/x", allow_empty=True) is None


@pytest.mark.parametrize("allow_empty", [False, True])
def test_structured_response_is_strict_json(monkeypatch, allow_empty):
    monkeypatch.setattr(setup, "run", lambda *_args, **_kwargs:
                        subprocess.CompletedProcess([], 0, "not json", ""))
    with pytest.raises(ValueError):
        setup.admin_cli("workspace", "get-status", "/x", allow_empty=allow_empty)


def test_required_json_rejects_empty_response(monkeypatch):
    monkeypatch.setattr(setup, "run", lambda *_args, **_kwargs:
                        subprocess.CompletedProcess([], 0, "", ""))
    with pytest.raises(ValueError):
        setup.admin_cli("jobs", "create")


def test_optional_empty_still_parses_json(monkeypatch):
    monkeypatch.setattr(setup, "run", lambda *_args, **_kwargs:
                        subprocess.CompletedProcess([], 0, '{"ok": true}', ""))
    assert setup.admin_cli("grants", "update", allow_empty=True) == {"ok": True}


def test_cli_error_reports_status_and_sanitized_stderr_without_argv(monkeypatch):
    def failed(*_args, **_kwargs):
        raise subprocess.CalledProcessError(
            1, ["databricks", "jobs", "create", "--json", "private-body"],
            stderr="Error: INVALID_PARAMETER_VALUE; Bearer eyJsecret "
                   "client_secret=hidden-value\n")

    monkeypatch.setattr(setup, "run", failed)
    with pytest.raises(RuntimeError, match="DATABRICKS_CLI_EXIT_1") as exc:
        setup.admin_cli("jobs", "create", "--json", "private-body")
    message = str(exc.value)
    assert "INVALID_PARAMETER_VALUE" in message
    assert "private-body" not in message
    assert "eyJsecret" not in message
    assert "hidden-value" not in message


def test_protected_service_uses_m2m_profile_without_sudo(monkeypatch):
    calls = []
    monkeypatch.setenv("EDP_DAY6_V3_SERVICE_CONTEXT", "1")
    monkeypatch.setattr(setup.os, "geteuid", lambda: 0)
    monkeypatch.setattr("edp_lab.vault.protected_sql.protected_environment",
                        lambda *_args: {"DATABRICKS_CONFIG_FILE": "/protected/config"})

    def invoke(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, '{"id":"72304318628585"}', "")

    monkeypatch.setattr(setup.subprocess, "run", invoke)
    assert setup.admin_cli("current-user", "me") == {"id": "72304318628585"}
    argv, kwargs = calls[0]
    assert argv[-5:] == ["current-user", "me", "-p", "vault-dev", "-o", "json"][-5:]
    assert argv[:3] == ["/opt/homebrew/bin/databricks", "current-user", "me"]
    assert kwargs["env"]["DATABRICKS_CONFIG_FILE"] == "/protected/config"
