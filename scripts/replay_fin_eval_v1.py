"""Read-only FIN_EVAL_V1 SQL replay; retain requests and complete API responses."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def execute(statement, name, out):
    request = {'warehouse_id': '589e80595c7c8cb8', 'statement': statement,
               'wait_timeout': '50s', 'row_limit': 1000}
    path = out / (name + '-request.json')
    path.write_text(json.dumps(request, indent=2) + '\n')
    result = subprocess.run(['databricks', 'api', 'post', '/api/2.0/sql/statements',
                             '--json', '@' + str(path), '-p', 'edp-lab', '-o', 'json'],
                            capture_output=True, text=True, check=True)
    response = json.loads(result.stdout)
    (out / (name + '-initial.json')).write_text(result.stdout)
    while response['status']['state'] in ('PENDING', 'RUNNING'):
        result = subprocess.run(['databricks', 'api', 'get',
                                 '/api/2.0/sql/statements/' + response['statement_id'] + '?wait_timeout=50s',
                                 '-p', 'edp-lab', '-o', 'json'],
                                capture_output=True, text=True, check=True)
        response = json.loads(result.stdout)
    (out / (name + '-result.json')).write_text(json.dumps(response, indent=2) + '\n')
    if response['status']['state'] != 'SUCCEEDED':
        raise RuntimeError(response['status'])
    if response.get('manifest', {}).get('truncated'):
        raise RuntimeError('Truncated SQL result')
    return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    contract = json.loads(Path('metadata/evaluations/fin_eval_v1.json').read_text())
    for name, expected in contract['files'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Changed evaluation input: ' + name)
    root = Path('sql/reconciliation/fin_eval_v1')
    view = 'workspace.edp_lab.q_c300_m1_records_reconciled_recovery_20261021_v2_full'
    for phase in ('before', 'after'):
        execute('SHOW CREATE TABLE ' + view, 'view-' + phase, args.output)
        if phase == 'before':
            for name in ('FIN_001', 'FIN_002'):
                execute((root / (name + '.sql')).read_text(), name, args.output)
            # Supplied FIN_002 projects differences only. Retain all selected amounts
            # and lineage separately to compare every literal in the fixture.
            sql = (root / 'FIN_002.sql').read_text()
            start = sql.index('SELECT\n    assets - liabilities')
            execute(sql[:start] + 'SELECT * FROM p', 'FIN_002-amounts', args.output)
            execute("SELECT DISTINCT source_line,byte_offset,byte_length,raw_sha256,archive_member,member_sha256,model_version,rule_version FROM " + view.replace("q_c300_m1_records_", "q_c300_m1_fields_") + " WHERE binding_sha256='341ce895a89fe164c1cc14af2679aa0b4637f593c6887e5c4d3a74bc49bbebcd' AND source_line IN (1548800,1793043,2461430,2606912,131726,1636110,3026665,3467762,677878,695193,1532665,2653949,3495804) ORDER BY source_line", 'lineage', args.output)
    execute('SHOW CREATE TABLE workspace.edp_lab.q_c300_m1_fields_reconciled_recovery_20261021_v2_full', 'fields-view', args.output)
    baseline = json.loads(Path('metadata/baselines/O_C300_M1.json').read_text())
    for i, table in enumerate(baseline['completion']['tables']):
        execute('DESCRIBE HISTORY ' + table + ' LIMIT 1', f'delta-history-{i}', args.output)
        execute('SHOW TBLPROPERTIES ' + table, f'delta-properties-{i}', args.output)
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.iterdir()}
    (args.output / 'hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')


if __name__ == '__main__':
    main()
