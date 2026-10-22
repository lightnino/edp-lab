"""Bounded structural checks never establish business authority."""
import importlib.util
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from edp_lab.agents.structural_evidence import attach_structural_evidence
from edp_lab.profiling.declared_fd import declared_fd
from edp_lab.profiling.source_reader import canonical_hash, read_synthetic
from edp_lab.profiling.tools import candidate_key_scan


def table(raw=b'x,y\na,1\na,1\nb,2\n', null_tokens=()):
    return read_synthetic(raw, delimiter=',', quote=None, null_tokens=null_tokens,
                          expected_header=('x', 'y'))


def test_pass_duplicates_are_occurrences_not_fd_violations_or_keys():
    source = table()
    before = deepcopy(source)
    result = declared_fd(source, ['x'], ['y'])
    assert result['status'] == result['literal_status'] == 'PASS'
    assert result['duplicate_xy_excess'] == 1
    assert result['repeated_determinant_groups'] == 1
    assert result['literal_self_join_pairs'] == 5
    assert result['counterexamples'] == []
    key = candidate_key_scan(source)['candidates'][0]
    assert not key['mechanically_unique_literal']['value']
    assert result['business_fd_status'] == result['business_key_status'] == 'NOT_APPROVED_NOT_ASSESSED'
    assert result['semantic_promotions'] == result['side_effects'] == []
    assert source == before
    assert declared_fd(source, ['x'], ['y']) == result
    assert result['population']['scope'] == 'DECLARED_INPUT_OCCURRENCES_ONLY'


def test_violations_have_actual_distinct_y_and_locators_with_exact_counts():
    source = table(b'x,y\na,1\na,1\na,2\nb,3\nb,4\n')
    result = declared_fd(source, ['x'], ['y'], group_limit=1)
    assert result['status'] == 'VIOLATED'
    assert result['violating_groups'] == 2
    assert result['counterexamples_truncated']
    assert result['duplicate_xy_excess'] == 1
    for group in result['counterexamples']:
        assert len(group['witnesses']) == 2
        assert len({tuple(w['dependent_values']) for w in group['witnesses']}) == 2
        for witness in group['witnesses']:
            i = witness['locator']['source_line'] - 2
            assert [source.rows[i][0]] == group['determinant_values']
            assert [source.rows[i][1]] == witness['dependent_values']


@pytest.mark.parametrize('tokens', [None, ('NULL',), ()])
def test_null_and_blank_semantics_never_silently_exclude_occurrences(tokens):
    source = table(b'x,y\na,\na,NULL\n', null_tokens=tokens)
    result = declared_fd(source, ['x'], ['y'])
    assert result['rows_scanned']['value'] == 2
    assert result['literal_status'] == 'VIOLATED'
    assert result['interpretation_status'] == 'UNRESOLVED'
    assert result['blank_occurrences'] == 1
    assert result['null_or_missing_occurrences'] == (1 if tokens == ('NULL',) else 0)
    consistent = declared_fd(table(b'x,y\na,1\nb,2\n', tokens), ['x'], ['y'])
    assert consistent['status'] == ('AMBIGUOUS' if tokens is None else 'PASS')


def test_missing_and_whitespace_preserved_and_empty_has_no_evidence():
    source = replace(table(), rows=(('a', None), ('a', ' ')),
                     locators=({'source_line': 2}, {'source_line': 3}))
    result = declared_fd(source, ['x'], ['y'])
    assert result['null_or_missing_occurrences'] == result['blank_occurrences'] == 1
    assert result['literal_status'] == 'VIOLATED'
    empty = declared_fd(table(b'x,y\n'), ['x'], ['y'])
    assert empty['status'] == 'NO_EVIDENCE'
    assert empty['literal_self_join_pairs'] == 0


def test_fail_closed_scope_parse_and_invalid_requests():
    blocked = declared_fd(replace(table(), authorization_outcome={'code': 'DENIED'}), ['x'], ['y'])
    assert blocked['status'] == 'BLOCKED'
    assert blocked['rows_scanned']['computation_mode'] == 'NOT_COMPUTED'
    failed = declared_fd(table(b'x,y\na\n'), ['x'], ['y'])
    assert failed['status'] == 'NOT_COMPUTED'
    for x, y in [([], ['y']), (['missing'], ['y']), (['x', 'x'], ['y'])]:
        with pytest.raises(ValueError):
            declared_fd(table(), x, y)
    with pytest.raises(ValueError):
        declared_fd(table(), ['x'], ['y'], group_limit=0)
    with pytest.raises(ValueError, match='ACCOUNTING'):
        declared_fd(replace(table(), locators=()), ['x'], ['y'])


def evaluation():
    path = Path(__file__).resolve().parents[2] / 'scripts/evaluate_declared_fd.py'
    spec = importlib.util.spec_from_file_location('bounded_fd_runner', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate()


def test_real_evidence_composites_and_v1_v2_boundary():
    result = evaluation()
    assert result == evaluation()
    supported, violated = result['supported_fd'], result['violated_fd']
    assert supported['literal_status'] == 'PASS'
    assert supported['status'] == 'AMBIGUOUS'  # unresolved source NULL rules
    assert supported['repeated_determinant_groups'] == 0
    assert violated['literal_status'] == 'VIOLATED'
    assert violated['violating_groups'] == 2
    assert violated['literal_self_join_pairs'] == 13
    keys = {tuple(c['columns']): c for c in result['keys']['candidates']}
    assert keys['adsh',]['mechanically_unique_literal']['value']
    assert not keys['period', 'form']['mechanically_unique_literal']['value']
    assert not keys['adsh', 'period']['mechanically_minimal_literal']['value']
    assert keys['adsh',]['candidate_eligible']['computation_mode'] == 'NOT_COMPUTED'
    useful, unsafe = result['v2_examples']
    assert useful['state'] == 'PROPOSED'
    assert unsafe['state'] == unsafe['candidate_label'] == 'UNRESOLVED'
    assert supported['result_sha256'] in {e.get('result_sha256') for e in useful['supporting_evidence']}
    assert violated['result_sha256'] in {e.get('result_sha256') for e in unsafe['supporting_evidence']}
    assert all(not p['semantic_promotions'] and not p['promotion_eligible']
               for p in result['v2_examples'])
    with pytest.raises(ValueError, match='INVALID_STRUCTURAL'):
        attach_structural_evidence(useful, [{**supported, 'literal_status': 'FAKE'}])
    other = deepcopy(supported)
    other['source'] = {'source_instance_id': 'WRONG'}
    other['result_sha256'] = canonical_hash({k: v for k, v in other.items() if k != 'result_sha256'})
    with pytest.raises(ValueError, match='SOURCE_MISMATCH'):
        attach_structural_evidence(useful, [other])
