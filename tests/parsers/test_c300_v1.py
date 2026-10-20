import io
import zipfile

import pytest

from edp_lab.parsers.c300_v1 import (
    DAILY_HEADER,
    inspect_stream,
    require_activation,
    verify_binding,
)
from edp_lab.profiling.source_reader import canonical_hash, digest


def test_literal_occurrences_and_encoding():
    raw = 'id\tvalue\r\n001\t"NULL"\r\n001\t"NULL"\r\n002\t日本\r\n'.encode()
    result = inspect_stream(io.BytesIO(raw), 'SEC_FSDS')
    assert result['validation'] == 'PASS'
    assert result['data_records'] == 3
    assert result['member_sha256'] == digest(raw)
    assert result['field_width_counts'] == {2: 3}
    assert result['line_endings'] == {'CRLF': 4}
    assert result['prefix_evidence'][0]['byte_offset'] == 0


@pytest.mark.parametrize('raw,code', [
    (b'a\tb\n1\n', 'INVALID_RECORD_WIDTH'),
    (b'a\ta\n1\t2\n', 'INVALID_HEADER'),
    (b'a\tb\n1\t\xff\n', 'codec'),
    (b'\xef\xbb\xbfa\tb\n', 'UTF8_BOM_REJECTED'),
    (b'a\tb\r1\t2\r', 'UNSUPPORTED_RECORD_TERMINATOR'),
    (b'', 'INCOMPLETE_HEADER'),
])
def test_failures_are_explicit(raw, code):
    result = inspect_stream(io.BytesIO(raw), 'SEC_FSDS')
    assert result['validation'] == 'FAILED'
    assert any(code in e for e in result['errors'])


def test_resource_failure_hashes_every_byte():
    raw = b'a\tb\n' + b'x' * 200 + b'\n'
    result = inspect_stream(io.BytesIO(raw), 'SEC_FSDS', max_line=16)
    assert result['scan_scope'] == 'INCOMPLETE'
    assert result['validation'] == 'FAILED'
    assert result['uncompressed_bytes'] == len(raw)
    assert result['member_sha256'] == digest(raw)
    assert result['data_records'] == 0


def daily():
    return ('Description: Daily Index\nLast Data Received: today\nComments: SEC\n'
            'Anonymous FTP: SEC\n \n' + DAILY_HEADER + '\n' + '-' * 80 + '\n'
            '001|Exact name|13F-HR/A|20200101|edgar/data/001/a.txt\n').encode()


def test_daily_metadata_and_header():
    result = inspect_stream(io.BytesIO(daily()), 'SEC_EDGAR_DAILY_MASTER')
    assert result['validation'] == 'PASS'
    assert result['header_line'] == 6
    assert result['data_records'] == 1
    assert result['metadata_records'] == 6
    assert len(result['prefix_evidence']) == 7
    for bad in (daily().replace(b'-' * 80, b'-' * 79),
                daily().replace(b'CIK|Company', b'Issuer|Company'),
                daily().replace(b'Description:', b'Unknown:')):
        assert inspect_stream(io.BytesIO(bad), 'SEC_EDGAR_DAILY_MASTER')['validation'] == 'FAILED'


def test_integrity_gates_and_replay(tmp_path):
    raw = b'a\tb\n001\t"NULL"\n001\t"NULL"\n'
    path = tmp_path / 'input.zip'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('sub.txt', raw)
    evidence = inspect_stream(io.BytesIO(raw), 'SEC_FSDS')
    binding = {'raw_path': 'input.zip', 'raw_sha256': digest(path.read_bytes()),
               'member_sha256': digest(raw), 'archive_member': 'sub.txt',
               'source_family': 'SEC_FSDS', 'expected_header': ['a', 'b'],
               'prefix_evidence': evidence['prefix_evidence'], 'uncompressed_bytes': len(raw)}
    assert verify_binding(tmp_path, binding) == verify_binding(tmp_path, binding)
    with pytest.raises(ValueError, match='MEMBER_SHA256'):
        verify_binding(tmp_path, {**binding, 'member_sha256': '0' * 64})
    with pytest.raises(ValueError, match='RAW_SHA256'):
        verify_binding(tmp_path, {**binding, 'raw_sha256': '0' * 64})
    with pytest.raises(ValueError, match='ORDERED_HEADER'):
        verify_binding(tmp_path, {**binding, 'expected_header': ['b', 'a']})


def test_admission_never_activates_parser():
    registry = {'bindings': [], 'activation': 'INACTIVE_PENDING_HUMAN_APPROVAL'}
    for approval in (None, {}, {'approve_lexical_activation': True},
                     {'registry_fingerprint': canonical_hash(registry)}):
        with pytest.raises(PermissionError):
            require_activation(registry, approval)


def test_occurrence_fidelity_and_byte_locators(tmp_path):
    from edp_lab.parsers.c300_reader_v1 import validated_occurrences

    raw = b'a\tb\r\n001\t"NULL"\r\n001\t"NULL"'
    (tmp_path / 'source.tsv').write_bytes(raw)
    evidence = inspect_stream(io.BytesIO(raw), 'SEC_FSDS')
    binding = {'source_instance_id': 'FIXTURE', 'raw_path': 'source.tsv',
               'raw_sha256': digest(raw), 'member_sha256': digest(raw), 'archive_member': '',
               'source_family': 'SEC_FSDS', 'expected_header': ['a', 'b'],
               'prefix_evidence': evidence['prefix_evidence'], 'uncompressed_bytes': len(raw)}
    records = list(validated_occurrences(tmp_path, binding))
    assert b''.join(r.original_bytes for r in records) == raw
    assert [r.kind for r in records] == ['HEADER', 'DATA', 'DATA']
    assert records[1].fields == records[2].fields == ('001', '"NULL"')
    assert records[1].byte_offset != records[2].byte_offset
    assert [r.source_line for r in records] == [1, 2, 3]
    assert records == list(validated_occurrences(tmp_path, binding))
    assert records[2].byte_offset + len(records[2].original_bytes) == len(raw)


def test_bounded_reader_matches_reviewed_literal_contract(tmp_path):
    from edp_lab.parsers.c300_reader_v1 import validated_occurrences
    from edp_lab.profiling.parser_fidelity import literal_records

    raw = b'id\tvalue\r\n0001\t"NULL"\r\n0001\t"NULL"\r\n+002\t  '
    (tmp_path / 'source.tsv').write_bytes(raw)
    evidence = inspect_stream(io.BytesIO(raw), 'SEC_FSDS')
    binding = {'source_instance_id': 'FIXTURE', 'raw_path': 'source.tsv',
               'raw_sha256': digest(raw), 'member_sha256': digest(raw), 'archive_member': '',
               'source_family': 'SEC_FSDS', 'expected_header': ['id', 'value'], 'footer': None,
               'prefix_evidence': evidence['prefix_evidence'], 'uncompressed_bytes': len(raw)}
    reviewed = list(literal_records(raw, binding, {'delimiter': '\t'}))
    bounded = list(validated_occurrences(tmp_path, binding))
    assert [(r.source_line, r.byte_offset, r.original_bytes, list(r.fields), r.kind)
            for r in bounded] == reviewed
