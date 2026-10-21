"""Explicit synthetic host authority for legacy in-memory profiling tests only."""

import json
from pathlib import Path

import pytest

from edp_lab.ingestion.universe import UniverseGate, sha
from edp_lab.tool_adapters import ProfilingAdapters


def authorized_host(sources, grants):
    members = []
    for table in sources.values():
        table.source["raw_path"] = table.source.get("raw_path") or "TEST_ONLY/in_memory"
        members.append(
            {
                "identity": table.source["source_instance_id"],
                "raw_sha256": table.source["raw_sha256"],
                "raw_path": table.source["raw_path"],
                "holdout": False,
            }
        )
    doc = {
        "schema": "SOURCE_UNIVERSE_AUTHORITY_V1",
        "universe_version": "TEST_ONLY",
        "approval_reference": "TEST_ONLY",
        "inventory_reference": "TEST_ONLY",
        "inventory_sha256": "0" * 64,
        "member_count": len(members),
        "members": members,
        "cohorts": {"GOLD_V2": {"identities": [m["identity"] for m in members]}},
    }
    raw = json.dumps(doc).encode()
    return ProfilingAdapters(sources, grants, universe_gate=UniverseGate(raw, sha(raw)))


# Production-evidence tests have explicit external prerequisites. Missing evidence
# blocks production execution; skipping these offline checks never grants scope.


@pytest.fixture
def owner_evidence():
    root = Path(__file__).resolve().parents[1]
    doc = json.loads((root/'metadata/source_universes/approved_v1/manifest.json').read_bytes())
    side = json.loads((root/'metadata/source_universes/historical_cohort_bindings_v1.json').read_bytes())
    paths = [doc['inventory_reference'], *side['evidence']]
    absent = [path for path in paths if not (root/path).is_file()]
    if absent:
        pytest.skip('ENVIRONMENT: pinned external owner evidence unavailable: ' + ', '.join(absent))
