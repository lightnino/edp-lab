"""Fixed V3 schema and insert-only SQL boundary."""

import json
from pathlib import Path

import pytest

from edp_lab.vault.v3_ddl import create_sql, insert_only_sql, plan


def test_rendered_ddl_matches_allowlist_and_never_updates():
    root = Path(__file__).resolve().parents[2]
    request = json.loads((root / "metadata/operating/day6_c2000_vault_v3_bounded_request_v1.json").read_bytes())
    expected = json.loads((root / "metadata/operating/day6_c2000_vault_v3_ddl_v1.json").read_bytes())
    assert plan(request["new_v3_table_allowlist"]) == expected
    assert len(expected["tables"]) == 23
    assert all("WHEN NOT MATCHED THEN INSERT" in item["insert_only_sql"]
               and "WHEN MATCHED" not in item["insert_only_sql"]
               for item in expected["tables"])
    with pytest.raises(ValueError):
        create_sql("other_schema.table")
    with pytest.raises(ValueError):
        insert_only_sql("v3_h_filing", "untrusted_view")
