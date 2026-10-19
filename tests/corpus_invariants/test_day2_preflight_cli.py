"""Day 2 Preflight: canonical CLI routing and decision-log schema."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from edp_lab import __main__ as cli


def test_verify_raw_cli_uses_canonical_manifest_validator(monkeypatch, capsys) -> None:
    calls: list[tuple[Path, bool]] = []

    def fake_verify(root: Path, *, check_raw: bool = False) -> list[str]:
        calls.append((root, check_raw))
        return [
            "PASS source identity structure: 4 distinct instances; 13 registered logical tables",
            "PASS RAW bytes and archive members: 4 instances",
        ]

    monkeypatch.setattr(cli, "verify_source_identity", fake_verify)
    monkeypatch.setattr(sys, "argv", ["edp-lab", "verify-raw"])
    assert cli.main() == 0
    assert calls == [(cli.PROJECT_ROOT, True)]
    output = capsys.readouterr().out
    assert "PASS RAW bytes and archive members: 4 instances" in output


def test_verify_raw_cli_fails_closed_when_validation_fails(monkeypatch, capsys) -> None:
    def fake_verify(_root: Path, *, check_raw: bool = False) -> list[str]:
        assert check_raw
        raise ValueError("RAW_SHA256_MISMATCH SRC000004")

    monkeypatch.setattr(cli, "verify_source_identity", fake_verify)
    monkeypatch.setattr(sys, "argv", ["edp-lab", "verify-raw"])
    assert cli.main() == 1
    assert "FAIL RAW_SHA256_MISMATCH SRC000004" in capsys.readouterr().out


def test_decision_log_starts_empty_with_stable_schema() -> None:
    repo = Path(__file__).resolve().parents[2]
    path = repo / "metadata/decision_log.csv"
    assert path.is_file()
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    assert rows == [
        [
            "decision_id",
            "recorded_at_utc",
            "decision_scope",
            "decision_type",
            "status",
            "question",
            "decision",
            "rationale",
            "evidence_refs",
            "source_instance_ids",
            "model_version",
            "approved_by",
        ]
    ]
