"""Native publication/reconciliation adapters; existing M1 tables and Lossless gate.

Every public entry checks installed authority. No historical writes, RAW writes,
semantic transforms or unversioned/current views. Spark is imported lazily.
"""
from __future__ import annotations

import json
import platform
import resource
import time
from datetime import UTC, datetime

from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.materialization.c300_m1 import BINDING_DDL, MODEL, RECORD_DDL, RULE, measure_inventory
from edp_lab.materialization.lossless_gate import VERSION, decide, view_sql
from edp_lab.materialization.n450_runtime import (
    BASE,
    PHASES,
    SMOKE,
    TABLES,
    VIEWS,
    ProcessingAccess,
    auth,
    checkpoint,
    exclusive_json,
    load_contract,
    output_path,
    require,
    verified_checkpoint,
)
from edp_lab.profiling.source_reader import canonical_hash


def differences(left, right):
    return left.exceptAll(right).unionAll(right.exceptAll(left)).limit(1).count()


def table_version(spark, table):
    require(table in TABLES, 'UNAUTHORIZED_TABLE')
    return int(spark.sql(f'DESCRIBE HISTORY {table}').first()['version'])


def binding_row(entry, receipt, contract, owner_pin, error):
    b = entry['registered_binding']
    result = receipt['verification'] if receipt else {}
    return {'run_id': 'n450_step3_v1', 'model_version': MODEL, 'rule_version': RULE,
        'source_instance_id': b['source_instance_id'], 'source_family': b['source_family'],
        'raw_path': b['raw_path'], 'volume_path': entry['remote_raw_path'].removeprefix('dbfs:'),
        'raw_sha256': b['raw_sha256'], 'archive_member': b['archive_member'],
        'member_sha256': b['member_sha256'], 'logical_table_name': b['logical_table_name'],
        'binding_sha256': entry['binding_sha256'], 'parser_profile_id': b['profile_id'],
        'parser_version': ('C300_PARSER_V1' if b['profile_id'] ==
                           'SEC_EDGAR_DAILY_MASTER_C300_PARSER_V1' else b['profile_id']),
        'parser_code_sha256': contract['files_sha256']['src/edp_lab/parsers/c300_v1.py'],
        'reader_code_sha256': contract['files_sha256']['src/edp_lab/parsers/c300_reader_v1.py'],
        'registry_sha256': contract['files_sha256'][contract['processing_bindings']],
        'approval_packet_sha256': owner_pin,
        'cohort_sha256': contract['files_sha256']['metadata/freezes/C750_v1/C750.csv'],
        'manifest_sha256': contract['files_sha256']['metadata/admissions/N450_v1/corpus_manifest_v4.csv'],
        'ordered_header': b['expected_header'], 'expected_member_bytes': b['uncompressed_bytes'],
        'processing_status': 'COMPLETE' if receipt else 'FAILED',
        'reason_code': 'IDENTITY_LEXICAL_PRESERVATION' if receipt else 'CHECKPOINT_NOT_COMPLETE',
        'error_evidence_ref': error, 'records_total': result.get('records_total'),
        'records_data': result.get('records_data'), 'fields_data': result.get('fields_data'),
        'observed_member_sha256': result.get('observed_member_sha256')}


def reauthorize(root, approved):
    bindings = [e['registered_binding'] for e in approved['entries']]
    current = auth.authorize(root, 'remote_processing', bindings, cohort='C750')
    require(current['owner_grant_sha256'] == approved['owner_grant_sha256'], 'OWNER_GRANT_CHANGED')
    return current


def clean_publish(spark, root, approved, access, base):
    approved = reauthorize(root, approved)
    contract, entries = approved['contract'], approved['entries']
    phase = json.loads(output_path(base, 'phases/full.json').read_bytes())
    require(phase['owner_grant_sha256'] == access.pin and
            phase['binding_sha256'] == [e['binding_sha256'] for e in entries],
            'FULL_PROCESSING_SCOPE_NOT_ATTEMPTED')
    from pyspark.sql import functions as F

    rows, receipts, paths, errors = [], {}, [], {}
    for entry in entries:
        digest = entry['binding_sha256']
        folder = output_path(base, 'checkpoints/' + digest)
        try:
            receipt = verified_checkpoint(root, entry, folder, access)
        except Exception as exc:  # noqa: BLE001 -- retain a failed/partial outcome; never publish its records
            receipt = None
            errors[digest] = str(exc)
        rows.append(binding_row(entry, receipt, contract, access.pin,
                                'checkpoints/' + digest if not receipt else None))
        if receipt:
            receipts[digest] = receipt
            paths.append(str(folder / 'records.parquet'))
    require(paths, 'NO_COMPLETE_BINDINGS')
    records = spark.read.schema(RECORD_DDL).parquet(*paths)
    bindings = spark.createDataFrame(rows, BINDING_DDL)
    marker = output_path(base, 'clean/completion.json')
    if marker.exists():
        retained = json.loads(marker.read_bytes())
        require(retained['owner_grant_sha256'] == access.pin, 'OUTPUT_AUTHORITY_CHANGED')
        versions = retained['tables']
    else:
        require(not any(spark.catalog.tableExists(t) for t in TABLES),
                'PARTIAL_OR_EXISTING_PUBLICATION_REQUIRES_NEW_VERSION')
        # Exclusive Delta mode, never replace/overwrite. A second-table failure is
        # incomplete publication; the first table is preserved and not repaired.
        records.write.format('delta').mode('errorifexists').saveAsTable(TABLES[0])
        bindings.write.format('delta').mode('errorifexists').saveAsTable(TABLES[1])
        versions = {t: table_version(spark, t) for t in TABLES}
    require(set(versions) == set(TABLES) and all(table_version(spark, t) == versions[t]
                                               for t in TABLES), 'OUTPUT_TABLE_VERSION_CHANGED')
    actual = spark.read.option('versionAsOf', versions[TABLES[0]]).table(TABLES[0])
    actual_bindings = spark.read.option('versionAsOf', versions[TABLES[1]]).table(TABLES[1])
    require(records.schema.simpleString() == actual.schema.simpleString() and
            bindings.schema.simpleString() == actual_bindings.schema.simpleString(), 'M1_SCHEMA_CHANGED')
    require(not differences(records, actual) and not differences(bindings, actual_bindings),
            'DELTA_MULTISET_DIFFERENCE')
    counts = {r['binding_sha256']: r.asDict() for r in actual.groupBy('binding_sha256').agg(
        F.count('*').alias('records_total'), F.countDistinct('source_line').alias('unique_locators'),
        F.sum(F.when(F.col('record_kind') == 'DATA', 1).otherwise(0)).alias('records_data'),
        F.sum(F.size('fields')).alias('fields_data')).collect()}
    gates = []
    inventory = [item for e in entries for item in measure_inventory(e['registered_binding'])]
    for row in rows:
        digest, status = row['binding_sha256'], row['processing_status']
        observed = counts.get(digest, {})
        ok = status == 'COMPLETE' and all(observed.get(k) == row[k] for k in (
            'records_total', 'records_data', 'fields_data')) and (
                observed.get('unique_locators') == row['records_total'])
        tests = {str(i): {'status': 'PASS' if ok else 'FAIL',
                          'evidence': ['clean/mandatory-validation.json', 'checkpoints/'+digest],
                          'failure_count': 0 if ok else 1,
                          'expected': {k: row[k] for k in ('records_total', 'records_data', 'fields_data')}}
                 for i in range(1, 6)}
        tests['6'] = {'status': 'NOT_APPLICABLE', 'boundary': MODEL,
                      'inventory_ref': 'clean/measure-inventory.json',
                      'justification': 'Lexical M1; no economic promotion or semantic inference'}
        gates.append({'binding_sha256': digest, 'source_instance_id': row['source_instance_id'],
                      'tests': tests, 'gate_status': decide(tests, status)})
    gate = {'version': VERSION, 'run_id': 'n450_step3_v1', 'tables': versions, 'bindings': gates,
            'owner_grant_sha256': access.pin, 'full_c300_lossless_pass': False}
    gate['evidence_sha256'] = canonical_hash(gate)
    result = {'tables': versions, 'owner_grant_sha256': access.pin, 'coverage': 450,
              'complete': len(receipts), 'errors': errors, 'gate_sha256': gate['evidence_sha256']}
    if not marker.exists():
        exclusive_json(output_path(base, 'clean/mandatory-validation.json'),
                       {'counts': counts, 'record_difference': 0, 'binding_difference': 0})
        exclusive_json(output_path(base, 'clean/measure-inventory.json'), inventory)
        exclusive_json(output_path(base, 'clean/lossless-gate.json'), gate)
        exclusive_json(marker, result)
    else:
        require(json.loads(output_path(base, 'clean/lossless-gate.json').read_bytes()) == gate
                and retained == result, 'PUBLISHED_OUTPUT_READBACK_CHANGED')
    return result


def query_plan(contract, c300_gate, n450_gate):
    """Reuse the existing fixed-schema UNION ALL/view_sql reconciler."""
    require(c300_gate['version'] == n450_gate['version'] == VERSION, 'UNKNOWN_LOSSLESS_GATE')
    for gate in (c300_gate, n450_gate):
        require(canonical_hash({k: v for k, v in gate.items() if k != 'evidence_sha256'}) ==
                gate['evidence_sha256'], 'UNSEALED_GATE')
    require(c300_gate['tables'] == contract['c300_versions'], 'C300_VERSION_DRIFT')
    require(len(c300_gate['bindings']) == 732 and len(n450_gate['bindings']) == 450,
            'C750_LOGICAL_COVERAGE_CHANGED')
    parts = []
    hashes = set()
    for gate in (c300_gate, n450_gate):
        by_tables = []
        if gate is c300_gate:
            by_tables = [(t, t.replace('_records_', '_bindings_')) for t in sorted(gate['tables'])
                         if '_records_' in t]
        else:
            require(gate['tables'].keys() == set(TABLES), 'UNAUTHORIZED_CLEAN_TABLE')
            by_tables = [TABLES]
        for records, bindings in by_tables:
            original = [g for g in gate['bindings'] if gate is n450_gate or
                        g['tests']['1']['input_run_ref'].split('/')[-2] in records]
            # C300's original input_run_ref distinguishes main vs NUM run IDs.
            if gate is c300_gate:
                require(original, 'C300_SOURCE_GATE_MAPPING_EMPTY')
            selected = {**gate, 'bindings': original}
            require(not hashes & {g['binding_sha256'] for g in original}, 'DUPLICATE_BINDING_UNION')
            hashes |= {g['binding_sha256'] for g in original}
            sql = list(view_sql('unused', records, bindings, gate['tables'], selected).values())
            scope = ','.join("'"+g['binding_sha256']+"'" for g in original)
            sql[2] += ' WHERE binding_sha256 IN (' + scope + ')'
            parts.append(sql)
    require(len(hashes) == 1182, 'C750_BINDING_UNION_CHANGED')
    return {name: ' UNION ALL '.join(part[i] for part in parts) for i, name in enumerate(VIEWS)}


def validation_groups(gates, expected):
    groups, current, records = [], [], 0
    for binding in gates:
        digest = binding['binding_sha256']
        count = expected.get(digest, {}).get('records_data') or 0
        if current and (len(current) >= 96 or records+count > 12_000_000):
            groups.append(current)
            current, records = [], 0
        current.append(digest)
        records += count
    if current:
        groups.append(current)
    return groups


def checkpoint_validation(base, identity, compare):
    key = canonical_hash(identity)
    path = output_path(base, 'queryable/checks/'+key+'.json')
    if path.exists():
        result = json.loads(path.read_bytes())
        require(result['identity'] == identity and result['status'] == 'PASS' and
                result['difference_count'] == 0 and canonical_hash({
                    k: v for k, v in result.items() if k != 'evidence_sha256'}) == result['evidence_sha256'],
                'VALIDATION_CHECKPOINT_CHANGED')
        return result
    started = time.perf_counter()
    count = compare()
    result = {'identity': identity, 'status': 'PASS' if count == 0 else 'FAIL',
              'difference_count': count, 'seconds': time.perf_counter()-started}
    result['evidence_sha256'] = canonical_hash(result)
    target = path if count == 0 else output_path(base,
        'queryable/checks/'+key+'-failed-'+str(time.time_ns())+'.json')
    exclusive_json(target, result)
    require(count == 0, 'QUERYABLE_MULTISET_DIFFERENCE')
    return result


def query_publish(spark, root, approved, base):
    approved = reauthorize(root, approved)
    contract = approved['contract']
    c300_gate = json.loads((root / contract['c300_gate']).read_bytes())
    new_gate = json.loads(output_path(base, 'clean/lossless-gate.json').read_bytes())
    require(new_gate['owner_grant_sha256'] == approved['owner_grant_sha256'], 'GATE_AUTHORITY_CHANGED')
    plan = query_plan(contract, c300_gate, new_gate)
    marker = output_path(base, 'queryable/completion.json')
    plan_path = output_path(base, 'queryable/plan.json')
    if plan_path.exists():
        require(json.loads(plan_path.read_bytes()) == plan, 'QUERYABLE_PLAN_CHANGED')
    if marker.exists():
        saved = json.loads(marker.read_bytes())
        require(saved['sql_sha256'] == {name: canonical_hash(sql) for name, sql in plan.items()},
                'QUERYABLE_PLAN_CHANGED')
    elif not plan_path.exists():
        require(not any(spark.catalog.tableExists(v) for v in VIEWS), 'QUERYABLE_ALREADY_EXISTS')
        for name, sql in plan.items():
            spark.sql(f'CREATE VIEW {name} AS {sql}')
        exclusive_json(plan_path, plan)
    else:
        require(all(spark.catalog.tableExists(v) for v in VIEWS), 'PARTIAL_QUERYABLE_PUBLICATION')
    counts = {}
    reuse = json.loads((root / contract['c300_reuse']).read_bytes())
    approved_c300 = {g['binding_sha256'] for g in c300_gate['bindings'] if g['gate_status'] == 'PASS'}
    approved_new = [g for g in new_gate['bindings'] if g['gate_status'] == 'PASS']
    expected_counts = {
        VIEWS[0]: sum(b['records_data'] for b in reuse if b['binding_sha256'] in approved_c300)
                  + sum(g['tests']['1']['expected']['records_data'] for g in approved_new),
        VIEWS[1]: sum(b['fields_data'] for b in reuse if b['binding_sha256'] in approved_c300)
                  + sum(g['tests']['1']['expected']['fields_data'] for g in approved_new),
        VIEWS[2]: 1182}
    for table, identity in contract['c300_storage_locations'].items():
        detail = spark.sql(f'DESCRIBE DETAIL {table}').first()
        require(detail['location'] == identity, 'C300_TABLE_REPLACED')
    for name, sql in plan.items():
        # Full native multiset comparison, partitioned by exact binding groups to
        # retain bounded validation checkpoints; no sampling/count-only PASS.
        actual, expected = spark.table(name), spark.sql(sql)
        if plan_path.exists():
            require(spark.sql(f'SHOW CREATE TABLE {name}').first()[0].strip().endswith(sql.strip()),
                    'QUERYABLE_DEFINITION_CHANGED')
        require(actual.schema.simpleString() == expected.schema.simpleString(), 'QUERYABLE_SCHEMA_CHANGED')
        summaries = {b['binding_sha256']: b for b in reuse}
        summaries.update({g['binding_sha256']: g['tests']['1']['expected']
                          for g in new_gate['bindings']})
        groups = validation_groups(c300_gate['bindings']+new_gate['bindings'], summaries)
        for scope in groups:
            identity = {'view': name, 'sql_sha256': canonical_hash(sql),
                        'bindings': scope, 'owner_grant_sha256': approved['owner_grant_sha256'],
                        'c300_tables': contract['c300_versions'], 'n450_tables': new_gate['tables'],
                        'contract_sha256': file_sha256(root/'proposals/n450-processing-v2/contract.json')}
            checkpoint_validation(base, identity, lambda scope=scope, actual=actual, expected=expected: differences(
                actual.where(actual.binding_sha256.isin(scope)),
                expected.where(expected.binding_sha256.isin(scope))))
        counts[name] = actual.count()
    require(counts == expected_counts and spark.table(VIEWS[2]).select(
        'source_instance_id').distinct().count() == 750, 'QUERYABLE_COVERAGE_OR_COUNT_CHANGED')
    result = {'status': 'PASS_FOR_GATE_APPROVED_SCOPE', 'counts': counts,
              'sql_sha256': {name: canonical_hash(sql) for name, sql in plan.items()},
              'owner_grant_sha256': approved['owner_grant_sha256'],
              'c300_versions': contract['c300_versions'], 'n450_versions': new_gate['tables'],
              'complete_N450_bindings': len(approved_new),
              'failed_or_blocked_N450_bindings': 450-len(approved_new),
              'full_C750_applicable_lossless': 'PASS' if len(approved_new) == 450 else 'PARTIAL',
              'freeze_status': 'NOT_FROZEN'}
    if not marker.exists():
        exclusive_json(marker, result)
    else:
        require(saved == result, 'QUERYABLE_READBACK_CHANGED')
    return result


def run(spark, root, phase):
    from pathlib import Path

    require(phase in PHASES, 'UNAUTHORIZED_JOB_PHASE')
    root, base = Path(root), Path(BASE)
    contract = load_contract(root)
    entries = json.loads((root / contract['processing_bindings']).read_bytes())
    bindings = [e['registered_binding'] for e in entries]
    approved = auth.authorize(root, 'remote_processing', bindings, cohort='C750')
    access = ProcessingAccess(root, bindings)
    started, clock, cpu_clock = datetime.now(UTC).isoformat(), time.perf_counter(), time.process_time()
    for table, version in contract['c300_versions'].items():
        detail = spark.sql(f'DESCRIBE DETAIL {table}').first()
        require(detail['location'] == contract['c300_storage_locations'][table], 'C300_TABLE_REPLACED')
        spark.read.option('versionAsOf', version).table(table).limit(1).count()
    # All fresh remote hashes precede any new runtime output/checkpoint.
    for entry in entries:
        require(file_sha256(access.path_for(entry['registered_binding'])) ==
                entry['registered_binding']['raw_sha256'], 'REMOTE_RAW_HASH_MISMATCH')
    output_path(base, 'attempts')  # containment/symlink check before mkdir
    if phase in {'smoke', 'full'}:
        if phase == 'full':
            for entry in entries:
                if entry['source_instance_id'] in SMOKE:
                    require(verified_checkpoint(root, entry, output_path(base,
                        'checkpoints/'+entry['binding_sha256']), access) is not None,
                        'SMOKE_NOT_VERIFIED')
        results = []
        for entry in entries:
            if phase == 'smoke' and entry['source_instance_id'] not in SMOKE:
                continue
            try:
                receipt = checkpoint(root, entry, output_path(base,
                    'checkpoints/'+entry['binding_sha256']), access, 'n450_step3_v1')
                results.append({'binding_sha256': entry['binding_sha256'], 'status': receipt['status']})
            except Exception as exc:  # noqa: BLE001 -- retain isolated failure
                failure = {'binding_sha256': entry['binding_sha256'], 'status': 'FAILED', 'error': str(exc)}
                exclusive_json(output_path(base, 'attempts/'+str(time.time_ns())+'.json'), failure)
                results.append(failure)
        phase_result = {'owner_grant_sha256': access.pin,
                        'binding_sha256': [e['binding_sha256'] for e in entries
                                           if phase == 'full' or e['source_instance_id'] in SMOKE]}
        phase_marker = output_path(base, 'phases/'+phase+'.json')
        if phase_marker.exists():
            require(json.loads(phase_marker.read_bytes()) == phase_result, 'PHASE_SCOPE_CHANGED')
        else:
            exclusive_json(phase_marker, phase_result)
        result = {'phase': phase, 'bindings': results}
    elif phase == 'publish':
        result = clean_publish(spark, root, approved, access, base)
    else:
        result = query_publish(spark, root, approved, base)
    result.update(started_at_utc=started, finished_at_utc=datetime.now(UTC).isoformat(),
                  wall_seconds=time.perf_counter()-clock, driver_cpu_seconds=time.process_time()-cpu_clock,
                  peak_rss_platform_units=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  runtime={'python': platform.python_version(), 'spark': spark.version,
                           'pyarrow': __import__('pyarrow').__version__,
                           'duckdb': __import__('duckdb').__version__},
                  contract_sha256=file_sha256(root / 'proposals/n450-processing-v2/contract.json'),
                  runtime_sha256=contract['runtime_sha256'],
                  unavailable_telemetry=['DBUs', 'executor CPU', 'executor peak RSS'],
                  model=MODEL, rule=RULE, output_freeze='NOT_FROZEN')
    exclusive_json(output_path(base, 'attempts/'+str(time.time_ns())+'-result.json'), result)
    return result
