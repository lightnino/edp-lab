"""Read-only observation boundaries and literal fidelity; no installed grants changed."""
import importlib.util
from pathlib import Path

import pytest

from edp_lab.ingestion.universe import ScopeDenied, sha
from edp_lab.parsers.c300_v1 import DAILY_HEADER

spec = importlib.util.spec_from_file_location(
    'n450_observation', Path(__file__).resolve().parents[2] / 'scripts/observe_n450_b1.py')
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


def fixture(tmp_path, raw):
    path = tmp_path / 'source.idx'
    path.write_bytes(raw)
    row = {'source_instance_id': 'FIXTURE', 'raw_path': str(path),
           'raw_sha256': sha(raw), 'source_family': observer.FAMILY}
    physical = {'source_identity': 'TEST_ONLY', 'bytes': len(raw)}
    return row, physical


def daily():
    framing = ('Description: Daily Index\nLast Data Received: today\nComments: SEC\n'
               'Anonymous FTP: SEC\n \n' + DAILY_HEADER + '\n' + '-' * 80 + '\n')
    record = '000123|"NULL" 日本|13F-HR/A|2020-01-01|edgar/data/example.txt\n'
    return (framing + record + record).encode()


def test_literal_observation_preserves_duplicates_and_locators(tmp_path):
    row, physical = fixture(tmp_path, daily())
    result = observer.observe(row, physical, tuple(DAILY_HEADER.split('|')))
    assert result['classification'] == 'FITS_EXISTING_MODEL'
    check, values, locators = observer.occurrence_check(result['descriptor'], 2, collect=True)
    assert check['accounting'] == {'METADATA': 6, 'HEADER': 1, 'DATA': 2}
    assert check['data_fields'] == 10
    assert values[0] == values[1]
    assert values[0][0] == '000123' and values[0][1] == '"NULL" 日本'
    assert locators[0]['byte_offset'] != locators[1]['byte_offset']


def test_unsupported_width_held_without_model_invention(tmp_path):
    row, physical = fixture(tmp_path, daily().replace(b'000123|', b'000123|extra|', 1))
    result = observer.observe(row, physical, tuple(DAILY_HEADER.split('|')))
    assert result['classification'] == 'HUMAN_UNRESOLVED'
    assert any('INVALID_RECORD_WIDTH' in error for error in result['errors'])


def test_changed_raw_rejected_before_inspection(tmp_path):
    row, physical = fixture(tmp_path, daily())
    Path(row['raw_path']).write_bytes(b'changed')
    with pytest.raises(ScopeDenied, match='N450_RAW_INTEGRITY_MISMATCH'):
        observer.observe(row, physical, tuple(DAILY_HEADER.split('|')))


def test_missing_host_evidence_blocks_before_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(observer, 'ROOT', tmp_path)
    monkeypatch.setattr(observer, 'OUT', tmp_path / 'runs/forbidden')
    with pytest.raises(ScopeDenied, match='MISSING_HOST_AUTHORITY'):
        observer.main()
    assert not (tmp_path / 'runs').exists()


def test_undecodable_daily_binding_is_held(tmp_path):
    raw = daily().replace('"NULL" 日本'.encode(), b'name\xc3X')
    row, physical = fixture(tmp_path, raw)
    result = observer.observe(row, physical, tuple(DAILY_HEADER.split('|')))
    assert result['classification'] == 'HUMAN_UNRESOLVED'
    assert result['structure']['encoding'] == 'UNRESOLVED'
    assert result['structure']['scan_scope'] == 'FULL_BYTES'
    assert result['structure']['member_sha256'] == row['raw_sha256']
    assert result['structure']['first_error_locator']['source_line'] == 8
    assert any('invalid continuation byte' in error for error in result['errors'])
