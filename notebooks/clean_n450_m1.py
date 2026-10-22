# Databricks notebook source
"""Fixed-scope Step 3 runtime. Trusted owner installation is external to payload."""
import ast
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

BASE = Path('/Volumes/workspace/edp_lab/raw/n450-m1/n450_step3_v1')
# Filled mechanically from the reviewed host module template, never an owner pin.
HOST_TEMPLATE_SHA256 = 'BUILD_HOST_TEMPLATE_SHA256'

def boot(base, expected_template):
    host_raw = (base / 'n450_authorization.host.py').read_bytes()
    text = host_raw.decode()
    nodes = ast.parse(text).body
    for name in ('OWNER_GRANT_SHA256', 'OWNER_GRANT_PATH'):
        selected = [n for n in nodes if isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name]
        if len(selected) != 1:
            raise ValueError('INVALID_HOST_DEPLOYMENT')
        node = selected[0]
        if node.lineno != node.end_lineno or sum(n.lineno == node.lineno for n in nodes) != 1:
            raise ValueError('INVALID_HOST_DEPLOYMENT')
        value = node.value
        if name == 'OWNER_GRANT_PATH':
            if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                    and value.func.id == 'Path' and len(value.args) == 1 and not value.keywords):
                raise ValueError('INVALID_HOST_DEPLOYMENT')
            value = value.args[0]
        if not isinstance(value, ast.Constant) or not (value.value is None or isinstance(value.value, str)):
            raise ValueError('INVALID_HOST_DEPLOYMENT')
    normalized = text
    for name in ('OWNER_GRANT_SHA256', 'OWNER_GRANT_PATH'):
        normalized, count = re.subn(r'^'+name+r' = .*$', name+' = None', normalized,
                                   flags=re.MULTILINE)
        if count != 1:
            raise ValueError('INVALID_HOST_DEPLOYMENT')
    if hashlib.sha256(normalized.encode()).hexdigest() != expected_template:
        raise ValueError('UNREVIEWED_HOST_CODE')
    assignments = {node.targets[0].id: node.value for node in ast.parse(text).body
                   if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
    pin = ast.literal_eval(assignments['OWNER_GRANT_SHA256'])
    record_raw = (base / 'owner-record.approved.json').read_bytes()
    if not pin or hashlib.sha256(record_raw).hexdigest() != pin:
        raise PermissionError('OWNER_GRANT_PIN_MISMATCH')
    grant = json.loads(record_raw)
    if grant['status'] != 'OWNER_APPROVED' or 'remote_processing' not in grant['scopes']:
        raise PermissionError('PROCESSING_NOT_APPROVED')
    contract_raw = (base / 'contract.json').read_bytes()
    if hashlib.sha256(contract_raw).hexdigest() != grant['processing_contract_sha256']:
        raise PermissionError('PROCESSING_CONTRACT_CHANGED')
    contract = json.loads(contract_raw)
    runtime = (base / 'runtime.zip').read_bytes()
    if hashlib.sha256(runtime).hexdigest() != contract['runtime_sha256']:
        raise PermissionError('RUNTIME_ARCHIVE_CHANGED')
    root = Path(tempfile.mkdtemp(prefix='edp-n450-runtime-'))
    with zipfile.ZipFile(base / 'runtime.zip') as archive:
        if any(Path(n).is_absolute() or '..' in Path(n).parts for n in archive.namelist()):
            raise ValueError('UNSAFE_RUNTIME_ARCHIVE')
        archive.extractall(root)
    sys.path.insert(0, str(root / 'src'))
    # Install only the already independently installed trusted host module, not a
    # caller pin or an Agent-produced approval. The payload deliberately excludes it.
    module_name = 'edp_lab.ingestion.n450_authorization'
    spec = importlib.util.spec_from_file_location(module_name, base / 'n450_authorization.host.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    # The imported package attribute must refer to the same trusted module.
    import edp_lab.ingestion
    edp_lab.ingestion.n450_authorization = module
    destination = root / module.OWNER_GRANT_PATH
    if Path(module.OWNER_GRANT_PATH).is_absolute() or '..' in Path(module.OWNER_GRANT_PATH).parts:
        raise ValueError('UNSAFE_AUTHORITY_LOCATION')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(record_raw)
    target = root / grant['processing_contract_path']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(contract_raw)
    return root


if __name__ == '__main__':
    dbutils.widgets.text('phase', 'smoke')  # noqa: F821
    phase = dbutils.widgets.get('phase')  # noqa: F821
    root = boot(BASE, HOST_TEMPLATE_SHA256)
    from edp_lab.materialization.n450_spark import run
    result = run(spark, root, phase)  # noqa: F821
    dbutils.notebook.exit(json.dumps(result))  # noqa: F821
