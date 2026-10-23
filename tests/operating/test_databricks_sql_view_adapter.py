"""Historic Day 4 CREATE VIEW and Day 2/3 CREATE TABLE guarded SQL validation."""

import json

import pytest

from edp_lab.operating.authority import Denied, digest
from edp_lab.operating.boundaries import databricks_write


@pytest.mark.parametrize("statement,allowed", [
    ("CREATE VIEW workspace.edp_lab.frozen_v2 AS SELECT 1", True),
    ("-- fixed historical source\nCREATE VIEW workspace.edp_lab.frozen_v2 AS\nWITH x AS (SELECT 1 AS v) SELECT v FROM x", True),
    ("CREATE TABLE workspace.edp_lab.frozen_v2 USING DELTA AS SELECT 1", True),
    ("CREATE VIEW workspace.edp_lab.frozen_v2 AS DELETE FROM x", False),
    ("CREATE OR REPLACE VIEW workspace.edp_lab.frozen_v2 AS SELECT 1", False),
    ("CREATE TABLE IF NOT EXISTS workspace.edp_lab.frozen_v2 AS SELECT 1", False),
    ("CREATE VIEW workspace.edp_lab.not_allowed AS SELECT 'workspace.edp_lab.frozen_v2'", False),
    ("CREATE VIEW workspace.edp_lab.frozen_v2 AS SELECT 1; DROP TABLE x", False),
])
def test_reviewed_sql_ddl_not_generic_proxy(tmp_path, statement, allowed):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "model").write_bytes(b"pinned")
    path = root / "statement.json"
    path.write_text(json.dumps({"warehouse_id": "approved-warehouse",
                                "statement": statement}))
    grant = {"cohort": "C2000", "operations": ["databricks_write"],
             "sources": {}, "contracts": {
                 **{k: {"version": "V1", "sha256": digest(b"pinned")}
                    for k in ("parser", "model", "rule")},
                 "statement": {"version": "S1", "sha256": digest(path.read_bytes())}},
             "databricks_paths": [], "databricks_tables": ["workspace.edp_lab.frozen_v2"],
             "outputs": ["o.c2000"], "git_operations": [], "protected_branches": ["main"],
             "limits": {"runtime_seconds": 120, "operations": 1,
                        "compute_units": 1, "token_count": 1, "retries": 0}}
    request = {"operation": "databricks_write", "cohort": "C2000",
               "output": "o.c2000", "databricks_table": "workspace.edp_lab.frozen_v2",
               "statement_path": "statement.json", "operation_id": "frozen-view-once",
               "contracts": {
                   **{k: {"version": "V1", "path": "model"}
                      for k in ("parser", "model", "rule")},
                   "statement": {"version": "S1", "path": "statement.json"}}}
    if allowed:
        assert databricks_write(root, grant, request, tmp_path / "ledger") == {
            "status": "AUTHORIZED_DRY_RUN"}
    else:
        with pytest.raises(Denied, match="NON_EXCLUSIVE_WRITE|TABLE_NOT_IN_STATEMENT"):
            databricks_write(root, grant, request, tmp_path / "ledger")
