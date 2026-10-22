"""The CLI must use the independently installed authority, never its own proposal."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from edp_lab.ingestion.universe import ScopeDenied

ROOT = Path(__file__).resolve().parents[2]


def test_uninstalled_proposal_cannot_publish(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location('cohort_cli', ROOT / 'scripts/publish_cohort.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from edp_lab.ingestion.universe import sha

    historical = (ROOT / 'metadata/authorizations/n450_processing_v6.json').read_bytes()
    (tmp_path / 'installed.json').write_bytes(historical)
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module.authority, 'OWNER_GRANT_PATH', Path('installed.json'))
    monkeypatch.setattr(module.authority, 'OWNER_GRANT_SHA256', sha(historical))
    monkeypatch.setattr(sys, 'argv', ['publish_cohort',
        str(ROOT / 'proposals/n750-step1-v3/plan.json'), 'admission'])
    with pytest.raises(ScopeDenied, match='OWNER_SCOPE_MISMATCH'):
        module.main()


def test_final_record_matches_accepted_plan_and_code():
    from edp_lab.ingestion.universe import sha

    packet = ROOT / 'proposals/n750-publication-v1'
    raw = (packet / 'owner-record.proposed.json').read_bytes()
    grant = json.loads(raw)
    review = json.loads((packet / 'review.json').read_bytes())
    assert grant['status'] == 'PENDING_OWNER_REVIEW'
    original_scope = json.loads(
        (ROOT / 'proposals/n750-step1-v3/grant.proposed.json').read_bytes())
    assert grant['scopes'] == original_scope['scopes']
    assert grant['remote_processing_readiness'] == {
        'verified': 450, 'unverified': 300, 'mismatches_established': False,
        'required_before': 'STEP_8_PROCESSING', 'unverified_processing': 'PROHIBITED'}
    assert sha(raw) == review['proposed_record_sha256']
    assert grant['plan_sha256'] == sha((ROOT / 'proposals/n750-step1-v3/plan.json').read_bytes())
    for relative, digest in grant['execution_files_sha256'].items():
        assert sha((ROOT / relative).read_bytes()) == digest
    assert sha((packet / 'install-owner.sh').read_bytes()) == review['installer_sha256']
    unresolved = json.loads((packet / 'remote-evidence-unresolved.json').read_bytes())
    assert unresolved['count'] == len(unresolved['sources']) == 300
