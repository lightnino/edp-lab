"""Bounded read-only candidate checks over explicitly paired source observations.

No SDK, source discovery, canonical store, persistence or promotion capability.
Labels are NOT an input; context checks answer the host's exact bounded question.
"""
from copy import deepcopy

from edp_lab.agents.analyst_v0 import STATES
from edp_lab.profiling.source_reader import canonical_hash

VERSION = 'EDP_CANDIDATE_AGENT_V2_BOUNDED_V1'
QUESTIONS = {'typed_projection', 'identifier_storage_slot', 'same_period_text',
             'same_measure', 'same_native_identifier', 'same_occurrence', 'canonical_entity'}
CASE_KEYS = {'id', 'dimension', 'question', 'left', 'right', 'review_required'}
REPORT_KEYS = {
    'agent_version', 'case_id', 'dimension', 'question', 'source_field', 'candidate_target',
    'required_transformation', 'compatibility', 'supporting_evidence', 'conflicting_evidence',
    'name_only_baseline_label', 'candidate_label', 'state', 'reason', 'validation_scope',
    'human_review_required', 'review_question', 'alternatives', 'consequences', 'side_effects',
    'semantic_promotions', 'promotion_eligible', 'input_fingerprint', 'result_fingerprint',
}


def _compatibility(left, right):
    def literal(key):
        a, b = left[key], right[key]
        if not a or not b or 'UNDECLARED' in (a, b):
            return 'UNRESOLVED'
        return 'LITERAL_EQUAL' if a == b else 'LITERAL_DIFFERENT'
    return {key: literal(key) for key in ('unit', 'grain', 'time')}


def _check(case):
    a, b, question = case['left'], case['right'], case['question']
    if question == 'canonical_entity':
        return 'UNRESOLVED', 'No independently approved canonical or temporal equivalence rule'
    if question == 'same_native_identifier':
        if not a['value'] or not b['value']:
            return 'UNRESOLVED', 'Blank tokens cannot establish identifier identity'
        if not a['namespace'] or not b['namespace']:
            return 'UNRESOLVED', 'Identifier namespace not supplied'
        if a['namespace'] != b['namespace']:
            return 'NON_MATCH', 'Identifier namespaces differ'
        return ('MATCH', 'Exact nonempty namespaced token observation only') if (
            a['value'] == b['value']) else ('NON_MATCH', 'Distinct source-native tokens')
    if question == 'same_occurrence':
        return ('MATCH', 'Same supplied technical occurrence locator') if (
            a['occurrence'] == b['occurrence']) else (
                'NON_MATCH', 'Different technical occurrences; shared tokens do not deduplicate them')
    if question == 'identifier_storage_slot':
        if a['field'].casefold() == b['field'].casefold() == 'cik' and (
                a['namespace'] == b['namespace'] == 'SEC_CIK'):
            return 'MATCH', 'Namespaced TEXT slot candidate; preserve distinct values and entity roles'
        return 'UNRESOLVED', 'No bounded field-alias evidence'
    if question == 'same_period_text':
        if a['role'] != b['role'] or a['time'] != b['time']:
            return 'NON_MATCH', 'Different supplied date roles or literal period contexts'
        if a['occurrence'] == b['occurrence'] and a['value'] == b['value']:
            return 'MATCH', 'Same native filing token and literal source-reported period text'
        return 'UNRESOLVED', 'No source-native shared filing/period witness'
    if question == 'typed_projection':
        if (b.get('origin') == 'approved_contract_target' and b['field'] == 'value_decimal'
                and b['namespace'] == 'M2_ADDITIVE_TYPED_NUMERIC_V1'):
            return 'MATCH', 'Exact representation target already specified; no conversion executed'
        return 'UNRESOLVED', 'Missing bounded representation target reference'
    # same_measure: only demonstrated incompatibilities are rejected. Shared
    # numerical representation/equal text never establishes business equivalence.
    if a['unit'] and b['unit'] and 'UNDECLARED' not in (a['unit'], b['unit']) and (
            a['unit'] != b['unit']):
        return 'NON_MATCH', 'Known source unit labels differ; no transformation authorized'
    if a['grain'] and b['grain'] and a['grain'].split()[0] != b['grain'].split()[0]:
        return 'NON_MATCH', 'Different supplied source grain categories'
    close_yield = ('CLOSE' in a['field'] and 'YIELD' in b['field']) or (
        'YIELD' in a['field'] and 'CLOSE' in b['field'])
    if close_yield and a['value'] != b['value']:
        return 'NON_MATCH', 'Distinct source CLOSE/YIELD properties and unequal observed values'
    return 'UNRESOLVED', 'Source definitions/units/tenor semantics do not establish equivalence'


def propose(case, witnesses):
    """Generate one paired candidate; this function never receives ground truth."""
    if set(case) != CASE_KEYS or case['question'] not in QUESTIONS:
        raise ValueError('INVALID_CASE_OR_LABEL_LEAK')
    before = deepcopy(case)
    a, b = case['left'], case['right']
    for endpoint in (a, b):
        source = witnesses[endpoint['witness']]
        if endpoint.get('origin') != 'approved_contract_target' and (
                source['fields'][endpoint['field']] != endpoint['value']):
            raise ValueError('SOURCE_OBSERVATION_CHANGED')
    compatibility = _compatibility(a, b)
    label, reason = _check(case)
    semantic = case['review_required'] or case['question'] == 'same_measure'
    state = ('UNRESOLVED' if label == 'UNRESOLVED' else 'REJECTED' if label == 'NON_MATCH'
             else 'PROPOSED' if semantic else 'VALIDATED')
    transform = {
        'typed_projection': 'EXACT_DECIMAL_38_4_V1; candidate only, not executed',
        'identifier_storage_slot': 'COPY_TEXT_WITH_NAMESPACE_AND_ROLE; no value normalization',
        'same_period_text': 'REFERENCE_EXACT_REPORTED_TEXT; no date alignment',
        'same_native_identifier': 'REFERENCE_NAMESPACED_LITERAL_ONLY; no canonical merge',
        'same_occurrence': 'PRESERVE_OCCURRENCES; no deduplication',
        'same_measure': 'NO_MEASURE_TRANSFORMATION_AUTHORIZED; retain separate original values',
        'canonical_entity': 'NO_ENTITY_MERGE_AUTHORIZED; identity rules unresolved',
    }[case['question']]
    conflicts = [f'{key}: {a[key]!r} versus {b[key]!r}' for key, status in compatibility.items()
                 if status == 'LITERAL_DIFFERENT']
    for key in ('namespace', 'role', 'occurrence'):
        if a[key] != b[key]:
            conflicts.append(f'{key}: {a[key]!r} versus {b[key]!r}')
    if not a['value'] or not b['value']:
        conflicts.append('Empty source value is not identity evidence')
    if case['question'] == 'canonical_entity':
        conflicts.append('LIMITATION: no canonical approval, validity interval or cardinality proof')
    report = {
        'agent_version': VERSION, 'case_id': case['id'], 'dimension': case['dimension'],
        'question': case['question'], 'source_field': deepcopy(a), 'candidate_target': deepcopy(b),
        'required_transformation': transform, 'compatibility': compatibility,
        'supporting_evidence': [{'witness': e['witness'],
                                 'source': deepcopy(witnesses[e['witness']]['source']),
                                 'locator': deepcopy(witnesses[e['witness']]['locator'])}
                                for e in (a, b)],
        'conflicting_evidence': conflicts,
        'name_only_baseline_label': 'MATCH' if a['field'] == b['field'] else 'NON_MATCH',
        'candidate_label': label, 'state': state, 'reason': reason,
        'validation_scope': 'Exact bounded question and supplied observations; not canonical approval',
        'human_review_required': bool(case['review_required'] or label == 'UNRESOLVED'),
        'review_question': 'Should this candidate be retained unresolved or rejected pending evidence?',
        'alternatives': ['Retain source distinctions and leave semantic relation unresolved',
                         'Reject current equivalence candidate; revisit only with new source evidence'],
        'consequences': 'No mapping/crosswalk/identity promotion or production join occurs in either case',
        'side_effects': [], 'semantic_promotions': [], 'promotion_eligible': False,
        'input_fingerprint': canonical_hash({'case': case, 'witnesses': {
            e['witness']: witnesses[e['witness']] for e in (a, b)}}),
    }
    report['result_fingerprint'] = canonical_hash(report)
    assert before == case
    return report


def validate_candidate(report):
    """Mechanical report validation does not authorize any semantic promotion."""
    if (set(report) != REPORT_KEYS or report['question'] not in QUESTIONS or
            report['agent_version'] != VERSION or report['state'] not in STATES or
            report['candidate_label'] not in {'MATCH', 'NON_MATCH', 'UNRESOLVED'} or
            report['side_effects'] or report['semantic_promotions'] or report['promotion_eligible']):
        raise ValueError('INVALID_CANDIDATE_OR_PROMOTION_ATTEMPT')
    if report['question'] == 'canonical_entity' and (
            report['candidate_label'] != 'UNRESOLVED' or report['state'] != 'UNRESOLVED'):
        raise ValueError('CANONICAL_INTERPRETATION_NOT_APPROVED')
    if canonical_hash({k: v for k, v in report.items() if k != 'result_fingerprint'}) != (
            report['result_fingerprint']):
        raise ValueError('CANDIDATE_FINGERPRINT_MISMATCH')
    return True


def score(proposals, labels):
    """Host-only scoring after proposals exist; labels never flow into propose()."""
    expected = {c['id']: c['expected_label'] for c in labels}
    if len(expected) != len(labels) or len(proposals) != len(expected) or (
            {p['case_id'] for p in proposals} != set(expected)):
        raise ValueError('CASE_ACCOUNTING_MISMATCH')
    results = {}
    for field in ('name_only_baseline_label', 'candidate_label'):
        matrix = {label: {pred: 0 for pred in ('MATCH', 'NON_MATCH', 'UNRESOLVED')}
                  for label in ('MATCH', 'NON_MATCH', 'UNRESOLVED')}
        for proposal in proposals:
            validate_candidate(proposal)
            matrix[expected[proposal['case_id']]][proposal[field]] += 1
        results[field] = {'confusion_matrix': matrix,
                          'correct': sum(matrix[k][k] for k in matrix), 'total': len(proposals),
                          'false_match_ids': [p['case_id'] for p in proposals if
                                              expected[p['case_id']] == 'NON_MATCH' and
                                              p[field] == 'MATCH'],
                          'false_split_ids': [p['case_id'] for p in proposals if
                                              expected[p['case_id']] == 'MATCH' and
                                              p[field] == 'NON_MATCH'],
                          'premature_resolution_ids': [p['case_id'] for p in proposals if
                                                       expected[p['case_id']] == 'UNRESOLVED' and
                                                       p[field] != 'UNRESOLVED']}
    return results
