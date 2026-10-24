"""Real approved fixture values must survive the protected live-control comparison."""

import csv
import shutil
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.operating.day5_control_verifier import _assess_fin, _assess_treasury

ROOT = Path(__file__).resolve().parents[2]


def _copy(root: Path, relative: str) -> None:
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / relative, destination)


def test_fin_control_rejects_changed_economic_difference(tmp_path: Path) -> None:
    relative = "sql/reconciliation/fin_eval_v1/observed_expected_results.csv"
    _copy(tmp_path, relative)
    with (tmp_path / relative).open(newline="") as stream:
        expected = list(csv.DictReader(stream))
    rows = [{"ddate": row["ddate"], "fin_001_result": "PASS",
             "assets": row["assets"], "liabilities": row["liabilities"],
             "equity": row["equity_used"], "reported_total": row["reported_total"],
             "difference_1": row["correct_difference"], "difference_2": "0"}
            for row in expected[:2]]
    _assess_fin(tmp_path, "FIN_001", rows)
    rows[1]["difference_1"] = "1"
    with pytest.raises(Denied, match="FIN_001_FIXTURE_MISMATCH"):
        _assess_fin(tmp_path, "FIN_001", rows)


def test_treasury_control_rejects_changed_absence_count(tmp_path: Path) -> None:
    relative = "metadata/evaluations/fixtures/treasury_lossless6_expected_v1.json"
    _copy(tmp_path, relative)
    values = ["TRY_003_V1", 12948, 12948, 12793, 12793, 155, 155,
              0, 0, 0, 0, 249, 0]
    _assess_treasury(tmp_path, "TRY_003", [
        {str(i): value for i, value in enumerate(values)}])
    values[6] = 154
    with pytest.raises(Denied, match="TRY_003_LIVE_RESULT_FAILED"):
        _assess_treasury(tmp_path, "TRY_003", [
            {str(i): value for i, value in enumerate(values)}])
