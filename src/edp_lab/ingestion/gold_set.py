"""Create and verify a frozen small, source-native RAW corpus baseline.

No semantic mapping, data parsing, API access, or RAW mutation.
Run: uv run python -m edp_lab.ingestion.gold_set init|verify
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

COHORT_ID = "GOLD_V1"
MANIFEST = Path("metadata/corpus_manifest.csv")
ROSTER = Path("metadata/cohorts/GOLD_V1.csv")
REPORT = Path("docs/gold_set_baseline.md")
HEADERS = (
    "source_instance_id",
    "source_family",
    "admitted_at_utc",
    "introduced_cohort",
    "raw_path",
    "raw_sha256",
    "real_or_controlled",
    "variant_type",
    "parent_source_id",
    "ground_truth_available",
    "schema_fingerprint",
    "status",
)


@dataclass(frozen=True)
class RawSource:
    source_instance_id: str
    source_family: str
    raw_path: str
    raw_sha256: str


# The expected hashes are taken from the supplied, manually verified RAW artifacts.
# These IDs refer to source-file instances, NOT enterprise entities/business keys.
GOLD_SOURCES = (
    RawSource(
        "SRC000001", "SEC_13F", "data/raw/sec/2013q2_form13f.zip",
        "569d56e978f7dee3775e544a1e46019389e22adcf482386fcfaba51ceb6c7e84",
    ),
    RawSource(
        "SRC000002", "NASDAQ_DIRECTORY", "data/raw/nasdaq/nasdaqlisted.txt",
        "1d3656d26cfddd35363ce8022d50cbb5342ae2b1cfebee74f3c3b168b0f0f808",
    ),
    RawSource(
        "SRC000003", "NASDAQ_DIRECTORY", "data/raw/nasdaq/otherlisted.txt",
        "7f099cd61db347f2199251dfe45dc132ffc8c75bd68a91471c30e217e4265d3d",
    ),
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_raw_path(root: Path, rel: str) -> Path:
    if Path(rel).is_absolute():
        raise ValueError(f"RAW path must be repository-relative: {rel}")
    base = (root / "data" / "raw").resolve()
    path = (root / rel).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise ValueError(f"RAW path missing or outside data/raw: {rel}")
    return path


def read_manifest(root: Path) -> list[dict[str, str]]:
    file = root / MANIFEST
    if not file.is_file():
        raise ValueError(f"Missing {MANIFEST}")
    with file.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != HEADERS:
            raise ValueError("Manifest header is not the 12-column agreed contract")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("Malformed manifest CSV row")
    return rows


def _contract_blob(root: Path) -> str:
    # Pin the exact reviewed document, not a different uncommitted working copy.
    for argv in (
        ["git", "diff", "--quiet", "--", "docs/evaluation_contract.md"],
        ["git", "diff", "--cached", "--quiet", "--", "docs/evaluation_contract.md"],
    ):
        status = subprocess.run(argv, cwd=root, capture_output=True, check=False)
        if status.returncode != 0:
            raise ValueError("Commit the current evaluation contract before admission")
    result = subprocess.run(
        ["git", "rev-parse", "HEAD:docs/evaluation_contract.md"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            "docs/evaluation_contract.md must be committed in Git before Gold Set admission"
        )
    sha = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40,64}", sha):
        raise ValueError("Could not resolve the committed evaluation contract Git blob")
    return sha


def _write_csv(file: Path, headers: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def init(root: Path, sources: tuple[RawSource, ...] = GOLD_SOURCES) -> None:
    root = root.resolve()
    if read_manifest(root):
        raise ValueError("Manifest already has entries: refusing to overwrite/admit a second time")
    for path in (root / ROSTER, root / REPORT):
        if path.exists():
            raise ValueError(f"Refusing to overwrite existing baseline artifact: {path}")
    for source in sources:
        path = checked_raw_path(root, source.raw_path)
        if file_sha256(path) != source.raw_sha256:
            raise ValueError(f"RAW SHA-256 mismatch; not admitted: {source.raw_path}")
    blob_sha = _contract_blob(root)
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    rows = [
        {
            "source_instance_id": src.source_instance_id,
            "source_family": src.source_family,
            "admitted_at_utc": timestamp,
            "introduced_cohort": COHORT_ID,
            "raw_path": src.raw_path,
            "raw_sha256": src.raw_sha256,
            "real_or_controlled": "REAL",
            "variant_type": "",
            "parent_source_id": "",
            "ground_truth_available": "FALSE",
            "schema_fingerprint": "",
            "status": "ADMITTED",
        }
        for src in sources
    ]
    _write_csv(root / MANIFEST, HEADERS, rows)
    _write_csv(
        root / ROSTER,
        ("source_instance_id",),
        [{"source_instance_id": src.source_instance_id} for src in sources],
    )
    report_lines = [
        "# Gold Set RAW Baseline",
        "",
        "**Cohort:** `GOLD_V1`",
        f"**Admitted at (UTC):** `{timestamp}`",
        f"**Source instances:** `{len(sources)}` immutable physical RAW artifacts",
        "**Inspected logical datasets:** `4` (SEC SUBMISSION, SEC INFOTABLE, and two Nasdaq directories)",
        "**Evaluation contract version:** `V1` (pinned to the committed Git blob below)",
        f"**Evaluation contract Git blob SHA:** `{blob_sha}`",
        "",
        "| Source instance | RAW path | SHA-256 |",
        "|---|---|---|",
        *[
            f"| `{s.source_instance_id}` | `{s.raw_path}` | `{s.raw_sha256}` |"
            for s in sources
        ],
        "",
        "## Scope and evidence",
        "",
        "- Original RAW file bytes were hashed read-only at admission and must remain unchanged.",
        "- Cohort membership is frozen in `metadata/cohorts/GOLD_V1.csv`; existing source IDs are never reassigned.",
        "- The archive is one physical source instance despite containing multiple logical tables.",
        "- `ground_truth_available=FALSE` means there are no independently adjudicated semantic truth labels yet; manual observations are not canonical ground truth.",
        "- Schema fingerprints, business-key decisions, entity equivalence and integrated outputs are not established.",
        "- This baseline proves membership and RAW immutability evidence, NOT the full Lossless 1–6 or Stability A/B/C tests.",
        "- C300 has not been created; no scaled regression comparison exists at this stage.",
        "",
        "## Verification",
        "",
        "Run `uv run python -m edp_lab.ingestion.gold_set verify` from repository root.",
        "Re-running `verify` must return the same PASS results while preserving all RAW bytes.",
        "",
    ]
    (root / REPORT).write_text("\n".join(report_lines), encoding="utf-8")
    print(f"ADMITTED {COHORT_ID}: {len(sources)} original RAW artifacts")
    for s in sources:
        print(f"  {s.source_instance_id} {s.raw_path} sha256={s.raw_sha256}")
    print(f"PINNED CONTRACT V1 Git blob={blob_sha}")


def verify(
    root: Path,
    sources: tuple[RawSource, ...] = GOLD_SOURCES,
    *,
    check_report: bool = True,
) -> list[str]:
    root = root.resolve()
    rows = read_manifest(root)
    ids = [row["source_instance_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate source_instance_id in corpus manifest")
    gold = {row["source_instance_id"]: row for row in rows if row["introduced_cohort"] == COHORT_ID}
    expected_ids = {src.source_instance_id for src in sources}
    if set(gold) != expected_ids:
        raise ValueError(f"Gold Set membership mismatch: {set(gold)} != {expected_ids}")

    roster = root / ROSTER
    with roster.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["source_instance_id"]:
            raise ValueError("Gold Set cohort header invalid")
        roster_ids = [row["source_instance_id"] for row in reader]
    if len(roster_ids) != len(set(roster_ids)) or set(roster_ids) != expected_ids:
        raise ValueError("Gold Set roster does not match frozen manifest IDs")

    outputs = [f"PASS {COHORT_ID}: {len(gold)} unique source instances; roster matches"]
    for src in sources:
        row = gold[src.source_instance_id]
        if any(
            (
                row["source_family"] != src.source_family,
                row["raw_path"] != src.raw_path,
                row["raw_sha256"] != src.raw_sha256,
                row["real_or_controlled"] != "REAL",
                row["variant_type"] != "",
                row["parent_source_id"] != "",
                row["ground_truth_available"] != "FALSE",
                row["schema_fingerprint"] != "",
                row["status"] != "ADMITTED",
            )
        ):
            raise ValueError(f"Frozen metadata mismatch for {src.source_instance_id}")
        stamp = row["admitted_at_utc"]
        if not stamp.endswith("Z"):
            raise ValueError(f"Missing/invalid UTC admission timestamp: {src.source_instance_id}")
        try:
            datetime.fromisoformat(stamp)
        except ValueError as exc:
            raise ValueError(f"Invalid admission timestamp: {src.source_instance_id}") from exc
        raw_path = checked_raw_path(root, src.raw_path)
        digest = file_sha256(raw_path)
        if digest != src.raw_sha256:
            raise ValueError(f"SHA-256 FAIL for {src.source_instance_id}: {digest}")
        outputs.append(f"PASS {src.source_instance_id}: SHA256={digest}")

    if check_report:
        report = (root / REPORT).read_text(encoding="utf-8")
        m = re.search(r"\*\*Evaluation contract Git blob SHA:\*\* `([0-9a-f]{40,64})`", report)
        if not m:
            raise ValueError("Baseline report is missing its pinned evaluation contract Git blob")
        obj = subprocess.run(
            ["git", "cat-file", "-e", f"{m.group(1)}^{{blob}}"],
            cwd=root,
            capture_output=True,
            check=False,
        )
        if obj.returncode != 0:
            raise ValueError("Pinned evaluation contract version is not available in Git")
        for s in sources:
            if s.raw_path not in report or s.raw_sha256 not in report:
                raise ValueError(f"Baseline report missing {s.source_instance_id} evidence")
        outputs.append(f"PASS evaluation contract V1: Git blob {m.group(1)} preserved")
    outputs.append("PASS Gold Set membership and RAW/hash baseline (not full Lossless tests)")
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("init", "verify"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        if args.action == "init":
            init(args.root)
        else:
            print("\n".join(verify(args.root)))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"FAIL {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
