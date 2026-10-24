"""Static navigation and canonical ownership safeguards; no external services."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = (
    "AGENTS.md",
    "docs/README.md",
    "docs/workflows/README.md",
    "docs/workflows/agent_operating_contract_v1.md",
    "docs/operating/agent_operating_guide_v1.md",
    "docs/operating/standing_policy_v1.md",
    "docs/contracts/README.md",
    "docs/contracts/tools/profiling_tool_contract_v1.md",
    "docs/vault_load_contract_v1.md",
    "docs/incidents/README.md",
    "docs/incidents/2026-10-21-source-universe/incident.md",
    "docs/incidents/2026-10-21-source-universe/evidence_index.md",
    "docs/incidents/2026-10-21-source-universe/retained_raw_references.md",
    "docs/incidents/2026-10-23-standing-authorization/finding.md",
    "docs/incidents/2026-10-23-c2000-p11-sql/incident.md",
    "docs/incidents/2026-10-23-c2000-p11-sql/recovery_packet.md",
    "reports/day5/c2000_live_closeout_20261024.md",
)

OLD_PATHS = (
    "docs/incidents/2026-10-21_source_universe_scope_control.md",
    "docs/incidents/2026-10-21_evidence_index.md",
    "docs/incidents/2026-10-21_retained_raw_references.md",
    "docs/incidents/2026-10-23_repeated_grant_installation_autonomy_gap.md",
    "reports/day5_c2000_runtime_recovery_incident_2026-10-23.md",
    "docs/operating/day5_c2000_live_closeout_20261024.md",
    "docs/operating/day5_c2000_sql_recovery_packet_20261024.md",
    "docs/agent_tool_contract.md",
)


def test_one_canonical_home_per_record() -> None:
    assert all((ROOT / p).is_file() for p in CANONICAL)
    assert all(not (ROOT / p).exists() for p in OLD_PATHS)


def test_operating_has_no_day_specific_execution_log() -> None:
    docs = [p.name for p in (ROOT / "docs/operating").glob("*.md")]
    assert not [n for n in docs if re.search(r"day[0-9]|c[0-9]{3,}", n.lower())]


def test_navigation_local_links_resolve() -> None:
    files = [
        "AGENTS.md", "README.md", "docs/README.md", "docs/workflows/README.md",
        "docs/contracts/README.md", "docs/incidents/README.md",
        "docs/experiments/README.md", "docs/operating/README.md",
        "docs/workflows/universe_lifecycle_v1.md",
        "docs/incidents/2026-10-21-source-universe/incident.md",
        "docs/incidents/2026-10-23-standing-authorization/finding.md",
        "docs/incidents/2026-10-23-c2000-p11-sql/incident.md",
    ]
    for item in files:
        path = ROOT / item
        for dest in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if dest.startswith(("http:", "https:", "#", "mailto:")):
                continue
            bare = dest.split("#", 1)[0]
            if bare:
                assert (path.parent / bare).exists(), (item, dest)


def test_r7_not_reported_as_currently_open() -> None:
    packet = (ROOT / "docs/incidents/2026-10-23-c2000-p11-sql/incident.md").read_text()
    header = packet.split("## 1.", 1)[0]
    assert "R7 CLOSED" in header
    assert "R4 OPEN" in header and "R8 OPEN" in header
    assert "Recovery Decision Matrix" in (
        ROOT / "docs/workflows/agent_operating_contract_v1.md"
    ).read_text()
