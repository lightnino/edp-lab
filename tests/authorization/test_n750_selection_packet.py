"""Portable integrity checks for recovered selection, without RAW processing."""
import collections
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'proposals/n750-step1-v3'


def load(path):
    return json.loads(path.read_bytes())


def test_selection_exact_universe_disjoint_scope():
    rows = load(PACKET / 'roster.json')
    universe = load(ROOT / 'metadata/source_universes/approved_v1/manifest.json')
    members = {r['identity']: r for r in universe['members']}
    historical = load(ROOT / 'metadata/freezes/C750_v1/C750.bindings.json')
    ids = {r['source_identity'] for r in rows}
    assert len(rows) == len(ids) == 750
    assert not ids & {r['source_identity'] for r in historical}
    assert sum(r['bytes'] for r in rows) == 269323425
    assert collections.Counter(r['family'] for r in rows) == {
        'TREASURY_ANNUAL_XML': 5, 'SEC_EDGAR_DAILY_MASTER': 745}
    for r in rows:
        member = members[r['source_identity']]
        assert not member['holdout']
        assert (r['raw_path'], r['raw_sha256']) == (
            member['raw_path'], member['raw_sha256'])
    q = load(PACKET / 'qualification.json')
    assert set(q['excluded_holdouts']) == {
        r['identity'] for r in members.values() if r['holdout']}
    assert len(q['excluded_holdouts']) == 41
    assert q['remote_coverage'] == len(q['remote_reuse']) == 450


def test_packet_pins_and_registration_scope():
    index = load(PACKET / 'review-index.json')
    for name, digest in index['files_sha256'].items():
        assert hashlib.sha256((PACKET / name).read_bytes()).hexdigest() == digest
    plan = load(PACKET / 'plan.json')
    grant = load(PACKET / 'grant.proposed.json')
    assert grant['status'] == 'PENDING_OWNER_REVIEW'
    assert grant['plan_sha256'] == hashlib.sha256((PACKET / 'plan.json').read_bytes()).hexdigest()
    assert len(plan['selected']) == 750
    for selected, source in zip(plan['selected'], load(PACKET / 'roster.json'), strict=True):
        assert selected['source_identity'] == source['source_identity']
        assert selected['physical_raw_path'] == source['raw_path']
        assert selected['raw_path'].startswith('data/raw/')
    for key, digest in plan['baseline_sha256'].items():
        assert hashlib.sha256((ROOT / plan[key]).read_bytes()).hexdigest() == digest
    with (ROOT / plan['baseline_manifest']).open() as stream:
        assert len(list(csv.DictReader(stream))) == 754
    assert grant['scopes']['admission']['destination'] == 'metadata/admissions/N750_v1'
    assert grant['scopes']['freeze']['destination'] == 'metadata/freezes/C1500_v1'
    assert len(grant['scopes']['admission']['files_sha256']) == 5
    assert len(grant['scopes']['freeze']['files_sha256']) == 4
