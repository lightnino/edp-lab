"""Post-approval shallow orchestration over verified immutable C300 evidence.

A current parent SHA check proves the archived member bytes are unchanged. Reuse
of the sealed, full-member validation avoids redundant decompression and parsing.
The pure orchestrator never loads files or creates authority; the host does both.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.parsers.c300_v1 import require_activation, roster
from edp_lab.profiling.source_reader import canonical_hash, digest

VERSION = 'C300_POST_APPROVAL_SHALLOW_V1'
PACKET_SHA256 = '3873e9d07e4bcc2f357f940d05cf4fc5dc1262358b641d1debba2ef117910e05'


def verified_json(root: Path, relative: str, expected: str):
    import json

    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'EVIDENCE_SHA256_MISMATCH {relative}')
    raw = path.read_bytes()
    if digest(raw) != expected:
        raise ValueError(f'EVIDENCE_SHA256_MISMATCH {relative}')
    return json.loads(raw)


def load_evidence(root: Path, prior_reference: dict, approval: dict):
    """Host gates: exact packet/scope, sealed evidence, parser code and current RAW.

    No member is reopened: the unchanged parent plus the sealed prior member hash
    and completed scan establish the exact same member population and locators.
    """
    packet = verified_json(root, prior_reference['approval_packet_path'], PACKET_SHA256)
    checkpoint = verified_json(root, prior_reference['checkpoint_path'],
                               prior_reference['checkpoint_sha256'])
    for rel, expected in checkpoint['artifact_sha256'].items():
        if file_sha256(root / rel) != expected:
            raise ValueError(f'CHECKPOINT_ARTIFACT_MISMATCH {rel}')
    registry = verified_json(root, packet['registry_path'], packet['registry_sha256'])
    require_activation(registry, approval)
    if (approval.get('approval_packet_sha256') != PACKET_SHA256
            or approval.get('eligible_binding_fingerprints') !=
            packet['eligible_binding_fingerprints']):
        raise PermissionError('EXACT_PACKET_SCOPE_REQUIRED')
    for rel, expected in packet['implementation_sha256'].items():
        if file_sha256(root / rel) != expected:
            raise ValueError(f'APPROVED_IMPLEMENTATION_CHANGED {rel}')
    registry_ids = [canonical_hash(b) for b in registry['bindings']]
    allowed = set(packet['eligible_binding_fingerprints'])
    passing = {canonical_hash(b) for b in registry['bindings']
               if b['discovery_validation'] == 'PASS'}
    if (len(registry_ids) != len(set(registry_ids)) or len(allowed) != packet['eligible_count']
            or allowed != passing):
        raise ValueError('APPROVED_MEMBERSHIP_MISMATCH')
    validation_rel = next(p for p in packet['evidence'] if p.endswith(
        '/validation-and-approval.json'))
    validation = verified_json(root, validation_rel, packet['evidence'][validation_rel])
    inventory_rel = next(p for p in packet['evidence'] if p.endswith('/inventory.json'))
    inventory = verified_json(root, inventory_rel, packet['evidence'][inventory_rel])
    scans = {canonical_hash(t['source']): t for t in validation['tables']}
    if set(scans) != set(registry_ids) or len(scans) != len(validation['tables']):
        raise ValueError('VALIDATION_COVERAGE_MISMATCH')
    sources = roster(root)
    by_id = {s['source_instance_id']: s for s in sources}
    if set(by_id) != {b['source_instance_id'] for b in registry['bindings']}:
        raise ValueError('SOURCE_COVERAGE_MISMATCH')
    for binding in registry['bindings']:
        row = by_id[binding['source_instance_id']]
        if any(binding[k] != row[k] for k in ('raw_path', 'raw_sha256', 'source_family')):
            raise ValueError('FROZEN_SOURCE_BINDING_MISMATCH')
        scan = scans[canonical_hash(binding)]
        if canonical_hash(binding) in allowed:
            result = scan['inspection']
            if (scan['validation'] != 'PASS' or result['validation'] != 'PASS'
                    or result['scan_scope'] != 'FULL_BYTES' or result['errors']
                    or result['member_sha256'] != binding['member_sha256']
                    or result['header'] != binding['expected_header']
                    or result['uncompressed_bytes'] != binding['uncompressed_bytes']
                    or result['prefix_evidence'] != binding['prefix_evidence']):
                raise ValueError('INCOMPLETE_OR_MISMATCHED_PRIOR_SCAN')
    raw_bytes = 0
    for source in sources:
        path = root / source['raw_path']
        if file_sha256(path) != source['raw_sha256']:
            raise ValueError(f"RAW_SHA256_MISMATCH {source['source_instance_id']}")
        raw_bytes += path.stat().st_size
    return {'registry': registry, 'packet': packet, 'approval': deepcopy(approval),
            'validation': validation, 'inventory': inventory, 'sources': sources,
            'raw_bytes_verified': raw_bytes,
            'validation_ref': {'path': validation_rel, 'sha256': packet['evidence'][validation_rel]},
            'inventory_ref': {'path': inventory_rel, 'sha256': packet['evidence'][inventory_rel]}}


def observe(evidence: dict, provenance: dict):
    """Execute every approved binding using already validated mechanical results."""
    allowed = set(evidence['approval']['eligible_binding_fingerprints'])
    scans = {canonical_hash(t['source']): t for t in evidence['validation']['tables']}
    trace = []
    for sequence, binding in enumerate(evidence['registry']['bindings']):
        fingerprint = canonical_hash(binding)
        scan = scans[fingerprint]
        entry = {'sequence': sequence, 'binding': deepcopy(binding),
                 'binding_fingerprint': fingerprint,
                 'validation_status': scan['validation'],
                 'mode': 'VERIFIED_EVIDENCE_REUSE',
                 'evidence_ref': {**evidence['validation_ref'],
                                  'source_instance_id': binding['source_instance_id'],
                                  'archive_member': binding['archive_member']}}
        if fingerprint in allowed:
            if scan['validation'] != 'PASS' or scan['inspection']['scan_scope'] != 'FULL_BYTES':
                raise ValueError('FAILED_EVIDENCE_CANNOT_EXECUTE')
            entry.update(status='PASS', result=deepcopy(scan['inspection']), errors=[])
        else:
            entry.update(status='BLOCKED', result=None,
                         errors=['EXCLUDED_FAILED_BINDING; retained in original evidence'])
        entry['result_fingerprint'] = canonical_hash(entry)
        trace.append(entry)
    report = {'version': VERSION, 'agent_version': 'EDP_ANALYST_AGENT_V0',
              'scope': 'SHALLOW_MECHANICAL_INSPECTION_WITH_VERIFIED_EVIDENCE_REUSE',
              'new_member_scans': 0, 'full_profiling': False,
              'approval_packet_sha256': PACKET_SHA256,
              'approval_fingerprint': canonical_hash(evidence['approval']),
              'registry_fingerprint': canonical_hash(evidence['registry']),
              'provenance': deepcopy(provenance), 'trace': trace,
              'instances': [{'source_instance_id': s['source_instance_id'],
                             'pass': sum(t['status'] == 'PASS' and t['binding'][
                                 'source_instance_id'] == s['source_instance_id'] for t in trace),
                             'blocked': sum(t['status'] == 'BLOCKED' and t['binding'][
                                 'source_instance_id'] == s['source_instance_id'] for t in trace)}
                            for s in evidence['sources']],
              'findings': [{'state': 'VALIDATED', 'claim':
                            'Approved lexical evidence reused after current parent hash verification'},
                           {'state': 'UNRESOLVED', 'claim':
                            '12 failed bindings; source NULL semantics and all business identities'}],
              'semantic_promotions': [], 'side_effects': []}
    report['result_fingerprint'] = canonical_hash(report)
    return report


def evaluate(report: dict, evidence: dict):
    """Independent expectation assembly from original discovery member evidence."""
    expected = {(s['source_instance_id'], m['archive_member']): m
                for s in evidence['inventory']['instances'] for m in s['members']
                if m['kind'] == 'TABLE'}
    allowed = set(evidence['packet']['eligible_binding_fingerprints'])
    checks = []
    for entry in report['trace']:
        binding = entry['binding']
        member = expected[binding['source_instance_id'], binding['archive_member']]
        if canonical_hash(binding) in allowed:
            result = entry['result']
            expected_result = {k: v for k, v in member.items() if k not in {
                'archive_member', 'declared_bytes', 'compressed_bytes', 'kind'}}
            equal = entry['status'] == 'PASS' and result == expected_result
        else:
            equal = entry['status'] == 'BLOCKED' and entry['result'] is None and (
                member['validation'] == 'FAILED')
        checks.append({'binding_fingerprint': canonical_hash(binding), 'equal': equal})
    fingerprints = all(canonical_hash({k: v for k, v in t.items()
                                      if k != 'result_fingerprint'}) == t['result_fingerprint']
                       for t in report['trace'])
    report_valid = canonical_hash({k: v for k, v in report.items()
                                  if k != 'result_fingerprint'}) == report['result_fingerprint']
    actual_ids = [c['binding_fingerprint'] for c in checks]
    expected_ids = {canonical_hash(b) for b in evidence['registry']['bindings']}
    complete = len(actual_ids) == len(set(actual_ids)) and set(actual_ids) == expected_ids
    return {'version': 'C300_POST_APPROVAL_EVALUATION_V1',
            'status': 'PASS' if checks and all(c['equal'] for c in checks)
            and fingerprints and report_valid and complete
            and not report['semantic_promotions'] and not report['side_effects'] else 'FAILED',
            'coverage': len(checks), 'checks': checks,
            'exact_coverage': complete,
            'trace_fingerprints_valid': fingerprints, 'report_fingerprint_valid': report_valid,
            'independence': 'Expectations assembled from sealed discovery, not agent validation dispatch'}
