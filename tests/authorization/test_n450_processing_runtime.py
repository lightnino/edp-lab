"""Offline runtime readiness. Test owner pins exist only in temporary test deployments."""
import copy
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from edp_lab.ingestion import n450_authorization as auth
from edp_lab.ingestion.c300_admission import encoded
from edp_lab.ingestion.universe import ScopeDenied, sha
from edp_lab.materialization import n450_runtime as runtime
from edp_lab.materialization.n450_spark import query_plan
from edp_lab.profiling.source_reader import canonical_hash

ROOT = Path(__file__).resolve().parents[2]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / ('scripts/'+name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def prepared(tmp_path_factory):
    if not (ROOT / 'runs/n450/step3-scope-v1/execution-scope.proposed.json').exists():
        pytest.skip('Local sealed Step 3 scope evidence unavailable')
    destination = tmp_path_factory.mktemp('offline-prepared') / 'packet'
    load_script('prepare_n450_m1_runtime').build(destination)
    return destination


@pytest.fixture
def installed_test_host(tmp_path, monkeypatch, prepared):
    root = tmp_path / 'synthetic-host'
    shutil.copytree(prepared / 'payload', root)
    grant = json.loads((prepared / 'owner-record.proposed.json').read_bytes())
    grant['status'] = 'OWNER_APPROVED'
    grant_path = Path('test-owner.json')
    monkeypatch.setattr(auth, 'OWNER_GRANT_PATH', grant_path)

    def install():
        raw = encoded(grant)
        (root / grant_path).write_bytes(raw)
        monkeypatch.setattr(auth, 'OWNER_GRANT_SHA256', sha(raw))
    install()
    contract = runtime.load_contract(root)
    entries = json.loads((root / contract['processing_bindings']).read_bytes())
    return root, grant, entries, install


def test_existing_admission_pin_does_not_grant_processing():
    with pytest.raises(ScopeDenied, match='ACTION_NOT_AUTHORIZED'):
        auth.authorize(ROOT, 'remote_processing', [], cohort='C750')


def test_complete_authorized_registry_and_c300_reuse(installed_test_host):
    root, _, entries, _ = installed_test_host
    approved = auth.authorize(root, 'processing', [e['registered_binding'] for e in entries], cohort='C750')
    assert approved['status'] == 'AUTHORIZED_PREFLIGHT_ONLY'
    assert len(approved['entries']) == 450 and len(approved['reuse']) == 732
    assert set(approved['contract']['c300_versions'].values()) == {0}
    assert not (root / 'output').exists()


@pytest.mark.parametrize('kind', ['missing', 'forged', 'reordered', 'duplicate', 'subset', 'code'])
def test_scope_denied_before_side_effects(installed_test_host, monkeypatch, kind):
    root, _, entries, _ = installed_test_host
    bindings = [e['registered_binding'] for e in entries]
    if kind == 'missing':
        monkeypatch.setattr(auth, 'OWNER_GRANT_SHA256', None)
    elif kind == 'forged':
        (root / auth.OWNER_GRANT_PATH).write_text('{"status":"OWNER_APPROVED"}')
    elif kind == 'reordered':
        bindings.reverse()
    elif kind == 'duplicate':
        bindings[-1] = bindings[0]
    elif kind == 'subset':
        bindings.pop()
    else:
        (root / 'src/edp_lab/parsers/src010128_v1.py').write_text('changed')
    before = {str(p.relative_to(root)): sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
    with pytest.raises((ScopeDenied, ValueError)):
        auth.authorize(root, 'remote_processing', bindings, cohort='C750')
    assert before == {str(p.relative_to(root)): sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('kind', ['outside', 'holdout', 'remote_path', 'registration', 'profile', 'raw_hash'])
def test_resigned_test_scope_cannot_broaden_frozen_inputs(installed_test_host, kind):
    root, grant, entries, install = installed_test_host
    contract = runtime.load_contract(root)
    entry = entries[0]
    if kind in ('outside', 'holdout'):
        entry['source_identity'] = 'SRC000705' if kind == 'outside' else 'SRC000704'
    elif kind == 'remote_path':
        entry['remote_raw_path'] = entries[1]['remote_raw_path']
    elif kind == 'registration':
        entry['registered_binding']['source_instance_id'] = 'SRC999999'
    elif kind == 'profile':
        entry['registered_binding']['profile_id'] = 'GLOBAL_LATIN1'
    else:
        entry['registered_binding']['raw_sha256'] = '0'*64
    entry['binding_sha256'] = canonical_hash(entry['registered_binding'])
    raw = encoded(entries)
    (root / contract['processing_bindings']).write_bytes(raw)
    contract['files_sha256'][contract['processing_bindings']] = sha(raw)
    raw = encoded(contract)
    (root / runtime.CONTRACT).write_bytes(raw)
    grant['processing_contract_sha256'] = sha(raw)
    for action in ('processing', 'remote_processing'):
        grant['scopes'][action]['bindings'] = [e['registered_binding'] for e in entries]
    install()  # synthetic owner deployment only; no production approval or pin changed
    with pytest.raises((ScopeDenied, ValueError)):
        auth.authorize(root, 'processing', grant['scopes']['processing']['bindings'], cohort='C750')


@pytest.mark.parametrize('kind', ['table', 'volume', 'view', 'c300_version'])
def test_output_and_c300_version_isolation(installed_test_host, kind):
    root, grant, entries, install = installed_test_host
    contract = runtime.load_contract(root)
    if kind == 'table':
        contract['tables'][0] = next(iter(contract['c300_versions']))
    elif kind == 'volume':
        contract['base'] = '/Volumes/workspace/edp_lab/raw/c300-verified-v1'
    elif kind == 'view':
        contract['views'][0] = 'workspace.edp_lab.historical_view'
    else:
        key = next(iter(contract['c300_versions']))
        contract['c300_versions'][key] = 1
    raw = encoded(contract)
    (root / runtime.CONTRACT).write_bytes(raw)
    grant['processing_contract_sha256'] = sha(raw)
    install()
    with pytest.raises(ScopeDenied):
        auth.authorize(root, 'processing', [e['registered_binding'] for e in entries], cohort='C750')


def test_query_scope_fixed_versions_full_union(installed_test_host):
    root, _, _, _ = installed_test_host
    contract = runtime.load_contract(root)
    old_gate = json.loads((root / contract['c300_gate']).read_bytes())
    new = {'version': old_gate['version'], 'tables': dict.fromkeys(runtime.TABLES, 0),
           'bindings': [{'binding_sha256': f'{i:064x}', 'gate_status': 'PASS'} for i in range(450)]}
    new['evidence_sha256'] = canonical_hash(new)
    sql = query_plan(contract, old_gate, new)
    assert list(sql) == list(runtime.VIEWS)
    assert all(statement.count('UNION ALL') == 2 and 'VERSION AS OF 0' in statement
               and 'CREATE OR REPLACE' not in statement for statement in sql.values())
    assert 'explode(r.fields)' in sql[runtime.VIEWS[1]]
    old_gate['tables'][next(iter(old_gate['tables']))] = 1
    with pytest.raises(ScopeDenied, match='UNSEALED_GATE'):
        query_plan(contract, old_gate, new)


def test_traversal_and_symlink_outputs_rejected(tmp_path, monkeypatch):
    base = tmp_path / 'approved'
    base.mkdir()
    monkeypatch.setattr(runtime, 'BASE', str(base))
    assert runtime.output_path(base, 'checkpoints/one') == base / 'checkpoints/one'
    for relative in ('../old', '/tmp/old', 'a/../../old'):
        with pytest.raises(ScopeDenied):
            runtime.output_path(base, relative)
    (base / 'escape').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ScopeDenied):
        runtime.output_path(base, 'escape/old')
    assert list(tmp_path.iterdir()) == [base]


def test_fixed_submit_permissions_no_arbitrary_remote_operations():
    controller = load_script('run_n450_m1')
    for phase in runtime.PHASES:
        good = {'run_name': 'n450-m1-step3-'+phase, 'timeout_seconds': 28800 if phase == 'query' else 3600,
            'idempotency_token': 'n450-m1-step3-v1-'+phase,
            'tasks': [{'task_key': phase, 'timeout_seconds': 28800 if phase == 'query' else 3600, 'max_retries': 0,
                'notebook_task': {'notebook_path': runtime.WORKSPACE+'/runtime', 'source': 'WORKSPACE',
                                  'base_parameters': {'phase': phase}}}]}
        controller.validate_submission(phase, good)
        bad = copy.deepcopy(good)
        bad['tasks'][0]['notebook_task']['notebook_path'] = '/Shared/unapproved'
        with pytest.raises(ScopeDenied, match='UNAUTHORIZED_JOB_SUBMISSION'):
            controller.validate_submission(phase, bad)


def test_independent_pin_template_only_two_assignments():
    raw = Path(auth.__file__).read_bytes()
    changed = raw.replace(auth.OWNER_GRANT_SHA256.encode(), b'0'*64)
    assert runtime.host_template(raw) == runtime.host_template(changed)
    assert sha(runtime.host_template(raw+b'\n# code change')) != sha(runtime.host_template(raw))


def test_checkpoint_idempotency_and_invalid_partial(tmp_path, monkeypatch):
    # Synthetic input only; production source mappings are separately exercised
    # above with the exact 450 bindings. No real RAW bytes are copied.
    import io

    pytest.importorskip('pyarrow')
    from edp_lab.parsers.c300_v1 import DAILY_HEADER, inspect_stream

    base = tmp_path / 'approved'
    base.mkdir()
    monkeypatch.setattr(runtime, 'BASE', str(base))
    framing = ('Description: fixture\nLast Data Received: fixture\nComments: fixture\n'
               'Anonymous FTP: fixture\n \n'+DAILY_HEADER+'\n'+'-'*80+'\n').encode()
    raw = framing + b'001|name|form|date|path\n'*2
    path = tmp_path / 'synthetic.idx'
    path.write_bytes(raw)
    structure = inspect_stream(io.BytesIO(raw), 'SEC_EDGAR_DAILY_MASTER')
    binding = {'source_instance_id': 'SYNTHETIC', 'raw_path': str(path), 'raw_sha256': sha(raw),
        'member_sha256': sha(raw), 'archive_member': '', 'source_family': 'SEC_EDGAR_DAILY_MASTER',
        'expected_header': DAILY_HEADER.split('|'), 'prefix_evidence': structure['prefix_evidence'],
        'uncompressed_bytes': len(raw), 'profile_id': 'SEC_EDGAR_DAILY_MASTER_C300_PARSER_V1'}
    entry = {'registered_binding': binding, 'binding_sha256': canonical_hash(binding),
             'expected_data_records_from_validated_inputs': 2}
    # Test-only synthetic host capability. No production pin is installed.
    access = object.__new__(runtime.ProcessingAccess)
    access.root, access.pin = tmp_path, 'TEST_ONLY'
    monkeypatch.setattr(access, 'validate_entry', lambda entry: None)  # storage unit only
    monkeypatch.setattr(access, 'path_for', lambda b: path)
    folder = runtime.output_path(base, 'checkpoints/'+entry['binding_sha256'])
    first = runtime.checkpoint(tmp_path, entry, folder, access, 'synthetic')
    before = {str(p): (p.stat().st_mtime_ns, sha(p.read_bytes())) for p in folder.iterdir()}
    assert runtime.checkpoint(tmp_path, entry, folder, access, 'synthetic') == first
    assert before == {str(p): (p.stat().st_mtime_ns, sha(p.read_bytes())) for p in folder.iterdir()}
    with pytest.raises(ScopeDenied, match='CHECKPOINT_DESTINATION_CHANGED'):
        runtime.checkpoint(tmp_path, entry, tmp_path/'historical', access, 'synthetic')
    (folder / 'records.parquet').write_bytes(b'changed')
    with pytest.raises(ScopeDenied, match='CHECKPOINT_BYTES_CHANGED'):
        runtime.checkpoint(tmp_path, entry, folder, access, 'synthetic')
    (folder / 'complete.json').unlink()
    with pytest.raises(ScopeDenied, match='INCOMPLETE_ATTEMPT'):
        runtime.checkpoint(tmp_path, entry, folder, access, 'synthetic')


def test_bad_raw_hash_stops_before_checkpoint_write(tmp_path, monkeypatch):
    pytest.importorskip('pyarrow')
    base = tmp_path / 'approved'
    base.mkdir()
    monkeypatch.setattr(runtime, 'BASE', str(base))
    raw = tmp_path/'raw'
    raw.write_bytes(b'changed synthetic bytes')
    access = object.__new__(runtime.ProcessingAccess)
    access.root, access.pin = tmp_path, 'TEST_ONLY'
    monkeypatch.setattr(access, 'validate_entry', lambda entry: None)  # storage unit only
    monkeypatch.setattr(access, 'path_for', lambda b: raw)
    entry = {'binding_sha256': '0'*64, 'registered_binding': {'raw_sha256': '0'*64}}
    with pytest.raises(ScopeDenied, match='REMOTE_RAW_HASH_MISMATCH'):
        runtime.checkpoint(tmp_path, entry, base/'checkpoints'/('0'*64), access, 'synthetic')
    assert not list(base.iterdir())


@pytest.mark.parametrize('sid', ['SRC010001', 'SRC010128'])
def test_reader_and_independent_verifier_access_adapter(installed_test_host, tmp_path, monkeypatch, sid):
    # Full real-source adapter compatibility, using a simulated read-only UC mount.
    # No RAW copy and no actual Step 3 output registration/publication occurs.
    pytest.importorskip('pyarrow')
    root, _, entries, _ = installed_test_host
    entry = next(e for e in entries if e['source_instance_id'] == sid)
    local = Path(entry['registered_binding']['raw_path'])
    if not local.exists():
        pytest.skip('Local exact source unavailable')
    access = runtime.ProcessingAccess(root, [e['registered_binding'] for e in entries])
    def approved_test_mount(binding):
        assert binding == entry['registered_binding']
        return local
    monkeypatch.setattr(access, 'path_for', approved_test_mount)
    base = tmp_path / 'test-derived'
    base.mkdir()
    monkeypatch.setattr(runtime, 'BASE', str(base))
    folder = base/'checkpoints'/entry['binding_sha256']
    receipt = runtime.checkpoint(root, entry, folder, access, 'n450_step3_v1')
    assert receipt['verification']['records_data'] == entry['expected_data_records_from_validated_inputs']
    assert receipt['verification']['observed_member_sha256'] == entry['registered_binding']['raw_sha256']
    if sid == 'SRC010128':
        import pyarrow.parquet as pq
        rows = pq.read_table(folder/'records.parquet').to_pylist()
        assert rows[6214]['fields'][1]['lexical_value'] == 'EXPLORA INVESTIMENTOS GESTÃO DE RECURSOS LTDA'
        assert receipt['verification']['fields_data'] == 42650


@pytest.mark.parametrize('entrypoint', ['clean_publish', 'query_publish'])
def test_publication_entrypoints_reject_old_admission_grant(entrypoint):
    from edp_lab.materialization import n450_spark
    function = getattr(n450_spark, entrypoint)
    args = (None, ROOT, {'entries': []})
    with pytest.raises(ScopeDenied, match='ACTION_NOT_AUTHORIZED'):
        if entrypoint == 'clean_publish':
            function(*args, None, Path(runtime.BASE))
        else:
            function(*args, Path(runtime.BASE))


def test_clean_publication_requires_attempted_full_scope(installed_test_host, tmp_path, monkeypatch):
    from types import SimpleNamespace

    from edp_lab.materialization import n450_spark
    root, _, entries, _ = installed_test_host
    approved = auth.authorize(root, 'remote_processing', [e['registered_binding'] for e in entries], cohort='C750')
    base = tmp_path / 'approved'
    base.mkdir()
    # Isolate phase metadata in tmp; production output containment is tested separately.
    monkeypatch.setattr(n450_spark, 'output_path', lambda base, relative: base / relative)
    access = SimpleNamespace(pin=approved['owner_grant_sha256'])
    with pytest.raises(FileNotFoundError):
        n450_spark.clean_publish(None, root, approved, access, base)
    assert not list(base.iterdir())
    (base/'phases').mkdir()
    (base/'phases/full.json').write_bytes(encoded({'owner_grant_sha256': access.pin,
                                                 'binding_sha256': []}))
    with pytest.raises(ScopeDenied, match='FULL_PROCESSING_SCOPE_NOT_ATTEMPTED'):
        n450_spark.clean_publish(None, root, approved, access, base)


def test_optimized_execution_cannot_disable_lossless_assertions():
    import os
    import subprocess
    import sys

    code = ('from pathlib import Path; from edp_lab.ingestion import n450_authorization as a; '
            'a.authorize(Path.cwd(), "processing", [], cohort="C750")')
    result = subprocess.run([sys.executable, '-O', '-c', code], cwd=ROOT, check=False,
                            capture_output=True, text=True,
                            env={**os.environ, 'PYTHONPATH': str(ROOT/'src')})
    assert result.returncode != 0 and 'OPTIMIZED_EXECUTION_FORBIDDEN' in result.stderr


@pytest.mark.parametrize('suffix', ['; print("unreviewed")', ' + "changed"'])
def test_host_constant_edit_cannot_hide_executable_code(suffix):
    raw = Path(auth.__file__).read_bytes()
    lines = raw.decode().splitlines(keepends=True)
    modified = ''.join(line.rstrip('\n')+suffix+'\n' if line.startswith('OWNER_GRANT_SHA256 =')
                       else line for line in lines).encode()
    with pytest.raises(ScopeDenied, match='INVALID_HOST_TEMPLATE'):
        runtime.host_template(modified)


@pytest.mark.parametrize('damage', [None, 'runtime', 'host', 'contract'])
def test_cold_remote_bootstrap_guard_offline(installed_test_host, prepared, tmp_path, damage):
    import os
    import re
    import subprocess
    import sys

    root, grant, _, _ = installed_test_host
    base = tmp_path/'simulated-host-deployment'
    base.mkdir()
    for name in ('runtime.zip', 'contract.json'):
        shutil.copyfile(prepared/name, base/name)
    owner = encoded(grant)
    (base/'owner-record.approved.json').write_bytes(owner)
    source = Path(auth.__file__).read_text()
    source = re.sub(r'^OWNER_GRANT_SHA256 = .*$', 'OWNER_GRANT_SHA256 = "'+sha(owner)+'"',
                    source, flags=re.MULTILINE)
    source = re.sub(r'^OWNER_GRANT_PATH = .*$', 'OWNER_GRANT_PATH = Path("test-owner.json")',
                    source, flags=re.MULTILINE)
    if damage == 'host':
        source += '\nraise RuntimeError("UNREVIEWED_CODE_EXECUTED")\n'
    (base/'n450_authorization.host.py').write_text(source)
    if damage in ('runtime', 'contract'):
        target = base/('runtime.zip' if damage == 'runtime' else 'contract.json')
        target.write_bytes(target.read_bytes()+b'changed')
    expected = runtime.load_contract(root)['host_template_sha256']
    code = '''import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('offline_boot',sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=m.boot(Path(sys.argv[2]),sys.argv[3])
from edp_lab.ingestion import n450_authorization as a
from edp_lab.materialization.n450_runtime import load_contract
c=load_contract(root);e=json.loads((root/c['processing_bindings']).read_bytes())
r=a.authorize(root,'remote_processing',[x['registered_binding'] for x in e],cohort='C750')
print(r['status'])
'''
    result = subprocess.run([sys.executable, '-c', code, str(ROOT/'notebooks/clean_n450_m1.py'),
                             str(base), expected], capture_output=True, text=True, check=False,
                            env={**os.environ, 'PYTHONPATH': ''})
    if damage is None:
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == 'AUTHORIZED_PREFLIGHT_ONLY'
    else:
        assert result.returncode != 0
        assert 'UNREVIEWED_CODE_EXECUTED' not in result.stderr
        assert 'AUTHORIZED_PREFLIGHT_ONLY' not in result.stdout
    assert not (base/'checkpoints').exists()


def test_generated_owner_script_is_inert_and_syntax_valid(prepared):
    import subprocess

    script = prepared/'install-owner.sh'
    result = subprocess.run(['sh', '-n', str(script)], capture_output=True, check=False)
    assert result.returncode == 0
    text = script.read_text()
    body = text.split("<<'OWNER_PY'\n", 1)[1].rsplit('\nOWNER_PY\n', 1)[0]
    compile(body, str(script), 'exec')  # parse only: MUST NOT issue approval or install a pin
    review = json.loads((prepared/'review.json').read_bytes())
    assert sha(script.read_bytes()) == review['owner_installer_sha256']
    assert json.loads((prepared/'owner-record.proposed.json').read_bytes())['status'] == 'PENDING_OWNER_REVIEW'
    assert not (ROOT/'metadata/authorizations/n450_processing_v1.json').exists()


def test_bounded_validation_groups_and_verified_check_reuse(tmp_path, monkeypatch):
    from edp_lab.materialization.n450_spark import checkpoint_validation, validation_groups
    gates = [{'binding_sha256': str(i)} for i in range(200)]
    expected = {str(i): {'records_data': 500_000} for i in range(200)}
    groups = validation_groups(gates, expected)
    assert [x for group in groups for x in group] == [g['binding_sha256'] for g in gates]
    assert all(len(group) <= 24 for group in groups)
    base = tmp_path/'approved'
    base.mkdir()
    monkeypatch.setattr(runtime, 'BASE', str(base))
    identity = {'bindings': ['one'], 'sql': 'PINNED_SQL', 'tables': {'fixed': 0}}
    first = checkpoint_validation(base, identity, lambda: 0)
    def unexpected_replay():
        raise AssertionError('Do not repeat a durably verified comparison')
    assert checkpoint_validation(base, identity, unexpected_replay) == first
    path = base/'queryable/checks'/(canonical_hash(identity)+'.json')
    changed = json.loads(path.read_bytes())
    changed['difference_count'] = 1
    path.write_bytes(encoded(changed))
    with pytest.raises(ScopeDenied, match='VALIDATION_CHECKPOINT_CHANGED'):
        checkpoint_validation(base, identity, lambda: 0)
    other = {**identity, 'bindings': ['two']}
    with pytest.raises(ScopeDenied, match='QUERYABLE_MULTISET_DIFFERENCE'):
        checkpoint_validation(base, other, lambda: 1)
    assert not (path.parent/(canonical_hash(other)+'.json')).exists()
    assert list(path.parent.glob('*-failed-*.json'))
