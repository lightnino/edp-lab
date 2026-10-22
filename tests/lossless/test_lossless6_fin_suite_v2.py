"""Keep the FIN regression part of Lossless 6 mandatory across cohort expansion.

This offline test validates the versioned acceptance contract and frozen fixtures.
It does NOT replace running FIN SQL against live C300/C750 candidates.
"""
import csv
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_lossless6_fin_suite_is_evergreen_and_frozen_fin_is_retained():
    suite = json.loads((ROOT / "metadata/evaluations/lossless6_fin_suite_v2.json").read_text())
    historical = json.loads((ROOT / "metadata/evaluations/fin_eval_v1.json").read_text())
    freeze = json.loads((ROOT / "metadata/freezes/O_C300_M1_v1/references.json").read_text())
    contract = (ROOT / "docs/evaluation_contract.md").read_text()

    assert suite["schema"] == "LOSSLESS_6_FIN_SUITE_V2"
    assert suite["mandatory_at_each_corpus_expansion"] is True
    assert suite["model"] == historical["attached_model"] == "M1_LEXICAL_V1"
    assert suite["model_change"] is False
    assert [x["id"] for x in suite["mandatory_cases"]] == ["FIN_001_V1", "FIN_002_V1"]
    assert [x["contexts"] for x in suite["mandatory_cases"]] == [2, 1]
    assert {"C300", "C750", "C1500", "C2000", "C3000"} <= set(
        suite["cohorts_containing_frozen_c300"]
    )
    assert freeze["financial_evaluation"]["status"] == "SCOPED_PASS"
    assert historical["results"]["FIN_001"] == "2/2 PASS"
    assert historical["results"]["FIN_002"].startswith("1/1 PASS")
    assert "### 2.2 Mandatory Lossless 6 financial regression suite" in contract
    assert "B2 / new-only sources" in contract
    assert "C / combined corpus" in contract
    assert "C2 and operational Stability C3 remain **separate**" in contract


def test_pinned_fin_fixture_contains_exact_three_numeric_cases_and_negative_control():
    suite = json.loads((ROOT / "metadata/evaluations/lossless6_fin_suite_v2.json").read_text())
    with (ROOT / "sql/reconciliation/fin_eval_v1/observed_expected_results.csv").open() as f:
        fixture = list(csv.DictReader(f))

    assert len(fixture) == sum(x["contexts"] for x in suite["mandatory_cases"]) == 3
    assert [r["test_id"] for r in fixture] == ["FIN_001_V1", "FIN_001_V1", "FIN_002_V1"]
    assert all(r["result"] == "PASS" for r in fixture)
    for row in fixture:
        assert Decimal(row["assets"]) == (
            Decimal(row["liabilities"]) + Decimal(row["equity_used"])
        )
        assert Decimal(row["assets"]) == Decimal(row["reported_total"])
        assert Decimal(row["correct_difference"]) == Decimal(0)
    assert Decimal(fixture[2]["wrong_equity_difference"]) == Decimal("1232700000.0000")
    assert Decimal(fixture[2]["implied_nci"]) == Decimal("1232700000.0000")


def test_no_silent_waiver_of_lossless6_or_fake_numeric_reconciliation():
    suite = json.loads((ROOT / "metadata/evaluations/lossless6_fin_suite_v2.json").read_text())
    scope = suite["scope_rules"]
    assert any("zero modeled economic measures" in x for x in scope["B2_new_only"])
    assert any("not a claim of numeric reconciliation" in x for x in scope["B2_new_only"])
    assert any("negative control" in x for x in scope["C_combined"])
    assert suite["status_semantics"]["not_yet_executed"] == "Do not assert PASS"
    assert "Never retroactively rewrite" in suite["historical_evidence_policy"]
