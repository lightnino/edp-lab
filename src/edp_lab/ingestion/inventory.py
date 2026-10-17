"""Deterministic, read-only RAW SHA-256 validation."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Hash the exact file bytes, without modifying the input."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_inventory(repo_root: Path, inventory_path: Path) -> tuple[bool, list[str]]:
    """Validate inventory paths/hashes only; no semantic interpretation."""
    outcomes: list[str] = []
    overall_ok = True
    with inventory_path.open("r", encoding="utf-8", newline="") as stream:
        for record in csv.DictReader(stream):
            rel = record["relative_path"]
            expected = record["sha256"].lower()
            path = (repo_root / rel).resolve()
            if not path.is_relative_to(repo_root.resolve()):
                overall_ok = False
                outcomes.append(f"INVALID_PATH {rel}")
                continue
            if not path.is_file():
                overall_ok = False
                outcomes.append(f"MISSING {rel}")
                continue
            actual = sha256_file(path)
            if actual != expected:
                overall_ok = False
                outcomes.append(f"MISMATCH {rel}: expected={expected} actual={actual}")
            else:
                outcomes.append(f"OK {rel}: {actual}")
    return overall_ok, outcomes
