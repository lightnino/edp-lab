"""Declared lexical FD checks only; no discovery or business-key approval."""
from collections import Counter

from edp_lab.profiling.source_reader import canonical_hash
from edp_lab.profiling.tools import authorized_table, indices, output


@authorized_table
def declared_fd(table, determinants, dependents, *, group_limit=10):
    """Keep every occurrence, including duplicate/blank/NULL-token tuples.

    PASS is literal consistency on this supplied population, never a permanent FD.
    Unknown NULL rules or any relevant blank/NULL makes interpretation ambiguous.
    """
    if not 1 <= group_limit <= 100:
        raise ValueError('Invalid group_limit')
    x, y = tuple(determinants), tuple(dependents)
    parameters = {'determinants': list(x), 'dependents': list(y), 'group_limit': group_limit}
    if table.errors:
        return output(table, 'declared_fd', {'status': 'NOT_COMPUTED',
                      'reason': 'PARSE_FAILED'}, parameters)
    xi, yi = indices(table, x), indices(table, y)
    if len(table.rows) != len(table.locators) or any(
            len(row) != len(table.columns) for row in table.rows):
        raise ValueError('OCCURRENCE_ACCOUNTING_MISMATCH')
    if any(value is not None and not isinstance(value, str)
           for row in table.rows for value in row):
        raise ValueError('TEXT_OR_EXPLICIT_MISSING_ONLY')
    groups, xy = {}, Counter()
    blank_rows, null_rows = [], []
    for row, locator in zip(table.rows, table.locators, strict=True):
        a, b = tuple(row[i] for i in xi), tuple(row[i] for i in yi)
        values = a + b
        if any(v is not None and not v.strip() for v in values):
            blank_rows.append(locator)
        if any(v is None or (table.null_tokens is not None and v in table.null_tokens)
               for v in values):
            null_rows.append(locator)
        group = groups.setdefault(a, {'count': 0, 'values': {}})
        group['count'] += 1
        group['values'].setdefault(b, locator)
        xy[a, b] += 1
    violations = [(a, g) for a, g in groups.items() if len(g['values']) > 1]
    violations.sort(key=lambda item: canonical_hash(item[0]))
    ambiguous = table.null_tokens is None or bool(blank_rows or null_rows)
    literal = 'NO_EVIDENCE' if not table.rows else 'VIOLATED' if violations else 'PASS'
    status = literal if literal != 'PASS' or not ambiguous else 'AMBIGUOUS'
    payload = {
        'status': status, 'literal_status': literal,
        'interpretation_status': 'UNRESOLVED' if ambiguous else 'LEXICAL_ONLY',
        'equality': 'EXACT_LITERAL_TUPLES_NO_NULL_OR_BLANK_EXCLUSION',
        'null_rules_known': table.null_tokens is not None,
        'blank_occurrences': len(blank_rows), 'null_or_missing_occurrences': len(null_rows),
        'blank_witnesses': blank_rows[:group_limit], 'null_witnesses': null_rows[:group_limit],
        'determinant_groups': len(groups),
        'repeated_determinant_groups': sum(g['count'] > 1 for g in groups.values()),
        'max_occurrences_per_determinant': max((g['count'] for g in groups.values()), default=0),
        'literal_self_join_pairs': sum(g['count'] ** 2 for g in groups.values()),
        'join_risk_scope': 'Hypothetical self equality join on X; no join executed or approved',
        'duplicate_xy_excess': sum(n - 1 for n in xy.values()),
        'violating_groups': len(violations),
        'counterexamples': [
            {'determinant_values': list(a), 'occurrences': g['count'],
             'distinct_dependent_tuples': len(g['values']),
             'witnesses': [{'dependent_values': list(b), 'locator': locator}
                           for b, locator in sorted(g['values'].items(),
                                                    key=lambda item: canonical_hash(item[0]))[:2]]}
            for a, g in violations[:group_limit]],
        'counterexamples_truncated': len(violations) > group_limit,
        'business_fd_status': 'NOT_APPROVED_NOT_ASSESSED',
        'business_key_status': 'NOT_APPROVED_NOT_ASSESSED',
        'side_effects': [], 'semantic_promotions': [],
        'input_occurrences_sha256': canonical_hash({'rows': table.rows, 'locators': table.locators}),
    }
    result = output(table, 'declared_fd', payload, parameters)
    # Existing envelope is reused, but a supplied bound must never masquerade as
    # a full logical-table scan. The host must declare exact population provenance.
    result['population']['scope'] = 'DECLARED_INPUT_OCCURRENCES_ONLY'
    result['population']['sampling_method'] = table.config.get('selection', 'HOST_SUPPLIED')
    result['result_sha256'] = canonical_hash({k: v for k, v in result.items()
                                             if k != 'result_sha256'})
    return result
