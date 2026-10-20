"""Authorized shallow C300 inspection; never claims full statistical profiling.

Reuses the bounded parser validator. GOLD's five profiling adapters remain the
Agent's statistical implementation; this path reports only lexical scan evidence.
"""
import zipfile
from pathlib import Path

from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.parsers.c300_v1 import (
    MAX_LINE,
    PROFILES,
    VERSION,
    require_activation,
    roster,
    verify_binding,
)
from edp_lab.profiling.source_reader import canonical_hash, execution_provenance


def inspect(root: Path, registry: dict, approval: dict | None):
    require_activation(registry, approval)
    if (registry['version'] != VERSION or registry['profiles'] != PROFILES
            or registry['max_line_bytes'] != MAX_LINE
            or registry['null_semantics'] != 'UNRESOLVED'
            or registry['parser_code_sha256'] != file_sha256(
                root / 'src/edp_lab/parsers/c300_v1.py')):
        raise ValueError('UNSUPPORTED_REGISTRY')
    rows = {r['source_instance_id']: r for r in roster(root)}
    trace = []
    for binding in registry['bindings']:
        entry = {'binding': binding, 'status': 'BLOCKED', 'errors': []}
        try:
            row = rows[binding['source_instance_id']]
            if any(row[k] != binding[k] for k in ('raw_path', 'raw_sha256', 'source_family')):
                raise ValueError('FROZEN_SOURCE_BINDING_MISMATCH')
            if binding['discovery_validation'] != 'PASS':
                raise ValueError('DISCOVERY_VALIDATION_FAILED')
            result = verify_binding(root, binding)
            entry.update(status=result['validation'], result=result)
        except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError) as exc:
            entry.update(status='FAILED', errors=[str(exc)])
        entry['result_fingerprint'] = canonical_hash(entry)
        trace.append(entry)
    report = {'version': 'C300_SHALLOW_OBSERVATION_V1', 'agent_version': 'EDP_ANALYST_AGENT_V0',
              'scope': 'SHALLOW_LEXICAL_INSPECTION_FULL_MEMBER_BYTES', 'full_profiling': False,
              'registry_fingerprint': canonical_hash(registry),
              'approval_fingerprint': canonical_hash(approval),
              'provenance': execution_provenance(root), 'trace': trace,
              'instances': [{'source_instance_id': sid,
                             'tables': sum(t['binding']['source_instance_id'] == sid for t in trace)}
                            for sid in rows],
              'semantic_promotions': [], 'side_effects': [],
              'unresolved': ['NULL semantics', 'All business identity and key decisions']}
    report['result_fingerprint'] = canonical_hash(report)
    return report
