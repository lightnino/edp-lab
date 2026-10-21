"""Diagnostic codecs must not silently become M1 text parsing policies."""
import importlib.util
from pathlib import Path

import pyarrow as pa
import pytest

from edp_lab.ingestion.universe import sha

spec = importlib.util.spec_from_file_location(
    'encoding_diagnosis', Path(__file__).resolve().parents[2] / 'scripts/diagnose_src010128.py')
diagnosis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnosis)


@pytest.mark.parametrize('value', [b'\xc3O', b'\xc3', b'\x80', b'\xff', b'\xc0\xaf'])
def test_invalid_bytes_located_and_reconstructed_without_adoption(value):
    raw = b'header\n' * 7 + b'123|' + value + b'|form|date|path\n'
    result = diagnosis.inspect_bytes(raw)
    error = result['all_utf8_errors'][0]
    assert error['line'] == 8
    assert error['line_start'] == 49
    assert error['invalid_absolute_offset'] == 53
    assert error['field_ordinal'] == 2
    assert result['data_widths'] == {5: 1}
    assert result['field_positions'] == 5
    assert result['line_terminators'] == {'LF': 8}
    candidate = result['counterfactual_codecs']
    assert candidate['status'] == 'DIAGNOSTIC_ONLY_NOT_ADOPTED'
    assert set(candidate['reconstructed_hashes'].values()) == {sha(raw)}
    assert candidate['source_charset_and_character_meaning'] == 'UNRESOLVED'


@pytest.mark.parametrize('raw', [b'', b'ascii\n', 'literal Ã\r\n'.encode()])
def test_utf8_controls_have_no_false_error(raw):
    assert diagnosis.inspect_bytes(raw)['all_utf8_errors'] == []


def test_reversible_surrogates_are_not_clean_string_values():
    raw = b'company\xc3O'
    value = raw.decode('utf-8', errors='surrogateescape')
    assert value.encode('utf-8', errors='surrogateescape') == raw
    with pytest.raises((UnicodeEncodeError, pa.ArrowInvalid)):
        pa.array([value], type=pa.string())


def test_actual_frozen_native_value_oracle(tmp_path):
    native, _ = diagnosis.retained_native()  # verifies frozen code and manifest hashes
    good, bad = tmp_path / 'good', tmp_path / 'bad'
    good.mkdir()
    bad.mkdir()
    result = diagnosis.native_fixture_check(native, good, invalid=False)
    assert result  # duplicate records and UTF-8 values pass actual native readback
    with pytest.raises(UnicodeDecodeError):
        diagnosis.native_fixture_check(native, bad, invalid=True)
