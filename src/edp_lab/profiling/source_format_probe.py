"""Read-only evidence probe of the registered logical file/member formats.

Prints JSON diagnostic evidence to stdout. Does not parse records or mutate RAW.
Run from repository root:
    uv run python -m edp_lab.profiling.source_format_probe
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from edp_lab.ingestion.source_identity import LOGICAL_TABLES, verify_source_identity


def _sample_bytes(value: bytes, *, limit: int = 140) -> str:
    # Escaped representation: no control characters/newlines in JSON display.
    return repr(value[:limit]) + (" [TRUNCATED]" if len(value) > limit else "")


def inspect_member(data: bytes) -> dict[str, object]:
    """Mechanical byte diagnostics; not a claim about the parser dialect."""
    lines = data.splitlines()
    nonempty = [line for line in lines if line]
    first = nonempty[0] if nonempty else b""
    last = nonempty[-1] if nonempty else b""
    crlf = data.count(b"\r\n")
    try:
        data.decode("utf-8", errors="strict")
        utf8 = True
    except UnicodeDecodeError:
        utf8 = False
    return {
        "member_sha256": hashlib.sha256(data).hexdigest(),
        "byte_length": len(data),
        "physical_line_count_diagnostic": len(lines),
        "newline_counts": {
            "crlf": crlf,
            "lf_only": data.count(b"\n") - crlf,
            "cr_only": data.count(b"\r") - crlf,
        },
        "utf8_decodable": utf8,
        "utf8_bom": data.startswith(b"\xef\xbb\xbf"),
        "first_nonempty_line_bytes": _sample_bytes(first),
        "last_nonempty_line_bytes": _sample_bytes(last),
        "first_line_tab_separator_count": first.count(b"\t"),
        "first_line_pipe_separator_count": first.count(b"|"),
        "last_line_tab_separator_count": last.count(b"\t"),
        "last_line_pipe_separator_count": last.count(b"|"),
    }


def probe_registered_sources(root: Path) -> list[dict[str, object]]:
    root = root.resolve()
    # Fail closed before any claimed source-level evidence is produced.
    identity = verify_source_identity(root, check_raw=True)
    if any(line.startswith("REVIEW_REQUIRED") for line in identity):
        raise ValueError("Source identity has unresolved equal-hash delivery evidence")
    with (root / LOGICAL_TABLES).open(encoding="utf-8-sig", newline="") as handle:
        entries = list(csv.DictReader(handle))
    output: list[dict[str, object]] = []
    for row in entries:
        raw = root / row["raw_path"]
        member = row["archive_member"]
        if member:
            with ZipFile(raw) as archive:
                payload = archive.read(member)
        else:
            payload = raw.read_bytes()
        output.append({
            "source_instance_id": row["source_instance_id"],
            "logical_table_name": row["logical_table_name"],
            "archive_member": member or None,
            "raw_sha256": row["raw_sha256"],
            **inspect_member(payload),
        })
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        output = probe_registered_sources(args.root)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"FAIL source format probe: {exc}\n")
    print(json.dumps(
        {"probe_kind": "BYTE_DIAGNOSTIC_NOT_PARSED", "logical_table_count": len(output),
         "tables": output},
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
