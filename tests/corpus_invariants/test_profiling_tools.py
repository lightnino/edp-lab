"""Behavioral tests for read-only deterministic profiling tools."""

import json

import pytest

from edp_lab.profiling import tools
from edp_lab.profiling.source_reader import read_synthetic


def fixture(raw=b'a,b\n001,x\n001,x\n001,x\n002,y\n002,y\n003,z\n', *,
            null_tokens=(), header=('a', 'b'), quote=None):
    return read_synthetic(raw, delimiter=',', quote=quote, null_tokens=null_tokens,
                          expected_header=header)


def value(result):
    return result['value']


def test_occurrences_duplicates_and_witnesses():
    table = fixture()
    p = tools.profile_table(table)
    assert value(p['row_count']) == 6
    assert value(p['column_count']) == 2
    assert p['columns'] == [{'name': 'a', 'type': 'TEXT'}, {'name': 'b', 'type': 'TEXT'}]
    d = tools.find_duplicates(table)
    assert value(d['duplicate_groups']) == 2
    assert value(d['rows_in_duplicate_groups']) == 5
    assert value(d['excess_rows']) == 3
    assert d['groups'][0]['values'] == ['001', 'x']
    assert d['groups'][0]['source_record_witnesses'] == [
        {'source_line': i, 'end_line': i} for i in (2, 3, 4)]
    bounded = tools.find_duplicates(table, group_limit=1, witness_limit=1)
    assert bounded['groups_truncated']
    assert value(bounded['duplicate_groups']) == 2
    assert len(table.rows) == 6  # no removal


def test_column_metrics_and_ordering():
    c = tools.profile_column(fixture(), 'a')['statistics']
    assert value(c['unique_count']) == 1
    assert value(c['distinct_non_null_count']) == 3
    assert value(c['distinct_pct']) == .5
    assert value(c['min']) == '001'
    assert value(c['top_values'])[0] == {'value': '001', 'count': 3}
    assert all('computation_mode' in m for m in c.values())


def test_leading_zero_ids_remain_distinct_text():
    table = fixture(b'a,b\n001,x\n1,x\n')
    assert table.rows == (('001', 'x'), ('1', 'x'))
    assert value(tools.profile_column(table, 'a')['literal_statistics']['distinct_text_count']) == 2
    assert value(tools.find_duplicates(table)['duplicate_groups']) == 0


def test_empty_all_null_and_blank():
    empty = fixture(b'a,b\n')
    c = tools.profile_column(empty, 'a')['statistics']
    assert value(c['null_count']) == 0
    assert value(c['null_pct']) is None
    assert value(c['distinct_pct']) is None
    assert value(c['unique_count']) == 0
    assert value(c['min']) is None
    assert not value(tools.candidate_key_scan(empty)['candidates'][0]['candidate_eligible'])
    nulls = fixture(b'a,b\nNULL,\nNULL, \n', null_tokens=('NULL',))
    a = tools.profile_column(nulls, 'a')['statistics']
    assert value(a['null_count']) == 2
    assert value(a['null_pct']) == 1
    assert value(a['distinct_pct']) is None
    assert value(a['unique_count']) == 0
    b = tools.profile_column(nulls, 'b')
    assert value(b['statistics']['non_null_count']) == 2
    assert value(b['literal_statistics']['empty_count']) == 1
    assert value(b['literal_statistics']['whitespace_only_count']) == 1


def test_unknown_nulls_do_not_imply_keys_or_zero():
    table = fixture(b'a,b\n001,\n002,NULL\n', null_tokens=None)
    c = tools.profile_column(table, 'b')
    for name in ('null_count', 'non_null_count', 'null_pct', 'distinct_non_null_count',
                 'unique_count', 'distinct_pct', 'min', 'max', 'top_values'):
        assert c['statistics'][name]['computation_mode'] == 'NOT_COMPUTED'
        assert value(c['statistics'][name]) is None
    assert value(c['literal_statistics']['distinct_text_count']) == 2
    key = tools.candidate_key_scan(table)['candidates'][0]
    assert value(key['mechanically_unique_literal']) is True
    assert key['candidate_eligible']['computation_mode'] == 'NOT_COMPUTED'
    assert key['business_key_status'] == 'NOT_APPROVED_NOT_ASSESSED'


def test_composites_and_minimality():
    table = fixture(b'a,b,c\n1,x,u\n1,y,v\n2,x,w\n2,y,z\n', header=('a', 'b', 'c'))
    scan = tools.candidate_key_scan(table, composites=[('a', 'b', 'c')], max_width=2)
    candidates = {tuple(c['columns']): c for c in scan['candidates']}
    assert not value(candidates['a',]['mechanically_unique_literal'])
    assert value(candidates['a', 'b']['candidate_eligible'])
    assert value(candidates['c',]['candidate_eligible'])
    assert not value(candidates['a', 'b', 'c']['mechanically_minimal_literal'])
    assert not value(candidates['a', 'c']['candidate_eligible'])
    with pytest.raises(ValueError, match='max_combinations'):
        tools.candidate_key_scan(table, max_width=2, max_combinations=3)
    with pytest.raises(ValueError, match='Unknown column'):
        tools.find_duplicates(table, ['unknown'])


def test_explicit_null_disqualifies_unique_column():
    table = fixture(b'a,b\nNULL,x\n001,y\n', null_tokens=('NULL',))
    key = tools.candidate_key_scan(table)['candidates'][0]
    assert value(key['mechanically_unique_literal'])
    assert not value(key['non_null_eligible'])
    assert not value(key['candidate_eligible'])


@pytest.mark.parametrize('raw', [
    b'a,b\nNULL,x\nNULL,y\n1,x\n1,y\n',
    b'a,b\nx,NULL\ny,NULL\nx,1\ny,1\n',
])
@pytest.mark.parametrize('null_tokens', [('NULL',), None])
def test_composite_null_key_eligibility(raw, null_tokens):
    # Explicit tokens apply only to this synthetic fixture, never registered RAW.
    table = fixture(raw, null_tokens=null_tokens)
    scan = tools.candidate_key_scan(table, composites=[('a', 'b')])
    key = next(c for c in scan['candidates'] if c['columns'] == ['a', 'b'])
    assert value(key['mechanically_unique_literal']) is True
    assert value(key['mechanically_minimal_literal']) is True
    for name in ('non_null_eligible', 'candidate_eligible'):
        if null_tokens is None:
            assert key[name]['computation_mode'] == 'NOT_COMPUTED'
            assert value(key[name]) is None
            assert key[name]['reason']
        else:
            assert value(key[name]) is False
            assert key[name]['computation_mode'] == 'EXACT_FULL_SCAN'
    assert key['business_key_status'] == 'NOT_APPROVED_NOT_ASSESSED'


def test_schema_order_and_distribution_separation():
    first = tools.schema_fingerprint(fixture())
    other_distribution = tools.schema_fingerprint(fixture(b'a,b\nx,y\n'))
    reordered = tools.schema_fingerprint(fixture(b'b,a\nx,y\n', header=('b', 'a')))
    renamed = tools.schema_fingerprint(fixture(b'a,c\nx,y\n', header=('a', 'c')))
    assert first['schema_sha256'] == other_distribution['schema_sha256']
    assert first['schema_sha256'] != reordered['schema_sha256']
    assert first['schema_sha256'] != renamed['schema_sha256']
    from edp_lab.profiling.conventions import schema_fingerprint
    assert value(first['schema_sha256']) == schema_fingerprint([('a', 'TEXT'), ('b', 'TEXT')])
    assert schema_fingerprint([('a', 'INTEGER')]) != schema_fingerprint([('a', 'TEXT')])


def test_explicit_quoted_delimiter_and_multiline_locator():
    table = fixture(b'a,b\n001,"x,y"\n002,"line1\nline2"\n', quote='"')
    assert table.parse_status == 'PASS'
    assert table.rows[0] == ('001', 'x,y')
    assert table.rows[1][1] == 'line1\nline2'
    assert table.locators[1] == {'source_line': 3, 'end_line': 4}
    assert fixture(b'a,b\n001,"x,y"\n').parse_status == 'FAIL'


def test_nested_json_field_is_preserved_as_literal_text():
    # This is a text field, not authorization for a JSON source parser or flattening.
    payload = '{"id":"001","nested":{"id":"002","items":[{"id":"003"},null]}}'
    raw = ('a,b\n001,"' + payload.replace('"', '""') + '"\n').encode()
    table = fixture(raw, quote='"', null_tokens=None)
    assert table.parse_status == 'PASS'
    assert table.columns == ('a', 'b')
    assert table.rows == (('001', payload),)
    result = tools.profile_column(table, 'b', sample_size=1)
    assert value(result['literal_statistics']['top_text_values']) == [
        {'value': payload, 'count': 1}]
    assert value(result['statistics']['sample']) == [
        {'literal_value': payload, 'column': 'b',
         'source_record': {'source_line': 2, 'end_line': 2}}]
    assert result['source'] == table.source
    assert result['statistics']['null_count']['computation_mode'] == 'NOT_COMPUTED'


def test_distinct_event_ids_with_equal_payloads_preserve_both_occurrences():
    table = fixture(b'event_id,payload\nEV001,same\nEV002,same\n',
                    header=('event_id', 'payload'), null_tokens=None)
    assert table.parse_status == 'PASS'
    assert table.rows == (('EV001', 'same'), ('EV002', 'same'))
    assert value(tools.profile_table(table)['row_count']) == 2
    assert value(tools.find_duplicates(table)['duplicate_groups']) == 0
    projected = tools.find_duplicates(table, ['payload'])
    assert value(projected['duplicate_groups']) == 1
    assert projected['groups'] == [
        {'values': ['same'], 'frequency': 2, 'source_record_witnesses': [
            {'source_line': 2, 'end_line': 2}, {'source_line': 3, 'end_line': 3}]}]
    assert projected['disposition'] == 'OBSERVATION_ONLY_NO_ERROR_CLASSIFICATION_OR_REMOVAL'
    assert len(table.rows) == 2


@pytest.mark.parametrize('raw', [b'a,b\n1,2\n3\n', b'a,b\n1,"unclosed\n',
                                     b'a,b\n\xff,2\n'])
def test_fail_closed(raw):
    table = fixture(raw, quote='"')
    assert table.parse_status == 'FAIL'
    for call in (tools.profile_table, tools.find_duplicates, tools.candidate_key_scan,
                 tools.schema_fingerprint, lambda t: tools.profile_column(t, 'a')):
        result = call(table)
        assert result['parse_status'] == 'FAIL'
        assert result['errors']
    assert tools.profile_table(table)['row_count']['computation_mode'] == 'NOT_COMPUTED'


def test_deterministic_replay_all_functions():
    one, two = fixture(), fixture()
    for call in (tools.profile_table, tools.find_duplicates, tools.candidate_key_scan,
                 tools.schema_fingerprint, lambda t: tools.profile_column(t, 'a', sample_seed=19)):
        a, b = call(one), call(two)
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
        assert a['result_sha256'] == b['result_sha256']
    samples = tools.profile_column(one, 'a', sample_size=2)['statistics']['sample']
    assert samples['computation_mode'] == 'EXACT_SAMPLE'
    assert len(value(samples)) == 2


def test_registered_reader_hash_gates_and_fidelity(tmp_path, monkeypatch):
    from edp_lab.profiling import source_reader as reader
    raw = b'a,b\n001,x\n'
    table = {'source_instance_id': 'SRC000001', 'logical_table_name': 'fixture.csv',
             'raw_path': 'fixture.csv', 'archive_member': '', 'raw_sha256': reader.digest(raw),
             'member_sha256': reader.digest(raw), 'expected_header': ['a', 'b'],
             'profile_id': 'EXPLICIT', 'footer': None}
    config = {'tables': [table], 'profiles': {'EXPLICIT': {'delimiter': ','}}}
    (tmp_path / 'metadata').mkdir()
    (tmp_path / reader.FREEZE).write_text(json.dumps({
        'effective_configuration': config, 'code_revision': {'file_sha256': {}}}))
    (tmp_path / 'fixture.csv').write_bytes(raw)
    # A directory listing includes retained unauthorized RAW, but read_registered
    # must open only its explicitly selected, pinned table.
    retained = tmp_path / 'outside-universe.csv'
    retained.write_bytes(b'unauthorized,raw\nnever,process\n')
    assert len(list(tmp_path.glob('*.csv'))) == 2
    from edp_lab.ingestion import universe as u
    authority = {'schema': 'SOURCE_UNIVERSE_AUTHORITY_V1', 'universe_version': 'TEST_ONLY',
                 'approval_reference': 'TEST_ONLY', 'inventory_reference': 'inventory',
                 'inventory_sha256': u.sha(b'inventory'), 'member_count': 1,
                 'members': [{'identity': 'SRC000001', 'raw_sha256': reader.digest(raw),
                              'raw_path': 'fixture.csv', 'holdout': False}],
                 'cohorts': {'GOLD_V2': {'identities': ['SRC000001']}}}
    location = tmp_path/u.AUTHORITY_PATH
    location.parent.mkdir(parents=True)
    location.write_text(json.dumps(authority))
    (tmp_path/'inventory').write_bytes(b'inventory')
    monkeypatch.setattr(u, 'APPROVED_AUTHORITY_SHA256', u.sha(location.read_bytes()))
    monkeypatch.setattr(reader, 'load_candidate', lambda root: config)
    monkeypatch.setattr(reader, 'verify_source_identity', lambda *args, **kwargs: None)
    result = reader.read_registered(tmp_path, 'SRC000001', 'fixture.csv', provenance={})
    assert result.parse_status == 'PASS'
    assert result.rows == (('001', 'x'),)
    assert retained.read_bytes() == b'unauthorized,raw\nnever,process\n'
    assert result.locators[0] == {'source_line': 2, 'byte_offset': 4, 'byte_length': 6}
    (tmp_path / 'fixture.csv').write_bytes(b'a,b\n002,y\n')
    def forbidden(*args):
        pytest.fail('Parsing attempted before integrity validation')

    # Keep the real parser for the successful read; failures must never reach it.
    monkeypatch.setattr(reader, 'literal_records', forbidden)
    bad = reader.read_registered(tmp_path, 'SRC000001', 'fixture.csv', provenance={})
    assert bad.parse_status == 'FAIL'
    assert bad.rows == ()
    assert 'RAW_SHA256_MISMATCH' in bad.errors[0]
    (tmp_path / 'fixture.csv').write_bytes(raw)
    monkeypatch.setattr(reader, 'read_member', lambda *args: b'a,b\n003,z\n')
    bad = reader.read_registered(tmp_path, 'SRC000001', 'fixture.csv', provenance={})
    assert bad.parse_status == 'FAIL'
    assert 'MEMBER_SHA256_MISMATCH' in bad.errors[0]
    assert bad.rows == ()
    assert (tmp_path / 'fixture.csv').read_bytes() == raw


def test_failure_before_schema_is_available(tmp_path):
    from edp_lab.profiling.source_reader import read_registered
    table = read_registered(tmp_path, 'SRC000001', 'missing', provenance={})
    for call in (tools.profile_table, tools.find_duplicates, tools.candidate_key_scan,
                 tools.schema_fingerprint, lambda t: tools.profile_column(t, 'unknown')):
        result = call(table)
        assert result['parse_status'] == 'BLOCKED'
        assert not result['errors']
        assert result['authorization_outcome']['code'] == 'AUTHORIZATION_REQUIRED'
        assert result['metrics']['computation_mode'] == 'NOT_COMPUTED'
        assert result['rows_scanned']['computation_mode'] == 'NOT_COMPUTED'
