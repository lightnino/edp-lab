"""One-pass protected RAW/member and selected byte-locator verification."""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_selected(raw_root: Path, rows: list[dict]) -> dict:
    """Verify the three ZIPs, members, and all selected line/byte intervals."""
    if len(rows) != 127:
        raise ValueError("PINNED_SAMPLE_SIZE_CHANGED")
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["source_instance_id"], []).append(row)
    if set(groups) != {"SRC000005", "SRC000054", "SRC000064"}:
        raise ValueError("SOURCE_SCOPE_CHANGED")
    result = {}
    for sid, selected in groups.items():
        first = selected[0]
        if any(any(row[name] != first[name] for name in
                   ("raw_path", "raw_sha256", "archive_member", "member_sha256"))
               for row in selected):
            raise ValueError("INCONSISTENT_SOURCE_LINEAGE")
        relative = Path(first["raw_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("RAW_PATH_OUT_OF_SCOPE")
        path = (raw_root / relative).resolve(strict=True)
        if not path.is_relative_to(raw_root.resolve()):
            raise ValueError("RAW_PATH_OUT_OF_SCOPE")
        if sha_file(path) != first["raw_sha256"]:
            raise ValueError("RAW_HASH_CHANGED")
        locators = {(row["source_line"], row["byte_offset"]): row for row in selected}
        if len(locators) != len(selected):
            raise ValueError("DUPLICATE_SELECTED_LOCATOR")
        found = set()
        member_hash = hashlib.sha256()
        offset = 0
        with zipfile.ZipFile(path) as archive, archive.open(first["archive_member"]) as stream:
            for line_number, raw in enumerate(stream, 1):
                member_hash.update(raw)
                row = locators.get((line_number, offset))
                if row is not None:
                    if len(raw) != row["byte_length"]:
                        raise ValueError("BYTE_LENGTH_CHANGED")
                    found.add((line_number, offset))
                offset += len(raw)
        if member_hash.hexdigest() != first["member_sha256"]:
            raise ValueError("MEMBER_HASH_CHANGED")
        if found != set(locators):
            raise ValueError("SELECTED_BYTE_LOCATOR_MISSING")
        result[sid] = {"raw_sha256": first["raw_sha256"],
                       "member_sha256": first["member_sha256"],
                       "selected_locators_verified": len(found), "member_bytes": offset}
    return result
