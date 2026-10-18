"""Gold Set V2 registry contract tests; no untracked RAW bytes needed in CI."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "metadata/corpus_manifest.csv"
GOLD_V1 = ROOT / "metadata/cohorts/GOLD_V1.csv"
GOLD_V2 = ROOT / "metadata/cohorts/GOLD_V2.csv"
TABLES_V2 = ROOT / "metadata/gold_set_logical_tables_v2.csv"

OLD_SOURCES = {
    "SRC000001": ("SEC_13F", "GOLD_V1", "569d56e978f7dee3775e544a1e46019389e22adcf482386fcfaba51ceb6c7e84"),
    "SRC000002": ("NASDAQ_DIRECTORY", "GOLD_V1", "1d3656d26cfddd35363ce8022d50cbb5342ae2b1cfebee74f3c3b168b0f0f808"),
    "SRC000003": ("NASDAQ_DIRECTORY", "GOLD_V1", "7f099cd61db347f2199251dfe45dc132ffc8c75bd68a91471c30e217e4265d3d"),
}
NEW_ID = "SRC000004"
NEW_HASH = "25f416b020fd3e62a67dbf8c6522c9f239e716099b61cf5d05a59a91ffdef1f1"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def cohort_ids(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == ["source_instance_id"]
        return [row["source_instance_id"] for row in reader]


def test_gold_v2_is_nested_and_immutable_in_structure() -> None:
    old_ids = cohort_ids(GOLD_V1)
    new_ids = cohort_ids(GOLD_V2)
    assert old_ids == list(OLD_SOURCES)
    assert new_ids == [*old_ids, NEW_ID]
    assert len(new_ids) == len(set(new_ids)) == 4
    rows = read_csv(MANIFEST)
    assert len(rows) == 4
    assert len({row["source_instance_id"] for row in rows}) == 4
    by_id = {row["source_instance_id"]: row for row in rows}
    for source_id, (family, cohort, digest) in OLD_SOURCES.items():
        row = by_id[source_id]
        assert (row["source_family"], row["introduced_cohort"], row["raw_sha256"]) == (
            family, cohort, digest
        )
        assert row["admitted_at_utc"] == "2026-10-18T05:11:35Z"
        assert row["real_or_controlled"] == "REAL"
        assert row["status"] == "ADMITTED"
    new = by_id[NEW_ID]
    assert new["source_family"] == "SEC_FSDS"
    assert new["introduced_cohort"] == "GOLD_V2"
    assert new["raw_path"] == "data/raw/sec/2010q2_fsds.zip"
    assert new["raw_sha256"] == NEW_HASH
    assert new["ground_truth_available"] == "FALSE"
    assert new["status"] == "ADMITTED"


def test_gold_v2_registers_13_real_logical_tables_with_archive_lineage() -> None:
    rows = read_csv(TABLES_V2)
    assert len(rows) == 13
    assert len({(row["source_instance_id"], row["logical_table_name"]) for row in rows}) == 13
    assert Counter(row["source_instance_id"] for row in rows) == {
        "SRC000001": 7, "SRC000002": 1, "SRC000003": 1, "SRC000004": 4
    }
    by_id = {row["source_instance_id"]: row for row in read_csv(MANIFEST)}
    for row in rows:
        parent = by_id[row["source_instance_id"]]
        assert row["raw_path"] == parent["raw_path"]
        assert row["raw_sha256"] == parent["raw_sha256"]
        assert row["source_family"] == parent["source_family"]
        assert row["source_documentation"]
        assert row["profiling_status"] in {
            "PRELIMINARY_PROFILE_EXISTS", "PENDING_DEEP_PROFILE"
        }
        if row["source_file"].endswith(".zip"):
            assert row["archive_member"] == row["logical_table_name"]
        else:
            assert not row["archive_member"]
    assert {row["source_introduced_day"] for row in rows if row["source_instance_id"] == NEW_ID} == {"2"}
    assert sum(row["profiling_status"] == "PRELIMINARY_PROFILE_EXISTS" for row in rows) == 4
