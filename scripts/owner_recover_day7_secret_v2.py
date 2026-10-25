"""One-use recovery from precisely verified Day 7 OAuth Duration parse failure.

Run only as root on the Mac after reviewing this file. Never rerun this file:
its v2 attempt marker deliberately prevents a second OAuth Secret create.

Loads but does not edit the existing git-pinned Day 7 implementation. It
preserves the existing Service Principal, installed policy, trusted source
index, old journal, and both prior create-attempt intent records.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/Users/lightnino/Projects/edp-lab-day7-universe')
sys.path.insert(0, str(ROOT / 'scripts'))
import owner_recover_day7_secret_v1 as previous

install = previous.install
OLD = previous.OLD_COMMIT
PRIOR_REPAIR_COMMIT = '2e40a26d0045407896382f1b3deffeac8469ccb1'
SP_ID = previous.SP_ID
PREVIOUS_ATTEMPT = previous.RECOVERY_INTENT
SUCCESSOR_ATTEMPT = install.BASE / 'ledger/day7-secret-duration-v2-attempt.json'


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(reason)


def trusted_file(path: Path, mode: int | None = None) -> None:
    require(path.is_file() and not path.is_symlink() and path.stat().st_uid == 0
            and not path.stat().st_mode & 0o022,
            'DAY7_ROOT_PROTECTED_FILE_CHANGED:' + path.name)
    if mode is not None:
        require(stat.S_IMODE(path.stat().st_mode) == mode,
                'DAY7_ROOT_PROTECTED_MODE_CHANGED:' + path.name)


def verify_old_partial_state(expected_commit: str) -> tuple[dict, dict]:
    require(os.geteuid() == 0, 'DAY7_ROOT_REQUIRED')
    require(len(expected_commit) == 40 and all(c in '0123456789abcdef' for c in expected_commit)
            and previous.git('rev-parse', 'HEAD') == expected_commit,
            'DAY7_GIT_HEAD_MUST_REMAIN_PINNED')
    require(not previous.git('status', '--porcelain'),
            'DAY7_WORKTREE_MUST_BE_CLEAN')
    changes = set(previous.git('diff', '--name-only', OLD, expected_commit).splitlines())
    permitted = previous.ALLOWED_CHANGES | {
        'scripts/owner_recover_day7_secret_v2.py',
        'tests/operating/test_day7_secret_v2.py',
    }
    require(changes <= permitted and
            {'scripts/owner_recover_day7_secret_v1.py',
             'scripts/owner_recover_day7_secret_v2.py',
             'tests/operating/test_day7_secret_v2.py'} <= changes,
            'DAY7_GIT_DIFF_UNEXPECTED')
    require(install.BASE.is_dir() and not install.BASE.is_symlink() and
            install.BASE.stat().st_uid == 0 and
            stat.S_IMODE(install.BASE.stat().st_mode) in (0o700, 0o710),
            'DAY7_PARTIAL_ROOT_BASE_CHANGED')
    for path, mode in [(install.JOURNAL, 0o600),
                       (previous.IDENTITY, 0o600),
                       (previous.ORIGINAL_INTENT, 0o600),
                       (PREVIOUS_ATTEMPT, 0o600)]:
        trusted_file(path, mode)
    trusted_file(previous.REVOKED)
    require(not SUCCESSOR_ATTEMPT.exists() and not SUCCESSOR_ATTEMPT.is_symlink(),
            'DAY7_SECOND_ATTEMPT_ALREADY_RECORDED_NEVER_RETRY')
    require(not previous.CONFIG.exists() and not previous.CONFIG.is_symlink() and
            not previous.CONFIG_TEMP.exists() and not previous.CONFIG_TEMP.is_symlink(),
            'DAY7_SECRET_CONFIG_ALREADY_EXISTS')
    require(not install.PLIST.exists() and
            not (install.BASE / 'receipts/day7-deployment.json').exists() and
            not (install.BASE / 'ledger/canary-submit-intent.json').exists(),
            'DAY7_INSTALL_ADVANCED_UNEXPECTEDLY')
    require(not any((install.BASE / 'grants').iterdir()),
            'DAY7_PROTECTED_GRANTS_ALREADY_PRESENT')
    journal = install._read_json(install.JOURNAL)
    require({k: v for k, v in journal.items() if k != 'completed'}
            == install._install_intent(OLD),
            'DAY7_OLD_JOURNAL_COMMIT_OR_POLICY_CHANGED')
    completed = journal.get('completed')
    require(isinstance(completed, dict) and 'protected_files' in completed
            and set(completed) <= previous.ALLOWED_COMPLETED,
            'DAY7_UNEXPECTED_COMPLETED_PHASES')
    identity = install._read_json(previous.IDENTITY)
    require(str(identity.get('service_principal_id')) == SP_ID and
            isinstance(identity.get('application_id'), str) and
            bool(identity['application_id']), 'DAY7_OLD_IDENTITY_CHANGED')
    require(install._read_json(previous.ORIGINAL_INTENT) == identity,
            'DAY7_ORIGINAL_SECRET_INTENT_CHANGED')
    old_attempt = install._read_json(PREVIOUS_ATTEMPT)
    require(old_attempt == {
        'schema': 'EDP_DAY7_SECRET_RECOVERY_ATTEMPT_V1',
        'old_install_commit': OLD,
        'repair_commit': PRIOR_REPAIR_COMMIT,
        'service_principal_id': SP_ID,
        'application_id': identity['application_id'],
        'prior_request_independently_found_zero_secrets': True,
    }, 'DAY7_PREVIOUS_ATTEMPT_RECORD_CHANGED')
    require(install.file_digest(install.POLICY) == install.POLICY_SHA and
            install.file_digest(install.SOURCE_INDEX) == install.SOURCE_INDEX_SHA and
            install.file_digest(ROOT / 'metadata/source_universes/approved/manifest.json')
            == install.MANIFEST_SHA, 'DAY7_PINNED_INPUT_CHANGED')

    sys.path.insert(0, str(ROOT / 'src'))
    from edp_lab.operating.authority import verified_document
    signed = verified_document(ROOT, install.BASE / 'trust/policy.signed.json',
                               install.BASE / 'trust')
    require(signed == install._read_json(install.POLICY) and
            install.file_digest(install.BASE / 'source_evidence_index.json')
            == install.SOURCE_INDEX_SHA,
            'DAY7_SIGNED_POLICY_OR_INDEX_CHANGED')
    broker_path = 'src/edp_lab/operating/policy_broker.py'
    old_broker = subprocess.run(
        ['/usr/bin/git', '-c', f'safe.directory={ROOT}', '-C', str(ROOT),
         'show', OLD + ':' + broker_path],
        capture_output=True, check=True, timeout=30).stdout
    require((install.BASE / 'runtime' / broker_path).read_bytes() == old_broker,
            'DAY7_PROTECTED_BROKER_CHANGED')
    require(previous.REVOKED.read_bytes() in (b'[]\\n', b'[]\n'),
            'DAY7_REVOKED_GRANTS_UNEXPECTED')
    principal = install.admin('service-principals', 'get', SP_ID)
    require(str(principal.get('id')) == SP_ID and
            principal.get('displayName') == install.SP_NAME and
            principal.get('applicationId') == identity['application_id'] and
            principal.get('active', True) is True,
            'DAY7_REMOTE_SERVICE_PRINCIPAL_CHANGED')
    matches = install._find_exact_service_principals()
    require(len(matches) == 1 and str(matches[0].get('id')) == SP_ID,
            'DAY7_DUPLICATE_OR_MISSING_PRINCIPAL')
    assignment = install.admin('api', 'get',
                               '/api/2.0/identity/workspace-assignments/' + SP_ID)
    effective = set(assignment.get('effective_entitlements', []))
    require(str(assignment.get('principal_id')) == SP_ID and
            assignment.get('principal_type') == 'SERVICE_PRINCIPAL' and
            {'WORKSPACE_ACCESS', 'DATABRICKS_SQL_ACCESS'} <= effective and
            'WORKSPACE_ADMIN' not in effective,
            'DAY7_WORKSPACE_ASSIGNMENT_CHANGED')
    require(len(previous._secret_metadata()) == 0,
            'DAY7_SECRET_EXISTS_STOP_NO_CREATE')
    install.verify_canary_raw_read_only()
    return journal, identity


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('expected_commit')
    args = parser.parse_args()
    journal, identity = verify_old_partial_state(args.expected_commit)

    # This marker is exclusive and durable. A second run, even after an
    # uncertain failure, cannot submit another Secret creation request.
    install._save_json(SUCCESSOR_ATTEMPT, {
        'schema': 'EDP_DAY7_DURATION_V2_ATTEMPT_V1',
        'old_install_commit': OLD, 'recovery_commit': args.expected_commit,
        'service_principal_id': SP_ID,
        'application_id': identity['application_id'],
        'previous_failure': 'DATABRICKS_DURATION_PARSE_ERROR',
        'previous_create_request_has_zero_remote_secrets': True,
        'request_lifetime': '7776000s',
    })
    request = json.dumps({'lifetime': '7776000s'}, separators=(',', ':'))
    command = ['/usr/bin/sudo', '-n', '-u', 'lightnino', '-H',
               install.CLI, 'service-principal-secrets-proxy', 'create', SP_ID,
               '--json', request, '-p', 'edp-lab', '-o', 'json']
    # stdout contains a SECRET: never print or log it; no retries.
    result = subprocess.run(command, capture_output=True, text=True,
                            check=False, timeout=120)
    if result.returncode:
        try:
            count = len(previous._secret_metadata())
        except (OSError, ValueError, subprocess.CalledProcessError):
            count = 'UNKNOWN'
        raise RuntimeError('DAY7_DURATION_V2_SECRET_CREATE_BLOCKED:'
                           + previous._safe_error(result.stderr)
                           + f':remote_secret_count={count}:NO_AUTOMATIC_RETRY')
    try:
        reply = json.loads(result.stdout)
    except (ValueError, TypeError) as exc:
        raise RuntimeError('DAY7_SECRET_RESPONSE_UNCERTAIN_NO_RETRY') from exc
    previous._store_oauth_profile(identity, reply)

    # Secret activation propagation can lag; read-only auth retries only.
    authenticated = False
    for attempt in range(12):
        try:
            current = install.service('current-user', 'me')
        except (OSError, ValueError, subprocess.CalledProcessError):
            if attempt == 11:
                break
            time.sleep(5)
            continue
        require(str(current.get('id')) == SP_ID,
                'DAY7_M2M_IDENTITY_MISMATCH')
        authenticated = True
        break
    require(authenticated, 'DAY7_M2M_AUTH_NOT_VERIFIED_NO_SECRET_RETRY')
    require(len(previous._secret_metadata()) == 1,
            'DAY7_SECRET_METADATA_READBACK_CHANGED')

    # The old installer wrote the two literal characters backslash+n, not
    # a real newline. Repair only this root-owned trust list, atomically.
    if previous.REVOKED.read_bytes() == b'[]\\n':
        temp = previous.REVOKED.with_name('revoked_grants.json.duration-v2-tmp')
        require(not temp.exists(), 'DAY7_REVOCATION_REPAIR_ALREADY_STARTED')
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(b'[]\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, previous.REVOKED)

    # Only after authenticated M2M and exact external readback do we advance
    # the old Owner journal to the already CI-validated checkout.
    journal['reviewed_commit'] = args.expected_commit
    journal['completed']['secret_duration_v2_recovery'] = {
        'from_commit': OLD, 'service_principal_id': SP_ID,
        'm2m_verified': True,
    }
    install._save_json(install.JOURNAL, journal)
    sys.argv = [str(ROOT / 'scripts/owner_install_day7.py'),
                args.expected_commit]
    # Continue the old resumable Owner installation, with no new SP create.
    install.main()


if __name__ == '__main__':
    main()
