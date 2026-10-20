"""Local bytes never imply an independently evidenced publisher archive edition."""

import hashlib
import json

import pytest

from edp_lab.ingestion.local_sources import local_match, move_existing, verify_representation


def representation(path, raw=b'original'):
    path.write_bytes(raw)
    return {'kind': 'FILE', 'path': str(path), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(), 'availability': 'VERIFIED'}


def test_existing_destination_is_reused_without_touching_original(tmp_path):
    source, target = tmp_path / 'source', tmp_path / 'target'
    source.write_bytes(b'original')
    record = representation(target)
    assert move_existing(source, target, expected_sha256=record['sha256'])[
        'action'] == 'REUSED_DESTINATION'
    assert source.read_bytes() == target.read_bytes() == b'original'
    with pytest.raises(ValueError, match='already exists'):
        move_existing(source, target, expected_sha256='0' * 64)


def test_local_edition_unknown_stops_duplicate_network_work(tmp_path):
    record = representation(tmp_path / 'local.zip')
    inventory = {'datasets': [{'dataset_id': 'existing', 'family': 'SEC_FSDS',
                              'edition_label': '2011Q1', 'representations': [record]}]}
    candidate = {'family': 'SEC_FSDS', 'edition': '2011Q1', 'url': 'https://example.invalid/a'}
    with pytest.raises(ValueError, match='no duplicate download'):
        local_match(candidate, inventory)
    candidate['expected_sha256'] = record['sha256']
    assert local_match(candidate, inventory)['representation'] == record
    candidate['expected_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='separate candidate evidence'):
        local_match(candidate, inventory)
    candidate['publisher_edition_evidence'] = {'receipt': 'new independently captured edition'}
    assert local_match(candidate, inventory) is None
    record_path = tmp_path / 'local.zip'
    record_path.write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed or missing'):
        local_match(candidate, inventory)


def test_directory_has_child_hashes_not_an_invented_archive_hash(tmp_path):
    folder = tmp_path / 'extracted'
    folder.mkdir()
    item = representation(folder / '001.json', b'{"id":"001"}')
    index = tmp_path / 'files.jsonl'
    index.write_text(json.dumps({'relative_path': '001.json', 'bytes': item['bytes'],
                                 'sha256': item['sha256']}) + '\n')
    record = {'kind': 'EXTRACTED_DIRECTORY', 'path': str(folder), 'bytes': item['bytes'],
              'file_count': 1, 'inventory_path': str(index),
              'inventory_sha256': hashlib.sha256(index.read_bytes()).hexdigest()}
    verify_representation(record)
    (folder / 'unaccounted.json').write_bytes(b'{}')
    with pytest.raises(ValueError, match='population mismatch'):
        verify_representation(record)


def test_changed_source_cannot_be_moved(tmp_path):
    source = tmp_path / 'source'
    source.write_bytes(b'changed')
    with pytest.raises(ValueError, match='Source changed'):
        move_existing(source, tmp_path / 'target', expected_sha256='0' * 64)
    assert source.exists()
    assert not (tmp_path / 'target').exists()
