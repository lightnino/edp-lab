"""Offline checks: production never installs test grants."""
import json
import runpy
from pathlib import Path
from unittest.mock import Mock

import pytest

from edp_lab.ingestion import n450_authorization as auth
from edp_lab.ingestion.universe import ScopeDenied

ROOT = Path(__file__).resolve().parents[2]
SIDE = json.loads((ROOT / 'metadata/source_universes/historical_cohort_bindings_v1.json').read_bytes())
HOST_EVIDENCE_AVAILABLE = all((ROOT / path).exists() for path in SIDE['evidence'])
requires_host_evidence = pytest.mark.skipif(
    not HOST_EVIDENCE_AVAILABLE, reason='Pinned host-local C300 authority evidence unavailable')


@requires_host_evidence
def test_exact_packet():
    result = auth.validate_packet(ROOT)
    assert result['status'] == 'VALIDATED_NOT_AUTHORIZED'
    assert (result['n450'], result['c750']) == (450, 750)


@pytest.mark.parametrize('action', sorted(auth.ACTIONS))
@pytest.mark.parametrize('cohort', ['N450', 'C750'])
def test_all_execution_boundaries_closed(action, cohort, monkeypatch):
    # This unit exercises the missing-installation state, independently of the
    # real owner-installed pin and separately tested host-local packet evidence.
    monkeypatch.setattr(auth, 'validate_packet', lambda root: {})
    monkeypatch.setattr(auth, 'OWNER_GRANT_SHA256', None)
    downstream = Mock()
    with pytest.raises(ScopeDenied, match='OWNER_EXECUTION_GRANT_NOT_INSTALLED'):
        auth.authorize(ROOT, action, [], cohort=cohort)
        downstream()
    downstream.assert_not_called()


def test_agent_approval_cannot_install_grant(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, 'validate_packet', lambda root: {})
    monkeypatch.setattr(auth, 'OWNER_GRANT_SHA256', '0'*64)
    path = tmp_path / auth.OWNER_GRANT_PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'status': 'OWNER_APPROVED', 'actions': sorted(auth.ACTIONS)}))
    with pytest.raises(ScopeDenied, match='OWNER_GRANT_PIN_MISMATCH'):
        auth.authorize(tmp_path, 'admission', [])


@requires_host_evidence
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


@requires_host_evidence
def test_synthetic_host_grant_positive_and_exact_input_negative(tmp_path, monkeypatch):
    # Synthetic deployment pins only. Real packet and exact complete bindings.
    roster = json.loads((ROOT / auth.PACKET / 'roster.json').read_text())
    bindings = [{'source_instance_id': r['source_identity'], 'raw_path': r['raw_path'],
                 'raw_sha256': r['raw_sha256']} for r in roster]
    grant = {'status': 'OWNER_APPROVED', 'packet_sha256': auth.PINS,
             'universe': auth.UniverseGate.load(ROOT).scope_reference(),
             'scopes': {'admission': {'cohort': 'N450', 'bindings': bindings}}}
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


@pytest.fixture
def publication_context(tmp_path, monkeypatch):
    """Temporary metadata publications, real packet/gate, synthetic host owner pin.

    RAW rehash functions are sentinels here: they were exercised independently;
    no positive publication test claims real C300 RAW or live execution coverage.
    """
    import shutil

    from edp_lab.ingestion import n450_admission as entry

    if not HOST_EVIDENCE_AVAILABLE:
        pytest.skip('Pinned host-local C300 authority evidence unavailable')
    side = json.loads(
        (ROOT / 'metadata/source_universes/historical_cohort_bindings_v1.json').read_text())
    paths = [Path(p) for p in side['evidence'] if not Path(p).is_absolute()]
    paths += [Path('metadata/source_universes/historical_cohort_bindings_v1.json'),
              Path('metadata/source_universes/approved_v1/manifest.json'),
              Path('metadata/source_universes/approved_v1/owner_authorization.json')]
    for path in paths:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, tmp_path / path)
    shutil.copytree(ROOT / auth.PACKET, tmp_path / auth.PACKET)
    roster = json.loads((tmp_path / auth.PACKET / 'roster.json').read_text())
    n450 = [{'source_instance_id': r['source_identity'], 'raw_path': r['raw_path'],
             'raw_sha256': r['raw_sha256']} for r in roster]
    c750 = json.loads((tmp_path / auth.PACKET / 'c750-proposed.json').read_text())
    grant = {'status': 'OWNER_APPROVED', 'packet_sha256': dict(auth.PINS),
             'universe': auth.UniverseGate.load(tmp_path).scope_reference(),
             'admitted_at_utc': '2026-10-21T00:00:00Z',
             'registrations': [{'source_identity': r['source_identity'],
                                'source_instance_id': f'SRC{900000+i:06d}'}
                               for i, r in enumerate(roster)],
             'scopes': {'admission': {'cohort': 'N450', 'bindings': n450,
                                      'destination': str(entry.ADMISSION)},
                        'freeze': {'cohort': 'C750', 'bindings': c750,
                                   'destination': str(entry.FREEZE)}}}
    admitted = entry.admission_files(tmp_path, grant)
    frozen = entry.freeze_files(tmp_path, grant, admitted)
    grant['scopes']['admission']['files_sha256'] = {n: auth.sha(b) for n, b in admitted.items()}
    grant['scopes']['freeze']['files_sha256'] = {n: auth.sha(b) for n, b in frozen.items()}
    grant_path = tmp_path / auth.OWNER_GRANT_PATH
    grant_path.parent.mkdir(parents=True)

    def install():
        grant_path.write_text(json.dumps(grant))
        monkeypatch.setattr(auth, 'OWNER_GRANT_SHA256', auth.sha(grant_path.read_bytes()))

    install()
    local = Mock()
    historical = Mock()
    monkeypatch.setattr(auth, 'verify_local_bytes', local)
    monkeypatch.setattr(auth, 'verify_historical_bytes', historical)
    return tmp_path, entry, grant, n450, c750, install, local, historical


def test_actual_admission_and_freeze_synthetic_publication(publication_context):
    root, entry, grant, n450, c750, _, local, historical = publication_context
    protected = {p: p.read_bytes() for p in (root / 'metadata').rglob('*') if p.is_file()}
    with pytest.raises(FileNotFoundError):
        entry.freeze(root, c750, root / entry.FREEZE)
    assert not (root / entry.FREEZE).exists()
    assert entry.admit(root, n450, root / entry.ADMISSION)['status'] == 'PUBLISHED'
    assert entry.freeze(root, c750, root / entry.FREEZE)['status'] == 'PUBLISHED'
    local.assert_called()
    historical.assert_called()
    assert all(p.read_bytes() == raw for p, raw in protected.items())
    for action, path in [('admission', entry.ADMISSION), ('freeze', entry.FREEZE)]:
        assert {p.name: auth.sha(p.read_bytes()) for p in (root / path).iterdir()} == (
            grant['scopes'][action]['files_sha256'])
    with pytest.raises(ScopeDenied, match='PUBLICATION_ALREADY_EXISTS'):
        entry.admit(root, n450, root / entry.ADMISSION)
    with pytest.raises(ScopeDenied, match='PUBLICATION_ALREADY_EXISTS'):
        entry.freeze(root, c750, root / entry.FREEZE)


@pytest.mark.parametrize('action', ['admission', 'freeze'])
@pytest.mark.parametrize('failure', ['missing', 'forged', 'outside', 'holdout', 'path', 'hash',
                                     'duplicate', 'cohort', 'destination', 'output_hash', 'raw'])
def test_publication_denials_before_writes(publication_context, action, failure, monkeypatch):
    root, entry, grant, n450, c750, install, local, _historical = publication_context
    bindings = json.loads(json.dumps(n450 if action == 'admission' else c750))
    output = root / (entry.ADMISSION if action == 'admission' else entry.FREEZE)
    if failure == 'missing':
        monkeypatch.setattr(auth, 'OWNER_GRANT_SHA256', None)
    elif failure == 'forged':
        (root / auth.OWNER_GRANT_PATH).write_text('{"status":"OWNER_APPROVED"}')
    elif failure in {'outside', 'holdout', 'path', 'hash', 'duplicate'}:
        if failure == 'outside':
            bindings[0]['source_instance_id' if action == 'admission' else 'source_identity'] = 'SRC000705'
        elif failure == 'holdout':
            held = next(m for m in auth.UniverseGate.load(root).document()['members'] if m['holdout'])
            bindings[0]['source_instance_id' if action == 'admission' else 'source_identity'] = held['identity']
        elif failure == 'path':
            bindings[0]['raw_path'] = '/unauthorized'
        elif failure == 'hash':
            bindings[0]['raw_sha256'] = '0' * 64
        else:
            bindings[-1] = bindings[0]
    elif failure == 'cohort':
        grant['scopes'][action]['cohort'] = 'C300'
        install()
    elif failure == 'destination':
        output = root / 'metadata/unauthorized'
    elif failure == 'output_hash':
        grant['scopes'][action]['files_sha256'] = {}
        install()
    elif failure == 'raw':
        local.side_effect = ScopeDenied('RAW_INTEGRITY_MISMATCH')
    # Freeze publication negatives need a completed *temporary synthetic* admission
    # to reach output-scope validation. No actual repo admission is performed.
    if action == 'freeze' and failure in {'destination', 'output_hash'}:
        entry.admit(root, n450, root / entry.ADMISSION)
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    reason = {'missing': 'OWNER_EXECUTION_GRANT_NOT_INSTALLED',
              'forged': 'OWNER_GRANT_PIN_MISMATCH', 'cohort': 'ACTION_NOT_AUTHORIZED',
              'destination': 'PUBLICATION_DESTINATION_MISMATCH',
              'output_hash': 'PUBLICATION_BYTES_NOT_APPROVED',
              'raw': 'RAW_INTEGRITY_MISMATCH'}.get(failure, 'EXACT_INPUT_SET_REQUIRED')
    with pytest.raises(ScopeDenied, match=reason):
        (entry.admit if action == 'admission' else entry.freeze)(root, bindings, output)
    assert not output.exists()
    assert {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()} == before


def test_freeze_rejects_changed_admission(publication_context):
    root, entry, _, n450, c750, _, _, _ = publication_context
    entry.admit(root, n450, root / entry.ADMISSION)
    (root / entry.ADMISSION / 'bindings.json').write_text('[]')
    with pytest.raises(ScopeDenied, match='ADMISSION_BYTES_CHANGED'):
        entry.freeze(root, c750, root / entry.FREEZE)
    assert not (root / entry.FREEZE).exists()


def test_freeze_rejects_historical_raw_failure(publication_context):
    root, entry, _, _, c750, _, _, historical = publication_context
    historical.side_effect = ScopeDenied('C300_RAW_INTEGRITY_MISMATCH')
    with pytest.raises(ScopeDenied, match='C300_RAW_INTEGRITY_MISMATCH'):
        entry.freeze(root, c750, root / entry.FREEZE)
    assert not (root / entry.FREEZE).exists()


def test_admission_rejects_registration_collision(publication_context):
    root, entry, grant, n450, _, install, _, _ = publication_context
    grant['registrations'][0]['source_instance_id'] = 'SRC000005'
    install()
    with pytest.raises(ScopeDenied, match='REGISTRATION_ID_COLLISION'):
        entry.admit(root, n450, root / entry.ADMISSION)
    assert not (root / entry.ADMISSION).exists()


@pytest.fixture
def historical_resolver(tmp_path, monkeypatch):
    """Synthetic pinned Universe/inventory; exercise the real alias and hash checks."""
    from edp_lab.ingestion import universe as u
    from edp_lab.ingestion.c300_admission import csv_bytes

    physical_root = tmp_path / 'shared/data/raw'
    monkeypatch.setattr(auth, 'HISTORICAL_RAW_ROOT', physical_root)
    members, bindings, inventory = [], [], []
    for i in range(300):
        relative = f'data/raw/test/{i}.raw'
        path = physical_root / f'test/{i}.raw'
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = str(i).encode()
        path.write_bytes(raw)
        digest = auth.sha(raw)
        identity = f'delivery-{i}'
        members.append({'identity': identity, 'raw_path': str(path),
                        'raw_sha256': digest, 'holdout': False})
        bindings.append({'delivery_identity': identity, 'identity': f'SRC{i+1:06d}',
                         'raw_path': relative, 'raw_sha256': digest})
        inventory.append({'inventory_id': identity, 'final_path': str(path),
                          'sha256': digest, 'bytes': str(len(raw))})
    side = {'universe_manifest_sha256': '', 'bindings': bindings,
            'cohorts': {'C300': {'identities': [b['identity'] for b in bindings]}}}
    doc = {'schema': 'SOURCE_UNIVERSE_AUTHORITY_V1', 'universe_version': 'TEST_ONLY',
           'approval_reference': 'TEST_ONLY', 'inventory_reference': 'inventory.csv',
           'inventory_sha256': '', 'member_count': 300, 'members': members}

    def install():
        inv = csv_bytes(tuple(inventory[0]), inventory)
        (tmp_path / 'inventory.csv').write_bytes(inv)
        doc['inventory_sha256'] = auth.sha(inv)
        raw = json.dumps(doc).encode()
        side['universe_manifest_sha256'] = auth.sha(raw)
        side_raw = json.dumps(side).encode()
        monkeypatch.setattr(u, 'BINDINGS_SHA256', auth.sha(side_raw))
        gate = u.UniverseGate(raw, auth.sha(raw), side_raw)
        monkeypatch.setattr(auth.UniverseGate, 'load', classmethod(lambda cls, root: gate))

    install()
    return tmp_path, physical_root, members, bindings, inventory, install


def test_historical_resolver_valid_shared_root(historical_resolver):
    root, _, _, bindings, _, _ = historical_resolver
    assert not (root / 'data/raw').exists()
    original = json.dumps(bindings)
    result = auth.verify_historical_bytes(root)
    assert result['verified_sources'] == 300
    assert result['verified_bytes'] == sum(len(str(i)) for i in range(300))
    assert json.dumps(bindings) == original


@pytest.mark.parametrize('failure,reason', [
    ('wrong_path', 'C300_PHYSICAL_PATH_MISMATCH'),
    ('traversal', 'UNSAFE_C300_REGISTRY_PATH'),
    ('absolute_alias', 'UNSAFE_C300_REGISTRY_PATH'),
    ('wrong_identity', 'INVALID_AUTHORITY'),
    ('wrong_inventory_path', 'C300_INVENTORY_BINDING_MISMATCH'),
    ('size', 'C300_RAW_INTEGRITY_MISMATCH'),
    ('hash', 'C300_RAW_INTEGRITY_MISMATCH'),
    ('missing', 'INVALID_OR_MISSING_C300_RAW_EVIDENCE'),
    ('symlink_escape', 'UNSAFE_C300_PHYSICAL_PATH'),
])
def test_historical_resolver_fails_closed(historical_resolver, failure, reason):
    root, physical, members, bindings, inventory, install = historical_resolver
    path = physical / 'test/0.raw'
    if failure == 'wrong_path':
        members[0]['raw_path'] = str(root / 'outside.raw')
    elif failure == 'traversal':
        bindings[0]['raw_path'] = 'data/raw/../../outside.raw'
    elif failure == 'absolute_alias':
        bindings[0]['raw_path'] = str(path)
    elif failure == 'wrong_identity':
        bindings[0]['delivery_identity'] = 'not-authorized'
    elif failure == 'wrong_inventory_path':
        inventory[0]['final_path'] = str(root / 'outside.raw')
    elif failure == 'size':
        inventory[0]['bytes'] = '123'
    elif failure == 'hash':
        path.write_bytes(b'X')  # Same size; content hash must still fail.
    elif failure == 'missing':
        path.unlink()
    elif failure == 'symlink_escape':
        path.unlink()
        outside = root / 'outside.raw'
        outside.write_bytes(b'0')  # Correct bytes cannot authorize an outside locator.
        path.symlink_to(outside)
    install()
    with pytest.raises(ScopeDenied, match=reason):
        auth.verify_historical_bytes(root)
