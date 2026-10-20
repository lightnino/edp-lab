"""Run all five profiling tools on all frozen GOLD_V2 tables, offline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from edp_lab.profiling.source_reader import FREEZE, execution_provenance, read_registered
from edp_lab.profiling.tools import (
    candidate_key_scan,
    find_duplicates,
    profile_column,
    profile_table,
    schema_fingerprint,
)


def run(root: Path, output_dir: Path):
    """Persist evidence separately from RAW; reject output paths inside data/metadata/src."""
    root, output_dir = root.resolve(), output_dir.resolve()
    if not output_dir.is_relative_to(root / 'runs'):
        raise ValueError('Output must be under the gitignored runs/ directory')
    freeze = json.loads((root / FREEZE).read_text())
    provenance = execution_provenance(root)
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for binding in freeze['effective_configuration']['tables']:
        table = read_registered(root, binding['source_instance_id'], binding['logical_table_name'],
                                provenance=provenance)
        table_result = profile_table(table)
        duplicate_result = find_duplicates(table)
        key_result = candidate_key_scan(table, search_columns=table.columns[:3], max_width=2)
        schema_result = schema_fingerprint(table)
        columns = [profile_column(table, name) for name in table.columns]
        results = {'table': table_result, 'columns': columns, 'duplicates': duplicate_result,
                   'keys': key_result, 'schema': schema_result}
        name = f"{binding['source_instance_id']}_{binding['logical_table_name']}"
        path = output_dir / f"{name}_{table_result['run_id']}.json"
        encoded = json.dumps(results, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
        if path.exists() and path.read_text() != encoded:
            raise ValueError(f'Existing evidence differs: {path}')
        if not path.exists():
            path.write_text(encoded)
        summary = {'source': binding['source_instance_id'], 'table': binding['logical_table_name'],
                   'parse_status': table.parse_status, 'rows': len(table.rows),
                   'columns': len(table.columns), 'evidence': str(path.relative_to(root)),
                   'duplicate_groups': duplicate_result.get('duplicate_groups'),
                   'rows_in_duplicate_groups': duplicate_result.get('rows_in_duplicate_groups'),
                   'excess_rows': duplicate_result.get('excess_rows'),
                   'errors': list(table.errors), 'all_five_functions_executed': True,
                   'column_profiles': len(columns),
                   'blocked_metrics': 'semantic NULL-dependent column metrics; key eligibility',
                   'key_search': 'all singles; bounded pairs within first three columns, max width 2'}
        summaries.append(summary)
        print(json.dumps(summary), flush=True)
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--output-dir', type=Path, default=Path('runs/profiling'))
    args = parser.parse_args()
    summaries = run(args.root, args.output_dir)
    return int(any(s['parse_status'] != 'PASS' for s in summaries))


if __name__ == '__main__':
    raise SystemExit(main())
