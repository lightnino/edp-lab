#!/bin/zsh
# Owner-terminal installation for the one stopped Day 5 SQL roster operation.
set -euo pipefail

repo=/Users/lightnino/Projects/edp-lab-day5-e2e
base=/private/var/db/edp-lab
queue=$repo/runs/day5/c2000_live_queue_v1.json
state=$base/state/day5/checkpoint.json
original=$base/ledger/day5-c2000-roster-v1.json
evidence=$base/state/day5/p11_sql_recovery_inspection
trust=$base/trust
python=$base/python/bin/python3.12
cli=/opt/homebrew/bin/databricks

test "$(id -u)" = 0
test "$(shasum -a 256 "$queue" | awk '{print $1}')" = e43cf9984e1c54b17cbdc44917954bf802acba3241168ea353b302ec41076e34
test "$(shasum -a 256 "$state" | awk '{print $1}')" = f652eb11e56e4d03e1e6fdb6a454bd21d8ada1ca0e44e29c98a53f2de6179cda
test -f "$original" -a -f "$base/private/owner.pem"
test -f "$base/private/verifier.pem" -a -f "$base/private/databrickscfg"
test ! -e "$base/ledger/day5-c2000-roster-v1-recovery-v1.json"
test ! -e "$base/receipts/recovery-sql-roster.json"
test ! -e "$base/receipts/sql-roster.json"
if launchctl print system/org.edp-lab.day5-supervisor | grep -q 'state = running'; then
  print -u2 'Supervisor must be stopped.'
  exit 1
fi

typeset -A expected
expected=(
  boundaries 6da9934fb9203eeac69628216d1c1db8d1536f9e2f442ba104b3b751746a4d0d
  runner 1659439c7aff4341a62aa9f17dd4d9a36236cbae044dd1e68677f9826fd7b7fb
  protected_verifier 62f720ca2463f963c2fe02d4c3aa68db08d18dc2549c80f444147abbabb81e0b
  protected_recovery 4301bfc258b57f6778039545a511320f3521a554b1a079376638680a4f3be366
)
for name in boundaries runner protected_verifier protected_recovery; do
  test "$(shasum -a 256 "$repo/src/edp_lab/operating/$name.py" | awk '{print $1}')" = "$expected[$name]"
done
"$repo/.venv/bin/python" -m pytest -q \
  "$repo/tests/operating/test_day5_sql_protected_recovery.py" \
  "$repo/tests/operating/test_day5_sql_submission_recovery.py"

install -d -m 700 -o root -g wheel "$evidence"
test "$(stat -f '%Su:%Lp' "$evidence")" = root:700
capture="$(mktemp -d "$evidence/capture.XXXXXX")"
chmod 700 "$capture"
cp -p "$state" "$capture/checkpoint_before.json"
export HOME=$base/private/home
export DATABRICKS_CONFIG_FILE=$base/private/databrickscfg
export DATABRICKS_AUTH_STORAGE=plaintext
export EDP_P11_REPO=$repo EDP_P11_BASE=$base EDP_P11_CAPTURE=$capture

# Save unedited CLI stdout/stderr and exit codes, then derive the four verifier inputs.
"$python" - <<'PY'
import hashlib, json, os, subprocess
from pathlib import Path

capture = Path(os.environ['EDP_P11_CAPTURE'])
cli = '/opt/homebrew/bin/databricks'
def call(name, *args, command=('api', 'get')):
    result = subprocess.run([cli, *command, *args], capture_output=True)
    (capture / (name + '.stdout')).write_bytes(result.stdout)
    (capture / (name + '.stderr')).write_bytes(result.stderr)
    (capture / (name + '.exit_code')).write_text(str(result.returncode) + '\n')
    return result

default = call('default_auth', command=('current-user', 'me'))
auth_errors = (b'error getting token', b'cannot configure default credentials',
               b'authentication', b'not authenticated', b'no cached credentials',
               b'default auth', b'profile not found')
if default.returncode != 1 or not any(
        marker in default.stderr.lower() for marker in auth_errors):
    raise SystemExit('Default profile did not fail authentication')
explicit = call('explicit_profile_auth', '-p', 'edp-lab', '-o', 'json',
                command=('current-user', 'me'))
if explicit.returncode != 0:
    raise SystemExit('Explicit profile authentication failed')
identity = json.loads(explicit.stdout)
user = identity.get('userName', identity.get('user_name'))
if user != 'chengzhu13@gmail.com':
    raise SystemExit('Unexpected authenticated identity')
history_path = ('/api/2.0/sql/history/queries?'
                'filter_by.query_start_time_range.start_time_ms=1792791300000&'
                'filter_by.query_start_time_range.end_time_ms=1792792200000&max_results=100')
history_call = call('query_history', history_path, '-p', 'edp-lab', '-o', 'json')
if history_call.returncode != 0:
    raise SystemExit('Authenticated Query History failed')
history = json.loads(history_call.stdout)
if history.get('has_next_page') is not False or any(history.get(k) for k in ('res', 'queries', 'results')):
    raise SystemExit('Query History is nonempty or incompletely paginated')
history['query_start_time_range'] = {'start_time_ms': 1792791300000,
                                      'end_time_ms': 1792792200000}
target = 'workspace.edp_lab.n500_input_roster_day5_v1'
uc = call('uc_target', '/api/2.1/unity-catalog/tables/' + target,
          '-p', 'edp-lab', '-o', 'json')
def uc_absence(result, table):
    """Recognize only a target-bound server not-found response after auth."""
    if result.returncode != 1:
        return False
    if result.stdout.strip() and result.stderr.strip():
        return False
    response = (result.stderr or result.stdout).decode('utf-8', errors='replace').strip()
    message = f"Table '{table}' does not exist."
    if response == 'Error: ' + message:
        return True  # Databricks CLI v1.21.0 renders this API error as text.
    try:
        body = json.loads(response.removeprefix('Error: '))
    except ValueError:
        return False
    return (isinstance(body, dict)
            and body.get('error_code') == 'TABLE_DOES_NOT_EXIST'
            and body.get('message') == message)

if not uc_absence(uc, target):
    raise SystemExit('Exact UC target absence was not established by authenticated CLI response')
artifacts = {
    'default_auth_test.json': {'exit_code': default.returncode},
    'explicit_profile_auth_test.json': {'exit_code': explicit.returncode,
                                        'authenticated_user': user},
    'protected_query_history_2135_2150_utc.json': history,
    'uc_target_test.json': {'exit_code': uc.returncode,
                            'error_code': 'TABLE_DOES_NOT_EXIST', 'table': target,
                            'stdout_sha256': hashlib.sha256(uc.stdout).hexdigest(),
                            'stderr_sha256': hashlib.sha256(uc.stderr).hexdigest()},
}
for name, value in artifacts.items():
    (capture / name).write_text(json.dumps(value, sort_keys=True,
                                         separators=(',', ':')) + '\n')
print('Authenticated evidence captured under', capture)
print('Default auth exit:', default.returncode)
print('Explicit profile identity:', user)
print('Query History complete zero page:', history['has_next_page'] is False)
print('Exact UC target authenticated not found:', target)
for name in artifacts:
    path = capture / name
    print(name, hashlib.sha256(path.read_bytes()).hexdigest())
PY

"$python" - <<'PY'
import hashlib, json, os
from pathlib import Path
base = Path(os.environ['EDP_P11_BASE'])
repo = Path(os.environ['EDP_P11_REPO'])
capture = Path(os.environ['EDP_P11_CAPTURE'])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
state = json.loads((base / 'state/day5/checkpoint.json').read_bytes())
ledger = json.loads((base / 'ledger/day5-c2000-roster-v1.json').read_bytes())
task = state['tasks']['sql-roster']
assert ledger == task['external']
assert task['status'] == 'VALIDATING'
assert sum(t['status'] == 'COMPLETE' for t in state['tasks'].values()) == 502
assert sum(t['status'] == 'PLANNED' for t in state['tasks'].values()) == 10
names = {'default_auth': 'default_auth_test.json',
         'explicit_profile': 'explicit_profile_auth_test.json',
         'query_history': 'protected_query_history_2135_2150_utc.json',
         'uc_target': 'uc_target_test.json'}
doc = {'schema': 'EDP_SQL_PRE_SUBMISSION_DISPOSITION_V1',
       'authority': 'owner-v1',
       'decision': 'AUTHORIZE_DISTINCT_TECHNICAL_RECOVERY',
       'task_id': 'sql-roster',
       'queue_sha256': sha(repo / 'runs/day5/c2000_live_queue_v1.json'),
       'checkpoint_sha256': sha(base / 'state/day5/checkpoint.json'),
       'original_operation_id': 'day5-c2000-roster-v1',
       'original_ledger_sha256': sha(base / 'ledger/day5-c2000-roster-v1.json'),
       'recovery_operation_id': 'day5-c2000-roster-v1-recovery-v1',
       'target_table': 'workspace.edp_lab.n500_input_roster_day5_v1',
       'original_statement_id': None,
       'query_history_result': 'ZERO_COMPLETE_PAGE',
       'query_history_window_start_ms': 1792791300000,
       'query_history_window_end_ms': 1792792200000,
       'uc_target_result': 'AUTHENTICATED_NOT_FOUND',
       'default_auth_result': 'FAILED',
       'explicit_profile_result': 'AUTHENTICATED_EXPECTED_USER',
       'evidence_sha256': {key: sha(capture / name) for key, name in names.items()}}
(capture / 'owner_disposition_payload.json').write_text(
    json.dumps(doc, sort_keys=True, separators=(',', ':')) + '\n')
PY

shasum -a 256 "$original" "$state" "$queue" "$capture"/* > "$capture/preflight_hashes.txt"
cat "$capture/owner_disposition_payload.json"
print 'Review the captured raw responses, disposition and bounded residual uncertainty.'
print -n 'Type SIGN to authorize this exact technical recovery: '
read -r answer
test "$answer" = SIGN

openssl pkeyutl -sign -inkey "$base/private/owner.pem" -rawin \
  -in "$capture/owner_disposition_payload.json" \
  -out "$capture/owner_disposition.sig"
"$python" - <<'PY'
import base64, json, os
from pathlib import Path
capture = Path(os.environ['EDP_P11_CAPTURE'])
doc = json.loads((capture / 'owner_disposition_payload.json').read_bytes())
sig = base64.b64encode((capture / 'owner_disposition.sig').read_bytes()).decode()
(capture / 'owner_disposition.json').write_text(json.dumps(
    {'document': doc, 'signature_base64': sig}, sort_keys=True,
    separators=(',', ':')) + '\n')
PY

# Retain any older inspection files in place under a prior/ directory.
install -d -m 700 -o root -g wheel "$evidence/prior"
for name in default_auth_test.json explicit_profile_auth_test.json \
  protected_query_history_2135_2150_utc.json uc_target_test.json \
  uc_target.stdout uc_target.stderr uc_target.exit_code \
  owner_disposition_payload.json owner_disposition.sig owner_disposition.json; do
  if test -e "$evidence/$name"; then
    cp -p "$evidence/$name" "$evidence/prior/$name.${capture:t}"
  fi
  install -m 600 -o root -g wheel "$capture/$name" "$evidence/$name"
done

install -d -m 700 -o root -g wheel "$evidence/installed_before"
for name in boundaries runner protected_verifier protected_recovery; do
  cp -p "$base/runtime/src/edp_lab/operating/$name.py" "$evidence/installed_before/$name.py"
  install -m 644 -o root -g wheel "$repo/src/edp_lab/operating/$name.py" \
    "$base/runtime/src/edp_lab/operating/$name.py"
  cmp "$repo/src/edp_lab/operating/$name.py" "$base/runtime/src/edp_lab/operating/$name.py"
  test "$(shasum -a 256 "$base/runtime/src/edp_lab/operating/$name.py" | awk '{print $1}')" = "$expected[$name]"
done
test "$(shasum -a 256 "$state" | awk '{print $1}')" = f652eb11e56e4d03e1e6fdb6a454bd21d8ada1ca0e44e29c98a53f2de6179cda
launchctl bootout system/org.edp-lab.policy-broker
launchctl bootstrap system /Library/LaunchDaemons/org.edp-lab.policy-broker.plist

grant_id="$("$python" -c 'import json,sys;print(json.load(open(sys.argv[1]))["grant_id"])' "$state")"
grant=$base/grants/$grant_id.json
test -f "$grant"
PYTHONPATH="$base/runtime/src" "$python" -m edp_lab.operating.protected_recovery \
  "$repo" "$queue" "$grant" "$state" "$trust" \
  "$base/private/verifier.pem" "$evidence/owner_disposition.json"

PYTHONPATH="$base/runtime/src" "$python" - <<'PY'
import hashlib, json, os
from pathlib import Path
from edp_lab.operating.protected_recovery import verify_sql_recovery
base = Path(os.environ['EDP_P11_BASE'])
repo = Path(os.environ['EDP_P11_REPO'])
capture = Path(os.environ['EDP_P11_CAPTURE'])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = json.loads((capture / 'checkpoint_before.json').read_bytes())
state = json.loads((base / 'state/day5/checkpoint.json').read_bytes())
task = state['tasks']['sql-roster']
assert task['status'] == 'PLANNED'
assert task['technical_recovery']['operation_id'] == 'day5-c2000-roster-v1-recovery-v1'
assert task['original_external']['status'] == 'UNCERTAIN_REQUIRES_READBACK'
assert sum(t['status'] == 'COMPLETE' for t in state['tasks'].values()) == 502
assert sum(t['status'] == 'PLANNED' for t in state['tasks'].values()) == 11
assert {k: v for k, v in state['tasks'].items() if k != 'sql-roster'} == {
    k: v for k, v in before['tasks'].items() if k != 'sql-roster'}
assert state['queue_sha256'] == before['queue_sha256']
assert not (base / 'ledger/day5-c2000-roster-v1-recovery-v1.json').exists()
assert (base / 'receipts/recovery-sql-roster.json').exists()
original = base / 'ledger/day5-c2000-roster-v1.json'
assert sha(original) == json.loads((capture / 'owner_disposition_payload.json').read_bytes())['original_ledger_sha256']
queue_path = repo / 'runs/day5/c2000_live_queue_v1.json'
queue = json.loads(queue_path.read_bytes())
sql_task, = (item for item in queue['tasks'] if item['id'] == 'sql-roster')
verify_sql_recovery(repo, queue_path, base / 'state/day5/checkpoint.json',
                    sql_task, task['technical_recovery'], base / 'trust')
print('VERIFIED_POST_INSTALL_502_COMPLETE_11_PLANNED')
PY

launchctl kickstart -k system/org.edp-lab.day5-supervisor
print 'Supervisor restarted from the existing checkpoint. Preserve this terminal output.'
