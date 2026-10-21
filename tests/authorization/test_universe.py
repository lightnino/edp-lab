"""Synthetic authority fixtures exercise controls; never approve actual sources."""
import json
from dataclasses import asdict, replace

import pytest

from edp_lab.agents.analyst_v0 import observe
from edp_lab.ingestion import universe as u
from edp_lab.ingestion.c300_admission import freeze, prepare, verify_registry
from edp_lab.profiling.source_reader import read_synthetic
from edp_lab.tool_adapters.profiling import Authorization, ProfilingAdapters, ToolRequest


def authority(version='test-v1', extra=False):
    members = [{'identity': 'original', 'raw_sha256': 'a'*64, 'raw_path': 'raw/original', 'holdout': False},
               {'identity': 'reserved', 'raw_sha256': 'b'*64, 'raw_path': 'raw/reserved', 'holdout': True},
               {'identity': 'daily', 'raw_sha256': 'c'*64, 'raw_path': 'raw/daily', 'holdout': False}]
    if extra:
        members.append({'identity': 'treasury-new', 'raw_sha256': 'd'*64,
                            'raw_path': 'raw/treasury-new', 'holdout': False})
    return {'schema': 'SOURCE_UNIVERSE_AUTHORITY_V1', 'universe_version': version,
                'approval_reference': 'TEST-ONLY-HUMAN-DECISION', 'inventory_reference': 'inventory.csv',
                'inventory_sha256': u.sha(b'test inventory'), 'member_count': len(members), 'members': members,
                'cohorts': {'GOLD_V2': {'identities': ['original']},
                         'future': {'identities': [m['identity'] for m in members]}}}


def gate(doc=None):
    raw = json.dumps(doc or authority()).encode()
    return u.UniverseGate(raw, u.sha(raw))


@pytest.mark.parametrize('identity,digest,path,cohort,reason', [
    ('external', 'd'*64, 'raw/external', None, 'NOT_IN_APPROVED_UNIVERSE'),
    ('treasury-new', 'd'*64, 'raw/treasury-new', None, 'NOT_IN_APPROVED_UNIVERSE'),
    ('reserved', 'b'*64, 'raw/reserved', None, 'RESERVED_HOLDOUT'),
    ('daily', 'c'*64, 'raw/daily', 'GOLD_V2', 'NOT_IN_PINNED_COHORT'),
    ('original', 'e'*64, 'raw/original', None, 'IDENTITY_EVIDENCE_MISMATCH'),
])
def test_denials(identity, digest, path, cohort, reason):
    with pytest.raises(u.ScopeDenied) as exc:
        gate().check(identity, digest, path, cohort=cohort)
    assert exc.value.outcome['reason'] == reason
    assert exc.value.outcome['status'] == 'OUT_OF_SCOPE'
    assert exc.value.outcome['route'] == 'Human Review'


def test_authorized_member_and_future_version():
    old = gate()
    assert old.check('original', 'a'*64, 'raw/original')['universe_version'] == 'test-v1'
    future = gate(authority('test-v2', extra=True))
    assert future.check('treasury-new', 'd'*64, 'raw/treasury-new', cohort='future')
    with pytest.raises(u.ScopeDenied):
        old.check('treasury-new', 'd'*64, 'raw/treasury-new')
    with pytest.raises(u.ScopeDenied):
        future.check('original', 'a'*64, 'raw/original', version='test-v1')
    assert old == gate()


@pytest.mark.parametrize('operation', ['prepare', 'freeze', 'registry', 'processing'])
def test_real_entrypoints_missing_authority(tmp_path, operation):
    with pytest.raises(u.ScopeDenied, match='MISSING_HOST_AUTHORITY'):
        if operation == 'prepare':
            prepare(tmp_path, tmp_path/'output')
        elif operation == 'freeze':
            freeze(tmp_path, tmp_path/'absent', tmp_path/'self-approval', tmp_path/'output')
        elif operation == 'registry':
            verify_registry(tmp_path, tmp_path/'absent')
        else:
            u.processing(tmp_path, {'source_instance_id': 'original', 'raw_sha256': 'a'*64,
                                        'raw_path': 'raw/original'}, 'GOLD_V2')
    assert not (tmp_path/'output').exists()


def test_manifest_and_inventory_pins(tmp_path, monkeypatch):
    location = tmp_path/u.AUTHORITY_PATH
    location.parent.mkdir(parents=True)
    location.write_bytes(gate().authority)
    with pytest.raises(u.ScopeDenied, match='AUTHORITY_PIN_MISMATCH'):
        u.UniverseGate.load(tmp_path).document()
    monkeypatch.setattr(u, 'APPROVED_AUTHORITY_SHA256', u.sha(location.read_bytes()))
    with pytest.raises(u.ScopeDenied, match='MISSING_INVENTORY'):
        u.UniverseGate.load(tmp_path).verify_inventory(tmp_path)
    (tmp_path/'inventory.csv').write_bytes(b'test inventory')
    u.UniverseGate.load(tmp_path).verify_inventory(tmp_path)
    (tmp_path/'inventory.csv').write_bytes(b'changed')
    with pytest.raises(u.ScopeDenied, match='INVENTORY_HASH_MISMATCH'):
        u.UniverseGate.load(tmp_path).verify_inventory(tmp_path)
    location.write_bytes(location.read_bytes()+b' ')
    with pytest.raises(u.ScopeDenied, match='AUTHORITY_PIN_MISMATCH'):
        u.UniverseGate.load(tmp_path).document()


def host(identity='original'):
    table = read_synthetic(b'x\n1\n', delimiter=',', quote=None, null_tokens=None,
                           expected_header=('x',), provenance={})
    table = replace(table, source={'source_instance_id': identity, 'raw_sha256': 'a'*64,
                                       'raw_path': 'raw/original'})
    return ProfilingAdapters({'binding': table}, {'agent': {'binding'}}, universe_gate=gate())


def test_agent_denial_survives_report():
    report = observe(host('external'), 'binding', 'agent', ('x',))
    assert report['execution_status'] == 'BLOCKED'
    assert all(step['response']['approval_required'] for step in report['trace'])
    assert any('Human Review' in q for q in report['unresolved_questions'])
    assert report['side_effects'] == []


@pytest.mark.parametrize('field,value', [('universe_version', 'self-approved'),
                                        ('approval', True), ('cohort', 'future')])
def test_agent_cannot_supply_scope(field, value):
    adapter = host()
    request = asdict(ToolRequest('profile_table', adapter.source_ref('binding'),
                                Authorization('agent')))
    request[field] = value
    response = adapter.invoke(request)
    assert response.status == 'BLOCKED' and response.approval_required
    assert response.result is None
    # Denial cannot mutate host scope; normal approved request still works.
    assert adapter.invoke(ToolRequest('profile_table', adapter.source_ref('binding'),
                                     Authorization('agent'))).result is not None


@pytest.mark.parametrize('point', ['N450/N750/N500 admission and freeze',
                                  'historical upload and targeted profiling',
                                  'Databricks remote processing',
                                  'future Agent onboarding/release evaluation'])
def test_missing_baseline_integration(point):
    pytest.skip('BLOCKED/PENDING: no rebuilt/current entrypoint: ' + point)


def test_actual_reader_reports_scope_not_parser_failure(tmp_path):
    from edp_lab.profiling.source_reader import read_registered
    table = read_registered(tmp_path, 'original', 'table', provenance={})
    assert table.parse_status == 'BLOCKED'
    assert table.authorization_outcome['code'] == 'AUTHORIZATION_REQUIRED'
    assert not table.rows and not table.errors


def test_c300_read_and_inspect_block_before_parser_or_raw(tmp_path):
    from edp_lab.agents.c300_shallow_v0 import inspect
    from edp_lab.parsers.c300_reader_v1 import occurrences
    binding = {'source_instance_id': 'original', 'raw_sha256': 'a'*64, 'raw_path': 'raw/original'}
    with pytest.raises(u.ScopeDenied):
        next(occurrences(tmp_path, {}, binding, {}))
    with pytest.raises(u.ScopeDenied):
        inspect(tmp_path, {'bindings': [binding]}, {'approved': True})


def test_actual_processing_with_host_pinned_test_evidence(tmp_path, monkeypatch):
    location = tmp_path/u.AUTHORITY_PATH
    location.parent.mkdir(parents=True)
    location.write_bytes(gate().authority)
    (tmp_path/'inventory.csv').write_bytes(b'test inventory')
    monkeypatch.setattr(u, 'APPROVED_AUTHORITY_SHA256', u.sha(location.read_bytes()))
    binding = {'source_instance_id': 'original', 'raw_sha256': 'a'*64, 'raw_path': 'raw/original'}
    assert u.processing(tmp_path, binding, 'GOLD_V2')['identity'] == 'original'
    binding.update(source_instance_id='daily', raw_sha256='c'*64, raw_path='raw/daily')
    with pytest.raises(u.ScopeDenied, match='NOT_IN_PINNED_COHORT'):
        u.processing(tmp_path, binding, 'GOLD_V2')


def test_explicit_delivery_registration_crosswalk_only():
    doc = authority()
    doc['members'][0]['bindings'] = [{'identity': 'SRC_TEST', 'raw_path': 'registered/raw'}]
    assert gate(doc).check('SRC_TEST', 'a'*64, 'registered/raw')
    with pytest.raises(u.ScopeDenied):
        gate(doc).check('SRC_TEST', 'a'*64, 'raw/original')
    doc['members'][0]['bindings'].append({'identity': 'daily', 'raw_path': 'other'})
    with pytest.raises(u.ScopeDenied, match='INVALID_AUTHORITY'):
        gate(doc).document()
