"""Tests for exact-once Day 7 OAuth Duration recovery contract."""

from __future__ import annotations

import ast
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/owner_recover_day7_secret_v2.py"


def _source() -> str:
    return SCRIPT.read_text()


def test_successor_is_syntactically_valid() -> None:
    ast.parse(_source())


def test_duration_uses_documented_json_format() -> None:
    source = _source()
    assert "{'lifetime': '7776000s'}" in source
    assert "'--json', request" in source
    assert "'--lifetime'" not in source


def test_previous_failed_intent_is_not_deleted_or_replayed() -> None:
    source = _source()
    assert "EDP_DAY7_SECRET_RECOVERY_ATTEMPT_V1" in source
    assert "'repair_commit': PRIOR_REPAIR_COMMIT" in source
    assert "DAY7_SECOND_ATTEMPT_ALREADY_RECORDED_NEVER_RETRY" in source
    assert "install._save_json(SUCCESSOR_ATTEMPT" in source
    assert source.index("install._save_json(SUCCESSOR_ATTEMPT") < source.index(
        "result = subprocess.run(command")


def test_no_print_of_oauth_secret_or_automatic_recreate() -> None:
    source = _source()
    assert "previous._store_oauth_profile(identity, reply)" in source
    assert "capture_output=True" in source
    assert "NO_AUTOMATIC_RETRY" in source
    assert "DAY7_SECRET_EXISTS_STOP_NO_CREATE" in source
    assert "DAY7_M2M_AUTH_NOT_VERIFIED_NO_SECRET_RETRY" in source
    assert "print(result.stdout)" not in source
    assert "print(reply)" not in source


def test_signed_historical_protections_and_journal_are_preserved() -> None:
    source = _source()
    assert "verified_document(" in source
    assert "DAY7_PINNED_INPUT_CHANGED" in source
    assert "DAY7_SIGNED_POLICY_OR_INDEX_CHANGED" in source
    assert "DAY7_OLD_JOURNAL_COMMIT_OR_POLICY_CHANGED" in source
    assert "install._save_json(install.JOURNAL, journal)" in source
    assert "install.main()" in source
