"""Owner-requested read-only N450 observations/B1; no CLEAN or parser activation.

Reuse the existing engineering inspector/validation iterator and profiling library.
The current owner's Step 2 instruction supplies this observation authority; the
Admission/Freeze grant supplies physical registration evidence only. Neither this
script nor its generated descriptors authorizes Step 3 processing.
"""
import csv
import json
import resource
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.ingestion import n450_authorization as admission_auth
from edp_lab.ingestion.c300_admission import encoded
from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.ingestion.universe import ScopeDenied, UniverseGate, sha
from edp_lab.parsers.c300_reader_v1 import validated_occurrences
from edp_lab.parsers.c300_v1 import PROFILES, VERSION, inspect_stream
from edp_lab.profiling import tools
from edp_lab.profiling.conventions import schema_fingerprint
from edp_lab.profiling.source_reader import SourceTable, canonical_hash, execution_provenance

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/n450/b1-v1'
LAB = Path('/Users/lightnino/Projects/edp-lab')
PACKET_SHA = '3873e9d07e4bcc2f357f940d05cf4fc5dc1262358b641d1debba2ef117910e05'
FAMILY = 'SEC_EDGAR_DAILY_MASTER'
MAX_STAT_BINDINGS = 3
MAX_STAT_ROWS = 20_000


def require(ok, reason):
    if not ok:
        raise ScopeDenied(reason)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(encoded(value))


def scope():
    """Verify the entire immutable physical input set before observation reads."""
    admission_auth.validate_packet(ROOT)
    authority = (ROOT / admission_auth.OWNER_GRANT_PATH).read_bytes()
    require(sha(authority) == admission_auth.OWNER_GRANT_SHA256, 'ADMISSION_AUTHORITY_CHANGED')
    grant = json.loads(authority)
    require(grant['status'] == 'OWNER_APPROVED', 'ADMISSION_NOT_APPROVED')
    for action in ('admission', 'freeze'):
        directory = ROOT / grant['scopes'][action]['destination']
        require({p.name: file_sha256(p) for p in directory.iterdir()} ==
                grant['scopes'][action]['files_sha256'], 'FROZEN_PUBLICATION_CHANGED')
    manifest = ROOT / grant['scopes']['admission']['destination'] / 'corpus_manifest_v4.csv'
    with manifest.open() as stream:
        rows = [r for r in csv.DictReader(stream) if r['introduced_cohort'] == 'N450']
    registrations = json.loads((manifest.parent / 'bindings.json').read_bytes())
    roster = json.loads((ROOT / admission_auth.PACKET / 'roster.json').read_bytes())
    require(len(rows) == len(registrations) == len(roster) == 450, 'N450_COUNT_MISMATCH')
    gate = UniverseGate.load(ROOT)
    for row, registration, physical in zip(rows, registrations, roster, strict=True):
        require(row['source_instance_id'] == registration['source_instance_id'] and
                registration['source_identity'] == physical['source_identity'] and
                row['raw_path'] == registration['raw_path'] == physical['raw_path'] and
                row['raw_sha256'] == registration['raw_sha256'] == physical['raw_sha256'] and
                row['source_family'] == physical['family'] == FAMILY, 'N450_BINDING_MISMATCH')
        gate.check(physical['source_identity'], row['raw_sha256'], row['raw_path'])
    return rows, roster, grant


def baseline():
    """Reuse exact reviewed C300 parser descriptors and frozen Day 2 metadata."""
    path = LAB / 'runs/section-2-6/review-v1/approval-packet.json'
    raw = path.read_bytes()
    require(sha(raw) == PACKET_SHA, 'BASELINE_PACKET_CHANGED')
    packet = json.loads(raw)
    registry_path = LAB / packet['registry_path']
    registry_raw = registry_path.read_bytes()
    require(sha(registry_raw) == packet['registry_sha256'], 'BASELINE_REGISTRY_CHANGED')
    registry = json.loads(registry_raw)
    require(registry['parser_code_sha256'] == file_sha256(ROOT / 'src/edp_lab/parsers/c300_v1.py'),
            'BASELINE_PARSER_REVISION_CHANGED')
    daily = [b for b in registry['bindings'] if b['source_family'] == FAMILY]
    require(len(daily) == 198 and registry['profiles'][FAMILY] == PROFILES[FAMILY],
            'BASELINE_DAILY_PROFILE_CHANGED')
    headers = {tuple(b['expected_header']) for b in daily}
    require(len(headers) == 1, 'BASELINE_HEADER_UNRESOLVED')
    return next(iter(headers)), {'packet_reference': str(path), 'packet_sha256': sha(raw),
        'registry_reference': str(registry_path), 'registry_sha256': sha(registry_raw),
        'parser_code_sha256': registry['parser_code_sha256'],
        'daily_bindings_reused': 198, 'model': 'M1_LEXICAL_V1',
        'model_contract': 'docs/day2_c300_m1_readiness_v1.md',
        'model_contract_sha256': file_sha256(ROOT / 'docs/day2_c300_m1_readiness_v1.md'),
        'frozen_baseline': 'metadata/freezes/O_C300_M1_v1/freeze.json',
        'frozen_baseline_sha256': file_sha256(ROOT / 'metadata/freezes/O_C300_M1_v1/freeze.json')}


def observe(row, physical, expected_header):
    path = Path(row['raw_path'])
    require(path.is_file() and not path.is_symlink(), 'MISSING_OR_LINKED_N450_RAW')
    require(path.stat().st_size == physical['bytes'] and file_sha256(path) == row['raw_sha256'],
            'N450_RAW_INTEGRITY_MISMATCH')
    with path.open('rb') as stream:
        observed = inspect_stream(stream, FAMILY)
    require(observed['member_sha256'] == row['raw_sha256'] and
            observed['uncompressed_bytes'] == physical['bytes'], 'N450_CHANGED_DURING_OBSERVATION')
    descriptor = {k: row[k] for k in ('source_instance_id', 'source_family', 'raw_path', 'raw_sha256')}
    descriptor.update(archive_member='', logical_table_name=path.name,
                      member_sha256=observed['member_sha256'],
                      uncompressed_bytes=observed['uncompressed_bytes'],
                      expected_header=observed['header'], prefix_evidence=observed['prefix_evidence'],
                      profile_id=f'{FAMILY}_{VERSION}', discovery_validation=observed['validation'])
    errors = list(observed['errors'])
    if tuple(observed['header']) != expected_header:
        errors.append('ORDERED_HEADER_DIFFERS_FROM_REVIEWED_M1_PROFILE')
    return {'source_instance_id': row['source_instance_id'], 'physical_identity': physical['source_identity'],
            'source_sha256': row['raw_sha256'], 'member_sha256': observed['member_sha256'],
            'source_fingerprint': canonical_hash({'registered': row, 'physical': physical}),
            'member_fingerprint': canonical_hash(descriptor),
            'schema_sha256': schema_fingerprint([(name, 'TEXT') for name in observed['header']]),
            'descriptor': descriptor, 'structure': observed, 'errors': errors,
            'classification': 'HUMAN_UNRESOLVED' if errors else 'FITS_EXISTING_MODEL'}


def occurrence_check(binding, expected_count, *, collect=False):
    """Observe intervals/lexical reconstruction only; never write CLEAN records."""
    counts = Counter()
    offset = 0
    rows, locators = [], []
    for record in validated_occurrences(ROOT, binding):
        require(record.byte_offset == offset, 'NONCONTIGUOUS_SOURCE_OCCURRENCE')
        counts[record.kind] += 1
        offset += len(record.original_bytes)
        if record.kind == 'DATA':
            content = record.original_bytes.removesuffix(b'\n').removesuffix(b'\r')
            ending = record.original_bytes[len(content):]
            require(len(record.fields) == len(binding['expected_header']) and
                    '|'.join(record.fields).encode('utf-8') + ending == record.original_bytes,
                    'LEXICAL_RECONSTRUCTION_MISMATCH')
            if collect:
                rows.append(record.fields)
                locators.append({'source_line': record.source_line, 'byte_offset': record.byte_offset,
                                 'byte_length': len(record.original_bytes)})
    require(counts['DATA'] == expected_count and offset == binding['uncompressed_bytes'],
            'OCCURRENCE_ACCOUNTING_MISMATCH')
    return {'accounting': dict(counts), 'covered_bytes': offset,
            'data_fields': counts['DATA'] * len(binding['expected_header']),
            'lexical_reconstruction': 'PASS', 'contiguous_occurrence_intervals': 'PASS'}, rows, locators


def main():
    started = datetime.now(UTC).isoformat()
    clock = time.perf_counter()
    rows, physical, grant = scope()
    expected_header, old_evidence = baseline()
    require(not OUT.exists(), 'OUTPUT_ALREADY_EXISTS')
    protected = {p: file_sha256(ROOT / p) for p in (
        'metadata/cohorts/C300.csv', 'metadata/corpus_manifest_v3.csv',
        'metadata/source_universes/approved_v1/manifest.json',
        'metadata/freezes/O_C300_M1_v1/freeze.json')}
    provenance = execution_provenance(ROOT)
    provenance['observation_driver_sha256'] = file_sha256(Path(__file__))
    provenance['step_authority'] = 'Explicit owner instruction DAY 3 STEP 2 N450 Profiling + B1 Model Fit'
    provenance['processing_authorization'] = 'NOT_GRANTED_BY_THIS_OBSERVATION'
    OUT.mkdir(parents=True)
    observations = []
    for row, member in zip(rows, physical, strict=True):
        try:
            result = observe(row, member, expected_header)
        except (OSError, ValueError) as exc:
            result = {'source_instance_id': row['source_instance_id'],
                      'physical_identity': member['source_identity'],
                      'classification': 'HUMAN_UNRESOLVED', 'errors': [str(exc)]}
        observations.append(result)
    eligible = [r for r in observations if r['classification'] == 'FITS_EXISTING_MODEL']
    choices = sorted({0, len(eligible)//2, len(eligible)-1}) if eligible else []
    selected = {eligible[i]['source_instance_id'] for i in choices[:MAX_STAT_BINDINGS]}
    for i, result in enumerate(observations, 1):
        if result['classification'] == 'FITS_EXISTING_MODEL':
            binding = result['descriptor']
            collect = (result['source_instance_id'] in selected and
                       result['structure']['data_records'] <= MAX_STAT_ROWS)
            try:
                check, values, locators = occurrence_check(
                    binding, result['structure']['data_records'], collect=collect)
                result['occurrence_validation'] = check
                if collect:
                    table = SourceTable(tuple(binding['expected_header']), tuple(values),
                        tuple(locators), binding,
                        {**PROFILES[FAMILY], 'quote': None, 'escape': None, 'types': 'ALL_TEXT',
                         'null_semantics': 'UNRESOLVED'}, provenance, None, check['accounting'])
                    stats = {'profile_table': tools.profile_table(table),
                             'schema_fingerprint': tools.schema_fingerprint(table),
                             'profile_columns': [tools.profile_column(table, name, top_limit=5,
                                                       sample_size=5, sample_seed=0)
                                                 for name in table.columns]}
                    save(OUT / 'statistics' / f'{result["source_instance_id"]}.json', stats)
                    result['statistical_profile'] = {'status': 'COMPLETE_FULL_SELECTED_TABLE',
                        'rows': len(values), 'columns': len(table.columns),
                        'reference': str((OUT / 'statistics' / f'{result["source_instance_id"]}.json')
                                         .relative_to(ROOT))}
                else:
                    result['statistical_profile'] = {'status': 'NOT_COMPUTED',
                        'reason': 'NOT_SELECTED_BY_BOUNDED_DESIGN' if
                        result['source_instance_id'] not in selected else 'ROW_BUDGET_EXCEEDED'}
            except (OSError, ValueError) as exc:
                result['classification'] = 'HUMAN_UNRESOLVED'
                result['errors'].append(str(exc))
        save(OUT / 'sources' / f'{result["source_instance_id"]}.json', result)
        if i % 50 == 0:
            print(f'observed {i}/450 sources', flush=True)
    fitted = [r for r in observations if r['classification'] == 'FITS_EXISTING_MODEL']
    stats = [r for r in fitted if r.get('statistical_profile', {}).get('status') ==
             'COMPLETE_FULL_SELECTED_TABLE']
    require(all(file_sha256(ROOT / p) == h for p, h in protected.items()), 'HISTORICAL_METADATA_CHANGED')
    require(sha((ROOT / admission_auth.OWNER_GRANT_PATH).read_bytes()) ==
            admission_auth.OWNER_GRANT_SHA256, 'INSTALLED_AUTHORIZATION_CHANGED')
    summary = {'step': 'N450_PROFILING_AND_B1_ONLY', 'started_at_utc': started,
        'finished_at_utc': datetime.now(UTC).isoformat(), 'wall_seconds': time.perf_counter()-clock,
        'peak_rss_platform_units': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'provenance': provenance, 'baseline_reused': old_evidence,
        'authority_separation': 'Current owner Step 2 instruction authorizes read-only lexical observations. '
          'Installed admission/freeze record is used only as sealed source-registration evidence; '
          'no Agent-generated parser approval or Step 3 activation is created.',
        'registration_snapshot': {'admission': grant['scopes']['admission']['files_sha256'],
                                  'freeze': grant['scopes']['freeze']['files_sha256']},
        'source_count': len(observations),
        'structural_full_sources': sum(r.get('structure', {}).get('scan_scope') == 'FULL_BYTES'
                                       for r in observations),
        'structural_pass_sources': sum(r.get('structure', {}).get('validation') == 'PASS'
                                       for r in observations),
        'data_occurrences': sum(r['structure']['data_records'] for r in fitted),
        'physical_records': sum(r['structure']['physical_records'] for r in fitted),
        'data_fields': sum(r['occurrence_validation']['data_fields'] for r in fitted),
        'schema_fingerprints': dict(Counter(r['schema_sha256'] for r in fitted)),
        'classification_counts': dict(Counter(r['classification'] for r in observations)),
        'eligible_model_fit_ids': [r['source_instance_id'] for r in fitted],
        'held': [{'source_instance_id': r['source_instance_id'], 'classification': r['classification'],
                  'errors': r['errors']} for r in observations if r not in fitted],
        'statistical_coverage': {'selection': 'First/middle/last passing source in approved roster order; '
            'at most three complete tables and 20000 DATA occurrences per table.',
            'sources': len(stats), 'column_profiles': sum(r['statistical_profile']['columns'] for r in stats),
            'data_occurrences': sum(r['statistical_profile']['rows'] for r in stats),
            'source_ids': [r['source_instance_id'] for r in stats],
            'scope': 'Exact full selected tables only; no population-level inference'},
        'not_computed': ['Semantic NULL metrics', 'Business key eligibility', 'FD search',
                         'Numeric/date casts', 'Economic semantic validity',
                         'N450 CLEAN/QUERYABLE Lossless results', 'Stability A/B/C'],
        'm2_requirement_evidenced': False,
        'step3_execution_status': 'NOT_EXECUTED; model eligibility is not parser/runtime activation',
        'c300_profiling_replayed': False, 'c300_metadata_preservation': 'PASS',
        'results': [{'source_instance_id': r['source_instance_id'],
                    'classification': r['classification'],
                    'reference': str((OUT/'sources'/f'{r["source_instance_id"]}.json').relative_to(ROOT)),
                    'sha256': file_sha256(OUT/'sources'/f'{r["source_instance_id"]}.json')}
                   for r in observations]}
    save(OUT / 'summary.json', summary)
    print(json.dumps({k: summary[k] for k in ('source_count', 'structural_full_sources',
        'data_occurrences', 'data_fields', 'classification_counts', 'statistical_coverage',
        'wall_seconds')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
