import json
import os
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.operating.checkpoint_supervisor import _persist_supervisor_state


def test_denial_is_durable_and_sanitized(tmp_path: Path):
    state = _persist_supervisor_state(tmp_path, "SQL_STATEMENT_ID_MISSING", blocked=True)
    on_disk = json.loads((tmp_path / "supervisor_status.json").read_text())
    assert state == on_disk
    assert state["status"] == "PAUSED_WITH_DECISION_PACKET"
    assert state["replay_authorized"] is False
    assert state["reason_code"] == "SQL_STATEMENT_ID_MISSING"
    assert not (tmp_path / "checkpoint.json").exists()
    assert not list(tmp_path.glob("*.tmp"))
    assert os.stat(tmp_path / "supervisor_status.json").st_mode & 0o777 == 0o600


def test_denial_text_does_not_leak_credentials(tmp_path: Path):
    state = _persist_supervisor_state(tmp_path, "Bearer SECRET VALUE", blocked=True)
    assert state["reason_code"] == "UNCLASSIFIED_DENIAL"
    assert "SECRET" not in (tmp_path / "supervisor_status.json").read_text()


def test_status_symlink_does_not_follow(tmp_path: Path):
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.write_text("do not overwrite")
    (tmp_path / "supervisor_status.json").symlink_to(outside)
    with pytest.raises(Denied, match="SUPERVISOR_STATUS_SYMLINK"):
        _persist_supervisor_state(tmp_path, "SQL_STATEMENT_ID_MISSING", blocked=True)
    assert outside.read_text() == "do not overwrite"
