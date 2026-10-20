"""Read-only lexical evidence for parser review; not a profiling baseline.

Print deterministic JSON to stdout. Verify admitted hashes before reading members.
Witness locators use one-based physical line and exact source header. No values
are normalized, cast, interpreted as NULL, or written back to RAW.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

from edp_lab.ingestion.source_identity import verify_source_identity
from edp_lab.profiling.conventions import LOGICAL_TABLES, load_conventions

CANDIDATE_TOKENS = frozenset({"null", "none", "n/a", "na", "nan", "\\n", "-", "."})


def read_member(root: Path, table: dict) -> bytes:
    """Read an already integrity-checked source; caller owns the hash gate."""
    path = root / table["raw_path"]
    if table["archive_member"]:
        with ZipFile(path) as archive:
            return archive.read(table["archive_member"])
    return path.read_bytes()


def investigate(root: Path) -> list[dict]:
    verify_source_identity(root, check_raw=True)
    _, bindings = load_conventions(root)
    with (root / LOGICAL_TABLES).open(encoding="utf-8", newline="") as stream:
        tables = list(csv.DictReader(stream))
    evidence = []
    for table in tables:
        profile = bindings[table["source_instance_id"], table["logical_table_name"]]
        raw = read_member(root, table)
        # Split only CR/LF record terminators, never Unicode text separators.
        lines = raw.decode("utf-8", errors="strict").splitlines(keepends=True)
        # bytes.splitlines recognizes CR/LF only; compare to catch text separators.
        byte_lines = raw.splitlines(keepends=True)
        if len(lines) != len(byte_lines):
            raise ValueError("NON_CR_LF_TEXT_SEPARATOR: review required")
        lines = [b.decode("utf-8", errors="strict") for b in byte_lines]
        header = lines[0].rstrip("\r\n").split(profile["delimiter"])
        if any(not name for name in header) or len(set(header)) != len(header):
            raise ValueError("INVALID_HEADER")
        counts: Counter = Counter()
        empty: Counter = Counter()
        tokens: Counter = Counter()
        witnesses = {}
        footer = []
        for number, line in enumerate(lines[1:], 2):
            fields = line.rstrip("\r\n").split(profile["delimiter"])
            if (profile["metadata_record_policy"] == "TRAILING_FILE_CREATION_TIME"
                    and fields[0].startswith("File Creation Time:")):
                footer.append({"line": number, "text": line.rstrip("\r\n")})
                continue
            if footer or len(fields) != len(header):
                raise ValueError(f"INVALID_RECORD {table['logical_table_name']}:{number}")
            counts["data_rows"] += 1
            for name, value in zip(header, fields, strict=True):
                flags = {
                    "empty": value == "",
                    "whitespace_only": bool(value) and not value.strip(),
                    "edge_whitespace": bool(value) and value != value.strip(),
                    "double_quote": '"' in value,
                    "backslash": "\\" in value,
                    "quoted_empty": value == '""',
                    "candidate_token": value.casefold() in CANDIDATE_TOKENS,
                    "leading_zero": bool(re.match(r"^0[0-9]", value)),
                    "decimal": bool(re.fullmatch(r"[+-]?[0-9]+\.[0-9]+", value)),
                    "exponent": bool(re.fullmatch(
                        r"[+-]?[0-9]+(?:\.[0-9]+)?[Ee][+-]?[0-9]+", value)),
                    "date_or_timestamp": bool(re.fullmatch(
                        r"(?:[0-9]{2}-[A-Z]{3}-[0-9]{4}|[0-9]{8}|"
                        r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?: [0-9:.]+)?)", value)),
                    "non_ascii": not value.isascii(),
                }
                for flag, present in flags.items():
                    if present:
                        counts[flag] += 1
                        witnesses.setdefault(flag, {"line": number, "column": name,
                                                    "value": value})
                if value == "":
                    empty[name] += 1
                if flags["candidate_token"]:
                    tokens[(name, value)] += 1
        if profile["metadata_record_policy"] != "NONE" and len(footer) != 1:
            raise ValueError("EXPECTED_ONE_FOOTER")
        evidence.append({
            "source_instance_id": table["source_instance_id"],
            "raw_path": table["raw_path"], "raw_sha256": table["raw_sha256"],
            "member": table["logical_table_name"],
            "member_sha256": hashlib.sha256(raw).hexdigest(),
            "header": header, "utf8_strict": True,
            "bom": raw.startswith((b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff")),
            "physical_lines": len(lines),
            "blank_lines": sum(not line.rstrip("\r\n") for line in lines),
            "crlf": raw.count(b"\r\n"),
            "lf_without_cr": raw.count(b"\n") - raw.count(b"\r\n"),
            "bare_cr": raw.count(b"\r") - raw.count(b"\r\n"),
            "final_newline": raw.endswith(b"\n"),
            "lexical_counts": dict(sorted(counts.items())),
            "empty_by_column": dict(empty), "first_witnesses": witnesses,
            "candidate_tokens": [
                {"column": name, "text": value, "count": count}
                for (name, value), count in sorted(tokens.items())
            ],
            "footer": footer,
        })
    return evidence


def main() -> None:
    print(json.dumps(investigate(Path.cwd()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
