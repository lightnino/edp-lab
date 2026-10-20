"""Offline C300 discovery, inactive binding proposal and streaming validation V1.

All parsing is literal ALL_TEXT: no quoting, escaping, casts or NULL inference.
Discovery/validation are engineering evidence, never activation authority.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path

from edp_lab.ingestion.c300_integrity import verify_persisted_freeze
from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.profiling.source_reader import canonical_hash, digest

VERSION = "C300_PARSER_V1"
MAX_LINE = 8 * 1024 * 1024
DAILY_HEADER = "CIK|Company Name|Form Type|Date Filed|File Name"
PROFILES = {
    "SEC_FSDS": {"delimiter": "\t", "encoding": "utf-8"},
    "SEC_13F": {"delimiter": "\t", "encoding": "utf-8"},
    "SEC_EDGAR_DAILY_MASTER": {"delimiter": "|", "encoding": "utf-8"},
}


def save_new(path: Path, value):
    """Exclusive publication: never replace previous evidence."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def run_directory(root: Path, output: Path):
    root, output = root.resolve(), output.resolve()
    if not output.is_relative_to(root / "runs"):
        raise ValueError("OUTPUT_OUTSIDE_RUNS")
    output.mkdir(parents=True, exist_ok=False)
    return output


def roster(root: Path):
    verify_persisted_freeze(root)
    with (root / "metadata/corpus_manifest_v3.csv").open(newline="") as stream:
        return [r for r in csv.DictReader(stream) if r["introduced_cohort"] == "C300"]


@contextmanager
def member_stream(path: Path, name: str):
    if name:
        with zipfile.ZipFile(path) as archive:
            if archive.namelist().count(name) != 1:
                raise ValueError("AMBIGUOUS_ARCHIVE_MEMBER")
            with archive.open(name) as stream:
                yield stream
    else:
        with path.open("rb") as stream:
            yield stream


def table_member(family, name):
    return (family == "SEC_EDGAR_DAILY_MASTER" or
            (family == "SEC_FSDS" and name in {"sub.txt", "pre.txt", "num.txt", "tag.txt"}) or
            (family == "SEC_13F" and name.endswith(".tsv")))


def inspect_stream(stream, family, *, table=True, max_line=MAX_LINE):
    """Hash every byte; bounded physical records; errors preclude full-scan PASS.

    Unsupported encoding is recorded, never guessed. read lengths bound memory;
    resource overflow drains and hashes the remainder without claiming a parse.
    """
    sha = hashlib.sha256()
    offset = number = data = max_seen = non_ascii = 0
    header, header_line, prefix, errors = [], None, [], []
    widths, endings = Counter(), Counter()
    first_error = None
    while True:
        raw = stream.readline(max_line + 1)
        if not raw:
            break
        sha.update(raw)
        if len(raw) > max_line:
            errors.append(f"RESOURCE_LINE_LIMIT byte={offset}")
            offset += len(raw)
            while chunk := stream.read(1024 * 1024):
                sha.update(chunk)
                offset += len(chunk)
            break
        number += 1
        max_seen = max(max_seen, len(raw))
        non_ascii += sum(b >= 128 for b in raw) if not raw.isascii() else 0
        endings["CRLF" if raw.endswith(b"\r\n") else "LF" if raw.endswith(b"\n")
                else "UNTERMINATED"] += 1
        content = raw.removesuffix(b"\n").removesuffix(b"\r")
        try:
            text = content.decode("utf-8", errors="strict")
            if number == 1 and content.startswith(b"\xef\xbb\xbf"):
                raise ValueError("UTF8_BOM_REJECTED")
            if b"\r" in content or (raw.endswith(b"\r") and not raw.endswith(b"\r\n")):
                raise ValueError("UNSUPPORTED_RECORD_TERMINATOR")
            if table:
                daily = family == "SEC_EDGAR_DAILY_MASTER"
                if daily and number <= 7:
                    prefix.append({"source_line": number, "byte_offset": offset,
                                   "byte_length": len(raw), "raw_hex": raw.hex()})
                    if number == 6 and text != DAILY_HEADER:
                        raise ValueError("DAILY_HEADER_MISMATCH")
                    if number == 7 and text != "-" * 80:
                        raise ValueError("DAILY_SEPARATOR_MISMATCH")
                    if number <= 5:
                        expected = ["Description:", "Last Data Received:", "Comments:",
                                    "Anonymous FTP:", " "][number - 1]
                        if not text.startswith(expected) or (number == 5 and text != " "):
                            raise ValueError("DAILY_PREAMBLE_MISMATCH")
                    if number == 6:
                        header, header_line = text.split("|"), number
                elif not daily and number == 1:
                    header, header_line = text.split("\t"), number
                    if not all(header) or len(set(header)) != len(header):
                        raise ValueError("INVALID_HEADER")
                    prefix.append({"source_line": number, "byte_offset": offset,
                                   "byte_length": len(raw), "raw_hex": raw.hex()})
                else:
                    width = text.count(PROFILES[family]["delimiter"]) + 1
                    widths[width] += 1
                    if not content or width != len(header):
                        raise ValueError(f"INVALID_RECORD_WIDTH expected={len(header)} got={width}")
                    data += 1
        except (UnicodeError, ValueError) as exc:
            if first_error is None:
                first_error = {"source_line": number, "byte_offset": offset,
                               "byte_length": len(raw), "raw_sha256": digest(raw)}
            if len(errors) < 20:
                errors.append(f"line={number} byte={offset}: {exc}")
        offset += len(raw)
    if table and (header_line is None or (family == "SEC_EDGAR_DAILY_MASTER" and number < 7)):
        errors.append("INCOMPLETE_HEADER_OR_PREAMBLE")
    return {"member_sha256": sha.hexdigest(), "uncompressed_bytes": offset,
            "physical_records": number, "data_records": data, "header": header,
            "header_line": header_line, "metadata_records": 6 if family ==
            "SEC_EDGAR_DAILY_MASTER" else 0, "prefix_evidence": prefix,
            "field_width_counts": dict(sorted(widths.items())), "line_endings": dict(endings),
            "max_record_bytes": max_seen, "non_ascii_bytes": non_ascii,
            "encoding": "utf-8" if not any("codec" in e for e in errors) else "UNRESOLVED",
            "first_error_locator": first_error, "errors": errors,
            "validation": "FAILED" if errors else "PASS", "max_line_bytes": max_line,
            "scan_scope": "INCOMPLETE" if any("RESOURCE_" in e for e in errors) else "FULL_BYTES"}


def discover(root: Path, output: Path):
    output = run_directory(root, output)
    instances, bindings, schemas = [], [], defaultdict(dict)
    for row in roster(root):
        path = root / row["raw_path"]
        instance = {**row, "physical_bytes": path.stat().st_size, "members": [], "errors": []}
        if file_sha256(path) != row["raw_sha256"]:
            instance["errors"].append("RAW_SHA256_MISMATCH")
        else:
            family = row["source_family"]
            try:
                if family == "SEC_EDGAR_DAILY_MASTER":
                    members = [("", path.stat().st_size, path.stat().st_size)]
                else:
                    with zipfile.ZipFile(path) as archive:
                        members = [(i.filename, i.file_size, i.compress_size)
                                   for i in archive.infolist()]
                        if len({m[0] for m in members}) != len(members):
                            raise ValueError("DUPLICATE_ARCHIVE_MEMBER")
                for name, size, compressed in members:
                    is_table = table_member(family, name)
                    with member_stream(path, name) as stream:
                        evidence = inspect_stream(stream, family, table=is_table)
                    evidence.update(archive_member=name, declared_bytes=size,
                                    compressed_bytes=compressed, kind="TABLE" if is_table
                                    else "SUPPORTING_METADATA")
                    if evidence["uncompressed_bytes"] != size:
                        evidence["errors"].append("MEMBER_SIZE_MISMATCH")
                        evidence["validation"] = "FAILED"
                    instance["members"].append(evidence)
                    if is_table:
                        binding = {k: row[k] for k in ("source_instance_id", "raw_path",
                                                       "raw_sha256", "source_family")}
                        binding.update(archive_member=name, logical_table_name=name or path.name,
                                       member_sha256=evidence["member_sha256"],
                                       uncompressed_bytes=size, expected_header=evidence["header"],
                                       prefix_evidence=evidence["prefix_evidence"],
                                       profile_id=f"{family}_{VERSION}",
                                       discovery_validation=evidence["validation"])
                        bindings.append(binding)
                        variants = schemas[family].setdefault(name or "DAILY_MASTER", {})
                        variants.setdefault(canonical_hash(evidence["header"]), {
                            "header": evidence["header"], "source_instances": []
                        })["source_instances"].append(row["source_instance_id"])
            except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
                instance["errors"].append(str(exc))
        instance["validation"] = "FAILED" if instance["errors"] or any(
            m["validation"] != "PASS" for m in instance["members"]) else "PASS"
        instances.append(instance)
        print(f"{row['source_instance_id']} {instance['validation']}", flush=True)
    inventory = {"version": VERSION, "instances": instances, "schema_editions": schemas,
                 "manifest_sha256": file_sha256(root / "metadata/corpus_manifest_v3.csv"),
                 "roster_sha256": file_sha256(root / "metadata/cohorts/C300.csv"),
                 "authority": "ENGINEERING_DISCOVERY_ONLY", "null_semantics": "UNRESOLVED"}
    save_new(output / "inventory.json", inventory)
    registry = {"version": VERSION, "activation": "INACTIVE_PENDING_HUMAN_APPROVAL",
                "profiles": PROFILES, "bindings": bindings,
                "inventory_sha256": file_sha256(output / "inventory.json"),
                "parser_code_sha256": file_sha256(Path(__file__)),
                "max_line_bytes": MAX_LINE, "null_semantics": "UNRESOLVED"}
    save_new(output / "bindings.proposed.json", registry)
    return inventory, registry


def verify_binding(root: Path, binding: dict, *, max_line=MAX_LINE):
    """Validate inactive proposed rules; RAW and member gates precede parsing."""
    path = root / binding["raw_path"]
    if file_sha256(path) != binding["raw_sha256"]:
        raise ValueError("RAW_SHA256_MISMATCH")
    with member_stream(path, binding["archive_member"]) as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    if sha != binding["member_sha256"]:
        raise ValueError("MEMBER_SHA256_MISMATCH")
    with member_stream(path, binding["archive_member"]) as stream:
        result = inspect_stream(stream, binding["source_family"], max_line=max_line)
    if result["member_sha256"] != sha:
        raise ValueError("MEMBER_CHANGED_DURING_READ")
    if result["header"] != binding["expected_header"]:
        raise ValueError("ORDERED_HEADER_MISMATCH")
    if result["prefix_evidence"] != binding["prefix_evidence"]:
        raise ValueError("PREFIX_MISMATCH")
    if result["uncompressed_bytes"] != binding["uncompressed_bytes"]:
        raise ValueError("MEMBER_SIZE_MISMATCH")
    return result


def require_activation(registry: dict, approval: dict | None = None):
    """Activation requires a separately supplied exact-registry human decision.

    The caller must supply an authenticated human approval; this function checks
    scope, never authenticates a person or creates an approval.
    """
    if (not approval or approval.get("registry_fingerprint") != canonical_hash(registry)
            or approval.get("approve_lexical_activation") is not True
            or not approval.get("authority") or not approval.get("authorization_text")):
        raise PermissionError("C300_PARSER_ACTIVATION_REQUIRES_SCOPED_HUMAN_APPROVAL")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    discover(args.root.resolve(), args.output)


if __name__ == "__main__":
    main()
