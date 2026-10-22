"""Bounded local source checks, skipped explicitly when pinned evidence is absent.

No network, source modification, full-feed conversion or M2 publication. All
source selection below is fixed to the approved contract; not numeric inference.
"""
import csv
import hashlib
import io
import json
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from edp_lab.materialization.typed_numeric_v1 import convert

ROOT = Path(__file__).resolve().parents[2]
LOCAL = Path('/Users/lightnino/Projects/edp-lab')
D = 'http://schemas.microsoft.com/ado/2007/08/dataservices'
M = 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata'
NS = {'a': 'http://www.w3.org/2005/Atom', 'm': M}
FSDS = {
    ('SRC000060', '64698'): ('0.0070', 'pure', 'InvestmentBasisSpreadVariableRate'),
    ('SRC000053', '312006'): ('0.0010', 'pure', 'InvestmentOwnedPercentOfNetAssets'),
    ('SRC000054', '337467'): ('9830000.0000', 'USD', 'InvestmentOwnedAtCost'),
}
ALLOW = {
    'SRC010451': ['BC_' + x for x in (
        '1MONTH', '1_5MONTH', '2MONTH', '3MONTH', '4MONTH', '6MONTH', '1YEAR', '2YEAR',
        '3YEAR', '5YEAR', '7YEAR', '10YEAR', '20YEAR', '30YEAR', '30YEARDISPLAY')],
    'SRC010452': [f'ROUND_B1_{a}_{b}WK_2' for a in ('CLOSE', 'YIELD')
                  for b in (4, 6, 8, 13, 17, 26, 52)] +
                 [f'CS_{b}WK_{a}_AVG' for a in ('CLOSE', 'YIELD')
                  for b in (4, 6, 8, 13, 17, 26, 52)],
    'SRC010453': ['RATE'],
    'SRC010454': ['TC_' + x for x in ('5YEAR', '7YEAR', '10YEAR', '20YEAR', '30YEAR')],
    'SRC010455': ['RATE'],
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def retained_archive(relative, digest):
    path = LOCAL / 'runs/c300-m1' / relative
    if not path.exists():
        pytest.skip('ENVIRONMENT: pinned local retained evidence unavailable: ' + str(path))
    raw = path.read_bytes()
    assert sha(raw) == digest
    return path, raw, zipfile.ZipFile(io.BytesIO(raw))


def project(source, text, source_rule, **flags):
    """Test-only envelope demonstrating independent source/projection lineage."""
    before = deepcopy(source)
    result = {'source': deepcopy(source), 'source_rule_version': source_rule,
              'projection': asdict(convert(text, **flags))}
    assert source == before == result['source']
    assert result == {'source': before, 'source_rule_version': source_rule,
                      'projection': asdict(convert(text, **flags))}
    return result


def test_actual_fsds_three_frozen_witnesses():
    path, raw, archive = retained_archive(
        'closeout-review-v1/supporting-evidence-v1.zip',
        '0903bb24047b95e6203eebca6b5af83441f8b94ab4a0b5addc136e9a18367e10')
    name = 'runs/c300-m1/reconciled_recovery_20261021_v2/warehouse-witness-result.json'
    member = archive.read(name)
    assert sha(member) == 'd5d8ae37317f9861fb075507f428218bc591e5d3bdce1888a8fa346709dbc9ae'
    doc = json.loads(member)
    columns = [c['name'] for c in doc['manifest']['schema']['columns']]
    groups = {}
    for values in doc['result']['data_array']:
        row = dict(zip(columns, values, strict=True))
        key = row['source_instance_id'], row['source_line']
        if key not in FSDS:
            continue
        group = groups.setdefault(key, {'fields': {}, 'lineage': {
            k: v for k, v in row.items()
            if k not in ('field_ordinal', 'original_name', 'lexical_value')}})
        assert row['original_name'] not in group['fields']
        group['fields'][row['original_name']] = row['lexical_value']
        if row['original_name'] == 'value':
            assert row['field_ordinal'] == '9'
    assert set(groups) == set(FSDS)
    outputs = []
    for key, source in groups.items():
        text, unit, tag = FSDS[key]
        fields, lineage = source['fields'], source['lineage']
        assert (fields['value'], fields['uom'], fields['tag']) == (text, unit, tag)
        assert set(fields) == {
            'adsh', 'tag', 'version', 'ddate', 'qtrs', 'uom',
            'segments', 'coreg', 'value', 'footnote'}
        assert lineage['archive_member'] == 'num.txt'
        assert lineage['model_version'] == 'M1_LEXICAL_V1'
        assert lineage['rule_version'] == 'C300_FSDS_NUM_QUOTE_BOUNDARY_V1'
        assert all(lineage[k] for k in ('byte_offset', 'byte_length', 'binding_sha256',
                                       'raw_sha256', 'member_sha256', 'run_id'))
        result = project(source, text, 'FSDS_NUM_VALUE_SCOPE_V1')
        assert result['projection']['value_decimal'].as_tuple() == Decimal(text).as_tuple()
        assert result['projection']['conversion_outcome'] == 'VALID'
        outputs.append(result)
    assert len(outputs) == len(groups) == 3
    assert path.read_bytes() == raw  # retained M1 evidence unchanged
    print('FSDS_TYPED_VALIDATED: 3/3 actual frozen value witnesses; context/lineage unchanged')


def test_existing_fin_evidence_unchanged():
    path, raw, archive = retained_archive(
        'fin_eval_v1/fin-eval-v1-evidence.zip',
        '9d0fc256970bf3815a9020bf628c960ee7f601ac6fd03596121ed211b758916d')
    prefix = 'runs/c300-m1/fin_eval_v1/replay-2/'
    verification = json.loads(archive.read(prefix + 'verification.json'))
    for name in ('FIN_001-result.json', 'FIN_002-result.json',
                 'FIN_002-amounts-result.json', 'lineage-corrected-result.json'):
        assert sha(archive.read(prefix + name)) == verification['hashes'][prefix + name]
    assert verification['lineage_rows'] == 13
    assert verification['view_unchanged_during_replay'] is True
    assert verification['status'] == 'SCOPED_PASS'
    fixture = ROOT / 'sql/reconciliation/fin_eval_v1/observed_expected_results.csv'
    contract = json.loads((ROOT / 'metadata/evaluations/fin_eval_v1.json').read_bytes())
    assert sha(fixture.read_bytes()) == contract['files'][str(fixture.relative_to(ROOT))]
    rows = list(csv.DictReader(io.StringIO(fixture.read_text())))
    assert len(rows) == 3
    with localcontext() as ctx:
        ctx.prec = 38
        for row in rows:
            assert Decimal(row['assets']) == Decimal(row['reported_total'])
            assert Decimal(row['assets']) - Decimal(row['liabilities']) - Decimal(
                row['equity_used']) == Decimal(row['correct_difference']) == 0
        assert Decimal(rows[-1]['wrong_equity_difference']) == Decimal('1232700000.0000')
    amounts = json.loads(archive.read(prefix + 'FIN_002-amounts-result.json'))
    assert amounts['result']['data_array'] == [[
        '5', '5', '5', '30929500000.0000', '15558800000.0000', '14138000000.0000',
        '15370700000.0000', '30929500000.0000']]
    assert path.read_bytes() == raw
    print('FIN: reused 3 contexts / 13 lineage witnesses; no SQL replay or M2 FIN backfill')


@pytest.mark.parametrize('sid', list(ALLOW))
def test_actual_treasury_representative_properties(sid):
    plan = json.loads((ROOT / 'proposals/n750-step1-v3/plan.json').read_bytes())
    source = next(r for r in plan['selected'] if r['source_instance_id'] == sid)
    path = Path(source['physical_raw_path'])
    if not path.exists():
        pytest.skip('ENVIRONMENT: approved Treasury RAW unavailable: ' + str(path))
    raw = path.read_bytes()
    assert sha(raw) == source['raw_sha256']
    entries = ET.fromstring(raw).findall('a:entry', NS)
    indices = [0, 1, 2, len(entries) - 1] if sid == 'SRC010453' else [
        0, 30, 31, len(entries) - 1]
    counts, outputs, locators = Counter(), [], []
    for index in indices:
        props = entries[index].find('a:content/m:properties', NS)
        context = [(c.tag, c.text, dict(c.attrib)) for c in props]
        date = next(c.text for c in props if c.tag in {
            f'{{{D}}}NEW_DATE', f'{{{D}}}INDEX_DATE', f'{{{D}}}QUOTE_DATE'})
        assert date
        for name in ALLOW[sid]:
            qname = f'{{{D}}}{name}'
            matches = [(i, c) for i, c in enumerate(props, 1) if c.tag == qname]
            # No dict flattening of repeated properties; occurrence ordinal retained.
            for ordinal, child in matches or [(None, None)]:
                lineage = {**source, 'entry_ordinal': index + 1, 'property_ordinal': ordinal,
                           'qname': qname, 'context': context, 'date_text': date,
                           'presence': child is not None}
                present = child is not None
                text = (child.text or '') if present else None
                marker = present and child.get(f'{{{M}}}null') == 'true'
                if present:
                    assert child.get(f'{{{M}}}type') == 'Edm.Double'
                output = project(lineage, text, 'TREASURY_RATE_QNAME_SCOPE_V1',
                                 present=present, null_marker=marker)
                projection = output['projection']
                assert projection['lexical_value'] == text
                if present:
                    assert projection['conversion_outcome'] == 'VALID'
                    assert projection['value_decimal'] == Decimal(text)
                    assert projection['value_decimal'].as_tuple().exponent == -4
                else:
                    assert projection['conversion_outcome'] == 'MISSING'
                    assert projection['value_decimal'] is None
                counts[projection['conversion_outcome']] += 1
                outputs.append(output)
                locators.append((sid, source['raw_sha256'], index + 1, qname, ordinal))
    assert len(outputs) == len(locators) == len(set(locators)) == 4 * len(ALLOW[sid])
    assert counts['MISSING'] == {'SRC010451': 2, 'SRC010452': 8}.get(sid, 0)
    assert path.read_bytes() == raw
    print(f'TREASURY_TYPED_VALIDATED {sid}: entries {[i + 1 for i in indices]}, '
          f'outcomes {dict(counts)}, exact QName/date/occurrence/context preserved')
