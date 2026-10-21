"""DEC-000010 acceptance checks only; no published CLEAN or Step 3 execution."""
import copy
import hashlib
import json
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from diagnose_src010128 import retained_native
from observe_n450_b1 import occurrence_check, scope

from edp_lab.ingestion.c300_admission import encoded
from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.materialization.m1_verifier_v2 import verify_parquet
from edp_lab.parsers import src010128_v1 as profile
from edp_lab.parsers.c300_reader_v1 import validated_occurrences

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/n450/src010128-recovery-v3'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def parquet_check(native, binding, directory):
    """Temporary validation artifact, never a registered/published CLEAN output."""
    path = directory / (binding['source_instance_id'] + '.parquet')
    schema = native.record_schema()
    with pq.ParquetWriter(path, schema) as writer:
        batch = []
        for record in validated_occurrences(ROOT, binding):
            batch.append(native.package_record('DEC000010_ACCEPTANCE_TEST_ONLY', binding, record))
            if len(batch) == 2048:
                writer.write_table(pa.Table.from_pylist(batch, schema=schema))
                batch.clear()
        if batch:
            writer.write_table(pa.Table.from_pylist(batch, schema=schema))
    actual = verify_parquet(ROOT, binding, path)
    if binding['profile_id'] == profile.PROFILE:
        # Prove the readback oracle rejects a changed derived value.
        rows = pq.read_table(path).to_pylist()
        rows[profile.LINE-1]['fields'][1]['lexical_value'] = 'UNAPPROVED VALUE'
        bad = directory / 'tampered.parquet'
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), bad)
        try:
            verify_parquet(ROOT, binding, bad)
        except AssertionError:
            actual['changed_company_name_rejected'] = True
        else:
            raise ValueError('TAMPERED_COMPANY_VALUE_ACCEPTED')
    else:
        require(actual == native.verify_parquet(ROOT, binding, path),
                'UNCHANGED_UTF8_NATIVE_ORACLE_REGRESSION')
    return actual


def main():
    started, clock = datetime.now(UTC).isoformat(), time.perf_counter()
    require(not OUT.exists(), 'NEW_EVIDENCE_DIRECTORY_REQUIRED')
    rows, _physical, _ = scope()
    protected_paths = ['metadata/cohorts/C300.csv', 'metadata/corpus_manifest_v3.csv',
                       'metadata/source_universes/approved_v1/manifest.json',
                       'metadata/authorizations/n450_execution_v1.json',
                       'metadata/admissions/N450_v1/corpus_manifest_v4.csv',
                       'metadata/freezes/C750_v1/freeze.json']
    protected = {p: file_sha256(ROOT / p) for p in protected_paths}
    old_raw = (ROOT / 'runs/n450/b1-v1/summary.json').read_bytes()
    old = json.loads(old_raw)
    reused = [r for r in old['results'] if r['source_instance_id'] != profile.SID]
    require(len(reused) == 449, 'PRIOR_POPULATION_COUNT_CHANGED')
    for record in reused:
        source_raw = (ROOT / record['reference']).read_bytes()
        require(hashlib.sha256(source_raw).hexdigest() == record['sha256'], 'PRIOR_EVIDENCE_CHANGED')
        source = json.loads(source_raw)
        row = next(r for r in rows if r['source_instance_id'] == record['source_instance_id'])
        require(source['classification'] == 'FITS_EXISTING_MODEL' and all(
            source['descriptor'][k] == row[k] for k in ('raw_path', 'raw_sha256', 'source_family')),
            'PRIOR_SOURCE_BINDING_CHANGED')
    original = ROOT / 'runs/n450/b1-v1/sources/SRC010128.json'
    prior = json.loads(original.read_bytes())
    require(prior['classification'] == 'HUMAN_UNRESOLVED', 'ORIGINAL_FINDING_NOT_PRESERVED')
    binding = copy.deepcopy(prior['descriptor'])
    binding.update(profile_id=profile.PROFILE, discovery_validation='PASS',
                   decoding_provenance=profile.provenance({**binding, 'profile_id': profile.PROFILE}))
    result = profile.profile_source(ROOT, binding)
    native, native_ref = retained_native()
    controls = {}
    with tempfile.TemporaryDirectory(prefix='dec000010-acceptance-') as tmp:
        directory = Path(tmp)
        native_check = parquet_check(native, binding, directory)
        for sid in ('SRC010001', 'SRC010226', 'SRC010450'):
            observation = json.loads((ROOT / f'runs/n450/b1-v1/sources/{sid}.json').read_bytes())
            descriptor = observation['descriptor']
            check, _, _ = occurrence_check(descriptor, observation['structure']['data_records'])
            require(check == observation['occurrence_validation'], 'UTF8_OCCURRENCE_REGRESSION')
            controls[sid] = {'occurrence_validation': check,
                             'native_readback': parquet_check(native, descriptor, directory),
                             'comparison_to_frozen_native_oracle': 'IDENTICAL'}
    require({p: file_sha256(ROOT / p) for p in protected} == protected, 'PROTECTED_METADATA_CHANGED')
    require(file_sha256(Path(binding['raw_path'])) == profile.RAW_SHA, 'RAW_CHANGED')
    evidence = {'assessment': 'B1_SC7_N450_V3', 'decision': 'DEC-000010',
        'started_at_utc': started, 'finished_at_utc': datetime.now(UTC).isoformat(),
        'wall_seconds': time.perf_counter()-clock, 'source_validation': result,
        'native_readback': native_check, 'frozen_native_reference': native_ref,
        'original_finding_reference': str(original.relative_to(ROOT)),
        'original_finding_sha256': file_sha256(original),
        'previous_summary_sha256': hashlib.sha256(old_raw).hexdigest(),
        'reused_449_fingerprints': reused, 'reused_count': 449,
        'bounded_utf8_regression': controls, 'protected_metadata_sha256': protected,
        'code_sha256': {p: file_sha256(ROOT / p) for p in (
            'src/edp_lab/parsers/src010128_v1.py', 'src/edp_lab/parsers/c300_reader_v1.py',
            'src/edp_lab/parsers/c300_v1.py', 'src/edp_lab/materialization/m1_verifier_v2.py',
            'scripts/validate_src010128_recovery.py')},
        'classifications': {'FITS_EXISTING_MODEL': 450}, 'eligible_n450': 450,
        'm1_model_changed': False, 'strict_utf8_sources': 449, 'scoped_encoding_exception_sources': 1,
        'lossless_scope': 'Exact source/record/field/byte/provenance and temporary native Parquet '
          'readback; no published N450 CLEAN/QUERYABLE or full platform Lossless/Stability claim.',
        'step3_executed': False, 'raw_mutated': False}
    OUT.mkdir(parents=True)
    (OUT / 'binding.validated.json').write_bytes(encoded(binding))
    (OUT / 'validation.json').write_bytes(encoded(evidence))
    print(json.dumps({k: evidence[k] for k in ('source_validation', 'native_readback',
          'eligible_n450', 'wall_seconds')}, indent=2))


if __name__ == '__main__':
    main()
