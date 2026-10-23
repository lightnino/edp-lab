"""N500 review-only preflight against real pinned Universe v1 and C1500 files."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied, canonical
from edp_lab.operating.n500_preflight import prepare_n500_review

ROOT = Path(__file__).resolve().parents[2]


def _proposal():
    universe = json.loads((ROOT / "metadata/source_universes/approved_v1/manifest.json"
                          ).read_bytes())
    old = json.loads((ROOT / "metadata/freezes/C1500_v1/C1500.bindings.json"
                     ).read_bytes())
    excluded = {item["source_identity"] for item in old}
    remaining = [m for m in universe["members"]
                 if m["identity"] not in excluded and not m["holdout"]]
    candidates = [{
        "source_instance_id": f"SRC{910000 + i:06d}",
        "source_identity": m["identity"],
        "raw_sha256": m["raw_sha256"],
        "raw_path": m["raw_path"],
    } for i, m in enumerate(remaining[:2])]
    assert len(candidates) == 2
    return candidates, old, universe


def test_real_c1500_universe_and_two_proposed_candidates():
    candidates, _old, _universe = _proposal()
    result = prepare_n500_review(ROOT, candidates, increment_count=2)
    assert result["schema"] == "EDP_N500_C2000_OWNER_REVIEW_PACKET_V1"
    assert result["status"] == "PROPOSED_NOT_AUTHORIZED"
    assert result["existing_count"] == 1500
    assert result["additional_count"] == 2
    assert result["combined_count"] == 1502
    assert result["authorization"] == "NOT_GRANTED"
    assert not result["databricks_raw_readback_verified"]
    assert not result["raw_bytes_verified"]
    assert "EXTERNAL_SIGNED_WORKFLOW_GRANT" in result["unresolved_next_gates"]
    assert result == prepare_n500_review(ROOT, candidates, increment_count=2)


def test_exact_n500_size_is_required_not_auto_populated():
    candidates, *_ = _proposal()
    with pytest.raises(Denied, match="N500_EXACT_COUNT_REQUIRED"):
        prepare_n500_review(ROOT, candidates)


def test_out_of_universe_rejected():
    candidates, *_ = _proposal()
    bad = deepcopy(candidates)
    bad[0]["source_identity"] = "f" * 64
    with pytest.raises(Denied, match="OUT_OF_UNIVERSE_SOURCE"):
        prepare_n500_review(ROOT, bad, increment_count=2)


def test_holdout_refused_even_if_universe_member():
    candidates, _old, universe = _proposal()
    holdout = next(m for m in universe["members"] if m["holdout"])
    candidates[0].update(source_identity=holdout["identity"],
                         raw_sha256=holdout["raw_sha256"],
                         raw_path=holdout["raw_path"])
    with pytest.raises(Denied, match="PROTECTED_HOLDOUT_SOURCE"):
        prepare_n500_review(ROOT, candidates, increment_count=2)


def test_duplicate_physical_and_registered_id_refused():
    candidates, old, _ = _proposal()
    bad = deepcopy(candidates)
    bad[1]["source_instance_id"] = old[0]["source_instance_id"]
    with pytest.raises(Denied, match="DUPLICATE_REGISTERED_SOURCE_ID"):
        prepare_n500_review(ROOT, bad, increment_count=2)
    bad = deepcopy(candidates)
    bad[1]["source_identity"] = bad[0]["source_identity"]
    bad[1]["raw_sha256"] = bad[0]["raw_sha256"]
    bad[1]["raw_path"] = bad[0]["raw_path"]
    with pytest.raises(Denied, match="DUPLICATE_PHYSICAL_SOURCE"):
        prepare_n500_review(ROOT, bad, increment_count=2)


def test_raw_hash_and_path_changes_rejected():
    candidates, *_ = _proposal()
    bad = deepcopy(candidates)
    bad[0]["raw_sha256"] = "0" * 64
    with pytest.raises(Denied, match="UNIVERSE_RAW_BINDING_MISMATCH"):
        prepare_n500_review(ROOT, bad, increment_count=2)
    bad = deepcopy(candidates)
    bad[0]["raw_path"] = "../path-traversal"
    with pytest.raises(Denied, match="UNIVERSE_RAW_BINDING_MISMATCH"):
        prepare_n500_review(ROOT, bad, increment_count=2)


def test_proposal_packet_bytes_do_not_imply_approval():
    candidates, *_ = _proposal()
    result = prepare_n500_review(ROOT, candidates, increment_count=2)
    assert canonical(result).endswith(b"\n")
    assert result["combined_membership_sha256"] != result["n500_binding_sha256"]
    assert "B1_MODEL_ROUTE_AND_PARSER_RULE_REVIEW" in result["unresolved_next_gates"]
