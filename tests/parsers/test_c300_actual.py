"""Local actual-input evidence checks; artifacts intentionally remain gitignored."""
import json
from collections import Counter
from pathlib import Path

import pytest

from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.parsers.c300_v1 import roster
from edp_lab.profiling.source_reader import canonical_hash

ROOT = Path(__file__).resolve().parents[2]
DISCOVERY = ROOT / 'runs/section-2-6/discovery-v1'
VALIDATION = ROOT / 'runs/section-2-6/validation-v1/validation-and-approval.json'


@pytest.mark.skipif(not VALIDATION.exists(), reason='Local C300 §2.6 evidence unavailable')
def test_actual_c300_parser_coverage():
    inventory = json.loads((DISCOVERY / 'inventory.json').read_bytes())
    registry = json.loads((DISCOVERY / 'bindings.proposed.json').read_bytes())
    packet = json.loads(VALIDATION.read_bytes())
    rows = roster(ROOT)
    assert [r['source_instance_id'] for r in rows] == [
        r['source_instance_id'] for r in inventory['instances']]
    assert Counter(r['source_family'] for r in rows) == {
        'SEC_FSDS': 60, 'SEC_13F': 42, 'SEC_EDGAR_DAILY_MASTER': 198}
    assert registry['inventory_sha256'] == file_sha256(DISCOVERY / 'inventory.json')
    assert packet['registry_sha256'] == file_sha256(DISCOVERY / 'bindings.proposed.json')
    assert packet['registry_fingerprint'] == canonical_hash(registry)
    assert registry['parser_code_sha256'] == file_sha256(
        ROOT / 'src/edp_lab/parsers/c300_v1.py')
    expected = {(i['source_instance_id'], m['archive_member'])
                for i in inventory['instances'] for m in i['members'] if m['kind'] == 'TABLE'}
    bound = {(b['source_instance_id'], b['archive_member']) for b in registry['bindings']}
    validated = {(t['source_instance_id'], t['source']['archive_member']) for t in packet['tables']}
    assert expected == bound == validated
    assert len(expected) == len(registry['bindings']) == len(packet['tables'])
    assert len(packet['instances']) == 300
    assert all(i['logical_tables'] > 0 for i in packet['instances'])
    discovery_status = {(b['source_instance_id'], b['archive_member']):
                        b['discovery_validation'] for b in registry['bindings']}
    assert all(t['validation'] == discovery_status[
        t['source_instance_id'], t['source']['archive_member']] for t in packet['tables'])
    failed = [t for t in packet['tables'] if t['validation'] == 'FAILED']
    assert len(failed) == 12
    assert all(t['logical_table_name'] == 'num.txt' and
               t['inspection']['first_error_locator'] for t in failed)
    assert all(t['activation'] == t['agent_execution'] == 'BLOCKED' for t in packet['tables'])
    assert registry['activation'] == 'INACTIVE_PENDING_HUMAN_APPROVAL'
    discovered = {(i['source_instance_id'], m['archive_member']): m
                  for i in inventory['instances'] for m in i['members'] if m['kind'] == 'TABLE'}
    for table in packet['tables']:
        expected = discovered[table['source_instance_id'], table['source']['archive_member']]
        assert table['inspection'] == {k: expected[k] for k in table['inspection']}


@pytest.mark.skipif(not VALIDATION.exists(), reason='Local C300 §2.6 evidence unavailable')
def test_actual_occurrence_reader_by_family():
    import hashlib

    from edp_lab.parsers.c300_reader_v1 import validated_occurrences

    registry = json.loads((DISCOVERY / 'bindings.proposed.json').read_bytes())
    for family in ('SEC_FSDS', 'SEC_13F', 'SEC_EDGAR_DAILY_MASTER'):
        binding = min((b for b in registry['bindings'] if b['source_family'] == family
                       and b['discovery_validation'] == 'PASS'),
                      key=lambda b: b['uncompressed_bytes'])
        sha = hashlib.sha256()
        offset = 0
        for record in validated_occurrences(ROOT, binding):
            assert record.byte_offset == offset
            assert record.source_instance_id == binding['source_instance_id']
            assert record.archive_member == binding['archive_member']
            sha.update(record.original_bytes)
            offset += len(record.original_bytes)
            if record.kind == 'DATA':
                assert len(record.fields) == len(binding['expected_header'])
        assert sha.hexdigest() == binding['member_sha256']
        assert offset == binding['uncompressed_bytes']
