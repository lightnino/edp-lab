"""Pure, source-scoped Vault V1 key and accounting checks; no warehouse writes."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

PREFIX = b"EDP_VAULT_LOAD_V1\x00"
CONTEXT = ("ddate", "qtrs", "uom", "coreg", "segments")
IDENTITY = ("adsh", "tag", "version")


def encode(domain: str, parts: Sequence[str | None]) -> bytes:
    """Length-prefix UTF-8 fields; None is distinct from the empty string."""
    output = bytearray(PREFIX)
    for part in (domain, *parts):
        if part is None:
            output.extend((0xFFFFFFFF).to_bytes(4, "big"))
            continue
        value = part.encode("utf-8")
        if len(value) >= 0xFFFFFFFF:
            raise ValueError("PART_TOO_LONG")
        output.extend(len(value).to_bytes(4, "big"))
        output.extend(value)
    return bytes(output)


def key(domain: str, parts: Sequence[str | None]) -> str:
    return hashlib.sha256(encode(domain, parts)).hexdigest()


def filing_key(adsh: str) -> str:
    if not adsh:
        raise ValueError("MISSING_ADSH")
    return key("H_FILING", ("SEC_FSDS", adsh))


def concept_key(tag: str, version: str) -> str:
    if not tag or not version:
        raise ValueError("MISSING_CONCEPT_COMPONENT")
    return key("H_CONCEPT", ("SEC_FSDS", tag, version))


def context_parts(row: Mapping[str, str | None], header: Sequence[str]) -> tuple[str | None, ...]:
    """Encode physical absence separately from present blank and unknown/null."""
    if not all(name in header for name in (*IDENTITY, "ddate", "qtrs", "uom", "coreg")):
        raise ValueError("UNSUPPORTED_NUM_SCHEMA")
    if len(header) != len(set(header)):
        raise ValueError("DUPLICATE_HEADER_FIELD")
    parts: list[str | None] = []
    for name in CONTEXT:
        if name not in header:
            if name != "segments":
                raise ValueError("UNSUPPORTED_NUM_SCHEMA")
            parts.extend((name, "ABSENT", None))
        elif name not in row:
            raise ValueError("PRESENT_FIELD_NOT_PARSED")
        elif row[name] is None:
            parts.extend((name, "NULL", None))
        else:
            parts.extend((name, "PRESENT", row[name]))
    return tuple(parts)


def fact_slot_key(row: Mapping[str, str | None], header: Sequence[str]) -> str:
    for name in IDENTITY:
        if name not in header or not row.get(name):
            raise ValueError("MISSING_BUSINESS_KEY_COMPONENT")
    # The complete context, including the schema presence marker, is part of the Link key.
    return key("L_FACT_SLOT", (filing_key(row["adsh"]),
                               concept_key(row["tag"], row["version"]),
                               *context_parts(row, header)))


def occurrence_key(source_id: str, member: str, member_sha256: str,
                   offset: int, length: int) -> str:
    if not source_id or not member or len(member_sha256) != 64 or offset < 0 or length <= 0:
        raise ValueError("INVALID_OCCURRENCE_LOCATOR")
    return key("SOURCE_OCCURRENCE", (source_id, member, member_sha256,
                                      str(offset), str(length)))


def assertion_key(slot_hk: str, occurrence_hk: str, parser_version: str) -> str:
    return key("S_FACT_ASSERTION", (slot_hk, occurrence_hk, parser_version))


def lexical_hashdiff(fields: Sequence[tuple[int, str, str, str | None]]) -> str:
    """Ordered (ordinal, original name, state, exact text) payload, excluding load metadata."""
    parts = [str(len(fields))]
    for expected, (ordinal, name, state, value) in enumerate(fields, 1):
        if ordinal != expected or state not in {"PRESENT", "NULL", "ABSENT"}:
            raise ValueError("INVALID_FIELD_STATE_OR_ORDER")
        if state == "PRESENT" and value is None:
            raise ValueError("PRESENT_REQUIRES_TEXT")
        if state != "PRESENT" and value is not None:
            raise ValueError("NONPRESENT_HAS_TEXT")
        parts.extend((str(ordinal), name, state, value))
    return key("FSDS_NUM_LEXICAL_PAYLOAD", tuple(parts))


def validate_lossless(records: Sequence[Mapping], expected_data: int,
                      expected_fields: int) -> None:
    """Fail closed on identity, field-width, provenance or duplicate replay drift."""
    seen: dict[str, tuple[str, str]] = {}
    data = fields = 0
    for record in records:
        required = ("occurrence_hk", "source_instance_id", "source_line", "byte_offset",
                    "byte_length",
                    "raw_sha256", "member_sha256", "binding_sha256", "raw_path",
                    "archive_member", "payload_hashdiff", "record_kind", "fields")
        if any(record.get(name) is None for name in required):
            raise ValueError("MISSING_LINEAGE")
        if record["occurrence_hk"] != occurrence_key(
            record["source_instance_id"], record["archive_member"],
            record["member_sha256"], record["byte_offset"], record["byte_length"]
        ):
            raise ValueError("OCCURRENCE_LINEAGE_MISMATCH")
        if record["record_kind"] == "DATA":
            data += 1
            ordered = record["fields"]
            if [f[0] for f in ordered] != list(range(1, len(ordered) + 1)):
                raise ValueError("FIELD_ORDER_MISMATCH")
            if record["payload_hashdiff"] != lexical_hashdiff(ordered):
                raise ValueError("PAYLOAD_HASHDIFF_MISMATCH")
            fields += len(ordered)
        signature = (record["member_sha256"], record["payload_hashdiff"])
        old = seen.get(record["occurrence_hk"])
        if old is not None:
            if old != signature:
                raise ValueError("REPLAY_DRIFT")
            raise ValueError("DUPLICATE_OCCURRENCE_IN_BATCH")
        seen[record["occurrence_hk"]] = signature
    if data != expected_data or fields != expected_fields:
        raise ValueError("LOSSLESS_COUNT_MISMATCH")
