"""Synthetic boundary fixtures; these are not observations about source meaning."""
from dataclasses import asdict
from decimal import Decimal, localcontext

import pytest

from edp_lab.materialization.typed_numeric_v1 import MODEL, RULE, convert


@pytest.mark.parametrize('text,expected', [
    ('0', '0.0000'), ('-0', '-0.0000'), ('+0.0000', '0.0000'),
    ('-1.2300', '-1.2300'), ('+0001.2', '1.2000'), ('0.0001', '0.0001'),
    ('-0.0001', '-0.0001'), ('9' * 34 + '.9999', '9' * 34 + '.9999'),
    ('-' + '9' * 34 + '.9999', '-' + '9' * 34 + '.9999'),
    ('0' * 40 + '1.00', '1.0000'),
])
def test_synthetic_exact_valid(text, expected):
    # A deliberately hostile context catches accidental arithmetic/quantize.
    with localcontext() as ctx:
        ctx.prec = 2
        ctx.traps.update(dict.fromkeys(ctx.traps, True))
        result = convert(text)
    assert result.value_decimal.as_tuple() == Decimal(expected).as_tuple()
    assert result.lexical_value == text
    assert (result.conversion_outcome, result.conversion_reason) == ('VALID', 'EXACT_PROJECTION')
    assert (result.model_version, result.conversion_rule_version) == (MODEL, RULE)


@pytest.mark.parametrize('text,outcome,reason', [
    ('', 'BLANK', 'EMPTY_TEXT'), (' \t\r\n\f\v', 'BLANK', 'WHITESPACE_ONLY'),
    ('1.00000', 'SCALE_EXCEEDED', 'FRACTIONAL_DIGITS_GT_4'),
    ('0.00001', 'SCALE_EXCEEDED', 'FRACTIONAL_DIGITS_GT_4'),
    ('9' * 35 + '.00000', 'SCALE_EXCEEDED', 'FRACTIONAL_DIGITS_GT_4'),
    ('1' + '0' * 34, 'OVERFLOW', 'INTEGER_DIGITS_GT_34'),
    ('-' + '9' * 35 + '.9999', 'OVERFLOW', 'INTEGER_DIGITS_GT_34'),
    *[(s, 'INVALID', 'LEXICAL_GRAMMAR') for s in [
        ' 1.0', '1.0 ', '1\n', 'NaN', 'Infinity', '-Infinity', '1e2', '1E-2',
        '1_000', '1,000', '1,5', '$1', '1%', '.5', '1.', '+', '--1',
        '１２.３', '١٢.٣', '\u00a0', 'NULL', 'null', 'N/A', '1\x00',
    ]],
])
def test_synthetic_nonconvertible(text, outcome, reason):
    result = convert(text)
    assert (result.conversion_outcome, result.conversion_reason) == (outcome, reason)
    assert result.value_decimal is None and result.lexical_value == text


@pytest.mark.parametrize('text,flags,outcome,reason', [
    (None, {'present': False}, 'MISSING', 'SOURCE_FIELD_ABSENT'),
    (None, {'null_marker': True}, 'NULL_UNRESOLVED', 'SOURCE_NULL_MARKER_UNINTERPRETED'),
    ('', {'null_marker': True}, 'NULL_UNRESOLVED', 'SOURCE_NULL_MARKER_UNINTERPRETED'),
    (' \t', {'null_marker': True}, 'NULL_UNRESOLVED', 'SOURCE_NULL_MARKER_UNINTERPRETED'),
    ('1.2', {'null_marker': True}, 'INVALID', 'CONFLICTING_NULL_MARKER'),
])
def test_synthetic_structural_states(text, flags, outcome, reason):
    result = convert(text, **flags)
    assert (result.conversion_outcome, result.conversion_reason) == (outcome, reason)
    assert result.value_decimal is None and result.lexical_value == text


@pytest.mark.parametrize('text,flags,error', [
    (None, {}, ValueError), ('1', {'present': False}, ValueError),
    (None, {'present': False, 'null_marker': True}, ValueError),
    (1.2, {}, TypeError), (1, {}, TypeError), (Decimal(1), {}, TypeError),
    (True, {}, TypeError), (b'1', {}, TypeError), ('1', {'present': 1}, TypeError),
    ('1', {'null_marker': 'false'}, TypeError),
])
def test_synthetic_adapter_errors(text, flags, error):
    with pytest.raises(error):
        convert(text, **flags)


def test_synthetic_multiplicity_and_determinism():
    values = ['1.00', '1.00', '-0', '', 'NULL', '1.00000']
    original = values.copy()
    outputs = [asdict(convert(v)) for v in values]
    assert outputs == [asdict(convert(v)) for v in values]
    assert [r['lexical_value'] for r in outputs] == values == original
    assert len(outputs) == len(values)


@pytest.mark.parametrize('text', [
    '9' * 34 + '.9999', '-' + '9' * 34 + '.9999', '4.45', '0.0070', '-0.0001',
])
def test_synthetic_independent_decimal_storage(text):
    import duckdb

    result = convert(text)
    with duckdb.connect(':memory:') as db:
        db.execute('create table projection (value_decimal decimal(38,4))')
        db.execute('insert into projection values (?)', [result.value_decimal])
        stored, rendered = db.execute(
            'select value_decimal, cast(value_decimal as varchar) from projection').fetchone()
    assert stored.as_tuple() == result.value_decimal.as_tuple()
    assert Decimal(rendered) == Decimal(text)
