"""Attach bounded V1 observations to an existing V2 candidate report."""
from copy import deepcopy

from edp_lab.agents.candidates_v2 import validate_candidate
from edp_lab.profiling.source_reader import canonical_hash


def attach_structural_evidence(proposal, evidence):
    """Structural evidence cannot promote semantic mappings or business keys."""
    validate_candidate(proposal)
    if not evidence or any(e.get('function') not in {'declared_fd', 'candidate_key_scan'}
                           or e.get('parse_status') != 'PASS' or e.get('status') == 'BLOCKED'
                           or canonical_hash({k: v for k, v in e.items()
                                              if k != 'result_sha256'}) != e.get('result_sha256')
                           for e in evidence):
        raise ValueError('INVALID_STRUCTURAL_EVIDENCE')
    sources = [ref['source'] for ref in proposal['supporting_evidence'] if 'source' in ref]
    if any(e['source'] not in sources for e in evidence):
        raise ValueError('STRUCTURAL_SOURCE_MISMATCH')
    result = deepcopy(proposal)
    for item in evidence:
        result['supporting_evidence'].append({
            'function': item['function'], 'result_sha256': item['result_sha256'],
            'source': deepcopy(item['source']), 'population': deepcopy(item['population']),
            'parameters': deepcopy(item['parameters']),
        })
    unsafe = any(e['function'] == 'declared_fd' and e['literal_status'] != 'PASS'
                 for e in evidence)
    result['candidate_label'] = 'UNRESOLVED' if unsafe else result['candidate_label']
    result['state'] = 'UNRESOLVED' if unsafe else (
        'PROPOSED' if result['state'] == 'VALIDATED' else result['state'])
    result['human_review_required'] = True
    result['reason'] += '; bounded V1 structural evidence attached; no business FD/key approval'
    if unsafe:
        result['conflicting_evidence'].append('Declared FD is violated or has no evidence')
    result['result_fingerprint'] = canonical_hash({k: v for k, v in result.items()
                                                 if k != 'result_fingerprint'})
    validate_candidate(result)
    return result
