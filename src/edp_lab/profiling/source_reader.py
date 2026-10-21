"""Shared, read-only, fail-closed source reader for deterministic profiling."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import platform
import subprocess
from dataclasses import dataclass
from importlib.metadata import distributions
from pathlib import Path

import duckdb

from edp_lab.ingestion.source_identity import verify_source_identity
from edp_lab.ingestion.universe import ScopeDenied, UniverseGate, processing
from edp_lab.profiling.parser_evidence import read_member
from edp_lab.profiling.parser_fidelity import literal_records, load_candidate

FREEZE = Path("metadata/parsing_profiling_freeze_v2.json")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_hash(value: object) -> str:
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode())


def execution_provenance(root: Path) -> dict:
    """Capture actual code/dependencies, including uncommitted code contents."""
    def git(*args):
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else None

    files = sorted((root / "src/edp_lab").rglob("*.py"))
    return {
        "tool_version": "EDP_PROFILING_V1",
        "git_revision": git("rev-parse", "HEAD"),
        "git_status": git("status", "--porcelain"),
        "code_sha256": {str(p.relative_to(root)): digest(p.read_bytes()) for p in files},
        "python_version": platform.python_version(),
        "duckdb_runtime_version": duckdb.__version__,
        "dependency_versions": dict(sorted((d.metadata["Name"], d.version)
                                           for d in distributions() if d.metadata["Name"])),
        "lock_sha256": digest((root / "uv.lock").read_bytes())
        if (root / "uv.lock").exists() else None,
    }


@dataclass(frozen=True)
class SourceTable:
    """Materialized exact text occurrences. NULL rules are explicit or unknown.

    Public tools accept this shared reader result, including failed reads, rather
    than reopening inputs or implementing their own parsing. Locators align to rows.
    """

    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    locators: tuple[dict, ...]
    source: dict
    config: dict
    provenance: dict
    null_tokens: tuple[str, ...] | None
    accounting: dict
    errors: tuple[str, ...] = ()

    authorization_outcome: dict | None = None

    @property
    def parse_status(self):
        if self.authorization_outcome:
            return "BLOCKED"
        return "FAIL" if self.errors else "PASS"


def read_synthetic(raw: bytes, *, delimiter: str, quote: str | None,
                   escape: str | None = None, null_tokens: tuple[str, ...] | None,
                   expected_header: tuple[str, ...], source_id: str = "SYNTHETIC",
                   provenance: dict | None = None) -> SourceTable:
    """Explicit UTF-8 ALL_TEXT fixture dialect; never used for registered RAW.

    None means unknown NULL semantics; () explicitly declares no NULL tokens.
    Quoted and unquoted token spellings follow the declared decoded-token rule.
    Locators include inclusive physical-line spans, supporting multiline CSV.
    """
    config = {"delimiter": delimiter, "quote": quote, "escape": escape,
              "doublequote": True, "encoding": "utf-8", "types": "ALL_TEXT",
              "null_tokens": null_tokens, "expected_header": expected_header,
              "null_rule": "DECODED_EXACT_TOKEN" if null_tokens is not None else "UNKNOWN"}
    source = {"source_instance_id": source_id, "raw_path": None,
              "raw_sha256": digest(raw), "member_sha256": digest(raw),
              "logical_table_name": "synthetic", "archive_member": ""}
    rows, locators, errors = [], [], []
    header_count = 0
    try:
        if len(delimiter) != 1 or delimiter in "\r\n":
            raise ValueError("INVALID_DELIMITER")
        if not expected_header or any(not n for n in expected_header) or (
                len(set(expected_header)) != len(expected_header)):
            raise ValueError("INVALID_HEADER")
        reader = csv.reader(io.StringIO(raw.decode("utf-8", errors="strict"), newline=""),
                            delimiter=delimiter, quotechar=quote, escapechar=escape,
                            quoting=csv.QUOTE_MINIMAL if quote else csv.QUOTE_NONE, strict=True)
        if next(reader, None) != list(expected_header):
            raise ValueError("ORDERED_HEADER_MISMATCH")
        header_count = 1
        previous = reader.line_num
        for fields in reader:
            if len(fields) != len(expected_header):
                raise ValueError(f"INVALID_RECORD_WIDTH line={previous + 1}")
            rows.append(tuple(fields))
            locators.append({"source_line": previous + 1, "end_line": reader.line_num})
            previous = reader.line_num
    except (ValueError, UnicodeError, csv.Error, TypeError) as exc:
        errors.append(str(exc))
    return SourceTable(expected_header, tuple(rows), tuple(locators), source, config,
                       provenance if provenance is not None else execution_provenance(Path.cwd()), null_tokens,
                       {"HEADER": header_count, "DATA": len(rows), "FOOTER": 0}, tuple(errors))


def read_registered(root: Path, source_instance_id: str, logical_table: str, *,
                    provenance: dict | None = None) -> SourceTable:
    """Read exactly the approved snapshot; never promote or modify frozen configs."""
    root = root.resolve()
    provenance = provenance if provenance is not None else execution_provenance(root)
    source = {"source_instance_id": source_instance_id, "logical_table_name": logical_table}
    rows, locators, errors = [], [], []
    accounting = {"HEADER": 0, "DATA": 0, "FOOTER": 0}
    config, columns = {}, ()
    try:
        UniverseGate.load(root).verify_inventory(root)
        freeze_bytes = (root / FREEZE).read_bytes()
        freeze = json.loads(freeze_bytes)
        candidate = load_candidate(root)
        if candidate != freeze["effective_configuration"]:
            raise ValueError("FROZEN_CONFIGURATION_MISMATCH")
        # Pin reviewed reader/validator/config inputs, not the new profiling implementation.
        for name, expected in freeze["code_revision"]["file_sha256"].items():
            if name.endswith(("parser_fidelity.py", "parser_evidence.py", "conventions.py",
                              "source_identity.py", ".json", ".csv", "uv.lock")) and (
                    digest((root / name).read_bytes()) != expected):
                raise ValueError(f"FROZEN_DEPENDENCY_MISMATCH {name}")
        source = next(t for t in candidate["tables"]
                      if (t["source_instance_id"], t["logical_table_name"])
                      == (source_instance_id, logical_table))
        source = dict(source)
        processing(root, source, "GOLD_V2")
        columns = tuple(source["expected_header"])
        profile = candidate["profiles"][source["profile_id"]]
        config = {"profile_id": source["profile_id"], "resolved_profile": profile,
                  "freeze_ref": str(FREEZE), "freeze_sha256": digest(freeze_bytes),
                  "table": source, "null_semantics": "UNRESOLVED"}
        verify_source_identity(root, check_raw=True)
        # Verify the exact bytes opened here as well as the registry-level checks.
        if digest((root / source["raw_path"]).read_bytes()) != source["raw_sha256"]:
            raise ValueError("RAW_SHA256_MISMATCH")
        raw = read_member(root, source)
        if digest(raw) != source["member_sha256"]:
            raise ValueError("MEMBER_SHA256_MISMATCH")
        for line, offset, original, fields, kind in literal_records(raw, source, profile):
            accounting[kind] += 1
            if kind == "DATA":
                rows.append(tuple(fields))
                locators.append({"source_line": line, "byte_offset": offset,
                                 "byte_length": len(original)})
    except ScopeDenied as exc:
        return SourceTable(columns, (), (), source, config, provenance, None, accounting,
                           (), exc.outcome)
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    return SourceTable(columns, tuple(rows), tuple(locators), source, config, provenance,
                       None, accounting, tuple(errors))
