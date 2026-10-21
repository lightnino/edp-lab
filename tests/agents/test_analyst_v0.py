from copy import deepcopy

import pytest
from conftest import authorized_host

from edp_lab.agents.analyst_v0 import observe, validate_report
from edp_lab.agents.checkpoint_v0 import evaluate
from edp_lab.profiling.source_reader import read_synthetic


def fixture_table():
    return read_synthetic(b'id\tvalue\n001\tNULL\n001\tNULL\n002\t\n', delimiter='\t',
                          quote=None, null_tokens=None, expected_header=('id', 'value'),
                          provenance={'test': 'fixed'})


def test_agent_independent_expectations_replay_and_provenance():
    table = fixture_table()
    host = authorized_host({'test': table}, {'reader': {'test'}})
    before = deepcopy(table)
    report = observe(host, 'test', 'reader', table.columns)
    assert validate_report(report)
    assert report == observe(host, 'test', 'reader', table.columns)
    assert report['execution_status'] == 'PASS'
    assert report['tool_statuses'] == ['PARTIAL', 'SUCCESS']
    assert {s['request']['tool'] for s in report['trace']} == {
        'profile_table', 'profile_column', 'schema_fingerprint',
        'find_duplicates', 'candidate_key_scan'}
    assert evaluate(host, report, table)['status'] == 'PASS'
    assert table == before
    assert report['semantic_promotions'] == report['side_effects'] == []
    assert report['unresolved_questions']
    for step in report['trace']:
        assert step['response']['evidence_refs']['source'] == table.source


def test_denied_authority_and_tampered_report():
    table = fixture_table()
    host = authorized_host({'test': table}, {})
    report = observe(host, 'test', 'reader', table.columns)
    assert report['execution_status'] == 'BLOCKED'
    assert all(s['response']['result'] is None for s in report['trace'])
    assert all(s['response']['approval_required'] for s in report['trace'])
    report['findings'][0]['state'] = 'APPROVED'
    with pytest.raises(ValueError):
        validate_report(report)


def test_malformed_source_is_not_completed_population():
    table = read_synthetic(b'id\tvalue\n1\t2\nmalformed\n', delimiter='\t', quote=None,
                           null_tokens=None, expected_header=('id', 'value'), provenance={})
    host = authorized_host({'bad': table}, {'reader': {'bad'}})
    report = observe(host, 'bad', 'reader', table.columns)
    assert report['execution_status'] == 'FAILED'
    assert report['tool_statuses'] == ['PARTIAL']
    assert report['errors']


def test_c300_shallow_denies_before_opening_sources(tmp_path):
    from edp_lab.agents.c300_shallow_v0 import inspect

    with pytest.raises(PermissionError, match='SCOPED_HUMAN_APPROVAL'):
        inspect(tmp_path, {'bindings': []}, None)


def test_agent_does_not_write_files_or_open_network(monkeypatch):
    import socket
    from pathlib import Path

    table = fixture_table()
    host = authorized_host({'test': table}, {'reader': {'test'}})

    def forbidden(*args, **kwargs):
        raise AssertionError('unexpected side effect')

    monkeypatch.setattr(Path, 'write_text', forbidden)
    monkeypatch.setattr(Path, 'write_bytes', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    assert observe(host, 'test', 'reader', table.columns)['execution_status'] == 'PASS'
