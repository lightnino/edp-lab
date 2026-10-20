"""Opt-in, read-only V2 candidate validation. Never used by the V1 CLI path."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from edp_lab.ingestion.source_identity import verify_source_identity
from edp_lab.profiling.conventions import LOGICAL_TABLES, load_conventions
from edp_lab.profiling.parser_evidence import CANDIDATE_TOKENS, read_member

CANDIDATE = Path("metadata/parser_fidelity_v2_candidate.json")
NULL_REASON = "Authoritative serialized source NULL semantics remain unresolved (D1/D5)."


def load_candidate(root: Path) -> dict:
    """Reject unsupported config changes, coverage drift and active promotion."""
    config = json.loads((root / CANDIDATE).read_text(encoding="utf-8"))
    if (set(config) != {"config_version", "activation_status", "scope", "approval_reference",
                        "profiles", "tables"}
            or config["config_version"] != "PARSER_FIDELITY_V2_CANDIDATE"
            or config["activation_status"] != "INACTIVE"
            or config["scope"] != "REGISTERED_RAW_SNAPSHOTS_ONLY"):
        raise ValueError("UNSUPPORTED_CANDIDATE_CONFIG")
    v1, _ = load_conventions(root)
    expected_profiles = {name.replace("_V1", "_V2_CANDIDATE"): profile
                         for name, profile in v1["profiles"].items()}
    if config["profiles"] != expected_profiles:
        raise ValueError("UNSUPPORTED_CANDIDATE_DIALECT")
    with (root / LOGICAL_TABLES).open(encoding="utf-8", newline="") as stream:
        registered = {(r["source_instance_id"], r["logical_table_name"]): r
                      for r in csv.DictReader(stream)}
    assignments = {(a["source_instance_id"], a["logical_table_name"]):
                   a["profile_id"].replace("_V1", "_V2_CANDIDATE") for a in v1["assignments"]}
    seen = set()
    for table in config["tables"]:
        if set(table) != {"source_instance_id", "logical_table_name", "raw_path", "raw_sha256",
                          "archive_member", "member_sha256", "profile_id", "expected_header",
                          "footer"}:
            raise ValueError("UNSUPPORTED_TABLE_CONFIG")
        key = table["source_instance_id"], table["logical_table_name"]
        if key in seen or key not in registered:
            raise ValueError("UNSUPPORTED_TABLE_BINDING")
        seen.add(key)
        if any(table[k] != registered[key][k] for k in (
                "raw_path", "raw_sha256", "archive_member")):
            raise ValueError("SNAPSHOT_SCOPE_MISMATCH")
        if (table["profile_id"] != assignments[key]
                or not re.fullmatch(r"[a-f0-9]{64}", table["member_sha256"])):
            raise ValueError("UNSUPPORTED_TABLE_PROFILE_OR_HASH")
        header = table["expected_header"]
        if (not isinstance(header, list) or not header
                or any(not isinstance(name, str) or not name or any(c in name for c in "\t|\r\n")
                       for name in header) or len(set(header)) != len(header)):
            raise ValueError("INVALID_EXPECTED_HEADER")
        expected_footer = ({"first_field": "File Creation Time: 1015202603:03",
                            "trailing_empty_fields": 7 if key[1] == "nasdaqlisted.txt" else 6}
                           if table["profile_id"] == "NASDAQ_PIPE_V2_CANDIDATE" else None)
        if table["footer"] != expected_footer:
            raise ValueError("UNSUPPORTED_FOOTER_CONFIG")
    if seen != set(registered) or len(seen) != 13:
        raise ValueError("CANDIDATE_COVERAGE_MISMATCH")
    return config


def literal_records(raw: bytes, table: dict, profile: dict):
    """Yield line, byte offset, original bytes, exact string fields and record kind.

    Pure byte validator for synthetic fixtures and already hash-checked snapshots.
    Footer timestamps are compared as source text, never converted to dates.
    """
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF8_BOM_REJECTED line=1")
    raw.decode("utf-8", errors="strict")
    if not raw:
        raise ValueError("EMPTY_SOURCE")
    records = raw.splitlines(keepends=True)  # bytes: CR/LF only, not Unicode separators
    offset = 0
    footer_seen = False
    for number, original in enumerate(records, 1):
        content = original.removesuffix(b"\n").removesuffix(b"\r")
        # Accept LF/CRLF or an unterminated last record; bare CR is unsupported.
        if b"\r" in content or (original.endswith(b"\r") and not original.endswith(b"\r\n")):
            raise ValueError(f"UNSUPPORTED_RECORD_TERMINATOR line={number}")
        if not content:
            raise ValueError(f"BLANK_PHYSICAL_RECORD line={number}")
        fields = content.decode("utf-8").split(profile["delimiter"])
        if number == 1:
            if fields != table["expected_header"]:
                raise ValueError("ORDERED_HEADER_MISMATCH line=1")
            kind = "HEADER"
        elif fields[0].startswith("File Creation Time:"):
            footer = table["footer"]
            if footer_seen:
                raise ValueError(f"DUPLICATE_FOOTER line={number}")
            if (footer is None or fields != [footer["first_field"]]
                    + [""] * footer["trailing_empty_fields"]):
                raise ValueError(f"MALFORMED_OR_UNEXPECTED_FOOTER line={number}")
            footer_seen = True
            kind = "FOOTER"
        else:
            if footer_seen:
                raise ValueError(f"NONFINAL_FOOTER line={number}")
            if len(fields) != len(table["expected_header"]):
                raise ValueError(f"INVALID_RECORD_WIDTH line={number}")
            kind = "DATA"
        yield number, offset, original, fields, kind
        offset += len(original)
    if table["footer"] is not None and not footer_seen:
        raise ValueError("ABSENT_FOOTER")


def quote_comparison(value: str) -> dict:
    """Hypothetical CSV double-quote decoding, never used by literal_records."""
    try:
        decoded = next(csv.reader([value], delimiter="\t", quotechar='"',
                                  doublequote=True, escapechar=None, strict=True))
        if len(decoded) != 1:
            raise ValueError("NOT_ONE_FIELD")
        return {"literal_value": value, "proposed_decoded_value": decoded[0],
                "status": "EVIDENCE_ONLY_NOT_APPROVED"}
    except (csv.Error, ValueError) as exc:
        return {"literal_value": value, "proposed_decoded_value": None,
                "status": "HYPOTHESIS_PARSE_FAILED", "reason": str(exc)}


def validate_bytes(raw: bytes, table: dict, profile: dict) -> dict:
    """Collect fidelity accounting and lexical counts, not production statistics."""
    counts = {name: Counter(empty_fields=0, whitespace_only_fields=0)
              for name in table["expected_header"]}
    tokens = Counter()
    accounting = Counter(HEADER=0, DATA=0, FOOTER=0)
    footers, comparisons, flags = [], [], []
    comparison_found = False
    for line, offset, original, fields, kind in literal_records(raw, table, profile):
        accounting[kind] += 1
        if kind == "FOOTER":
            footers.append({"source_line": line, "byte_offset": offset,
                            "raw_bytes_hex": original.hex()})
        if kind != "DATA":
            continue
        for name, value in zip(table["expected_header"], fields, strict=True):
            counts[name]["empty_fields"] += value == ""
            counts[name]["whitespace_only_fields"] += bool(value) and not value.strip()
            if value.casefold() in CANDIDATE_TOKENS:
                tokens[name, value] += 1
            if not comparison_found and '"' in value:
                comparisons.append({"source_line": line, "column_name": name,
                                    **quote_comparison(value)})
                comparison_found = True
            if table["logical_table_name"] == "pre.txt" and name == "plabel" and value == "":
                flags.append({"source_line": line, "column_name": name,
                              "code": "DOCUMENTED_NON_NULLABLE_FIELD_IS_EMPTY",
                              "disposition": "PRESERVED_LITERAL_NOT_REJECTED"})
    return {
        "record_accounting": {**accounting, "physical_records": sum(accounting.values())},
        "footer_evidence": footers, "lexical_blank_counts_by_column": counts,
        "lexical_candidate_tokens": [{"column_name": name, "literal_value": value, "count": n}
                                     for (name, value), n in sorted(tokens.items())],
        "semantic_metrics": {name: {"status": "NOT_COMPUTED", "reason": NULL_REASON}
                             for name in ("null_count", "null_pct")},
        "quote_comparisons": comparisons, "documented_inconsistencies": flags,
    }


def validate_candidate(root: Path) -> list[dict]:
    config = load_candidate(root)
    verify_source_identity(root, check_raw=True)
    results = []
    for table in config["tables"]:
        raw = read_member(root, table)
        if hashlib.sha256(raw).hexdigest() != table["member_sha256"]:
            raise ValueError(f"MEMBER_SHA256_MISMATCH {table['logical_table_name']}")
        result = validate_bytes(raw, table, config["profiles"][table["profile_id"]])
        results.append({"validation": "PASS", "config_version": config["config_version"],
                        "activation_status": config["activation_status"],
                        "profile": config["profiles"][table["profile_id"]],
                        "source": table, **result})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true", help="Include full evidence on stdout")
    args = parser.parse_args()
    try:
        results = validate_candidate(args.root)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for result in results:
                source, counts = result["source"], result["record_accounting"]
                print(f"CANDIDATE PASS {source['source_instance_id']} "
                      f"{source['logical_table_name']}: {counts['DATA']} data, "
                      f"{counts['HEADER']} header, {counts['FOOTER']} footer, "
                      f"{counts['physical_records']} physical records")
            print("INACTIVE; profiles PROVISIONAL; semantic null_count/null_pct NOT_COMPUTED")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"FAIL candidate validation: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
