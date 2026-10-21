"""Exact occurrence reader for approved C300 V1 bindings; bounded, fail closed.

Validation may inspect proposed rules, but consumption through this public reader
requires host-supplied scoped human authority. This module never materializes a
population or infers NULLs. Exceptions invalidate completion of the iteration.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.ingestion.universe import processing
from edp_lab.parsers.c300_v1 import (
    MAX_LINE,
    PROFILES,
    VERSION,
    member_stream,
    require_activation,
    roster,
)
from edp_lab.profiling.source_reader import canonical_hash


@dataclass(frozen=True)
class RecordOccurrence:
    source_instance_id: str
    archive_member: str
    source_line: int
    byte_offset: int
    original_bytes: bytes
    fields: tuple[str, ...]
    kind: str


def occurrences(root: Path, registry: dict, binding: dict, approval: dict):
    processing(root, binding, "C300")
    require_activation(registry, approval)
    if binding.get('discovery_validation') != 'PASS':
        raise PermissionError('FAILED_BINDING_NOT_ELIGIBLE_FOR_ACTIVATION')
    if (registry['version'] != VERSION or registry['profiles'] != PROFILES
            or registry['max_line_bytes'] != MAX_LINE
            or registry['parser_code_sha256'] != file_sha256(
                root / 'src/edp_lab/parsers/c300_v1.py')
            or canonical_hash(binding) not in {canonical_hash(b) for b in registry['bindings']}):
        raise ValueError('UNREGISTERED_PARSER_OR_BINDING')
    row = next((r for r in roster(root)
                if r['source_instance_id'] == binding['source_instance_id']), None)
    if row is None or any(row[k] != binding[k] for k in (
            'raw_path', 'raw_sha256', 'source_family')):
        raise ValueError('FROZEN_BINDING_MISMATCH')
    yield from validated_occurrences(root, binding)


def validated_occurrences(root: Path, binding: dict):
    """Engineering validation iterator; not an activation or profiling entry point.

    Hash gates precede the first record. Locators refer to uncompressed member
    bytes; original bytes include exact terminators. Prefix records are accounted
    separately, and all equal-looking DATA occurrences are emitted individually.
    """
    path = root / binding['raw_path']
    if file_sha256(path) != binding['raw_sha256']:
        raise ValueError('RAW_SHA256_MISMATCH')
    with member_stream(path, binding['archive_member']) as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != binding['member_sha256']:
            raise ValueError('MEMBER_SHA256_MISMATCH')
    prefix = {p['source_line']: p for p in binding['prefix_evidence']}
    family = binding['source_family']
    header_line = 6 if family == 'SEC_EDGAR_DAILY_MASTER' else 1
    offset = number = 0
    sha = hashlib.sha256()
    with member_stream(path, binding['archive_member']) as stream:
        while raw := stream.readline(MAX_LINE + 1):
            number += 1
            if len(raw) > MAX_LINE:
                raise ValueError(f'RESOURCE_LINE_LIMIT line={number} byte={offset}')
            sha.update(raw)
            content = raw.removesuffix(b'\n').removesuffix(b'\r')
            if b'\r' in content or (raw.endswith(b'\r') and not raw.endswith(b'\r\n')):
                raise ValueError(f'UNSUPPORTED_RECORD_TERMINATOR line={number}')
            text = content.decode('utf-8', errors='strict')
            fields = tuple(text.split(PROFILES[family]['delimiter']))
            if number in prefix:
                p = prefix[number]
                if (raw.hex() != p['raw_hex'] or offset != p['byte_offset']
                        or len(raw) != p['byte_length']):
                    raise ValueError(f'PREFIX_MISMATCH line={number}')
                kind = 'HEADER' if number == header_line else 'METADATA'
            else:
                kind = 'DATA'
                if not content or len(fields) != len(binding['expected_header']):
                    raise ValueError(f'INVALID_RECORD_WIDTH line={number} byte={offset}')
            if number == header_line and list(fields) != binding['expected_header']:
                raise ValueError('ORDERED_HEADER_MISMATCH')
            yield RecordOccurrence(binding['source_instance_id'], binding['archive_member'],
                                   number, offset, raw, fields, kind)
            offset += len(raw)
    if number < max(prefix, default=header_line):
        raise ValueError('INCOMPLETE_HEADER_OR_PREAMBLE')
    if offset != binding['uncompressed_bytes'] or sha.hexdigest() != binding['member_sha256']:
        raise ValueError('MEMBER_CHANGED_DURING_READ')
    if file_sha256(path) != binding['raw_sha256']:
        raise ValueError('RAW_CHANGED_DURING_READ')
