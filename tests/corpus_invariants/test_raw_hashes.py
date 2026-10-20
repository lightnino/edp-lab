"""Read-only local snapshot checks; CI explicitly reports unavailable RAW."""

import json
from pathlib import Path

import pytest

from edp_lab.ingestion.source_identity import verify_source_identity
from edp_lab.profiling.parser_evidence import read_member
from edp_lab.profiling.source_reader import FREEZE, digest, read_registered
from edp_lab.profiling.tools import profile_table

ROOT = Path(__file__).resolve().parents[2]
BINDINGS = json.loads((ROOT / FREEZE).read_bytes())["effective_configuration"]["tables"]


@pytest.mark.parametrize("binding", BINDINGS,
                         ids=lambda b: f"{b['source_instance_id']}/{b['logical_table_name']}")
def test_registered_raw_and_member_hashes_and_read_only_profile(binding):
    path = ROOT / binding["raw_path"]
    if not path.exists():
        pytest.skip(f"Local registered RAW unavailable: {binding['raw_path']}")
    # Hash integrity precedes member access and parsing, including on local runs.
    before = path.read_bytes()
    assert digest(before) == binding["raw_sha256"]
    member = read_member(ROOT, binding)
    assert digest(member) == binding["member_sha256"]
    metadata_paths = [ROOT / FREEZE, *sorted((ROOT / "metadata").rglob("*.csv")),
                      ROOT / "metadata/parser_fidelity_v2_candidate.json",
                      ROOT / "metadata/profiling_conventions_v1.json"]
    evidence = {p: p.read_bytes() for p in metadata_paths}
    table = read_registered(ROOT, binding["source_instance_id"], binding["logical_table_name"],
                            provenance={"test": "read-only regression"})
    assert table.parse_status == "PASS", table.errors
    assert profile_table(table)["parse_status"] == "PASS"
    assert table.null_tokens is None
    assert path.read_bytes() == before
    assert read_member(ROOT, binding) == member
    assert {p: p.read_bytes() for p in metadata_paths} == evidence


def test_local_registry_hash_validation():
    missing = sorted({b["raw_path"] for b in BINDINGS if not (ROOT / b["raw_path"]).exists()})
    if missing:
        pytest.skip(f"Local RAW unavailable: {missing}")
    assert "PASS RAW bytes and archive members: 4 instances" in verify_source_identity(
        ROOT, check_raw=True)
