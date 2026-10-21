"""Exact N450 runtime adapter under the existing host-pinned owner grant.

No authority is installed here. C300 is read only at frozen versions; RAW access
is limited to the signed 450-object map. Existing M1 schemas and gate are reused.
"""
from __future__ import annotations

import ast
import json
import re
import time
from pathlib import Path

from edp_lab.ingestion import n450_authorization as auth
from edp_lab.ingestion.c300_admission import encoded
from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.ingestion.universe import (
    APPROVAL_SHA256,
    APPROVED_AUTHORITY_SHA256,
    AUTHORITY_PATH,
    BINDINGS_PATH,
    BINDINGS_SHA256,
    UniverseGate,
    sha,
)
from edp_lab.materialization.c300_m1 import package_record, record_schema
from edp_lab.materialization.m1_verifier_v2 import verify_parquet
from edp_lab.parsers.c300_reader_v1 import validated_occurrences
from edp_lab.profiling.source_reader import canonical_hash

CONTRACT = 'proposals/n450-processing-v2/contract.json'
BASE = '/Volumes/workspace/edp_lab/raw/n450-m1/n450_step3_v1'
WORKSPACE = '/Shared/edp-lab-n450-m1/n450_step3_v1'
TABLES = ('workspace.edp_lab.clean_n450_m1_records_n450_step3_v1',
          'workspace.edp_lab.clean_n450_m1_bindings_n450_step3_v1')
VIEWS = tuple(f'workspace.edp_lab.q_c750_m1_{kind}_c750_step3_v1'
              for kind in ('records', 'fields', 'coverage'))
PHASES = ('smoke', 'full', 'publish', 'query')
SMOKE = ('SRC010001', 'SRC010128', 'SRC010450')


def require(ok, message):
    auth._require(ok, message)


def host_template(raw):
    """Only the existing trusted deployment's two owner-pin assignments may vary."""
    text = raw.decode('utf-8')
    nodes = ast.parse(text).body
    for name in ('OWNER_GRANT_SHA256', 'OWNER_GRANT_PATH'):
        selected = [n for n in nodes if isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name]
        require(len(selected) == 1, 'INVALID_HOST_TEMPLATE')
        node = selected[0]
        require(node.lineno == node.end_lineno and
                sum(n.lineno == node.lineno for n in nodes) == 1, 'INVALID_HOST_TEMPLATE')
        value = node.value
        if name == 'OWNER_GRANT_PATH':
            require(isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                    and value.func.id == 'Path' and len(value.args) == 1 and not value.keywords,
                    'INVALID_HOST_TEMPLATE')
            value = value.args[0]
        require(isinstance(value, ast.Constant) and (value.value is None or isinstance(value.value, str)),
                'INVALID_HOST_TEMPLATE')
    for name in ('OWNER_GRANT_SHA256', 'OWNER_GRANT_PATH'):
        text, count = re.subn(r'^' + name + r' = .*$', name + ' = None', text, flags=re.MULTILINE)
        require(count == 1, 'INVALID_HOST_TEMPLATE')
    return text.encode()


def snapshot_gate(root, contract):
    """Verify identical authority bytes via explicit hash-addressed metadata aliases.

    This relocates metadata only. It never resolves or substitutes a RAW path.
    Absolute historical review references are packaged as .evidence/<exact SHA>.
    """
    raw = (root / AUTHORITY_PATH).read_bytes()
    side_raw = (root / BINDINGS_PATH).read_bytes()
    require(sha(raw) == APPROVED_AUTHORITY_SHA256 and sha(side_raw) == BINDINGS_SHA256,
            'SOURCE_AUTHORITY_CHANGED')
    document, side = json.loads(raw), json.loads(side_raw)
    approval = (root / document['approval_reference']).read_bytes()
    require(sha(approval) == APPROVAL_SHA256 and json.loads(approval)['status'] == 'APPROVED'
            and json.loads(approval)['manifest_sha256'] == sha(raw), 'INVALID_OWNER_AUTHORITY')
    require(side['universe_manifest_sha256'] == sha(raw) and side['universe_version'] == '1',
            'INVALID_COHORT_AUTHORITY')
    for logical, digest in side['evidence'].items():
        relative = contract['evidence_aliases'].get(logical, logical)
        require(relative == logical if not Path(logical).is_absolute()
                else relative == '.evidence/' + digest, 'UNAPPROVED_METADATA_ALIAS')
        require(sha((root / relative).read_bytes()) == digest, 'AUTHORITY_EVIDENCE_CHANGED')
    return UniverseGate(raw, sha(raw), side_raw)


def load_contract(root):
    return json.loads((root / CONTRACT).read_bytes())


def authorize_processing(root, action, bindings):
    """Installed owner pin, complete ordered scope and code closure before effects."""
    require(__debug__, 'OPTIMIZED_EXECUTION_FORBIDDEN')
    require(action in {'processing', 'remote_processing'}, 'INVALID_PROCESSING_ACTION')
    require(auth.OWNER_GRANT_SHA256 is not None, 'OWNER_EXECUTION_GRANT_NOT_INSTALLED')
    raw = (root / auth.OWNER_GRANT_PATH).read_bytes()
    require(sha(raw) == auth.OWNER_GRANT_SHA256, 'OWNER_GRANT_PIN_MISMATCH')
    grant = json.loads(raw)
    require(grant.get('status') == 'OWNER_APPROVED', 'INVALID_OWNER_GRANT')
    scope = grant['scopes'].get(action)
    require(scope is not None and scope['cohort'] == 'C750', 'ACTION_NOT_AUTHORIZED')
    require(bindings == scope['bindings'], 'EXACT_INPUT_SET_REQUIRED')
    # The new record extends execution authority; historical grants/freezes are
    # byte-identical inputs, never editable declarations in the new scope.
    historical_raw = (root / 'metadata/authorizations/n450_execution_v1.json').read_bytes()
    require(sha(historical_raw) == '50507c7fcde3d5d7295bfa396cd216587402c6852eb5e6d827ee3ad53beb3a48'
            == grant['historical_admission_grant_sha256'], 'HISTORICAL_ADMISSION_AUTHORITY_CHANGED')
    historical = json.loads(historical_raw)
    for action_name in ('admission', 'freeze'):
        require(grant['scopes'][action_name] == historical['scopes'][action_name],
                'HISTORICAL_EXECUTION_SCOPE_CHANGED')
        old_scope = historical['scopes'][action_name]
        for name, digest in old_scope['files_sha256'].items():
            require(sha((root / old_scope['destination'] / name).read_bytes()) == digest,
                    'FROZEN_COHORT_METADATA_CHANGED')
    require(sha((root / 'metadata/freezes/O_C300_M1_v1/freeze.json').read_bytes()) ==
            'db710f6152c6ffe33ee2d0371e7dadc8f9ff76e67af3a8e82d807a4c7923542c',
            'C300_BASELINE_FREEZE_CHANGED')
    frozen_c300 = json.loads((root / 'metadata/freezes/O_C300_M1_v1/freeze.json').read_bytes())
    for relative, digest in frozen_c300['files'].items():
        require(sha((root / relative).read_bytes()) == digest, 'C300_FROZEN_REFERENCE_CHANGED')
    contract_raw = (root / CONTRACT).read_bytes()
    require(grant['processing_contract_path'] == CONTRACT and
            sha(contract_raw) == grant['processing_contract_sha256'], 'PROCESSING_CONTRACT_CHANGED')
    contract = json.loads(contract_raw)
    require(contract['base'] == BASE and contract['tables'] == list(TABLES)
            and contract['views'] == list(VIEWS) and contract['workspace'] == WORKSPACE
            and contract['phases'] == list(PHASES), 'OUTPUT_SCOPE_CHANGED')
    for relative, digest in contract['files_sha256'].items():
        require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,
                'UNSAFE_RUNTIME_FILE')
        require(sha((root / relative).read_bytes()) == digest, 'RUNTIME_CONTENT_CHANGED')
    authority_source = Path(auth.__file__).read_bytes()
    require(sha(host_template(authority_source)) == contract['host_template_sha256'],
            'UNREVIEWED_HOST_CODE')
    gate = snapshot_gate(root, contract)
    auth.validate_packet(root, _verified_gate=gate)
    require(grant['packet_sha256'] == auth.PINS and grant['universe'] == gate.scope_reference(),
            'GRANT_UNIVERSE_OR_PACKET_CHANGED')
    entries = json.loads((root / contract['processing_bindings']).read_bytes())
    reuse = json.loads((root / contract['c300_reuse']).read_bytes())
    require(len(entries) == 450 and bindings == [e['registered_binding'] for e in entries],
            'EXACT_INPUT_SET_REQUIRED')
    frozen = json.loads((root / 'metadata/freezes/C750_v1/C750.bindings.json').read_bytes())
    admitted = json.loads((root / 'metadata/admissions/N450_v1/bindings.json').read_bytes())
    c300_gate_raw = (root / contract['c300_gate']).read_bytes()
    require(sha(c300_gate_raw) ==
            'c80f46c9ccc1be6a48b23b16279d657a056a21bc9fd97828d3120bc5f319d3d1',
            'C300_REUSE_GATE_CHANGED')
    c300_gate = json.loads(c300_gate_raw)
    require({(e['source_instance_id'], e['binding_sha256']) for e in reuse} ==
            {(e['source_instance_id'], e['binding_sha256']) for e in c300_gate['bindings']},
            'C300_REUSE_BINDINGS_CHANGED')
    require(len(reuse) == 732 and len({e['source_instance_id'] for e in reuse}) == 300,
            'C300_REUSE_SCOPE_CHANGED')
    require(len({e['binding_sha256'] for e in reuse}) == 732, 'DUPLICATE_C300_BINDING')
    reuse_ids, new_ids = {e['source_instance_id'] for e in reuse}, set()
    remote = json.loads((root / 'proposals/n450-v1/remote-live.json').read_bytes())['objects']
    remote = {e['source_identity']: e for e in remote}
    for entry, registration in zip(entries, admitted, strict=True):
        b = entry['registered_binding']
        require(entry['source_instance_id'] == registration['source_instance_id']
                and entry['source_identity'] == registration['source_identity']
                and all(b[k] == registration[k] for k in ('source_instance_id', 'raw_path', 'raw_sha256'))
                and entry['binding_sha256'] == canonical_hash(b), 'ADMITTED_BINDING_CHANGED')
        gate.check(entry['source_identity'], b['raw_sha256'], b['raw_path'])
        obj = remote[entry['source_identity']]
        require(entry['remote_raw_path'] == obj['remote'] and entry['expected_raw_bytes'] == obj['bytes']
                and obj['actual_sha256'] == b['raw_sha256'], 'REMOTE_IDENTITY_CHANGED')
        require(b['discovery_validation'] == 'PASS', 'INELIGIBLE_BINDING')
        if b['source_instance_id'] == 'SRC010128':
            from edp_lab.parsers import src010128_v1 as exception
            exception.check_binding(b)
            require(b['decoding_provenance'] == exception.provenance(b), 'DECODING_PROVENANCE_CHANGED')
        else:
            require(b['profile_id'] == 'SEC_EDGAR_DAILY_MASTER_C300_PARSER_V1',
                    'UNAPPROVED_PARSER_PROFILE')
        new_ids.add(b['source_instance_id'])
    require(len(new_ids) == 450 and not new_ids & reuse_ids and
            new_ids | reuse_ids == {e['source_instance_id'] for e in frozen}, 'C750_UNION_CHANGED')
    require(contract['c300_versions'] == json.loads((root /
        'metadata/freezes/O_C300_M1_v1/references.json').read_bytes())['historical_clean_versions'],
        'FROZEN_C300_VERSIONS_CHANGED')
    return {'status': 'AUTHORIZED_PREFLIGHT_ONLY', 'grant': grant, 'contract': contract,
            'entries': entries, 'reuse': reuse, 'owner_grant_sha256': sha(raw)}


class ProcessingAccess:
    """No override path. Only exact reviewed UC Volume objects are readable."""
    def __init__(self, root, bindings):
        self.root = Path(root)
        approved = auth.authorize(self.root, 'remote_processing', bindings, cohort='C750')
        self.pin = approved['owner_grant_sha256']
        self.entries = {e['binding_sha256']: e for e in approved['entries']}

    def validate_entry(self, entry):
        raw = (self.root / auth.OWNER_GRANT_PATH).read_bytes()
        require(self.pin == auth.OWNER_GRANT_SHA256 == sha(raw), 'OWNER_GRANT_CHANGED')
        grant = json.loads(raw)
        require(grant['status'] == 'OWNER_APPROVED' and
                entry['registered_binding'] in grant['scopes'].get('remote_processing', {}).get('bindings', [])
                and self.entries.get(entry['binding_sha256']) == entry,
                'UNREGISTERED_PROCESSING_BINDING')

    def path_for(self, binding):
        entry = self.entries.get(canonical_hash(binding))
        require(entry is not None and entry['registered_binding'] == binding,
                'UNREGISTERED_PROCESSING_BINDING')
        self.validate_entry(entry)
        remote = entry['remote_raw_path']
        require(remote.startswith('dbfs:/Volumes/workspace/edp_lab/raw/n450-raw-v1-4a4585f6b03d/')
                and '..' not in Path(remote).parts, 'UNAPPROVED_REMOTE_PATH')
        path = Path(remote.removeprefix('dbfs:'))
        require(not path.is_symlink() and path.resolve() == path and path.is_file()
                and path.stat().st_size == entry['expected_raw_bytes'], 'REMOTE_RAW_LOCATION_OR_SIZE')
        return path


def exclusive_json(path, value):
    path = output_path(Path(BASE), str(path.relative_to(BASE)))
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'SYMLINK_OUTPUT')
    with path.open('xb') as stream:
        stream.write(encoded(value))


def verified_checkpoint(root, entry, folder, access):
    """Rehash/readback COMPLETE evidence before reuse; incomplete files never count."""
    require(isinstance(access, ProcessingAccess) and root == access.root,
            'TRUSTED_PROCESSING_ACCESS_REQUIRED')
    require(folder == output_path(Path(BASE), 'checkpoints/'+entry['binding_sha256']),
            'CHECKPOINT_DESTINATION_CHANGED')
    access.validate_entry(entry)
    access.path_for(entry['registered_binding'])
    receipt_path = folder / 'complete.json'
    if not receipt_path.exists():
        require(not folder.exists(), 'INCOMPLETE_ATTEMPT_REQUIRES_NEW_VERSION')
        return None
    require(not folder.is_symlink() and not receipt_path.is_symlink(), 'SYMLINK_CHECKPOINT')
    receipt = json.loads(receipt_path.read_bytes())
    require(receipt['binding_sha256'] == entry['binding_sha256']
            and receipt['owner_grant_sha256'] == access.pin and receipt['status'] == 'COMPLETE',
            'CHECKPOINT_SCOPE_CHANGED')
    path = folder / 'records.parquet'
    require(not path.is_symlink() and file_sha256(path) == receipt['parquet_sha256'],
            'CHECKPOINT_BYTES_CHANGED')
    require(verify_parquet(root, entry['registered_binding'], path, access=access) == receipt['verification'],
            'CHECKPOINT_READBACK_CHANGED')
    return receipt


def checkpoint(root, entry, folder, access, run_id):
    import pyarrow as pa
    import pyarrow.parquet as pq

    previous = verified_checkpoint(root, entry, folder, access)
    if previous:
        return previous
    binding = entry['registered_binding']
    # Fresh entire remote object SHA before ANY checkpoint side effect.
    raw_path = access.path_for(binding)
    require(file_sha256(raw_path) == binding['raw_sha256'], 'REMOTE_RAW_HASH_MISMATCH')
    started = time.perf_counter()
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / 'records.parquet'
    batch = []
    with pq.ParquetWriter(path, record_schema(), compression='zstd') as writer:
        for record in validated_occurrences(root, binding, access=access):
            batch.append(package_record(run_id, binding, record))
            if len(batch) == 2048:
                writer.write_table(pa.Table.from_pylist(batch, schema=record_schema()))
                batch.clear()
        if batch:
            writer.write_table(pa.Table.from_pylist(batch, schema=record_schema()))
    verified = verify_parquet(root, binding, path, access=access)
    require(verified['records_data'] == entry['expected_data_records_from_validated_inputs'],
            'DATA_OCCURRENCE_COUNT_CHANGED')
    require(file_sha256(raw_path) == binding['raw_sha256'], 'REMOTE_RAW_CHANGED_AFTER_PARSE')
    receipt = {'status': 'COMPLETE', 'binding_sha256': entry['binding_sha256'],
               'owner_grant_sha256': access.pin, 'parquet_sha256': file_sha256(path),
               'verification': verified, 'seconds': time.perf_counter()-started}
    exclusive_json(folder / 'complete.json', receipt)
    return receipt


def output_path(base, relative):
    require(str(base) == BASE and not base.is_symlink() and base.resolve() == base,
            'OUTPUT_ROOT_CHANGED')
    path = base / relative
    require(not Path(relative).is_absolute() and '..' not in Path(relative).parts
            and path.resolve().is_relative_to(base)
            and not any(p.is_symlink() for p in (path, *path.parents)), 'OUTPUT_PATH_ESCAPE')
    return path
