from pathlib import Path

import duckdb


def test_committed_sql_healthcheck() -> None:
    project = Path(__file__).resolve().parents[2]
    query = (project / "sql/raw/00_healthcheck.sql").read_text(encoding="utf-8")
    with duckdb.connect(":memory:") as con:
        assert con.execute(query).fetchone() == (42, "duckdb-ok")
