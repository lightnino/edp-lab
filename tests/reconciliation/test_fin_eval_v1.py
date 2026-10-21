"""Regression of exact-value comparison using actual retained FIN SQL output."""
import copy
import csv
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('fin_verify', 'scripts/verify_fin_eval_v1.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_exact_fixture_and_offsetting_wrong_amounts():
    root = Path('runs/c300-m1/fin_eval_v1/replay-2')
    if not (root / 'FIN_002-amounts-result.json').exists():
        pytest.skip('Actual Databricks result evidence unavailable locally')
    with Path('sql/reconciliation/fin_eval_v1/observed_expected_results.csv').open() as stream:
        fixture = list(csv.DictReader(stream))
    fin1 = module.rows(root / 'FIN_001-result.json')
    fin2 = module.rows(root / 'FIN_002-result.json')
    amounts = module.rows(root / 'FIN_002-amounts-result.json')
    module.compare(fin1, fin2, amounts, fixture)
    wrong = copy.deepcopy(fin1)
    # Equation and PASS string remain unchanged, but two amounts drift together.
    wrong[0]['assets'] = '384159001.0000'
    wrong[0]['liabilities'] = '290982001.0000'
    with pytest.raises(AssertionError):
        module.compare(wrong, fin2, amounts, fixture)
    wrong_control = copy.deepcopy(fin2)
    wrong_control[0]['wrong_equity_difference'] = '0.0000'
    with pytest.raises(AssertionError):
        module.compare(fin1, wrong_control, amounts, fixture)
