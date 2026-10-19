"""Frozen §1.4 semantics and conservative parser probe tests (CI-safe)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from edp_lab.profiling import conventions as profile

ROOT = Path(__file__).resolve().parents[2]


def test_gold_v2_profiles_bound_and_versions_frozen() -> None:
    config, bindings = profile.load_conventions(ROOT)
    assert len(bindings) == 13
    assert len(config["profiles"]) == 3
    assert config["profiler_implementation_status"] == "NOT_IMPLEMENTED"
    assert config["duckdb_version"].startswith("1.5.6")
    assert {x["validation_status"] for x in bindings.values()} == {"PROVISIONAL"}


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (
            [],
            {"row_count": 0, "null_count": 0, "non_null_count": 0,
             "distinct_non_null_count": 0, "unique_count": 0,
             "null_pct": None, "distinct_pct": None},
        ),
        (
            [None, None],
            {"row_count": 2, "null_count": 2, "non_null_count": 0,
             "distinct_non_null_count": 0, "unique_count": 0,
             "null_pct": 1.0, "distinct_pct": None},
        ),
        (
            ["", None, "NULL", "001", "001", "1"],
            {"row_count": 6, "null_count": 1, "non_null_count": 5,
             "distinct_non_null_count": 4, "unique_count": 3,
             "null_pct": 1 / 6, "distinct_pct": 4 / 5},
        ),
        (
            ["A", "A", "B", "C"],
            {"row_count": 4, "null_count": 0, "non_null_count": 4,
             "distinct_non_null_count": 3, "unique_count": 2,
             "null_pct": 0.0, "distinct_pct": 3 / 4},
        ),
    ],
)
def test_reference_statistic_semantics(values: list[str | None], expected: dict) -> None:
    assert profile.reference_count_metrics(values) == expected


def test_fingerprint_is_order_sensitive_and_not_semantically_normalized() -> None:
    baseline = profile.schema_fingerprint([("CUSIP", "TEXT"), ("VALUE", "TEXT")])
    assert baseline == profile.schema_fingerprint(
        [("CUSIP", "TEXT"), ("VALUE", "TEXT")]
    )
    assert baseline != profile.schema_fingerprint(
        [("VALUE", "TEXT"), ("CUSIP", "TEXT")]
    )
    assert baseline != profile.schema_fingerprint(
        [("cusip", "TEXT"), ("VALUE", "TEXT")]
    )
    assert baseline != profile.schema_fingerprint(
        [("CUSIP", "INTEGER"), ("VALUE", "TEXT")]
    )


def test_parser_options_cannot_silently_change(tmp_path: Path) -> None:
    (tmp_path / "metadata").mkdir()
    original = json.loads(
        (ROOT / profile.CONVENTIONS).read_text(encoding="utf-8")
    )
    original["profiles"]["NASDAQ_PIPE_V1"]["null_tokens"] = [""]
    (tmp_path / profile.CONVENTIONS).write_text(
        json.dumps(original), encoding="utf-8"
    )
    (tmp_path / profile.LOCK).write_text(
        (ROOT / profile.LOCK).read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / profile.LOGICAL_TABLES).write_text(
        (ROOT / profile.LOGICAL_TABLES).read_text(encoding="utf-8"), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="UNREVIEWED_DECODING_OR_NULL_TOKENS"):
        profile.load_conventions(tmp_path)


def test_read_only_probe_accounts_for_footer_and_rejects_bad_width(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = tmp_path / "data/raw/nasdaqlisted.txt"
    raw.parent.mkdir(parents=True)
    raw.write_text(
        "Symbol|Name\nAAPL|Apple\nFile Creation Time: 202610150303\n",
        encoding="utf-8",
    )
    table_csv = tmp_path / profile.LOGICAL_TABLES
    table_csv.parent.mkdir(parents=True)
    with table_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["source_instance_id", "logical_table_name",
                                 "raw_path", "archive_member"],
        )
        writer.writeheader()
        writer.writerow({
            "source_instance_id": "SRC000002",
            "logical_table_name": "nasdaqlisted.txt",
            "raw_path": "data/raw/nasdaqlisted.txt",
            "archive_member": "",
        })
    base_config, bindings = profile.load_conventions(ROOT)
    selected = bindings[("SRC000002", "nasdaqlisted.txt")]
    monkeypatch.setattr(
        profile, "load_conventions",
        lambda _root: (base_config, {("SRC000002", "nasdaqlisted.txt"): selected}),
    )
    monkeypatch.setattr(profile, "verify_source_identity", lambda *_a, **_kw: [])
    result = profile.probe_raw_parsers(tmp_path)
    assert "1 data rows, 1 accounted metadata rows" in result[0]

    raw.write_text("Symbol|Name\nAAPL|Apple|EXTRA\nFile Creation Time: 123\n")
    with pytest.raises(ValueError, match="ROW_WIDTH_MISMATCH"):
        profile.probe_raw_parsers(tmp_path)
