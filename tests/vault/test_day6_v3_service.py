"""The protected V3 service never advances past an unresolved submission."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from edp_lab.vault import v3_service
from edp_lab.vault.v3_spark_runtime import v0a_smoke


def test_attempt_checkpoint_requires_signed_no_effect(tmp_path, monkeypatch):
    base = tmp_path / "protected"
    (base / "ledger").mkdir(parents=True)
    (base / "receipts").mkdir()
    successor = SimpleNamespace()

    def configure(number):
        successor.SUBMISSION = base / f"ledger/attempt-{number}-submission.json"
        successor.RESERVATION = base / f"ledger/attempt-{number}-reservation.json"
        successor.SUCCESSOR_INSTALL = base / f"receipts/attempt-{number}-install.json"
        successor.SUCCESSOR_GRANT = base / f"receipts/attempt-{number}-grant.json"

    successor.configure_attempt = configure
    configure(1)
    successor.RESERVATION.write_text("reserved")
    monkeypatch.setattr(v3_service, "_imports", lambda: (successor,))
    assert v3_service._next_attempt(tmp_path, base) == (1, "RECONCILIATION_REQUIRED")
    successor.SUBMISSION.write_text("submitted")
    no_effect = base / "receipts/day6-v3-attempt-1-no-effect.signed.json"
    no_effect.write_text("signed")
    monkeypatch.setattr(v3_service, "verified_document", lambda *_args: {
        "status": "TERMINAL_NO_REMOTE_EFFECT", "attempt_number": 1,
        "submission_sha256": "digest"})
    monkeypatch.setattr(v3_service, "file_digest", lambda _path: "digest")
    assert v3_service._next_attempt(tmp_path, base) == (2, "READY_FOR_DISTINCT_ATTEMPT")


def test_smoke_uses_fixed_isolated_delta_table():
    calls = []
    table = "workspace.edp_lab_day6_vault_proto.v0a_day6_e2e_20261025"

    class Result:
        def __init__(self, kind):
            self.kind = kind

        def first(self):
            return SimpleNamespace(asDict=lambda recursive: {"format": "delta", "id": "id"})

        def collect(self):
            return [{"probe_id": "day6-v0a", "probe_value": "ready"}]

    class Spark:
        def sql(self, statement):
            calls.append(statement)
            return Result(statement)

    request = {"target_namespace": "workspace.edp_lab_day6_vault_proto"}
    result = v0a_smoke(Spark(), request)
    assert result == {"status": "V0A_SMOKE_PERSISTED_REQUIRES_INDEPENDENT_READBACK",
                      "table": table, "delta_id": "id", "row_count": 1}
    assert calls == [f"CREATE TABLE {table} (probe_id STRING, probe_value STRING) USING DELTA",
                     f"INSERT INTO {table} VALUES ('day6-v0a', 'ready')",
                     "DESCRIBE DETAIL " + table,
                     "SELECT probe_id, probe_value FROM " + table]


def test_installed_request_still_bounds_ten_million_attempts():
    root = Path(__file__).resolve().parents[2]
    request = json.loads((root / "metadata/operating/day6_c2000_vault_v3_bounded_request.json")
                         .read_bytes())
    assert request["execution"]["job_submissions_max"] == 10000000
