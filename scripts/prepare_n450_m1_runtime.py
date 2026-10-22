"""Offline deterministic runtime readiness; no approval, upload, jobs or RAW reads."""
from __future__ import annotations

import argparse
import json
import subprocess
import zipfile
from pathlib import Path

from edp_lab.ingestion.c300_admission import encoded
from edp_lab.ingestion.universe import sha
from edp_lab.materialization.n450_runtime import (
    BASE,
    CONTRACT,
    PHASES,
    TABLES,
    VIEWS,
    WORKSPACE,
    host_template,
)

ROOT = Path(__file__).resolve().parents[1]
LAB = Path('/Users/lightnino/Projects/edp-lab')


def build(destination):
    source = ROOT / 'runs/n450/step3-scope-v1'
    original = json.loads((source / 'execution-scope.proposed.json').read_bytes())
    assert sha((source / 'execution-scope.proposed.json').read_bytes()) == (
        '1b8d8a66b08793107899b67d7a8c9a7a9d92bdee704fc2f7c6a4786d5e7ff840')
    assert not destination.exists(), 'Preserve previous preparation; use a new output directory'
    destination.mkdir(parents=True)
    payload = destination / 'payload'
    payload.mkdir()
    files = {}

    def include(relative, raw):
        path = payload / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        files[relative] = sha(raw)

    for path in sorted((ROOT / 'src/edp_lab').rglob('*.py')):
        if path.name != 'n450_authorization.py':
            include(str(path.relative_to(ROOT)), path.read_bytes())
    # All frozen metadata/proposals are immutable runtime inputs, never outputs.
    for folder in ('metadata', 'proposals/n450-v1'):
        for path in sorted((ROOT / folder).rglob('*')):
            if path.is_file():
                include(str(path.relative_to(ROOT)), path.read_bytes())
    historical_freeze = json.loads((ROOT / 'metadata/freezes/O_C300_M1_v1/freeze.json').read_bytes())
    for relative, digest in historical_freeze['files'].items():
        raw = (ROOT / relative).read_bytes()
        assert sha(raw) == digest
        include(relative, raw)
    include('uv.lock', (ROOT / 'uv.lock').read_bytes())
    for relative in ('scripts/run_n450_m1.py', 'scripts/prepare_n450_m1_runtime.py',
                     'notebooks/clean_n450_m1.py'):
        include(relative, (ROOT / relative).read_bytes())
    aliases = {}
    authority = json.loads((ROOT / 'metadata/source_universes/approved_v1/manifest.json').read_bytes())
    inventory_raw = Path(authority['inventory_reference']).read_bytes()
    assert sha(inventory_raw) == authority['inventory_sha256']
    inventory_alias = '.evidence/' + authority['inventory_sha256']
    aliases[authority['inventory_reference']] = inventory_alias
    include(inventory_alias, inventory_raw)
    side = json.loads((ROOT / 'metadata/source_universes/historical_cohort_bindings_v1.json').read_bytes())
    for logical, digest in side['evidence'].items():
        if Path(logical).is_absolute():
            raw = Path(logical).read_bytes()
            assert sha(raw) == digest
            aliases[logical] = '.evidence/' + digest
            include(aliases[logical], raw)
    prefix = str(Path(CONTRACT).parent)
    for filename, digest in original['ordered_scope_files'].items():
        raw = (source / filename).read_bytes()
        assert sha(raw) == digest
        include(prefix + '/' + filename, raw)
    # Verify retained gate/snapshot evidence through the frozen baseline index.
    baseline = json.loads((ROOT / 'metadata/baselines/O_C300_M1.json').read_bytes())
    ref = 'runs/c300-m1/reconciled_recovery_20261021_v2/collected-full/profile_run_manifest.json'
    manifest_raw = (LAB / ref).read_bytes()
    assert sha(manifest_raw) == baseline['retained_input_manifests'][ref]['sha256']
    manifest = json.loads(manifest_raw)
    gate_raw = ((LAB / ref).parent / 'lossless-gate.json').read_bytes()
    assert sha(gate_raw) == manifest['artifacts']['lossless-gate.json']['sha256']
    gate_path = '.evidence/' + sha(gate_raw)
    include(gate_path, gate_raw)
    identities, table_identities = {}, {}
    detail_ref = 'runs/c300-m1/main_recovery_20261021_v4/delta-output-metadata-v2.json'
    detail_raw = (LAB / detail_ref).read_bytes()
    assert sha(detail_raw) == baseline['closeout_review']['supporting_evidence']['members'][detail_ref]
    detail_path = '.evidence/' + sha(detail_raw)
    include(detail_path, detail_raw)
    historical_details = json.loads(detail_raw)['tables']
    versions = original['C300_snapshot_versions']
    for table in versions:
        ref = 'runs/c300-m1/closeout-review-v1/' + table.split('.')[-1] + '-catalog.json'
        raw = (LAB / ref).read_bytes()
        assert sha(raw) == baseline['closeout_review']['supporting_evidence']['members'][ref]
        catalog = json.loads(raw)
        identities[table] = catalog['storage_location']
        detail = historical_details[table]['detail']
        assert json.loads(detail['properties'])['io.unitycatalog.tableId'] == catalog['table_id']
        table_identities[table] = {'delta_id': detail['id'], 'uc_table_id': catalog['table_id'],
                                   'detail_location': detail['location']}
    host_raw = (ROOT / 'src/edp_lab/ingestion/n450_authorization.py').read_bytes()
    host_sha = sha(host_template(host_raw))
    rendered = (ROOT / 'notebooks/clean_n450_m1.py').read_text().replace(
        'BUILD_HOST_TEMPLATE_SHA256', host_sha).encode()
    include('notebooks/clean_n450_m1.deployed.py', rendered)
    (destination / 'notebook.py').write_bytes(rendered)
    submissions = {}
    for phase in PHASES:
        submission = {'run_name': 'n450-m1-step3-'+phase, 'timeout_seconds': 28800 if phase == 'query' else 3600,
            'idempotency_token': 'n450-m1-step3-v1-'+phase+('-exact-path-v1' if phase == 'smoke' else '-clean-write-fix-v1' if phase == 'publish' else ''),
            'tasks': [{'task_key': phase, 'timeout_seconds': 28800 if phase == 'query' else 3600, 'max_retries': 0,
                'notebook_task': {'notebook_path': WORKSPACE+'/runtime', 'source': 'WORKSPACE',
                                  'base_parameters': {'phase': phase}}}]}
        raw = encoded(submission)
        (destination / ('submit-'+phase+'.json')).write_bytes(raw)
        submissions[phase] = sha(raw)
        include(prefix + '/submit-'+phase+'.json', raw)
    runtime = destination / 'runtime.zip'
    with zipfile.ZipFile(runtime, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in sorted(files):
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (payload / relative).read_bytes(), compresslevel=9)
    contract = {'schema': 'N450_M1_RUNTIME_V1', 'base': BASE, 'workspace': WORKSPACE,
        'tables': list(TABLES), 'views': list(VIEWS), 'phases': list(PHASES),
        'base_code_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                                    text=True).strip(),
        'original_scope_sha256': sha((source / 'execution-scope.proposed.json').read_bytes()),
        'processing_bindings': prefix + '/processing-bindings.proposed.json',
        'c300_reuse': prefix + '/c300-reuse.proposed.json',
        'c300_versions': versions, 'c300_storage_locations': identities, 'c300_gate': gate_path,
        'c300_table_identities': table_identities, 'c300_detail_evidence': detail_path,
        'evidence_aliases': aliases, 'files_sha256': files, 'host_template_sha256': host_sha,
        'runtime_sha256': sha(runtime.read_bytes()), 'notebook_sha256': sha(rendered),
        'dependency_policy': 'Use existing workspace pyarrow/Spark; DuckDB is offline-only. Fail before outputs if '
            'missing. No pip/network dependency installation. Record actual versions.',
        'permissions': {'RAW': 'READ_ONLY_EXACT_450_OBJECTS', 'C300': 'READ_ONLY_VERSION_0',
            'deployment': ['runtime.zip', 'contract.json', 'owner-record.approved.json',
                           'n450_authorization.host.py'],
            'write_tables': list(TABLES), 'write_views': list(VIEWS),
            'write_volume_root': BASE, 'write_workspace_path': WORKSPACE + '/runtime'},
        'model': 'M1_LEXICAL_V1', 'rule': 'C300_LITERAL_IDENTITY_V1',
        'historical_raw_replay': False, 'output_freeze': 'NOT_AUTHORIZED',
        'storage_limitations': original['storage_limitations'],
        'raw_writes_authorized': False, 'immutable_RAW_claim': False,
        'actual_execution_timestamp_policy': 'Record actual execution times; effective on valid host installation'}
    contract_raw = encoded(contract)
    (destination / 'contract.json').write_bytes(contract_raw)
    target = payload / CONTRACT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(contract_raw)
    historical_raw = (ROOT / 'metadata/authorizations/n450_execution_v1.json').read_bytes()
    previous = json.loads(historical_raw)
    grant = {k: previous[k] for k in ('universe', 'packet_sha256', 'scopes',
                                     'registrations', 'admitted_at_utc')}
    grant['schema'] = 'N450_PROCESSING_EXECUTION_V1'
    grant['historical_admission_grant_sha256'] = sha(historical_raw)
    grant['historical_timing_scope'] = 'admitted_at_utc is historical Admission metadata only; '
    grant['historical_timing_scope'] += 'processing becomes eligible upon valid host installation'
    grant.update(status='PENDING_OWNER_REVIEW', processing_contract_path=CONTRACT,
                 processing_contract_sha256=sha(contract_raw),
                 processing_policy='Immediate eligibility only after valid independent host installation; '
                    'actual events recorded independently. No Admission replay or output freeze.')
    entries = json.loads((payload / contract['processing_bindings']).read_bytes())
    scope = {'cohort': 'C750', 'bindings': [e['registered_binding'] for e in entries]}
    grant['scopes'].update(processing=scope, remote_processing=scope)
    pending_raw = encoded(grant)
    (destination / 'owner-record.proposed.json').write_bytes(pending_raw)
    approved = {**grant, 'status': 'OWNER_APPROVED'}
    pin = sha(encoded(approved))  # calculation only; never write an approved record or install a pin
    installed_host = host_raw.decode()
    import re
    installed_host = re.sub(r'^OWNER_GRANT_SHA256 = .*$', 'OWNER_GRANT_SHA256 = "'+pin+'"',
                            installed_host, flags=re.MULTILINE)
    installed_host = re.sub(r'^OWNER_GRANT_PATH = .*$',
        'OWNER_GRANT_PATH = Path("metadata/authorizations/n450_processing_v5.json")',
        installed_host, flags=re.MULTILINE)
    review = {'status': 'READY_FOR_OWNER_REVIEW_NOT_INSTALLED', 'contract_sha256': sha(contract_raw),
        'proposed_record_sha256': sha(pending_raw), 'expected_approved_record_host_pin': pin,
        'runtime_sha256': contract['runtime_sha256'], 'notebook_sha256': sha(rendered),
        'host_template_sha256': host_sha, 'expected_installed_host_code_sha256': sha(installed_host.encode()),
        'submission_sha256': submissions, 'new_processing_bindings': 450,
        'reused_C300_bindings': 732, 'physical_C750': 750, 'logical_bindings': 1182,
        'host_record_path': 'metadata/authorizations/n450_processing_v5.json',
        'installed': False, 'remote_deployed': False}
    import shlex
    installer = """#!/bin/sh
# OWNER/TRUSTED TERMINAL ONLY, after independent review of the exact proposed record.
set -eu
cd __ROOT__
PYTHONPATH=src __PYTHON__ - "$0" <<'OWNER_PY'
import json, os, re, sys
from pathlib import Path
from edp_lab.ingestion.c300_admission import encoded
from edp_lab.ingestion.universe import sha
from edp_lab.materialization.n450_runtime import host_template
prepared = Path(sys.argv[1]).resolve().parent
proposal = (prepared / 'owner-record.proposed.json').read_bytes()
assert sha(proposal) == '__PROPOSAL__', 'Proposed record differs from owner-reviewed bytes'
grant = json.loads(proposal)
assert grant['status'] == 'PENDING_OWNER_REVIEW' and encoded(grant) == proposal
grant['status'] = 'OWNER_APPROVED'
approved = encoded(grant)
assert sha(approved) == '__PIN__'
original = Path('metadata/authorizations/n450_execution_v1.json')
assert sha(original.read_bytes()) == '50507c7fcde3d5d7295bfa396cd216587402c6852eb5e6d827ee3ad53beb3a48'
host = Path('src/edp_lab/ingestion/n450_authorization.py')
source = host.read_bytes()
assert sha(host_template(source)) == '__TEMPLATE__', 'Host code differs from reviewed implementation'
updated, n = re.subn(r'^OWNER_GRANT_SHA256 = .*$', 'OWNER_GRANT_SHA256 = "__PIN__"', source.decode(), flags=re.MULTILINE)
assert n == 1
updated, n = re.subn(r'^OWNER_GRANT_PATH = .*$', 'OWNER_GRANT_PATH = Path("metadata/authorizations/n450_processing_v5.json")', updated, flags=re.MULTILINE)
assert n == 1
updated = updated.encode()
assert sha(updated) == '__HOST__' and host_template(updated) == host_template(source)
target = Path('metadata/authorizations/n450_processing_v5.json')
if target.exists():
    assert target.read_bytes() == approved, 'Existing processing record differs; STOP'
else:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(approved)
if source != updated:
    temporary = host.with_name(host.name + '.owner-install.tmp')
    with temporary.open('xb') as stream:
        stream.write(updated)
    os.chmod(temporary, host.stat().st_mode)
    os.replace(temporary, host)
assert sha(host.read_bytes()) == '__HOST__' and sha(target.read_bytes()) == '__PIN__'
assert sha(original.read_bytes()) == '50507c7fcde3d5d7295bfa396cd216587402c6852eb5e6d827ee3ad53beb3a48'
print('Owner record and existing host pin verified. No remote deployment or processing executed.')
OWNER_PY
"""
    replacements = {'__ROOT__': shlex.quote(str(ROOT)),
        '__PYTHON__': shlex.quote(str(LAB / '.venv/bin/python')),
        '__PROPOSAL__': review['proposed_record_sha256'], '__PIN__': pin,
        '__TEMPLATE__': host_sha, '__HOST__': review['expected_installed_host_code_sha256']}
    for marker, value in replacements.items():
        installer = installer.replace(marker, value)
    (destination / 'install-owner.sh').write_text(installer)
    review['owner_installer_sha256'] = sha(installer.encode())
    review['owner_install_command'] = 'sh ' + shlex.quote(str(destination.resolve() / 'install-owner.sh'))
    code_hashes = {p: h for p, h in files.items() if p.endswith('.py')}
    (destination / 'code-fingerprints.json').write_bytes(encoded(code_hashes))
    review['code_fingerprints_sha256'] = sha(encoded(code_hashes))
    instructions = ('# Exact Step 3 owner review\n\n'
        'Preparation only. No approval or owner pin has been installed.\n\n'
        'Review owner-record.proposed.json and contract.json, including the complete '
        'ordered 450 processing bindings, 732 C300 reuse bindings, 750 physical / '
        '1182 logical scope, exact destinations and all fingerprints.\n\n'
        'Only after independently approving those exact bytes, run in your trusted '
        'local terminal:\n\n```sh\n' + review['owner_install_command'] + '\n```\n\n'
        'This uses the existing canonical status change and existing two host constants. '
        'It preserves the old Admission grant and changes no other code. No fixed '
        'effective-time delay, new trust root or backup requirement. Actual execution '
        'times will be recorded separately. The executor must subsequently validate '
        'the installed pin, code/runtime closure and consume-time source/host checks.\n\n'
        'Neither this review nor the pending proposal permits the execution agent to '
        'run install-owner.sh. No remote deploy, processing or output write during readiness.\n')
    (destination / 'REVIEW.md').write_text(instructions)
    (destination / 'review.json').write_bytes(encoded(review))
    print(json.dumps(review, indent=2))
    return review


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    build(args.destination)
