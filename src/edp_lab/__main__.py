"""Small deterministic CLI. No agent/API calls."""

from __future__ import annotations

import argparse
from pathlib import Path

from edp_lab.ingestion.inventory import verify_inventory

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description="EDP Lab Day 1 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-env", help="Print Python and DuckDB versions")
    verify = sub.add_parser("verify-raw", help="Verify original raw SHA-256 files")
    verify.add_argument("--inventory", type=Path, default=Path("metadata/source_inventory.csv"))
    sql = sub.add_parser("sql", help="Execute a committed SQL file in local DuckDB")
    sql.add_argument("filename", type=Path)
    args = parser.parse_args()

    if args.cmd == "check-env":
        import sys

        import duckdb
        print(f"Python {sys.version.split()[0]}; DuckDB {duckdb.__version__}")
        return 0
    if args.cmd == "verify-raw":
        inventory = args.inventory
        if not inventory.is_absolute():
            inventory = PROJECT_ROOT / inventory
        ok, lines = verify_inventory(PROJECT_ROOT, inventory)
        print("\n".join(lines))
        return 0 if ok else 1
    if args.cmd == "sql":
        import duckdb
        file = args.filename
        if not file.is_absolute():
            file = PROJECT_ROOT / file
        if not file.is_relative_to(PROJECT_ROOT):
            parser.error("SQL path must be inside the project")
        query = file.read_text(encoding="utf-8")
        db_path = PROJECT_ROOT / "data/local/edp_lab.duckdb"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(db_path)) as con:
            result = con.execute(query)
            if result.description:
                print(result.fetchall())
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
