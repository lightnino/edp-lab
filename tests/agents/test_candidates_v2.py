"""Bounded discovery regressions and existing read-only authorization boundary."""
import hashlib
import json
import socket
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

import pytest
from conftest import authorized_host

from edp_lab.agents.candidates_v2 import propose, score, validate_candidate
from edp_lab.profiling.source_reader import canonical_hash, read_synthetic

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'metadata/evaluations/agent_v2'


def load():
    return (json.loads((BASE / 'inputs_v1.json').read_text()),
            json.loads((BASE / 'ground_truth_v1.json').read_text()))


def test_fixed_labels_follow_evidence_not_agent_output():
    inputs, truth = load()
    assert hashlib.sha256((BASE / 'inputs_v1.json').read_bytes()).hexdigest() == (
        truth['inputs_sha256'])
    assert hashlib.sha256((BASE / 'ground_truth_v1.json').read_bytes()).hexdigest() == (
        '9ba83190b260b1bb5ac7feb0043fa7591b9da846f49a40be0d7fe6c4428477fd')
    assert 'expected_label' not in json.dumps(inputs)
    before = deepcopy(inputs)
    reports = [propose(case, inputs['witnesses']) for case in inputs['cases']]
    assert inputs == before
    assert reports == [propose(case, inputs['witnesses']) for case in inputs['cases']]
    assert all(validate_candidate(r) for r in reports)
    metrics = score(reports, truth['cases'])
    assert metrics['candidate_label']['correct'] == len(truth['cases'])
    assert metrics['name_only_baseline_label']['false_match_ids']
    assert metrics['name_only_baseline_label']['false_split_ids']
    assert not any(r['semantic_promotions'] or r['promotion_eligible'] for r in reports)
    # Missing/duplicate proposals cannot improve metrics by changing denominator.
    with pytest.raises(ValueError, match='CASE_ACCOUNTING'):
        score(reports[:-1], truth['cases'])
    with pytest.raises(ValueError, match='CASE_ACCOUNTING'):
        score([*reports[:-1], reports[0]], truth['cases'])


def test_same_cusip_does_not_merge_occurrences_or_canonical_entities():
    inputs, _ = load()
    reports = {c['id']: propose(c, inputs['witnesses']) for c in inputs['cases']}
    assert reports['E03']['candidate_label'] == 'NON_MATCH'
    assert reports['E04']['candidate_label'] == 'MATCH'
    assert reports['E05']['candidate_label'] == reports['E12']['candidate_label'] == 'UNRESOLVED'
    assert reports['E05']['state'] == 'UNRESOLVED'
    assert reports['S05']['state'] == reports['S06']['state'] == 'PROPOSED'


def test_source_tampering_label_leak_and_semantic_promotion_are_rejected():
    inputs, _ = load()
    case = deepcopy(inputs['cases'][0])
    case['left']['value'] = 'FABRICATED'
    with pytest.raises(ValueError, match='SOURCE_OBSERVATION_CHANGED'):
        propose(case, inputs['witnesses'])
    case = deepcopy(inputs['cases'][0])
    case['expected_label'] = 'MATCH'
    with pytest.raises(ValueError, match='LABEL_LEAK'):
        propose(case, inputs['witnesses'])
    report = propose(inputs['cases'][0], inputs['witnesses'])
    report['semantic_promotions'] = [{'canonical_identity': 'FORGED'}]
    report['result_fingerprint'] = canonical_hash({k: v for k, v in report.items()
                                                  if k != 'result_fingerprint'})
    with pytest.raises(ValueError, match='PROMOTION_ATTEMPT'):
        validate_candidate(report)
    report = propose(inputs['cases'][0], inputs['witnesses'])
    report['approved_crosswalk'] = {'x': 'y'}
    with pytest.raises(ValueError):
        validate_candidate(report)


def test_pure_agent_has_no_filesystem_or_network_side_effects(monkeypatch):
    inputs, _ = load()

    def forbidden(*args, **kwargs):
        raise AssertionError('Unexpected I/O')

    monkeypatch.setattr(Path, 'read_text', forbidden)
    monkeypatch.setattr(Path, 'write_text', forbidden)
    monkeypatch.setattr(Path, 'write_bytes', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    assert validate_candidate(propose(inputs['cases'][0], inputs['witnesses']))


def test_agent_proposal_cannot_write_approved_stores_via_existing_adapter(tmp_path):
    # Explicit synthetic protected-store fixtures, not invented production stores.
    stores = [tmp_path / name for name in ('mappings.json', 'crosswalks.json', 'identities.json')]
    for path in stores:
        path.write_text('{"approved":"UNCHANGED"}\n')
    before = {p.name: p.read_bytes() for p in stores}
    table = read_synthetic(b'id\n001\n', delimiter='\t', quote=None, null_tokens=None,
                           expected_header=('id',), provenance={'test': 'READ_ONLY_BOUNDARY'})
    host = authorized_host({'fixture': table}, {'agent': {'fixture'}})
    inputs, _ = load()
    candidate = propose(inputs['cases'][0], inputs['witnesses'])
    attack = {'tool': 'publish_mapping', 'source': asdict(host.source_ref('fixture')),
              'authorization': {'principal': 'agent', 'permission': 'WRITE_MAPPING'},
              'parameters': {'candidate': candidate, 'destinations': [str(p) for p in stores]},
              'approval': 'OWNER_APPROVED'}
    denied = host.invoke(attack).to_dict()
    assert denied['status'] == 'BLOCKED' and denied['approval_required']
    assert denied['result'] is None and not denied['side_effects']
    attack.pop('approval')
    unsupported = host.invoke(attack).to_dict()
    assert unsupported['status'] == 'FAILED' and unsupported['result'] is None
    assert not unsupported['side_effects']
    assert {p.name: p.read_bytes() for p in stores} == before
