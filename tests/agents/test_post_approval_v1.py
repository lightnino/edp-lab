from copy import deepcopy

import pytest

from edp_lab.agents.post_approval_v1 import evaluate, observe, verified_json
from edp_lab.profiling.source_reader import canonical_hash


def fixture_evidence():
    bindings, scans, members = [], [], []
    for i in range(3):
        status = 'PASS' if i < 2 else 'FAILED'
        binding = {'source_instance_id': 'FIXTURE', 'archive_member': str(i),
                   'discovery_validation': status}
        result = {'validation': status, 'scan_scope': 'FULL_BYTES', 'data_records': i,
                  'member_sha256': str(i), 'prefix_evidence': [{'byte_offset': 0}]}
        bindings.append(binding)
        scans.append({'source': binding, 'validation': status, 'inspection': result})
        members.append({**result, 'archive_member': str(i), 'kind': 'TABLE'})
    allowed = [canonical_hash(b) for b in bindings[:2]]
    return {'registry': {'bindings': bindings},
            'approval': {'eligible_binding_fingerprints': allowed},
            'packet': {'eligible_binding_fingerprints': allowed},
            'validation': {'tables': scans},
            'inventory': {'instances': [{'source_instance_id': 'FIXTURE', 'members': members}]},
            'sources': [{'source_instance_id': 'FIXTURE'}],
            'validation_ref': {'path': 'fixture.json', 'sha256': 'fixed'}}


def test_exact_scope_replay_and_independent_expectations():
    evidence = fixture_evidence()
    before = deepcopy(evidence)
    report = observe(evidence, {'runtime': 'fixed'})
    assert report == observe(evidence, {'runtime': 'fixed'})
    assert [t['status'] for t in report['trace']] == ['PASS', 'PASS', 'BLOCKED']
    assert report['trace'][2]['validation_status'] == 'FAILED'
    assert report['trace'][2]['result'] is None
    assert report['new_member_scans'] == 0 and not report['full_profiling']
    assert report['instances'] == [{'source_instance_id': 'FIXTURE', 'pass': 2, 'blocked': 1}]
    assert evaluate(report, evidence)['status'] == 'PASS'
    assert evidence == before
    report['trace'][0]['result']['data_records'] += 1
    assert evaluate(report, evidence)['status'] == 'FAILED'


def test_failed_binding_cannot_be_promoted():
    evidence = fixture_evidence()
    evidence['approval']['eligible_binding_fingerprints'].append(
        canonical_hash(evidence['registry']['bindings'][2]))
    with pytest.raises(ValueError, match='FAILED_EVIDENCE_CANNOT_EXECUTE'):
        observe(evidence, {})


def test_changed_evidence_is_rejected(tmp_path):
    path = tmp_path / 'evidence.json'
    path.write_text('{"scope": "changed"}')
    with pytest.raises(ValueError, match='EVIDENCE_SHA256_MISMATCH'):
        verified_json(tmp_path, 'evidence.json', '0' * 64)


def test_missing_binding_cannot_pass_evaluation():
    evidence = fixture_evidence()
    report = observe(evidence, {})
    report['trace'].pop()
    report['result_fingerprint'] = canonical_hash({k: v for k, v in report.items()
                                                  if k != 'result_fingerprint'})
    assert evaluate(report, evidence)['status'] == 'FAILED'


def test_actual_post_approval_scope_when_available():
    import json
    from pathlib import Path

    from edp_lab.agents.post_approval_v1 import PACKET_SHA256
    from edp_lab.ingestion.gold_set import file_sha256

    root = Path(__file__).resolve().parents[2]
    out = root / 'runs/c300-post-approval-v1'
    if not (out / 'report.json').exists():
        pytest.skip('Local post-approval execution evidence unavailable')
    report = json.loads((out / 'report.json').read_bytes())
    approval = json.loads((out / 'authorization.json').read_bytes())
    packet = root / 'runs/section-2-6/review-v1/approval-packet.json'
    assert file_sha256(packet) == approval['approval_packet_sha256'] == PACKET_SHA256
    allowed = set(approval['eligible_binding_fingerprints'])
    passed = {t['binding_fingerprint'] for t in report['trace'] if t['status'] == 'PASS'}
    blocked = [t for t in report['trace'] if t['status'] == 'BLOCKED']
    assert passed == allowed and len(passed) == 720
    assert len(blocked) == 12 and len(report['instances']) == 300
    assert all(t['validation_status'] == 'FAILED' and t['result'] is None for t in blocked)
    assert all(t['mode'] == 'VERIFIED_EVIDENCE_REUSE' for t in report['trace'])
    assert report['new_member_scans'] == 0 and not report['full_profiling']
