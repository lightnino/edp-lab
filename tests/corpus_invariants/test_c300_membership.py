"""Validate the actual local freeze when its deliberately untracked evidence exists."""

from pathlib import Path

import pytest

from edp_lab.ingestion.c300_integrity import verify_freeze, verify_persisted_freeze

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / 'runs/c300/frozen-v1'


@pytest.mark.skipif(not (FREEZE / 'freeze.json').is_file(),
                    reason='Local C300 freeze evidence is unavailable; RAW is never committed')
def test_actual_c300_membership():
    result = verify_freeze(ROOT, FREEZE, check_raw=True)
    assert result['members'] == 300
    assert result['admission'] == 'ADMITTED'
    assert result['freeze'] == 'FROZEN'


def test_canonical_c300_metadata_without_raw():
    result = verify_persisted_freeze(ROOT)
    assert result['members'] == 300
    assert result['status'] == 'FROZEN'


def test_canonical_metadata_preserves_original_fingerprints():
    from edp_lab.ingestion.gold_set import file_sha256

    assert file_sha256(ROOT / 'metadata/cohorts/C300.csv') == (
        'f052599a7cfac3b566a236965e2ab163934d4541e7b09e03da98be728c1541e4')
    assert file_sha256(ROOT / 'metadata/corpus_manifest_v3.csv') == (
        '27ce93f363ebeb234737659e9a411927aed3dd3a674bc8a21b780e05dfdc4bdf')
    assert file_sha256(ROOT / 'metadata/freezes/C300_v1/freeze.json') == (
        '7378b5d183cc4d45e0670eae6d501f204e62fdee02d8b345d9a910300d411835')
