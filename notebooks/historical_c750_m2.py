# Databricks notebook source
# ruff: noqa: F821
"""DEC-000014: one CLEAN-only C750 NUM projection, then independent readback.

No RAW reader, M1 writer, authority installer, separate C300 ETL or N750 input.
Payload contains the unchanged Step 5 converter and frozen accepted query SQL.
"""
import hashlib
import json
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from pyspark import cloudpickle
from pyspark.sql import functions as F
from pyspark.sql import types as T

BASE = Path('/Volumes/workspace/edp_lab/raw/day4-m2/historical_v1')
TABLE = 'workspace.edp_lab.typed_c750_m2_historical_20261022_v1'
RECORDS = 'workspace.edp_lab.o_c750_m2_records_historical_20261022_v1'
SUBSET = 'workspace.edp_lab.o_c300_m2_records_historical_20261022_v1'
KEY = ['run_id', 'source_instance_id', 'binding_sha256', 'source_line', 'field_ordinal']


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    with (BASE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, default=str)
        stream.write('\n')


def state(refs, plan):
    tables = []
    for item in refs['clean_snapshots']:
        table = item['table']
        detail = spark.sql('DESCRIBE DETAIL ' + table).first().asDict(recursive=True)
        history = spark.sql('DESCRIBE HISTORY ' + table + ' LIMIT 1').first().asDict()
        assert detail['id'] == item['delta_id'], table
        assert history['version'] == item['latest_metadata_version'], (table, history)
        catalog = catalog_descriptors[table]
        assert catalog['table_id'] == item['uc_table_id'], table
        assert catalog['storage_location'] == item['storage_location'], table
        assert detail['location'] in ('', item['storage_location']), table
        assert detail['properties']['io.unitycatalog.tableId'] == item['uc_table_id'], table
        frame = spark.sql('SELECT * FROM ' + table + ' VERSION AS OF 0')
        tables.append({'table': table, 'delta_id': detail['id'],
                       'location': detail['location'], 'catalog_location': catalog['storage_location'],
                       'latest_version': history['version'],
                       'latest_operation': history['operation'],
                       'schema_json': frame.schema.json(), 'read_version': 0})
    definitions = {name: spark.sql('SHOW CREATE TABLE ' + name).first()[0] for name in plan}
    return {'tables': tables, 'definitions': definitions}


def eligible_inputs(plan):
    # Accepted frozen UNION ALL selects already exclude superseded BLOCKED rows.
    coverage = spark.sql(plan['workspace.edp_lab.q_c750_m1_coverage_c750_step3_v1'])
    bindings = coverage.where((F.col('source_family') == 'SEC_FSDS') &
                              (F.col('archive_member') == 'num.txt')).collect()
    assert len(bindings) == len({r.binding_sha256 for r in bindings}) == 60
    assert len({r.source_instance_id for r in bindings}) == 60
    for row in bindings:
        assert row.processing_status == 'COMPLETE'
        assert row.ordered_header.count('value') == 1
        assert row.ordered_header[8] == 'value'
    fields = spark.sql(plan['workspace.edp_lab.q_c750_m1_fields_c750_step3_v1'])
    selected = fields.where((F.col('archive_member') == 'num.txt') &
                            (F.col('original_name') == 'value') &
                            F.col('binding_sha256').isin([r.binding_sha256 for r in bindings]))
    inventory = [{'source_instance_id': r.source_instance_id,
                  'binding_sha256': r.binding_sha256, 'records_data': r.records_data}
                 for r in bindings]
    return selected, sorted(inventory, key=lambda r: r['source_instance_id'])


def fingerprint(frame, columns):
    # Count plus independent SHA-256 halves summed exactly; an order-independent
    # reproducibility fingerprint, not a substitute for EXCEPT ALL below.
    hashed = frame.select('binding_sha256', F.sha2(F.to_json(F.struct(
        *[F.col(c) for c in columns])), 256).alias('h'))
    return [r.asDict() for r in hashed.groupBy('binding_sha256').agg(
        F.count('*').alias('count'),
        F.sum(F.conv(F.substring('h', 1, 15), 16, 10).cast('decimal(38,0)')).alias('sha_head_sum'),
        F.sum(F.conv(F.substring('h', 50, 15), 16, 10).cast('decimal(38,0)')).alias('sha_tail_sum')
    ).orderBy('binding_sha256').collect()]


def oracle(frame):
    """Independent native-string classification; no Python converter involved."""
    text = F.col('lexical_value')
    grammar = text.rlike(r'\A[+-]?[0-9]+(?:\.[0-9]+)?\z')
    fraction = F.length(F.regexp_extract(text, r'\.([0-9]+)\z', 1))
    integer = F.regexp_extract(text, r'\A[+-]?([0-9]+)', 1)
    width = F.length(F.regexp_replace(integer, '^0+', ''))
    blank = text.rlike(r'\A[\x20\x09\x0d\x0a\x0c\x0b]*\z')
    outcome = (F.when(blank, 'BLANK').when(~grammar, 'INVALID')
               .when(fraction > 4, 'SCALE_EXCEEDED').when(width > 34, 'OVERFLOW')
               .otherwise('VALID'))
    reason = (F.when(text == '', 'EMPTY_TEXT').when(blank, 'WHITESPACE_ONLY')
              .when(~grammar, 'LEXICAL_GRAMMAR')
              .when(fraction > 4, 'FRACTIONAL_DIGITS_GT_4')
              .when(width > 34, 'INTEGER_DIGITS_GT_34').otherwise('EXACT_PROJECTION'))
    # Guard classification BEFORE the cast. CAST never acts as a rounding parser.
    value = F.when(outcome == 'VALID', text.cast('decimal(38,4)'))
    return frame.where(~F.col('conversion_outcome').eqNullSafe(outcome) |
                       ~F.col('conversion_reason').eqNullSafe(reason) |
                       ~F.col('value_decimal').eqNullSafe(value))


def fin_checks(root, plan):
    original = plan['workspace.edp_lab.q_c750_m1_records_c750_step3_v1']
    spark.sql(original).createOrReplaceTempView('historical_m1_fin_input')
    report = {}
    old_view = 'workspace.edp_lab.q_c300_m1_records_reconciled_recovery_20261021_v2_full'
    for case in ('FIN_001', 'FIN_002'):
        sql = (root / 'sql' / (case + '.sql')).read_text()
        old = spark.sql(sql.replace(old_view, 'historical_m1_fin_input')).collect()
        lexical = spark.sql(sql.replace(old_view, RECORDS)).collect()
        typed_sql = sql.replace(old_view, RECORDS).replace(
            'TRY_CAST(fields[8].lexical_value AS DECIMAL(38,4)) AS amount',
            'value_decimal AS amount')
        typed = spark.sql(typed_sql).collect()
        subset = spark.sql(typed_sql.replace(RECORDS, SUBSET)).collect()
        assert old == lexical == typed == subset, case
        assert all(r[-1] == 'PASS' for r in typed), case
        expected = json.loads((root / 'fin-expected.json').read_text())
        actual = [r.asDict() for r in typed]
        if case == 'FIN_001':
            assert len(actual) == 2
            for row, fixture in zip(actual, expected[:2], strict=True):
                for column in ('ddate', 'assets', 'liabilities', 'equity', 'reported_total'):
                    key = 'equity_used' if column == 'equity' else column
                    assert str(row[column]) == fixture[key], (column, row)
        else:
            assert len(actual) == 1
            assert str(actual[0]['wrong_equity_difference']) == expected[2]['wrong_equity_difference']
            amounts = typed_sql[:typed_sql.index('SELECT\n    assets - liabilities')] + 'SELECT * FROM p'
            row = spark.sql(amounts).first()
            for column in ('assets', 'liabilities', 'reported_total'):
                assert str(row[column]) == expected[2][column]
            assert str(row.equity_including_nci) == expected[2]['equity_used']
        report[case] = {'M1_pinned': [r.asDict() for r in old],
                        'M2_lexical': [r.asDict() for r in lexical], 'M2_typed': actual,
                        'C300_logical_subset_typed': [r.asDict() for r in subset]}
    lines = [1548800, 1793043, 2461430, 2606912, 131726, 1636110, 3026665,
             3467762, 677878, 695193, 1532665, 2653949, 3495804]
    p = spark.sql('SELECT * FROM ' + TABLE + ' VERSION AS OF 0').where(
        (F.col('binding_sha256') == '341ce895a89fe164c1cc14af2679aa0b4637f593c6887e5c4d3a74bc49bbebcd') &
        F.col('source_line').isin(lines))
    assert p.count() == 13 and p.where(F.col('conversion_outcome') != 'VALID').count() == 0
    witness_columns = ['source_line', 'byte_offset', 'byte_length', 'raw_sha256',
                       'archive_member', 'member_sha256', 'model_version', 'rule_version']
    witnessed = [[str(v) for v in row] for row in p.select(*witness_columns)
                 .orderBy('source_line').collect()]
    assert witnessed == json.loads((root / 'fin-witnesses.json').read_text())
    report['lineage_witnesses'] = [r.asDict() for r in p.orderBy('source_line').collect()]
    return report


started = time.time()
phase = dbutils.widgets.get('phase')
assert phase in ('build', 'verify')
runtime_file = dbutils.widgets.get('runtime_file')
assert runtime_file in ('runtime.zip', 'runtime-v2.zip')
raw = (BASE / runtime_file).read_bytes()
assert digest(raw) == dbutils.widgets.get('runtime_sha256')
root = Path(tempfile.mkdtemp(prefix='historical-m2-'))
with zipfile.ZipFile(BASE / runtime_file) as archive:
    assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in archive.namelist())
    archive.extractall(root)
sys.path.insert(0, str(root))
import typed_numeric_v1 as converter

cloudpickle.register_pickle_by_value(converter)
catalog_descriptors = json.loads((root / 'catalog-descriptors.json').read_text())
refs = json.loads((root / 'references.json').read_text())
plan = json.loads((root / 'queryable-plan.json').read_text())
assert digest((root / 'references.json').read_bytes()) == 'be2001860d5900b64bc4bdc3178b7367d54cbb89e7de703e515fd4c9cb1d5a50'
assert digest((root / 'queryable-plan.json').read_bytes()) == '17522cb06f354986fac104316bb68401de3255de6225566b84c311c6e205b42d'
assert digest((root / 'typed_numeric_v1.py').read_bytes()) == 'ae06d39409c2542273f269356a5905553b08621546de2bda6c972b22bc50d507'
selected, inventory = eligible_inputs(plan)
expected = sum(r['records_data'] for r in inventory)
assert expected == 176060325

if phase == 'build':
    assert not any(spark.catalog.tableExists(n) for n in (TABLE, RECORDS, SUBSET))
    before = state(refs, plan)
    save('m1-before.json', before)

    def exact(text):
        result = converter.convert(text)
        return result.value_decimal, result.conversion_outcome, result.conversion_reason

    projected = F.udf(exact, T.StructType([
        T.StructField('value_decimal', T.DecimalType(38, 4)),
        T.StructField('conversion_outcome', T.StringType(), False),
        T.StructField('conversion_reason', T.StringType(), False)]))
    probe_texts = ['0', '-0', '+1.20', '4.45', '0.0070', '9830000.0000',
                   '9' * 34 + '.9999', '-' + '9' * 34 + '.9999',
                   '1' + '0' * 34, '1.00000', '0.00001', '', ' \t',
                   'NULL', 'N/A', 'NaN', '1e2', '1\n', '１２.３', '\u00a0']
    probe = (spark.createDataFrame([(v,) for v in probe_texts], ['lexical_value'])
             .withColumn('_typed', projected('lexical_value'))
             .select('*', '_typed.*').drop('_typed'))
    assert oracle(probe).count() == 0, 'Spark transport/native oracle probe failed'
    save('runtime-probe.json', [r.asDict() for r in probe.collect()])
    output = (selected.withColumn('_typed', projected('lexical_value'))
              .select('*', '_typed.*').drop('_typed')
              .withColumn('m2_model_version', F.lit(converter.MODEL))
              .withColumn('conversion_rule_version', F.lit(converter.RULE))
              .withColumn('source_rule_version', F.lit('FSDS_NUM_VALUE_SCOPE_V1')))
    output.write.format('delta').mode('error').saveAsTable(TABLE)
    detail = spark.sql('DESCRIBE DETAIL ' + TABLE).first().asDict(recursive=True)
    save('build.json', {'status': 'PERSISTED_PENDING_INDEPENDENT_VALIDATION',
                        'table': TABLE, 'read_version': 0, 'detail': detail,
                        'eligible_count': expected, 'inventory': inventory,
                        'runtime_sha256': digest(raw), 'wall_seconds': time.time() - started,
                        'python': sys.version, 'spark': spark.version})
else:
    original = json.loads((BASE / 'm1-before.json').read_text())
    assert state(refs, plan) == original, 'M1 changed before independent verification'
    persisted = spark.sql('SELECT * FROM ' + TABLE + ' VERSION AS OF 0')
    counts = [r.asDict() for r in persisted.groupBy(
        'source_instance_id', 'binding_sha256', 'conversion_outcome').count().collect()]
    assert sum(r['count'] for r in counts) == expected
    actual = {}
    for row in counts:
        actual[row['binding_sha256']] = actual.get(row['binding_sha256'], 0) + row['count']
    assert actual == {r['binding_sha256']: r['records_data'] for r in inventory}
    assert persisted.groupBy(*KEY).count().where('count <> 1').limit(1).count() == 0
    assert selected.exceptAll(persisted.select(*selected.columns)).limit(1).count() == 0
    assert persisted.select(*selected.columns).exceptAll(selected).limit(1).count() == 0
    assert persisted.where('lexical_value IS NULL').limit(1).count() == 0
    assert oracle(persisted).limit(1).count() == 0
    assert persisted.where("m2_model_version <> 'M2_ADDITIVE_TYPED_NUMERIC_V1' OR "
                           "conversion_rule_version <> 'EXACT_DECIMAL_38_4_V1' OR "
                           "source_rule_version <> 'FSDS_NUM_VALUE_SCOPE_V1'").limit(1).count() == 0
    # Readback complete: preserve all original M1 columns and append only M2
    # columns through a proven one-to-one technical-locator join. N450 cannot
    # join NUM entries; its original fields remain verbatim in this view.
    condition = ' AND '.join('r.' + c + '=p.' + c for c in (
        'run_id', 'source_instance_id', 'binding_sha256', 'source_line'))
    records_sql = ('SELECT r.*,p.value_decimal,p.conversion_outcome,p.conversion_reason,'
                   'p.m2_model_version,p.conversion_rule_version,p.source_rule_version FROM (' +
                   plan['workspace.edp_lab.q_c750_m1_records_c750_step3_v1'] +
                   ') r LEFT JOIN ' + TABLE + ' VERSION AS OF 0 p ON ' + condition)
    assert not any(spark.catalog.tableExists(n) for n in (RECORDS, SUBSET))
    spark.sql('CREATE VIEW ' + RECORDS + ' AS ' + records_sql)
    c300 = json.loads((root / 'c300-ids.json').read_text())
    c300_ids = ','.join("'" + sid + "'" for sid in c300)
    spark.sql('CREATE VIEW ' + SUBSET + ' AS SELECT * FROM ' + RECORDS +
              ' WHERE source_instance_id IN (' + c300_ids + ')')
    assert {r['source_instance_id'] for r in inventory}.issubset(set(c300))
    assert persisted.groupBy('run_id', 'source_instance_id', 'binding_sha256',
                              'source_line').count().where('count <> 1').limit(1).count() == 0
    fin = fin_checks(root, plan)
    assert state(refs, plan) == original, 'M1 changed during validation'
    report = {'status': 'HISTORICAL_M2_VALIDATED', 'table': TABLE, 'read_version': 0,
              'records_view': RECORDS, 'c300_logical_subset': SUBSET,
              'eligible_count': expected, 'inventory': inventory, 'outcomes_by_binding': counts,
              'source_field_except_all_both_directions': 'PASS', 'unique_occurrence_keys': 'PASS',
              'independent_native_decimal_oracle': 'PASS', 'M1_unchanged': 'PASS',
              'C300_typed_count': expected, 'N450_typed_count': 0,
              'C300_total_DATA_records': refs['population']['C300']['DATA_records'],
              'C750_total_DATA_records': refs['population']['C750']['DATA_records'],
              'untouched_population_counts': 'Inherited pinned M1 population; not a fresh global count',
              'fin': fin, 'fingerprints': fingerprint(persisted, persisted.columns),
              'output_schema_json': persisted.schema.json(),
              'definitions': {n: spark.sql('SHOW CREATE TABLE ' + n).first()[0]
                              for n in (RECORDS, SUBSET)},
              'detail': spark.sql('DESCRIBE DETAIL ' + TABLE).first().asDict(recursive=True),
              'runtime_sha256': digest(raw), 'wall_seconds': time.time() - started}
    save('verification.json', report)
print(json.dumps({'phase': phase, 'wall_seconds': time.time() - started,
                  'status': 'COMPLETED', 'expected_eligible': expected}))
