"""Scope-limited regression guards for Phase 2 historical-doc migration."""
import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAY3 = ROOT / "docs/history/day3-c750/n450_step3_runtime_readiness.md"
DAY4 = ROOT / "docs/history/day4-c1500/n750_c1500_execution_evidence.md"
VAULT = ROOT / "docs/vault_load_contract_v1.md"


def _git(*args: str, content: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, input=content, text=True,
        capture_output=True, check=False,
    )


def test_archived_paths_and_original_blob_identity() -> None:
    assert DAY3.is_file() and DAY4.is_file()
    assert not (ROOT / "docs/n450_step3_runtime_readiness.md").exists()
    assert not (ROOT / "docs/n750_c1500_execution_evidence.md").exists()

    kept = _git("hash-object", str(DAY4))
    assert kept.returncode == 0
    assert kept.stdout.strip() == "88f52f1c060ae514dff8b63e6e45c09e7ede339f"

    # Only the relative link to the still path-pinned execution evidence changed.
    restored = DAY3.read_text().replace(
        "(../../n450_c750_execution_evidence.md)",
        "(n450_c750_execution_evidence.md)",
    )
    original = _git("hash-object", "--stdin", content=restored)
    assert original.returncode == 0
    assert original.stdout.strip() == "84f088f3460640e1243518d56d722b384ca45d14"


def test_approved_vault_contract_bytes_unchanged() -> None:
    assert hashlib.sha256(VAULT.read_bytes()).hexdigest() == (
        "681c3f6a9a4446b5357c3ab6c6534e6fd5b8cf944f967ea9ab27dcc2c8b5aabe"
    )


def test_no_stale_legacy_path_references() -> None:
    # Split the strings so this regression test is not itself a false positive.
    old_paths = [
        "docs/n450_step3_" + "runtime_readiness.md",
        "docs/n750_c1500_" + "execution_evidence.md",
    ]
    args = ["grep", "-n", "-F"]
    for old in old_paths:
        args.extend(["-e", old])
    found = _git(*args, "--", ".")
    assert found.returncode == 1, found.stdout[:1600] + found.stderr[:1000]


def test_moved_file_links_resolve_across_markdown() -> None:
    basenames = {
        "n450_step3_runtime_readiness.md",
        "n750_c1500_execution_evidence.md",
    }
    for path in [ROOT / "README.md", ROOT / "AGENTS.md", *ROOT.rglob("docs/**/*.md")]:
        content = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", content):
            if target.startswith(("http:", "https:", "#", "mailto:")):
                continue
            target_path = target.split("#", 1)[0]
            if Path(target_path).name in basenames:
                assert (path.parent / target_path).is_file(), (str(path), target)
