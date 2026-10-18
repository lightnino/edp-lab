"""Read-only source-instance identity and archive-member validation."""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from edp_lab.ingestion.gold_set import HEADERS, checked_raw_path, file_sha256

MANIFEST = Path("metadata/corpus_manifest.csv")
LOGICAL_TABLES = Path("metadata/gold_set_logical_tables_v2.csv")
LOGICAL_FIELDS = (
    "source_instance_id",
    "source_family",
    "source_dataset",
    "source_file",
    "raw_path",
    "raw_sha256",
    "source_documentation",
    "logical_table_name",
    "archive_member",
    "profiling_status",
)
ID_RE = re.compile(r"SRC[0-9]{6}\Z")
SHA_RE = re.compile(r"[a-f0-9]{64}\Z")


def _csv_rows(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"MISSING_REGISTRY {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != fields:
            raise ValueError(f"SCHEMA_MISMATCH {path}")
        records = list(reader)
    if any(None in record or any(value is None for value in record.values())
           for record in records):
        raise ValueError(f"MALFORMED_CSV {path}")
    return records


def _safe_path(value: str, *, archive_member: bool = False) -> bool:
    if not value or "\\" in value or value.startswith("/"):
        return False
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    if archive_member:
        return True
    return parts[:2] == ["data", "raw"] and len(parts) >= 3


def verify_source_identity(root: Path, *, check_raw: bool = False) -> list[str]:
    """Verify registry structure, or structure plus physical RAW bytes when requested.

    This validates source identity and archive lineage, NOT source business semantics.
    Equal SHA-256 values are allowed for independently evidenced deliveries; they
    are never interpreted as proof that source instances are equivalent.
    """
    root = root.resolve()
    rows = _csv_rows(root / MANIFEST, HEADERS)
    if not rows:
        raise ValueError("EMPTY_CORPUS_MANIFEST")

    by_id: dict[str, dict[str, str]] = {}
    by_path: dict[str, str] = {}
    by_hash: dict[str, list[str]] = defaultdict(list)

    for row in rows:
        source_id = row["source_instance_id"]
        if not ID_RE.fullmatch(source_id):
            raise ValueError(f"INVALID_SOURCE_ID {source_id!r}")
        if source_id in by_id:
            raise ValueError(f"DUPLICATE_SOURCE_ID {source_id}")
        if not row["source_family"] or not row["introduced_cohort"]:
            raise ValueError(f"MISSING_IDENTITY_SCOPE {source_id}")
        if row["status"] != "ADMITTED":
            raise ValueError(f"NON_ADMITTED_IN_CORPUS {source_id}: {row['status']}")
        stamp = row["admitted_at_utc"]
        if not stamp.endswith("Z"):
            raise ValueError(f"INVALID_ADMISSION_UTC {source_id}")
        try:
            dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"INVALID_ADMISSION_UTC {source_id}") from exc
        if dt.utcoffset() != timedelta(0):
            raise ValueError(f"INVALID_ADMISSION_UTC {source_id}")

        rel = row["raw_path"]
        if not _safe_path(rel):
            raise ValueError(f"INVALID_RAW_PATH {source_id}: {rel!r}")
        if rel in by_path:
            raise ValueError(f"RAW_PATH_REUSED {by_path[rel]} {source_id}: {rel}")
        sha = row["raw_sha256"]
        if not SHA_RE.fullmatch(sha):
            raise ValueError(f"INVALID_RAW_SHA256 {source_id}")
        kind = row["real_or_controlled"]
        parent = row["parent_source_id"]
        variant = row["variant_type"]
        if kind == "REAL":
            if parent or variant:
                raise ValueError(f"REAL_HAS_CONTROLLED_METADATA {source_id}")
        elif kind == "CONTROLLED":
            if not parent or not variant:
                raise ValueError(f"CONTROLLED_MISSING_PARENT_OR_VARIANT {source_id}")
            if parent == source_id:
                raise ValueError(f"SELF_PARENT {source_id}")
        else:
            raise ValueError(f"INVALID_SOURCE_KIND {source_id}")
        if row["ground_truth_available"] not in {"TRUE", "FALSE"}:
            raise ValueError(f"INVALID_GROUND_TRUTH_FLAG {source_id}")

        by_id[source_id] = row
        by_path[rel] = source_id
        by_hash[sha].append(source_id)

    for source_id, row in by_id.items():
        if row["real_or_controlled"] == "CONTROLLED":
            parent = row["parent_source_id"]
            if parent not in by_id:
                raise ValueError(f"UNKNOWN_CONTROLLED_PARENT {source_id}: {parent}")
            visited = {source_id}
            current = parent
            while by_id[current]["real_or_controlled"] == "CONTROLLED":
                if current in visited:
                    raise ValueError(f"CONTROLLED_PARENT_CYCLE {source_id}")
                visited.add(current)
                current = by_id[current]["parent_source_id"]
                if current not in by_id:
                    raise ValueError(f"UNKNOWN_CONTROLLED_PARENT {source_id}: {current}")
            if current in visited:
                raise ValueError(f"CONTROLLED_PARENT_CYCLE {source_id}")

    logical = _csv_rows(root / LOGICAL_TABLES, LOGICAL_FIELDS)
    observed: set[tuple[str, str]] = set()
    members_by_id: dict[str, set[str]] = defaultdict(set)
    for item in logical:
        source_id = item["source_instance_id"]
        if source_id not in by_id:
            raise ValueError(f"UNKNOWN_LOGICAL_PARENT {source_id}")
        parent = by_id[source_id]
        for field in ("source_family", "raw_path", "raw_sha256"):
            if item[field] != parent[field]:
                raise ValueError(f"LOGICAL_PARENT_MISMATCH {source_id}: {field}")
        if item["source_file"] != Path(parent["raw_path"]).name:
            raise ValueError(f"LOGICAL_SOURCE_FILE_MISMATCH {source_id}")
        if not item["source_documentation"] or not item["source_dataset"]:
            raise ValueError(f"MISSING_LOGICAL_PROVENANCE {source_id}")
        if not item["profiling_status"]:
            raise ValueError(f"MISSING_PROFILING_STATUS {source_id}")
        name = item["logical_table_name"]
        if not name:
            raise ValueError(f"EMPTY_LOGICAL_TABLE_NAME {source_id}")
        key = (source_id, name)
        if key in observed:
            raise ValueError(f"DUPLICATE_LOGICAL_TABLE {source_id}: {name}")
        observed.add(key)
        member = item["archive_member"]
        if parent["raw_path"].lower().endswith(".zip"):
            if not _safe_path(member, archive_member=True) or name != member:
                raise ValueError(f"INVALID_ARCHIVE_MEMBER {source_id}: {member!r}")
            members_by_id[source_id].add(member)
        elif member or name != Path(parent["raw_path"]).name:
            raise ValueError(f"INVALID_STANDALONE_LOGICAL_TABLE {source_id}: {name}")

    outputs = [
        f"PASS source identity structure: {len(rows)} distinct instances; "
        f"{len(logical)} registered logical tables",
    ]
    for sha, ids in by_hash.items():
        if len(ids) > 1:
            outputs.append(
                "REVIEW_REQUIRED identical RAW SHA-256 across distinct instances "
                + ",".join(ids) + f" ({sha}); verify independent delivery evidence"
            )

    if check_raw:
        for source_id, row in by_id.items():
            rel = row["raw_path"]
            try:
                path = checked_raw_path(root, rel)
            except ValueError as exc:
                raise ValueError(f"RAW_UNAVAILABLE {source_id}: {rel}") from exc
            actual = file_sha256(path)
            if actual != row["raw_sha256"]:
                raise ValueError(f"RAW_SHA256_MISMATCH {source_id}: {rel}")
            if source_id in members_by_id:
                try:
                    with ZipFile(path) as archive:
                        archive_names = {
                            info.filename for info in archive.infolist() if not info.is_dir()
                        }
                except (BadZipFile, OSError) as exc:
                    raise ValueError(f"INVALID_SOURCE_ARCHIVE {source_id}") from exc
                missing = members_by_id[source_id] - archive_names
                if missing:
                    raise ValueError(
                        f"MISSING_ARCHIVE_MEMBER {source_id}: {sorted(missing)}"
                    )
        outputs.append(f"PASS RAW bytes and archive members: {len(rows)} instances")
    else:
        outputs.append("NOT_CHECKED RAW bytes (metadata-only validation)")

    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check-raw", action="store_true")
    args = parser.parse_args()
    try:
        print("\n".join(verify_source_identity(args.root, check_raw=args.check_raw)))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"FAIL {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
