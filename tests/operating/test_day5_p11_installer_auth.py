"""The owner installer must test CLI authentication, not an arbitrary API path."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "scripts/owner_install_day5_p11_sql_recovery.sh"


def auth_snippet():
    script = INSTALLER.read_text()
    return script.split("import hashlib, json, os, subprocess\n", 1)[1].split(
        "history_path =", 1)[0]


def test_owner_installer_auth_uses_current_user_for_both_profiles(tmp_path, monkeypatch):
    monkeypatch.setenv("EDP_P11_CAPTURE", str(tmp_path))
    commands = []

    def run(command, *, capture_output):
        assert capture_output is True
        commands.append(command)
        if len(commands) == 1:
            return SimpleNamespace(returncode=1, stdout=b"",
                                   stderr=b"Error: error getting token: no cached credentials")
        return SimpleNamespace(returncode=0,
                               stdout=b'{"userName":"chengzhu13@gmail.com"}', stderr=b"")

    monkeypatch.setattr(subprocess, "run", run)
    exec("import hashlib, json, os, subprocess\n" + auth_snippet(), {})  # noqa: S102
    assert commands == [
        ["/opt/homebrew/bin/databricks", "current-user", "me"],
        ["/opt/homebrew/bin/databricks", "current-user", "me", "-p", "edp-lab", "-o", "json"],
    ]
    assert (tmp_path / "default_auth.stderr").read_bytes().startswith(b"Error: error getting token")


def test_owner_installer_rejects_non_authentication_default_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("EDP_P11_CAPTURE", str(tmp_path))

    def run(command, *, capture_output):
        return SimpleNamespace(returncode=1, stdout=b"", stderr=b"Error: 404 Not Found")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(SystemExit, match="Default profile did not fail authentication"):
        exec("import hashlib, json, os, subprocess\n" + auth_snippet(), {})  # noqa: S102


@pytest.mark.parametrize("stderr,stdout,code,accepted", [
    (b"Error: Table 'workspace.edp_lab.n500_input_roster_day5_v1' does not exist.\n",
     b"", 1, True),
    ((b'{"error_code":"TABLE_DOES_NOT_EXIST","message":"Table '
      b"'workspace.edp_lab.n500_input_roster_day5_v1' does not exist.\"}"), b"", 1, True),
    (b"Error: PERMISSION_DENIED", b"", 1, False),
    (b"Error: connection refused", b"", 1, False),
    (b"Error: Table 'workspace.edp_lab.other' does not exist.\n", b"", 1, False),
    (b"Error: TABLE_DOES_NOT_EXIST", b"", 1, False),
    (b"Error: Table 'workspace.edp_lab.n500_input_roster_day5_v1' does not exist.\n",
     b"", 0, False),
])
def test_uc_absence_requires_exact_authenticated_target_response(
        stderr, stdout, code, accepted):
    script = INSTALLER.read_text()
    function = script.split("def uc_absence(result, table):\n", 1)[1].split(
        "\nif not uc_absence(uc, target):", 1)[0]
    scope = {"json": json}
    exec("def uc_absence(result, table):\n" + function, scope)  # noqa: S102
    response = SimpleNamespace(returncode=code, stderr=stderr, stdout=stdout)
    assert scope["uc_absence"](
        response, "workspace.edp_lab.n500_input_roster_day5_v1") is accepted
