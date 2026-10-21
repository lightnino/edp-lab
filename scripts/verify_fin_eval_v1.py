"""Compare complete SQL result values to the independent historical fixture."""
import csv
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path


def rows(path):
    response = json.loads(path.read_text())
    assert response['status']['state'] == 'SUCCEEDED'
    assert not response['manifest'].get('truncated', False)
    cols = [c['name'] for c in response['manifest']['schema']['columns']]
    values = response.get('result', {}).get('data_array', [])
    assert len(values) == response['manifest']['total_row_count']
    return [dict(zip(cols, row, strict=True)) for row in values]


def compare(fin1, fin2, amounts, fixture):
    assert len(fin1) == 2 and len(fin2) == 1 and len(amounts) == 1
    assert len(fixture) == 3
    for actual, expected in zip(sorted(fin1, key=lambda r: r['ddate']), fixture[:2], strict=True):
        assert actual['ddate'] == expected['ddate']
        assert actual['fin_001_result'] == expected['result'] == 'PASS'
        for field, target in {'assets': 'assets', 'liabilities': 'liabilities', 'equity': 'equity_used', 'reported_total': 'reported_total', 'difference_1': 'correct_difference'}.items():
            assert Decimal(actual[field]) == Decimal(expected[target]), field
        assert Decimal(actual['difference_2']) == 0
    expected = fixture[2]
    for field in ('correct_difference', 'wrong_equity_difference', 'implied_nci'):
        assert Decimal(fin2[0][field]) == Decimal(expected[field]), field
    assert fin2[0]['fin_002_result'] == expected['result'] == 'PASS'
    for field, target in {'assets': 'assets', 'liabilities': 'liabilities', 'equity_including_nci': 'equity_used', 'reported_total': 'reported_total'}.items():
        assert Decimal(amounts[0][field]) == Decimal(expected[target]), field
    assert Decimal(amounts[0]['equity_parent']) == Decimal('14138000000.0000')
    assert all(int(amounts[0][k]) == 5 for k in ('n_facts', 'n_tags', 'n_valid_amounts'))
    assert Decimal(fin2[0]['wrong_equity_difference']) != 0


def main():
    out = Path(sys.argv[1])
    with Path('sql/reconciliation/fin_eval_v1/observed_expected_results.csv').open() as stream:
        fixture = list(csv.DictReader(stream))
    compare(rows(out / 'FIN_001-result.json'), rows(out / 'FIN_002-result.json'), rows(out / 'FIN_002-amounts-result.json'), fixture)
    assert rows(out / 'view-before-result.json') == rows(out / 'view-after-result.json')
    historical = json.loads(Path('runs/c300-m1/reconciled_recovery_20261021_v2/collected-full/queryable.json').read_text())
    for label, kind in [('view-before', 'records'), ('fields-view', 'fields')]:
        definition = next(iter(rows(out / (label + '-result.json'))[0].values()))
        key = 'q_c300_m1_' + kind + '_reconciled_recovery_20261021_v2_full'
        assert historical['views'][key] in definition
    for i in range(4):
        assert rows(out / f'delta-history-{i}-result.json')[0]['version'] == '0'
    lineage = rows(out / 'lineage-corrected-result.json')
    assert len(lineage) == 13
    assert all(r['model_version'] == 'M1_LEXICAL_V1' and r['rule_version'] == 'C300_LITERAL_IDENTITY_V1' for r in lineage)
    assert all(r['raw_sha256'] == 'f075d721dde4393dabd49c1746578294ada4665ec29c85c2b3184f44f6f09187' and r['member_sha256'] == 'ebc8e2b055f893e56a4ce431ee16ef314d6be7c891e3791ae31afcaec635ba0c' for r in lineage)
    summary = {'status': 'SCOPED_PASS', 'FIN_001': '2/2 PASS; exact fixture values', 'FIN_002': '1/1 PASS; exact fixture values and wrong-equity detection', 'view_unchanged_during_replay': True, 'lineage_rows': 13, 'hashes': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.name != 'verification.json'}}
    (out / 'verification.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'hashes'}))


if __name__ == '__main__':
    main()
