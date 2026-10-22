"""DEC-000010: one field-local, reversible source interpretation; never a fallback."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.ingestion.universe import UniverseGate
from edp_lab.parsers.c300_v1 import DAILY_HEADER

PROFILE = 'SRC010128_COMPANY_ISO8859_1_V1'
SID = 'SRC010128'
IDENTITY = 'd0dc0ef10dabfaff1d02bb75b5efae1ef047e938418f08fb8cb92c1cb332e7f7'
RAW_SHA = '5869c2d2e76ec56302291d7812add9d8cc1a0b9788478050344e40d14927e71d'
ROW_SHA = '0204d6e8cca1a45efd0ef5956cfe49766ea7ee5a1e3143e3d5a60a7eaa60591a'
LINE, OFFSET, SIZE = 6215, 516310, 708188
COMPANY = 'EXPLORA INVESTIMENTOS GESTÃO DE RECURSOS LTDA'
FIELD_HEX = '4558504c4f524120494e56455354494d454e544f532047455354c34f204445205245435552534f53204c544441'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def check_binding(binding):
    require(binding.get('profile_id') == PROFILE and binding.get('source_instance_id') == SID
            and binding.get('raw_sha256') == RAW_SHA and binding.get('member_sha256') == RAW_SHA
            and binding.get('source_family') == 'SEC_EDGAR_DAILY_MASTER'
            and binding.get('archive_member') == '' and binding.get('uncompressed_bytes') == SIZE
            and binding.get('expected_header') == DAILY_HEADER.split('|'),
            'SRC010128_PROFILE_BINDING_MISMATCH')


def check_scope(root: Path, binding, *, access=None):
    """Check sealed admission, physical location and Universe before opening RAW."""
    from edp_lab.ingestion import n450_authorization as auth

    check_binding(binding)
    require(binding.get('decoding_provenance') == provenance(binding),
            'SRC010128_DECODING_PROVENANCE_REQUIRED')
    if access is not None:
        access.path_for(binding)  # Installed authority, exact registry and remote identity.
        return
    auth.validate_packet(root)
    grant_raw = (root / auth.OWNER_GRANT_PATH).read_bytes()
    require(hashlib.sha256(grant_raw).hexdigest() == auth.OWNER_GRANT_SHA256,
            'INSTALLED_ADMISSION_AUTHORITY_CHANGED')
    grant = json.loads(grant_raw)
    scope = grant['scopes']['admission']
    path = root / scope['destination'] / 'bindings.json'
    require(file_sha256(path) == scope['files_sha256']['bindings.json'], 'ADMITTED_BINDINGS_CHANGED')
    registered = next(r for r in json.loads(path.read_bytes()) if r['source_instance_id'] == SID)
    require(registered['source_identity'] == IDENTITY and all(
        registered[k] == binding[k] for k in ('raw_path', 'raw_sha256')),
        'SRC010128_REGISTERED_IDENTITY_OR_PATH_MISMATCH')
    UniverseGate.load(root).check(IDENTITY, RAW_SHA, binding['raw_path'])
    raw = root / binding['raw_path']
    require(raw.is_file() and not raw.is_symlink() and raw.stat().st_size == SIZE,
            'SRC010128_RAW_LOCATION_OR_SIZE_MISMATCH')


def check_record(binding, number, offset, raw):
    check_binding(binding)
    require(number == LINE and offset == OFFSET and len(raw) == 114
            and hashlib.sha256(raw).hexdigest() == ROW_SHA and raw.endswith(b'\n')
            and raw[34:36] == b'\xc3O' and offset + 34 == 516344,
            'SRC010128_EXCEPTION_WITNESS_MISMATCH')
    parts = raw[:-1].split(b'|')
    require(len(parts) == 5 and parts[1].hex() == FIELD_HEX,
            'SRC010128_COMPANY_BYTES_MISMATCH')
    return parts


def decode_fields(binding, number, offset, raw):
    """Only the exact approved field uses Latin-1; everything else stays strict UTF-8."""
    check_binding(binding)
    if number != LINE:
        return tuple(raw.removesuffix(b'\n').removesuffix(b'\r').decode('utf-8').split('|'))
    parts = check_record(binding, number, offset, raw)
    values = tuple(p.decode('iso-8859-1' if i == 1 else 'utf-8', errors='strict')
                   for i, p in enumerate(parts))
    require(values[1] == COMPANY and values[1].encode('iso-8859-1') == parts[1],
            'SRC010128_FIELD_REVERSIBILITY_FAILED')
    return values


def provenance(binding):
    check_binding(binding)
    return {'profile_id': PROFILE, 'decision': 'DEC-000010', 'source_instance_id': SID,
            'source_identity': IDENTITY, 'raw_sha256': RAW_SHA, 'source_line': LINE,
            'record_byte_offset': OFFSET, 'record_bytes': 114, 'record_sha256': ROW_SHA,
            'field_ordinal': 2, 'original_name': 'Company Name', 'field_bytes_hex': FIELD_HEX,
            'invalid_byte_absolute_offset': 516344, 'encoding': 'iso-8859-1',
            'scope': 'Only this exact field; other fields/records remain strict UTF-8',
            'decision_reference': 'docs/src010128_encoding_exception.md',
            'original_finding': 'metadata/evaluations/n450_b1_v1.json'}


def profile_source(root: Path, binding):
    """Full structural/lexical validation using the same reader as CLEAN packaging."""
    from collections import Counter

    from edp_lab.parsers.c300_reader_v1 import validated_occurrences

    check_binding(binding)
    counts, widths = Counter(), Counter()
    rebuilt = hashlib.sha256()
    for record in validated_occurrences(root, binding):
        counts[record.kind] += 1
        ending = record.original_bytes[len(record.original_bytes.removesuffix(b'\n')
                                          .removesuffix(b'\r')):]
        if record.kind == 'DATA':
            parts = [value.encode('iso-8859-1' if record.source_line == LINE and i == 1
                                  else 'utf-8', errors='strict')
                     for i, value in enumerate(record.fields)]
            require(b'|'.join(parts) + ending == record.original_bytes,
                    'LEXICAL_BYTE_RECONSTRUCTION_FAILED')
            widths[len(record.fields)] += 1
        rebuilt.update(record.original_bytes)
    require(counts == {'METADATA': 6, 'HEADER': 1, 'DATA': 8530}
            and widths == {5: 8530} and rebuilt.hexdigest() == RAW_SHA,
            'SRC010128_FULL_SOURCE_ACCOUNTING_FAILED')
    return {'validation': 'PASS', 'profile_id': PROFILE, 'physical_records': sum(counts.values()),
            'record_kinds': dict(counts), 'data_records': counts['DATA'], 'fields': 42650,
            'widths': dict(widths), 'reconstructed_sha256': rebuilt.hexdigest(),
            'lexical_byte_roundtrip': 'PASS', 'encoding_exception': provenance(binding)}
