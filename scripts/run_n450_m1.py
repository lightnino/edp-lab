"""Guarded fixed-scope deploy/submit controller. No RAW upload or generic CLI proxy."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from edp_lab.ingestion import n450_authorization as auth
from edp_lab.ingestion.universe import sha
from edp_lab.materialization.n450_runtime import BASE, CONTRACT, PHASES, WORKSPACE, require

# Exact failed deployment eligible for the authorized exact-path correction only.
PREVIOUS_DEPLOYMENT = {
    'runtime.zip': '5b073834c0950ec09212c9fab52b1c754953e3cc8345ebf2cfb221750e481ac0',
    'contract.json': '3b0e59c79f2eafb3ba78be5c3ece96b4c18e4177361c84d1f875fa5bf2b6b037',
    'owner-record.approved.json': '3fd9c5a6ccb62ffd79610a84dc8ac8cb78f674581a2edcfbd23d18da50e91654',
    'n450_authorization.host.py': '8a8123b24b3c8bc30983af76b9ad519e2f4fe9dd345719fb645192f69a9eb9b1',
}


def validate_submission(phase, submission):
    expected = {'run_name': 'n450-m1-step3-'+phase, 'timeout_seconds': 28800 if phase == 'query' else 3600,
        'idempotency_token': 'n450-m1-step3-v1-'+phase+('-exact-path-v1' if phase == 'smoke' else '-clean-write-fix-v1' if phase == 'publish' else ''),
        'tasks': [{'task_key': phase, 'timeout_seconds': 28800 if phase == 'query' else 3600, 'max_retries': 0,
            'notebook_task': {'notebook_path': WORKSPACE+'/runtime', 'source': 'WORKSPACE',
                              'base_parameters': {'phase': phase}}}]}
    require(phase in PHASES and submission == expected, 'UNAUTHORIZED_JOB_SUBMISSION')


def prepare_authority(root, prepared):
    raw = (root / auth.OWNER_GRANT_PATH).read_bytes()
    require(auth.OWNER_GRANT_SHA256 is not None and sha(raw) == auth.OWNER_GRANT_SHA256
            and json.loads(raw)['status'] == 'OWNER_APPROVED', 'OWNER_GRANT_PIN_MISMATCH')
    payload = prepared / 'payload'
    require(not payload.is_symlink() and payload.resolve() == payload, 'UNSAFE_PREPARED_PAYLOAD')
    contract_raw = (prepared / 'contract.json').read_bytes()
    grant = json.loads(raw)
    require(grant.get('processing_contract_sha256') == sha(contract_raw), 'PROCESSING_NOT_AUTHORIZED')
    target = payload / auth.OWNER_GRANT_PATH
    require(not Path(auth.OWNER_GRANT_PATH).is_absolute() and '..' not in target.relative_to(payload).parts,
            'UNSAFE_AUTHORITY_PATH')
    require(not any(p.is_symlink() for p in (target, *target.parents)), 'UNSAFE_AUTHORITY_PATH')
    if target.exists():
        require(target.read_bytes() == raw, 'PREPARED_AUTHORITY_CHANGED')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)  # copy installed owner bytes only; never manufacture approval
    contract = json.loads(contract_raw)
    entries = json.loads((payload / contract['processing_bindings']).read_bytes())
    approved = auth.authorize(payload, 'processing', [e['registered_binding'] for e in entries], cohort='C750')
    require(sha((prepared / 'runtime.zip').read_bytes()) == contract['runtime_sha256'] and
            sha((prepared / 'notebook.py').read_bytes()) == contract['notebook_sha256'],
            'DEPLOYMENT_BYTES_CHANGED')
    return approved, raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prepared', type=Path)
    parser.add_argument('action', choices=['deploy', *PHASES])
    args = parser.parse_args()
    root, prepared = Path(__file__).resolve().parents[1], args.prepared.resolve()
    approved, record = prepare_authority(root, prepared)
    contract = approved['contract']

    def cli(*arguments):
        result = subprocess.run(['databricks', *arguments, '-p', 'edp-lab'], capture_output=True, check=False)
        if result.returncode:
            raise RuntimeError(result.stderr.decode())
        return result.stdout

    if args.action == 'deploy':
        # The operation allowlist is code, not caller-provided CLI arguments.
        host_file = prepared / 'n450_authorization.host.py'
        raw = Path(auth.__file__).read_bytes()
        if host_file.exists():
            require(host_file.read_bytes() == raw, 'HOST_DEPLOYMENT_CHANGED')
        else:
            host_file.write_bytes(raw)
        owner_file = prepared / 'owner-record.installed.json'
        if owner_file.exists():
            require(owner_file.read_bytes() == record, 'OWNER_DEPLOYMENT_CHANGED')
        else:
            owner_file.write_bytes(record)
        sources = {'runtime.zip': prepared/'runtime.zip', 'contract.json': prepared/'contract.json',
                   'owner-record.approved.json': owner_file, 'n450_authorization.host.py': host_file}
        require(set(sources) == set(contract['permissions']['deployment']), 'DEPLOYMENT_SCOPE_CHANGED')
        # Listing errors are not interpreted as absence: auth/transport failures STOP.
        parent = 'dbfs:' + str(Path(BASE).parent)
        cli('fs', 'mkdir', parent)
        listing = json.loads(cli('fs', 'ls', parent, '-o', 'json'))
        exists = any(e['name'].rstrip('/') == Path(BASE).name for e in listing)
        if not exists:
            cli('fs', 'mkdir', 'dbfs:' + BASE)
        listing = json.loads(cli('fs', 'ls', 'dbfs:'+BASE, '-o', 'json'))
        names = {e['name'] for e in listing}
        for name, source in sources.items():
            target = 'dbfs:' + BASE + '/' + name
            if name in names:
                current = sha(cli('fs', 'cat', target))
                if current != sha(source.read_bytes()):
                    require(current == PREVIOUS_DEPLOYMENT[name], 'EXISTING_DEPLOYMENT_HASH_MISMATCH')
                    cli('fs', 'cp', str(source), target, '--overwrite')
                    require(sha(cli('fs', 'cat', target)) == sha(source.read_bytes()),
                            'DEPLOYMENT_READBACK_MISMATCH')
            else:
                cli('fs', 'cp', str(source), target)  # no --overwrite
        # Notebook bytes are unchanged by the inventory correction.
        cli('workspace', 'mkdirs', WORKSPACE)
        listing = json.loads(cli('workspace', 'list', WORKSPACE, '-o', 'json'))
        deployed = any(item['path'] == WORKSPACE+'/runtime' for item in listing)
        if deployed:
            exported = json.loads(cli('workspace', 'export', WORKSPACE+'/runtime', '-o', 'json'))
            import base64
            require(sha(base64.b64decode(exported['content'])) == contract['notebook_sha256'],
                    'EXISTING_NOTEBOOK_CHANGED')
        else:
            cli('workspace', 'mkdirs', WORKSPACE)
            cli('workspace', 'import', WORKSPACE+'/runtime', '--file', str(prepared/'notebook.py'),
                '--format', 'SOURCE', '--language', 'PYTHON')
    else:
        payload = prepared / 'payload'
        relative = str(Path(CONTRACT).parent / ('submit-'+args.action+'.json'))
        raw = (payload / relative).read_bytes()
        require(sha(raw) == contract['files_sha256'][relative], 'SUBMISSION_BYTES_CHANGED')
        validate_submission(args.action, json.loads(raw))
        # Revalidate the deployed code/record immediately before every job; no
        # reliance on an earlier deployment receipt or writable workspace path.
        expected_remote = {'runtime.zip': contract['runtime_sha256'],
            'contract.json': sha((prepared/'contract.json').read_bytes()),
            'owner-record.approved.json': sha(record),
            'n450_authorization.host.py': sha(Path(auth.__file__).read_bytes())}
        for name, digest in expected_remote.items():
            require(sha(cli('fs', 'cat', 'dbfs:'+BASE+'/'+name)) == digest,
                    'DEPLOYED_RUNTIME_CHANGED')
        import base64
        exported = json.loads(cli('workspace', 'export', WORKSPACE+'/runtime', '-o', 'json'))
        require(sha(base64.b64decode(exported['content'])) == contract['notebook_sha256'],
                'DEPLOYED_NOTEBOOK_CHANGED')
        # API idempotency_token is fixed per approved phase. A repeated submit must
        # resolve to the same job run rather than silently scheduling a replay.
        response = cli('jobs', 'submit', '--json', '@'+str(payload / relative), '--no-wait', '-o', 'json')
        receipt = prepared / ('submitted-'+args.action+'.json')
        if receipt.exists():
            require(json.loads(receipt.read_bytes()) == json.loads(response), 'SUBMISSION_IDEMPOTENCY_CHANGED')
        else:
            with receipt.open('xb') as stream:
                stream.write(response)
        sys.stdout.buffer.write(response)


if __name__ == '__main__':
    main()
