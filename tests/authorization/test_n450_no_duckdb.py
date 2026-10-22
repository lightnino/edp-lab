"""Spark runtime must not import the offline profiling engine."""
import os
import subprocess
import sys
from pathlib import Path


def test_spark_runtime_without_duckdb():
    root = Path(__file__).resolve().parents[2]
    code = '''
import importlib.abc
import sys
class RejectDuckDB(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] == 'duckdb':
            raise AssertionError('Spark execution imported DuckDB')
sys.meta_path.insert(0, RejectDuckDB())
from edp_lab.materialization.n450_spark import run
from edp_lab.materialization.n450_runtime import checkpoint
from edp_lab.materialization.m1_verifier_v2 import verify_parquet
assert 'duckdb' not in sys.modules
'''
    subprocess.run([sys.executable, '-c', code], cwd=root,
                   env={**os.environ, 'PYTHONPATH': str(root / 'src')}, check=True)


def test_offline_provenance_retains_duckdb_version():
    import duckdb

    from edp_lab.profiling.source_reader import execution_provenance

    root = Path(__file__).resolve().parents[2]
    assert execution_provenance(root)['duckdb_runtime_version'] == duckdb.__version__
