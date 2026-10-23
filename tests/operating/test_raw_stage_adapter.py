"""RAW staging is exact, source-preserving and exclusive at the boundary."""

import pytest

from edp_lab.operating.authority import Denied, digest
from edp_lab.operating.boundaries import raw_stage


def test_raw_stage_scope_and_traversal(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    raw = root / "master.idx"
    raw.write_bytes(b"fixed RAW\n")
    source = {"identity": "a" * 64, "path": str(raw), "sha256": digest(raw.read_bytes())}
    remote = ("dbfs:/Volumes/workspace/edp_lab/raw/day5-n500-v1/" +
              source["identity"] + "/master.idx")
    grant = {"cohort": "C2000", "operations": ["raw_stage"],
             "sources": {source["identity"]: source["sha256"]}, "contracts": {},
             "databricks_paths": [remote], "databricks_tables": [],
             "outputs": ["workspace.edp_lab.c2000"], "git_operations": [],
             "protected_branches": ["main"],
             "limits": {"runtime_seconds": 60, "compute_units": 1, "token_count": 1,
                        "retries": 1, "operations": 2}}
    request = {"operation": "raw_stage", "cohort": "C2000",
               "output": "workspace.edp_lab.c2000", "source": source,
               "databricks_path": remote, "operation_id": "stage-raw-1"}
    assert raw_stage(root, grant, request, tmp_path / "ledger") == {
        "status": "AUTHORIZED_DRY_RUN"}
    bad = remote.replace("day5-n500-v1/", "day5-n500-v1/../")
    grant["databricks_paths"].append(bad)
    with pytest.raises(Denied, match="RAW_DESTINATION_OUT_OF_SCOPE"):
        raw_stage(root, grant, dict(request, databricks_path=bad), tmp_path / "ledger")
    raw.write_bytes(b"changed RAW\n")
    with pytest.raises(Denied, match="RAW_HASH_CHANGED"):
        raw_stage(root, grant, request, tmp_path / "ledger")
