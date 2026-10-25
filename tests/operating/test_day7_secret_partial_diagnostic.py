"""No external writes or OAuth secret values during partial Day 7 diagnosis."""

from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/diagnose_day7_secret.py"
SPEC = importlib.util.spec_from_file_location("day7_secret_diagnose", SCRIPT)
assert SPEC and SPEC.loader
diag = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diag)


def test_secret_diagnostic_only_uses_read_only_cli(monkeypatch):
    actions = []

    def run(argv, **kwargs):
        actions.append(argv)
        assert kwargs["check"] is False
        assert "create" not in argv and "delete" not in argv
        if argv[1:3] == ["service-principals", "get"]:
            result = {"id": diag.SP_ID, "active": True,
                      "displayName": "edp-lab-day7-c3000-cohort"}
        elif argv[1:3] == ["api", "get"]:
            result = {"principal_id": int(diag.SP_ID),
                      "principal_type": "SERVICE_PRINCIPAL",
                      "effective_entitlements": ["WORKSPACE_ACCESS"]}
        else:
            result = {"secrets": [{"id": "secret-id", "status": "ACTIVE",
                                   "secret": "SHOULD_NEVER_PRINT"}]}
        return SimpleNamespace(returncode=0, stdout=json.dumps(result), stderr="")

    monkeypatch.setattr(diag.subprocess, "run", run)
    output = json.dumps(diag.diagnose())
    assert "SHOULD_NEVER_PRINT" not in output
    assert "secret-id" not in output
    assert '"returned_secret_metadata_count": 1' in output
    assert len(actions) == 3


def test_read_only_diagnostic_redacts_bearer(monkeypatch):
    monkeypatch.setattr(diag.subprocess, "run", lambda *_args, **_kwargs:
                        SimpleNamespace(
                            returncode=1,
                            stderr="Error: bearer secret-token client_secret=abc123",
                            stdout=""))
    response = diag.read_only("service-principal-secrets-proxy", "list", diag.SP_ID)
    assert "secret-token" not in response["message"]
    assert "abc123" not in response["message"]
    assert response["status"] == "ERROR"


def test_installer_has_actual_newlines_in_protected_files():
    script = (Path(__file__).resolve().parents[2]
              / "scripts/owner_install_day7.py").read_text()
    assert r'revoked.write_text("[]\n")' in script
    assert r'stream.write("[edp-lab]\n"' in script
    assert r'client_id = {app_id}\nclient_secret = {secret}\n' in script
    assert r'revoked.write_text("[]\\n")' not in script
    assert r'stream.write("[edp-lab]\\n"' not in script


def test_installer_fails_closed_on_uncertain_secret_effects():
    script = (Path(__file__).resolve().parents[2]
              / "scripts/owner_install_day7.py").read_text()
    assert "DAY7_SECRET_UNCERTAIN_MANUAL_RECONCILIATION" in script
    assert inspect.isfunction(diag.diagnose)
    assert "list" in inspect.getsource(diag.diagnose)
