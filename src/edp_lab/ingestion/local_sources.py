"""Physical local availability, independent of admission and publisher-edition identity."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

from edp_lab.ingestion.inventory import sha256_file

VERSION = "LOCAL_SOURCE_AVAILABILITY_V1"


def verify_representation(representation):
    path = Path(representation["path"])
    if representation["kind"] == "FILE":
        if (not path.is_file() or path.is_symlink()
                or path.stat().st_size != representation["bytes"]
                or sha256_file(path) != representation["sha256"]):
            raise ValueError(f"Local file changed or missing: {path}")
    elif representation["kind"] == "EXTRACTED_DIRECTORY":
        index = Path(representation["inventory_path"])
        if sha256_file(index) != representation["inventory_sha256"]:
            raise ValueError("Directory inventory changed")
        count, size = 0, 0
        # Every physical child is hashed; no single publisher archive hash is invented.
        with index.open() as stream:
            for line in stream:
                item = json.loads(line)
                child = (path / item["relative_path"]).resolve()
                if (Path(item["relative_path"]).is_absolute()
                        or not child.is_relative_to(path.resolve())):
                    raise ValueError("Directory inventory path escape")
                verify_representation({"kind": "FILE", "path": str(child), **item})
                count += 1
                size += item["bytes"]
        actual_count = sum(len(files) for _, _, files in os.walk(path))
        if (count != representation["file_count"] or size != representation["bytes"]
                or actual_count != count):
            raise ValueError("Directory inventory population mismatch")
    else:
        raise ValueError("Unsupported local representation")


def move_existing(source, destination, *, expected_sha256=None, expected_bytes=None):
    """Never overwrite. Same-volume rename; cross-volume copies require size headroom.

    The caller must inventory a directory first. Move preserves its original tree;
    the receipt uses device/inode to distinguish rename from cross-volume transfer.
    """
    source, destination = Path(source), Path(destination)
    if source.is_symlink():
        raise ValueError("Refusing to relocate a symbolic link")
    if destination.is_symlink():
        raise ValueError("Refusing a symbolic-link destination")
    if destination.exists():
        if (expected_sha256 is not None and destination.is_file()
                and sha256_file(destination) == expected_sha256):
            return {"action": "REUSED_DESTINATION", "original_path": str(source),
                    "final_path": str(destination), "sha256": expected_sha256}
        raise ValueError(f"Destination already exists: {destination}")
    before = source.stat()
    if expected_sha256 is not None and sha256_file(source) != expected_sha256:
        raise ValueError("Source changed before relocation")
    destination.parent.mkdir(parents=True, exist_ok=True)
    same_volume = before.st_dev == destination.parent.stat().st_dev
    free = shutil.disk_usage(destination.parent).free
    if not same_volume:
        if expected_bytes is None or free < expected_bytes:
            raise ValueError("Insufficient/unknown cross-volume transfer headroom")
        # Do not unlink the original before verification. Cross-volume moves need
        # a separately verified copy; keep this routine fail-closed for directories.
        raise ValueError("Cross-volume relocation requires a verified-copy operation")
    # macOS renamex_np(RENAME_EXCL) prevents a concurrent destination from being replaced.
    if os.uname().sysname == "Darwin":
        import ctypes

        library = ctypes.CDLL(None, use_errno=True)
        rename = library.renamex_np
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        if rename(os.fsencode(source), os.fsencode(destination), 0x00000004) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), str(destination))
    else:
        raise ValueError("Exclusive directory rename is implemented for macOS only")
    after = destination.stat()
    if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
        raise ValueError("Relocation did not preserve physical inode")
    if expected_sha256 is not None and sha256_file(destination) != expected_sha256:
        raise ValueError("Destination hash mismatch after relocation")
    return {"action": "SAME_VOLUME_RENAME", "original_path": str(source),
            "final_path": str(destination), "device": after.st_dev, "inode": after.st_ino,
            "available_bytes_before": free, "sha256": expected_sha256}


def load_availability(path):
    inventory = json.loads(Path(path).read_bytes())
    if inventory["version"] != VERSION:
        raise ValueError("Unsupported local availability version")
    return inventory


def local_match(candidate, inventory):
    """Find a local delivery slot; URLs/period names alone do not prove an edition."""
    matches = [r for r in inventory["datasets"] if (
        candidate["url"] in r.get("publisher_url_hints", []) or (
            r.get("family") == candidate.get("family")
            and r.get("edition_label") is not None
            and r["edition_label"] == candidate.get("edition")))]
    if not matches:
        return None
    if len(matches) != 1:
        expected = candidate.get("expected_sha256")
        exact = [(record, representation) for record in matches
                 for representation in record["representations"]
                 if expected and representation.get("sha256") == expected
                 and representation.get("availability") == "VERIFIED"
                 and representation["kind"] == "FILE"]
        if len(exact) == 1:
            record, representation = exact[0]
            verify_representation(representation)
            return {"dataset_id": record["dataset_id"], "representation": representation}
        raise ValueError("Multiple local delivery slots; retain edition evidence")
    record = matches[0]
    usable = [r for r in record["representations"] if r.get("availability") == "VERIFIED"]
    if not usable:
        raise ValueError("Known local dataset has no verified usable representation")
    for representation in usable:
        verify_representation(representation)
    expected = candidate.get("expected_sha256")
    if expected:
        exact = [r for r in usable if r.get("sha256") == expected and r["kind"] == "FILE"]
        if exact:
            return {"dataset_id": record["dataset_id"], "representation": exact[0]}
        # A changed edition needs explicit independent evidence, not a same-URL overwrite.
        if not candidate.get("publisher_edition_evidence"):
            raise ValueError("Changed publisher edition requires separate candidate evidence")
        return None
    raise ValueError(
        f"Verified local dataset already available: {record['dataset_id']}; "
        "publisher edition is unresolved, so no duplicate download was attempted")


def inventory_digest(path):
    """Hash inventory bytes, not a fabricated original publisher ZIP."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
