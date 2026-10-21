"""Offline admission governance checks; synthetic tests do not admit C300."""

import json
from pathlib import Path

import pytest

from edp_lab.ingestion.c300_admission import freeze, verify_nested, verify_registry

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.usefixtures("owner_evidence")
def test_historical_registry_supported():
    assert len(verify_registry(ROOT, ROOT / 'metadata/corpus_manifest.csv')) == 4


@pytest.mark.usefixtures("owner_evidence")
def test_registry_rejects_historical_rewrite(tmp_path):
    path = tmp_path / 'changed.csv'
    path.write_text((ROOT / 'metadata/corpus_manifest.csv').read_text().replace(
        'SRC000004', 'SRC000005'))
    with pytest.raises(ValueError, match='Historical GOLD'):
        verify_registry(ROOT, path)


def test_nested_expansion_cannot_replace_member():
    selections = {f'C{size}': {'candidate_ids': list(range(size))}
                  for size in (700, 1500, 2000, 3000)}
    verify_nested(selections, list(range(300)))
    selections['C1500']['candidate_ids'][0] = 9999
    with pytest.raises(ValueError, match='Nested membership changed'):
        verify_nested(selections, list(range(300)))


@pytest.mark.usefixtures("owner_evidence")
def test_no_freeze_without_scoped_authority(tmp_path):
    packet = tmp_path / 'packet.json'
    authority = tmp_path / 'authority.json'
    packet.write_text('{}')
    authority.write_text(json.dumps({'admit_and_freeze': True}))
    with pytest.raises(ValueError, match='Authority scope mismatch'):
        freeze(ROOT, packet, authority, tmp_path / 'frozen')
    assert not (tmp_path / 'frozen').exists()


@pytest.mark.usefixtures("owner_evidence")
def test_expansion_protects_complete_frozen_rows(tmp_path):
    path = tmp_path / 'protected.csv'
    path.write_text((ROOT / 'metadata/corpus_manifest.csv').read_text().replace(
        'GOLD_V2', 'C300'))
    with pytest.raises(ValueError, match='Frozen source replaced'):
        verify_registry(ROOT, ROOT / 'metadata/corpus_manifest.csv', frozen=path)
