"""Reproduce bounded FD/key observations and separate V1→V2 examples."""
import argparse
import json
from copy import deepcopy
from pathlib import Path

from edp_lab.agents.candidates_v2 import propose
from edp_lab.agents.structural_evidence import attach_structural_evidence
from edp_lab.profiling.declared_fd import declared_fd
from edp_lab.profiling.source_reader import SourceTable, canonical_hash, digest
from edp_lab.profiling.tools import candidate_key_scan

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'metadata/evaluations/agent_v1'


def evaluate():
    raw = (BASE / 'observations_v1.json').read_bytes()
    data = json.loads(raw)
    table = SourceTable(
        columns=tuple(data['columns']), rows=tuple(tuple(r) for r in data['rows']),
        locators=tuple(data['locators']), source=data['source'],
        config={'selection': data['selection'], 'input_sha256': digest(raw)},
        provenance={'artifact': data['artifact'], 'pointer': data['artifact_pointer']},
        null_tokens=None, accounting={'supplied_occurrences': len(data['rows']),
                                     'whole_table': False},
    )
    supported = declared_fd(table, ['adsh'], ['cik', 'period'])
    violated = declared_fd(table, ['form'], ['cik'])
    keys = candidate_key_scan(table, composites=[('form', 'period'), ('adsh', 'period')])
    keys['population']['scope'] = 'DECLARED_INPUT_OCCURRENCES_ONLY'
    keys['population']['sampling_method'] = data['selection']
    keys['result_sha256'] = canonical_hash({k: v for k, v in keys.items()
                                          if k != 'result_sha256'})
    original = json.loads((ROOT / 'metadata/evaluations/agent_v2/inputs_v1.json').read_text())
    useful = deepcopy(next(c for c in original['cases'] if c['id'] == 'S05'))
    useful['id'] = 'V1_USEFUL_SCHEMA_CONTEXT'
    useful_report = attach_structural_evidence(propose(useful, original['witnesses']),
                                               [supported, keys])
    # Same 10-Q and reporting period do not justify merging native registrant CIKs.
    witnesses, endpoints = {}, []
    for line in (84, 281):
        i = next(i for i, loc in enumerate(table.locators) if loc['source_line'] == line)
        fields = dict(zip(table.columns, table.rows[i], strict=True))
        name = f'sub{line}'
        witnesses[name] = {'fields': fields, 'source': table.source,
                           'locator': table.locators[i]}
        endpoints.append({'witness': name, 'field': 'cik', 'value': fields['cik'],
                          'namespace': 'SEC_CIK', 'unit': '', 'grain': 'SUB filing',
                          'role': 'registrant', 'time': fields['period'],
                          'occurrence': f'SRC000004/sub.txt/{line}'})
    unsafe = {'id': 'V1_UNSAFE_FORM_RELATION', 'dimension': 'ER',
              'question': 'canonical_entity', 'left': endpoints[0], 'right': endpoints[1],
              'review_required': True}
    unsafe_report = attach_structural_evidence(propose(unsafe, witnesses), [violated, keys])
    result = {
        'version': 'BOUNDED_DECLARED_FD_EVALUATION_V1', 'observations_sha256': digest(raw),
        'supported_fd': supported, 'violated_fd': violated, 'keys': keys,
        'v2_examples': [useful_report, unsafe_report],
        'side_effects': [], 'semantic_promotions': [],
    }
    result['result_sha256'] = canonical_hash(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Create new evidence; refuses overwrite')
    args = parser.parse_args()
    result = evaluate()
    path = BASE / 'results_v1.json'
    if args.write:
        with path.open('x') as stream:
            stream.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    else:
        assert result == json.loads(path.read_text()), 'Evidence reproduction mismatch'
    print(json.dumps({'status': 'REPRODUCED', 'rows': 5,
                      'fd_literal': [result[k]['literal_status']
                                     for k in ('supported_fd', 'violated_fd')],
                      'self_join_pairs_on_form': result['violated_fd']['literal_self_join_pairs'],
                      'fingerprint': result['result_sha256']}, sort_keys=True))


if __name__ == '__main__':
    main()
