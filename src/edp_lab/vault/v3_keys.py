"""Packaged copy of the approved V1 length-prefixed key serialization.

The original reference lives in scripts/day6_vault_contract_v1.py, outside the
runtime wheel. Cross-check tests require byte-for-byte matching key outputs.
"""

from __future__ import annotations

import hashlib

PREFIX = b"EDP_VAULT_LOAD_V1\x00"


def key(domain: str, parts: tuple[str | None, ...]) -> str:
    output = bytearray(PREFIX)
    for part in (domain, *parts):
        if part is None:
            output.extend((0xFFFFFFFF).to_bytes(4, "big"))
            continue
        encoded = part.encode("utf-8")
        if len(encoded) >= 0xFFFFFFFF:
            raise ValueError("PART_TOO_LONG")
        output.extend(len(encoded).to_bytes(4, "big"))
        output.extend(encoded)
    return hashlib.sha256(output).hexdigest()


def filing_key(adsh: str) -> str:
    if not adsh:
        raise ValueError("MISSING_ADSH")
    return key("H_FILING", ("SEC_FSDS", adsh))


def concept_key(tag: str, version: str) -> str:
    if not tag or not version:
        raise ValueError("MISSING_CONCEPT_COMPONENT")
    return key("H_CONCEPT", ("SEC_FSDS", tag, version))


def occurrence_key(source_id: str, member: str, member_sha256: str,
                   offset: int, length: int) -> str:
    if not source_id or not member or len(member_sha256) != 64 or offset < 0 or length <= 0:
        raise ValueError("INVALID_OCCURRENCE_LOCATOR")
    return key("SOURCE_OCCURRENCE", (source_id, member, member_sha256,
                                     str(offset), str(length)))
