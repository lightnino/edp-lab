"""The Day 7 background actor cannot fall back to user OAuth or RAW writes."""

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.operating.protected_cli import databricks_argv


def test_day7_refuses_interactive_run_as(monkeypatch):
    monkeypatch.setenv("EDP_DAY7_PROTECTED", "1")
    monkeypatch.setenv("EDP_DATABRICKS_RUN_AS_USER", "lightnino")
    monkeypatch.setattr("os.geteuid", lambda: 0)
    with pytest.raises(Denied, match="DAY7_M2M_IDENTITY_REQUIRED"):
        databricks_argv("current-user", "me")


def test_day7_requires_fixed_root_credential_file(monkeypatch):
    monkeypatch.setenv("EDP_DAY7_PROTECTED", "1")
    monkeypatch.delenv("EDP_DATABRICKS_RUN_AS_USER", raising=False)
    monkeypatch.setenv("DATABRICKS_CONFIG_FILE", "/tmp/agent-config")
    monkeypatch.setattr("os.geteuid", lambda: 0)
    with pytest.raises(Denied, match="DAY7_M2M_CREDENTIAL_STORE_REQUIRED"):
        databricks_argv("current-user", "me")
