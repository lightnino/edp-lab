"""DEC-000010 field-local exception: exact match, no fallback or silent repair."""
import copy
import json
from pathlib import Path

import pytest

from edp_lab.materialization import m1_verifier_v2
from edp_lab.parsers import src010128_v1 as profile
from edp_lab.parsers.c300_reader_v1 import validated_occurrences

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def binding():
    # Original witness is unchanged; opt-in validation uses a new profile ID.
    evidence = ROOT / 'runs/n450/b1-v1/sources/SRC010128.json'
    if not evidence.exists():
        pytest.skip('Local authorized SRC010128 evidence unavailable')
    source = json.loads(evidence.read_bytes())
    value = {**source['descriptor'], 'profile_id': profile.PROFILE}
    value['decoding_provenance'] = profile.provenance(value)
    return value


@pytest.fixture
def row(binding):
    with Path(binding['raw_path']).open('rb') as stream:
        stream.seek(profile.OFFSET)
        return stream.readline()


def test_approved_field_exact_value_roundtrip_and_other_fields(binding, row):
    values = profile.decode_fields(binding, profile.LINE, profile.OFFSET, row)
    assert values[1] == profile.COMPANY
    parts = row[:-1].split(b'|')
    assert [v.encode('iso-8859-1' if i == 1 else 'utf-8')
            for i, v in enumerate(values)] == parts
    assert values[0] == '1538467'  # literal source text, not independently verified CIK
    assert len(values) == 5
    provenance = profile.provenance(binding)
    assert provenance['field_bytes_hex'] == parts[1].hex()
    assert provenance['invalid_byte_absolute_offset'] == 516344


@pytest.mark.parametrize('key,value', [
    ('source_instance_id', 'SRC010127'), ('raw_sha256', '0'*64),
    ('member_sha256', '0'*64), ('profile_id', 'GLOBAL_LATIN1'),
    ('archive_member', 'other'), ('source_family', 'SEC_FSDS'),
    ('uncompressed_bytes', 708189), ('expected_header', ['wrong']),
])
def test_wrong_binding_rejected(binding, row, key, value):
    with pytest.raises(ValueError, match='PROFILE_BINDING_MISMATCH'):
        profile.decode_fields({**binding, key: value}, profile.LINE, profile.OFFSET, row)


@pytest.mark.parametrize('mutate', [
    lambda b: b.replace(b'\xc3O', b'\xc3X'),
    lambda b: b.replace(b'1538467', b'1538468', 1),
    lambda b: b.replace(b'|ADV-NR|', b'|ADV-\xff|'),
    lambda b: b.replace(b'\n', b'\r\n'),
    lambda b: b.replace(b'|ADV-NR|', b'|extra|ADV-NR|'),
])
def test_changed_witness_fails_closed(binding, row, mutate):
    with pytest.raises(ValueError, match='WITNESS_MISMATCH'):
        profile.decode_fields(binding, profile.LINE, profile.OFFSET, mutate(row))


def test_offset_and_line_boundaries_no_fallback(binding, row):
    with pytest.raises(ValueError, match='WITNESS_MISMATCH'):
        profile.decode_fields(binding, profile.LINE, profile.OFFSET+1, row)
    for number in (profile.LINE-1, profile.LINE+1):
        with pytest.raises(UnicodeDecodeError):
            profile.decode_fields(binding, number, profile.OFFSET, row)
    assert profile.decode_fields(binding, 8, 319, '1|日本|f|d|p\n'.encode())[1] == '日本'
    for bad in (b'1|company\xff|f|d|p\n', b'1|company\xc3O|f|d|p\n'):
        with pytest.raises(UnicodeDecodeError):
            profile.decode_fields(binding, 8, 319, bad)


def test_wrong_path_rejected_before_reading(binding):
    bad = {**binding, 'raw_path': '/tmp/unapproved/master.20120104.idx'}
    with pytest.raises(ValueError, match='REGISTERED_IDENTITY_OR_PATH_MISMATCH'):
        next(validated_occurrences(ROOT, bad))
    with pytest.raises(ValueError, match='REGISTERED_IDENTITY_OR_PATH_MISMATCH'):
        m1_verifier_v2.verify_parquet(ROOT, bad, Path('/tmp/nonexistent.parquet'))


def test_original_failure_and_legacy_profile_remain(binding):
    original = copy.deepcopy(binding)
    original['profile_id'] = 'SEC_EDGAR_DAILY_MASTER_C300_PARSER_V1'
    with pytest.raises(UnicodeDecodeError):
        list(validated_occurrences(ROOT, original))
    source = json.loads((ROOT / 'runs/n450/b1-v1/sources/SRC010128.json').read_bytes())
    assert source['classification'] == 'HUMAN_UNRESOLVED'
    assert source['descriptor']['discovery_validation'] == 'FAILED'


def test_full_source_recovery_and_byte_lossless(binding):
    result = profile.profile_source(ROOT, binding)
    assert result['data_records'] == 8530 and result['fields'] == 42650
    assert result['physical_records'] == 8537
    assert result['reconstructed_sha256'] == profile.RAW_SHA


def test_missing_provenance_rejected(binding):
    binding.pop('decoding_provenance')
    with pytest.raises(ValueError, match='DECODING_PROVENANCE_REQUIRED'):
        next(validated_occurrences(ROOT, binding))


def test_native_parquet_lossless_and_tampering(binding, tmp_path):
    import importlib.util

    import pyarrow as pa
    import pyarrow.parquet as pq

    spec = importlib.util.spec_from_file_location(
        'diagnostic_for_recovery_test', ROOT / 'scripts/diagnose_src010128.py')
    diagnostic = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(diagnostic)
    native, _ = diagnostic.retained_native()
    rows = [native.package_record('DEC000010_TEST_ONLY', binding, record)
            for record in validated_occurrences(ROOT, binding)]
    path = tmp_path / 'validation.parquet'
    pq.write_table(pa.Table.from_pylist(rows, schema=native.record_schema()), path)
    result = m1_verifier_v2.verify_parquet(ROOT, binding, path)
    assert result['records_data'] == 8530 and result['fields_data'] == 42650
    assert result['observed_member_sha256'] == profile.RAW_SHA
    # Same STRING schema / DIRECT_MAP packaging, new scoped byte interpretation.
    assert rows[profile.LINE-1]['fields'][1]['lexical_value'] == profile.COMPANY
    for mutation in ('company', 'missing', 'duplicate', 'ordinal', 'locator'):
        bad = copy.deepcopy(rows)
        if mutation == 'company':
            bad[profile.LINE-1]['fields'][1]['lexical_value'] = 'UNAPPROVED'
        elif mutation == 'missing':
            bad.pop(profile.LINE-1)
        elif mutation == 'duplicate':
            bad.insert(profile.LINE-1, copy.deepcopy(bad[profile.LINE-1]))
        elif mutation == 'ordinal':
            bad[profile.LINE-1]['fields'][1]['field_ordinal'] = 3
        else:
            bad[profile.LINE-1]['byte_offset'] += 1
        pq.write_table(pa.Table.from_pylist(bad, schema=native.record_schema()), path)
        with pytest.raises((AssertionError, ValueError)):
            m1_verifier_v2.verify_parquet(ROOT, binding, path)
