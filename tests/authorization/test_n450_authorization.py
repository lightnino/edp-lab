"""Offline checks: production never installs test grants."""
import json
import runpy
from pathlib import Path
from unittest.mock import Mock

import pytest

from edp_lab.ingestion import n450_authorization as auth
from edp_lab.ingestion.universe import ScopeDenied

ROOT = Path(__file__).resolve().parents[2]


def test_exact_packet():
    result = auth.validate_packet(ROOT)
    assert result['status'] == 'VALIDATED_NOT_AUTHORIZED'
    assert (result['n450'], result['c750']) == (450, 750)


@pytest.mark.parametrize('action', sorted(auth.ACTIONS))
@pytest.mark.parametrize('cohort', ['N450', 'C750'])
def test_all_execution_boundaries_closed(action, cohort):
    downstream = Mock()
    with pytest.raises(ScopeDenied, match='OWNER_EXECUTION_GRANT_NOT_INSTALLED'):
        auth.authorize(ROOT, action, [], cohort=cohort)
        downstream()
    downstream.assert_not_called()


def test_agent_approval_cannot_install_grant(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, 'validate_packet', lambda root: {})
    path = tmp_path / auth.OWNER_GRANT_PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'status': 'OWNER_APPROVED', 'actions': sorted(auth.ACTIONS)}))
    with pytest.raises(ScopeDenied, match='OWNER_EXECUTION_GRANT_NOT_INSTALLED'):
        auth.authorize(tmp_path, 'admission', [])


def test_changed_packet_rejected(tmp_path, monkeypatch):
    # Use real host context; change only packet location to a damaged copy.
    packet = tmp_path / 'packet'
    packet.mkdir()
    (packet / 'roster.json').write_text('[]')
    monkeypatch.setattr(auth, 'PACKET', packet)
    with pytest.raises(ScopeDenied, match='COHORT_PACKET_PIN_MISMATCH'):
        auth.validate_packet(ROOT)


def test_remote_notebook_stops_before_contract_or_spark():
    with pytest.raises(RuntimeError, match='REMOTE_EXECUTION_EXCLUDED'):
        runpy.run_path(str(ROOT / 'notebooks/bronze_nasdaq_listed.py'))


def test_synthetic_host_grant_positive_and_exact_input_negative(tmp_path, monkeypatch):
    # Synthetic deployment pins only. Real packet and exact complete bindings.
    roster = json.loads((ROOT / auth.PACKET / 'roster.json').read_text())
    bindings = [{'source_instance_id': r['source_identity'], 'raw_path': r['raw_path'],
                 'raw_sha256': r['raw_sha256']} for r in roster]
    grant = {'status': 'OWNER_APPROVED', 'packet_sha256': auth.PINS,
             'universe': auth.UniverseGate.load(ROOT).scope_reference(),
             'actions': ['admission'], 'cohort': 'N450', 'bindings': bindings}
    path = tmp_path / 'owner.json'
    path.write_text(json.dumps(grant))
    monkeypatch.setattr(auth, 'OWNER_GRANT_PATH', path)
    monkeypatch.setattr(auth, 'OWNER_GRANT_SHA256', auth.sha(path.read_bytes()))
    integrity = Mock()
    monkeypatch.setattr(auth, 'verify_local_bytes', integrity)
    assert auth.authorize(ROOT, 'admission', bindings)['status'] == 'AUTHORIZED_PREFLIGHT_ONLY'
    integrity.assert_called_once()
    integrity.reset_mock()
    for invalid in [bindings[:-1], bindings + bindings[:1], list(reversed(bindings)),
                    [{**bindings[0], 'raw_path': '/unapproved'}] + bindings[1:],
                    [{**bindings[0], 'raw_sha256': '0'*64}] + bindings[1:],
                    [{**bindings[0], 'source_instance_id': 'SRC000705'}] + bindings[1:]]:
        with pytest.raises(ScopeDenied, match='EXACT_INPUT_SET_REQUIRED'):
            auth.authorize(ROOT, 'admission', invalid)
    integrity.assert_not_called()
    with pytest.raises(ScopeDenied, match='ACTION_NOT_AUTHORIZED'):
        auth.authorize(ROOT, 'freeze', bindings)
