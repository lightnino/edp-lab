# Day 5 C2000 SQL recovery packet (2026-10-24 SGT)

**Historical incident-time disposition:** `PAUSED_WITH_DECISION_PACKET`. **ARCHIVED — DO NOT RE-EXECUTE OWNER RECOVERY COMMANDS.** This packet records the then-stopped run; it is not a current SQL retry, an active P13 freeze task, or a new P14 authorization. **Current outcome:** original uncertainty preserved, separate owner-authorized recovery verified, 513/513 COMPLETE, signed P13 and owner-approved P14 merged via [PR #64](https://github.com/lightnino/edp-lab/pull/64). See the [canonical incident status](incident.md). The original signed Queue was
SHA-256 `e43cf9984e1c54b17cbdc44917954bf802acba3241168ea353b302ec41076e34`.
PR #62's later workflow amendment is prospective and does not change that signed Queue.

## Protected checkpoint at incident-time inspection (historical)

- `/private/var/db/edp-lab/state/day5/checkpoint.json`: SHA-256
  `f652eb11e56e4d03e1e6fdb6a454bd21d8ada1ca0e44e29c98a53f2de6179cda`
  at inspection; 502 of 513 tasks `COMPLETE`, ten `PLANNED`, `sql-roster`
  `VALIDATING`. `P6` is `COMPLETE`. The checkpoint reports 503 operations,
  zero retries and 6,863 cumulative runtime seconds.
- `sql-roster` external state is `UNCERTAIN_REQUIRES_READBACK`, return code 1,
  no Statement ID or remote state, submitted at
  `2026-10-23T21:42:29.403568+00:00`. The stdout hash is SHA-256 of empty
  bytes; stderr hash is
  `ba416ff94762e46c9cdfc34fe26a40ea54e89cf6dced5a9e44a77d2fe3bcfaa5`.
- Protected event history ends with `WAITING_EXTERNAL_READBACK` for
  `sql-roster` at `2026-10-23T21:42:29.434601+00:00`.
- The root-owned Supervisor is stopped with exit code 1. Its log records
  `SQL_STATEMENT_ID_MISSING`. No `sql-roster` signed receipt exists.
- The root-only operation ledger is
  `/private/var/db/edp-lab/ledger/day5-c2000-roster-v1.json`. The owner
  supplied its `UNCERTAIN_REQUIRES_READBACK` fields. The agent could not
  independently open it: `sudo -n` requires the owner's credential.

## Diagnosis and bounded correction

The installed protected runtime files matched the worktree at the original
commit before correction. Its SQL adapter invokes the CLI without `-p
edp-lab`; the protected LaunchDaemon supplies a root-owned config but no
default CLI profile. The owner previously reproduced failure without a
profile and successful authentication with `-p edp-lab`. This is a strong
cause hypothesis until the exact protected environment and original ledger
are independently checked. The missing Statement ID follows from the failed
CLI result, and the verifier correctly refused to issue a receipt.

Read-only Unity Catalog inspection returned “Table ... does not exist” for
`workspace.edp_lab.n500_input_roster_day5_v1`. The owner supplied a
paginated, complete zero-candidate Query History inspection for the original
21:35–21:50 UTC window. These observations support pre-submission failure;
they do not prove remote absence with sufficient certainty for a replay.

The code correction adds the approved `edp-lab` CLI profile to the SQL
submission, syncs the resulting Statement ID and response state to the
protected operation ledger, leaves errors/timeouts uncertain, and denies a
SQL checkpoint completion unless its signed receipt matches a recorded
Statement ID. No semantic SQL, Queue, grant, RAW, model or frozen result is
changed. Local verification: 55 operating tests passed; full repository
suite 562 passed and 82 skipped; Ruff passed.

## Protected owner gate and exact next action

1. Under the existing protected owner identity, inspect the original ledger,
   installed code/config and CLI stderr evidence, preserving their bytes and
   hashes. Independently verify Query History over the exact submission
   interval with complete pagination and inspect the exact UC target and any
   related side effect. Record the read-only responses and hashes in the
   protected evidence store. Do not change the original ledger.
2. If the original operation exists, use its actual Statement ID and
   terminal/UC readback to reconcile that same operation. If non-submission
   and absence of side effects are established, approve a **distinct**
   `sql-roster` recovery operation ID tied to the original ledger and
   checkpoint in a protected, signed technical disposition. If uncertainty
   remains, leave `sql-roster` `VALIDATING` and return an owner integrity
   decision; do not submit SQL.
3. Review and install only the corrected code through the protected
   deployment mechanism. A protected recovery transition must link the new
   operation ID to `sql-roster`, preserve the original ledger and all 502
   completed tasks, and require exact Statement ID/terminal/UC readback and
   a matching signed receipt. Do not restart the Supervisor until that
   transition exists and is verified.

After this gate, the same signed Queue has eleven remaining tasks, ending at
P13. P14 remains separate and requires a passed live freeze followed by
PR/CI, human review and explicit merge approval.

## Subsequent independent read-only check (2026-10-24)

The stopped checkpoint still hashes to
`f652eb11e56e4d03e1e6fdb6a454bd21d8ada1ca0e44e29c98a53f2de6179cda`;
the signed Queue still hashes to
`e43cf9984e1c54b17cbdc44917954bf802acba3241168ea353b302ec41076e34`.
The checkpoint remains 502 `COMPLETE`, one `VALIDATING` (`sql-roster`), ten
`PLANNED`. The installed protected `boundaries.py` SHA-256 is
`bf160d4820193b030abefdd8590acd8783171854bda18ab8ba3d325f2bb2bf28`;
the corrected worktree file is
`6da9934fb9203eeac69628216d1c1db8d1536f9e2f442ba104b3b751746a4d0d`.
The installed `runner.py` also differs from the corrected worktree. The
LaunchDaemon remains stopped (`last exit code = 1`), and its last traceback
is `SQL_STATEMENT_ID_MISSING`.

An independent Databricks Query History request for 2026-10-23 21:35–21:50
UTC returned `{"has_next_page":false}` with no query entries. The exact
response is `runs/day5/p11_recovery_v1/query_history_2135_2150_utc.json`,
SHA-256 `9fc9149be12779da64a26415b20b2f09a314d6faa817cb33a86a25b627a4053a`.
An independent Unity Catalog GET still reports that
`workspace.edp_lab.n500_input_roster_day5_v1` does not exist. These are
read-only corroboration, not authority to submit again: the original ledger
and protected CLI stderr remain inaccessible without the owner's root
credential (`sudo -n` returned `a password is required`).

### Exact protected owner inspection

Run the following in an owner-controlled terminal. These commands inspect the
original operation and save new read-only responses under the protected state
directory; they do not change the original ledger, Queue or checkpoint.

```zsh
sudo -s
set -euo pipefail
base=/private/var/db/edp-lab
repo=/Users/lightnino/Projects/edp-lab-day5-e2e
evidence=$base/state/day5/p11_sql_recovery_inspection
install -d -m 700 -o root -g wheel "$evidence"
shasum -a 256 "$base/ledger/day5-c2000-roster-v1.json" "$base/state/day5/checkpoint.json" "$repo/runs/day5/c2000_live_queue_v1.json" "$base/runtime/src/edp_lab/operating/boundaries.py" "$base/runtime/src/edp_lab/operating/runner.py" > "$evidence/local_hashes.txt"
cat "$base/ledger/day5-c2000-roster-v1.json" > "$evidence/original_ledger_readback.json"
export HOME=$base/private/home
export DATABRICKS_CONFIG_FILE=$base/private/databrickscfg
export DATABRICKS_AUTH_STORAGE=plaintext
/opt/homebrew/bin/databricks auth describe -p edp-lab > "$evidence/protected_auth_description.txt"
if /opt/homebrew/bin/databricks auth describe > "$evidence/default_auth_description.txt" 2> "$evidence/default_auth.stderr"; then
  print 'DEFAULT_AUTH_PRESENT: compare with the original adapter environment'
else
  print 'DEFAULT_AUTH_FAILED: inspect stderr for the missing-profile failure'
fi
/opt/homebrew/bin/databricks api get '/api/2.0/sql/history/queries?filter_by.query_start_time_range.start_time_ms=1792791300000&filter_by.query_start_time_range.end_time_ms=1792792200000&max_results=100' -p edp-lab -o json > "$evidence/protected_query_history_2135_2150_utc.json"
if /opt/homebrew/bin/databricks api get /api/2.1/unity-catalog/tables/workspace.edp_lab.n500_input_roster_day5_v1 -p edp-lab -o json > "$evidence/uc_target.json" 2> "$evidence/uc_target.stderr"; then
  print 'UC_TARGET_EXISTS: inspect exact table and its history before any recovery'
else
  print 'UC_TARGET_GET_FAILED: inspect stderr; only an authenticated not-found response supports absence'
fi
shasum -a 256 "$evidence"/*
```

Expected evidence for a technical pre-submission disposition: the original
ledger agrees exactly with the checkpoint's uncertain result and original
operation ID; the protected CLI without a profile reproduces the authentication
failure while `-p edp-lab` authenticates; the protected Query History response is fully paginated and
contains no matching statement; the authenticated UC response confirms target
absence and no related side effect; and the protected identity matches the
approved EDP Lab user. If any of these fail, stop for an owner integrity
decision. A zero-result Query History response alone is insufficient.

If all conditions pass, the standing policy permits a distinct bounded
technical recovery without a new semantic decision. The owner must install a
reviewed protected transition that binds a new operation ID to this original
ledger and checkpoint, preserves all 502 `COMPLETE` records, and enforces
Statement ID plus independent terminal/UC readback before completion. The
current runtime has no such SQL transition; restarting the Supervisor or
manually changing `sql-roster` would not be safe. Only after that transition
and the corrected adapter are installed should the existing LaunchDaemon be
started from this checkpoint.

## Owner-reported authenticated API test and disposition

The owner has now completed the read-only inspection and reports: default
Databricks API authentication exited 1; the same API call with `-p edp-lab`
exited 0 as `chengzhu13@gmail.com`; the original ledger remains
`UNCERTAIN_REQUIRES_READBACK`; checkpoint and signed Queue hashes still match;
the exact-window Query History returned zero visible records and no next page;
and authenticated Unity Catalog readback found no exact target table. These
are owner-reported results, not a protected signed disposition yet. The raw
authenticated API response and the exact original ledger bytes have not been
made available in this worktree. The failed default profile is a strong
pre-submission explanation, but Query History visibility and eventual service
effects cannot be proven absolutely from a zero page and absent table.

The existing standing policy can cover a **technical pre-submission** recovery
after the owner accepts that bounded residual uncertainty and signs the exact
disposition below. It cannot be inferred by editing the checkpoint. If the
original ledger, protected response, identity, or absence check differs from
the reported facts, keep `sql-roster` `VALIDATING` and seek an integrity
decision. The original operation `day5-c2000-roster-v1` remains reserved.

The implementation adds a distinct operation
`day5-c2000-roster-v1-recovery-v1` to the existing `sql-roster` task. The
transition moves only that task from `VALIDATING` to `PLANNED`, retains its
original external result as `original_external`, and signs a protected link
receipt. The Runner then submits only the new operation through the existing
broker and grant. Completion requires its Statement ID in the checkpoint, an
independent successful Statements API readback, the exact UC table ID and a
matching signed receipt. Any uncertain result remains reserved and waiting.

### Owner decision and protected installation (not executed)

**Decision requested:** approve or decline a bounded technical non-submission
disposition for this one SQL operation, owner-sign the packet, and install the
four reviewed runtime modules. This is a privileged installation and owner
signature; the agent must stop before those actions. No P14 PR review or merge
approval is requested here.

Run in the owner's Terminal only after reviewing the evidence and decision.
The following preflight checks are mandatory and have expected exit 0. A
failed check means **do not sign, install, transition, or restart**.

```zsh
sudo -s
set -euo pipefail
repo=/Users/lightnino/Projects/edp-lab-day5-e2e
base=/private/var/db/edp-lab
queue=$repo/runs/day5/c2000_live_queue_v1.json
state=$base/state/day5/checkpoint.json
trust=$base/trust
evidence=$base/state/day5/p11_sql_recovery_inspection
original=$base/ledger/day5-c2000-roster-v1.json
test "$(id -u)" = 0
test "$(shasum -a 256 "$queue" | awk '{print $1}')" = e43cf9984e1c54b17cbdc44917954bf802acba3241168ea353b302ec41076e34
test "$(shasum -a 256 "$state" | awk '{print $1}')" = f652eb11e56e4d03e1e6fdb6a454bd21d8ada1ca0e44e29c98a53f2de6179cda
test ! -e "$base/ledger/day5-c2000-roster-v1-recovery-v1.json"
test ! -e "$base/receipts/recovery-sql-roster.json"
test ! -e "$base/receipts/sql-roster.json"
if launchctl print system/org.edp-lab.day5-supervisor | grep -q 'state = running'; then exit 1; fi
```

The four protected evidence files below are required inputs to the
transition. Preserve the owner's completed responses in this root-owned
directory with these exact names and modes. `default_auth_test.json` records
`{"exit_code":1}`; `explicit_profile_auth_test.json` records
`{"exit_code":0,"authenticated_user":"chengzhu13@gmail.com"}`;
`protected_query_history_2135_2150_utc.json` is the complete original
response with `has_next_page:false`, no `res`, `queries`, or `results`, plus
`"query_start_time_range":{"start_time_ms":1792791300000,
"end_time_ms":1792792200000}`; and `uc_target_test.json` records the
authenticated response as `{"exit_code":1,
"error_code":"TABLE_DOES_NOT_EXIST",
"table":"workspace.edp_lab.n500_input_roster_day5_v1"}`. Retain the
original CLI stdout/stderr and HTTP responses separately in the same
directory. If the previously completed inspection did not retain the raw
authenticated responses, rerun only those read-only calls to create them;
that missing protected artifact is the specific evidentiary need.

The Installer now recognizes the observed Databricks CLI v1.21.0 response
`Error: Table 'workspace.edp_lab.n500_input_roster_day5_v1' does not exist.`
after successful explicit-profile identity and Query History calls. It also
accepts an exact target-bound structured `TABLE_DOES_NOT_EXIST` response.
Permission, transport, authentication, unrelated-table and unrecognized CLI
errors fail closed. The protected verifier checks the preserved raw UC stdout,
stderr and exit code against their hashes in `uc_target_test.json` before the
recovery transition. The owner should review those raw files before `SIGN`.

```zsh
install -d -m 700 -o root -g wheel "$evidence"
test "$(stat -f '%Su:%Lp' "$evidence")" = root:700
test "$(shasum -a 256 "$repo/src/edp_lab/operating/boundaries.py" | awk '{print $1}')" = 6da9934fb9203eeac69628216d1c1db8d1536f9e2f442ba104b3b751746a4d0d
test "$(shasum -a 256 "$repo/src/edp_lab/operating/runner.py" | awk '{print $1}')" = 1659439c7aff4341a62aa9f17dd4d9a36236cbae044dd1e68677f9826fd7b7fb
test "$(shasum -a 256 "$repo/src/edp_lab/operating/protected_verifier.py" | awk '{print $1}')" = 62f720ca2463f963c2fe02d4c3aa68db08d18dc2549c80f444147abbabb81e0b
test "$(shasum -a 256 "$repo/src/edp_lab/operating/protected_recovery.py" | awk '{print $1}')" = befbc5d2b520d68a05df72859d75bb79b5e50bd405d3a71dcc3ba38a39d412d3
shasum -a 256 "$original" "$state" "$queue" "$evidence"/*.json > "$evidence/preflight_hashes.txt"
```

Prepare the exact unsigned disposition from those preserved files, inspect
its JSON and hashes, then sign with the existing owner key. This is the owner
authorization step. It does not modify the ledger, Queue or checkpoint.

```zsh
export EDP_P11_REPO="$repo" EDP_P11_BASE="$base"
"$base/python/bin/python3.12" - <<'PY'
import json, hashlib, os
from pathlib import Path
repo = Path(os.environ['EDP_P11_REPO'])
base = Path(os.environ['EDP_P11_BASE'])
evidence = base / 'state/day5/p11_sql_recovery_inspection'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
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
       'evidence_sha256': {key: sha(evidence / name) for key, name in names.items()}}
(evidence / 'owner_disposition_payload.json').write_text(
    json.dumps(doc, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n')
PY
cat "$evidence/owner_disposition_payload.json"
openssl pkeyutl -sign -inkey "$base/private/owner.pem" -rawin -in "$evidence/owner_disposition_payload.json" -out "$evidence/owner_disposition.sig"
"$base/python/bin/python3.12" - <<'PY'
import base64, json, os
from pathlib import Path
base = Path(os.environ['EDP_P11_BASE'])
evidence = base / 'state/day5/p11_sql_recovery_inspection'
doc = json.loads((evidence / 'owner_disposition_payload.json').read_bytes())
sig = base64.b64encode((evidence / 'owner_disposition.sig').read_bytes()).decode()
(evidence / 'owner_disposition.json').write_text(
    json.dumps({'document': doc, 'signature_base64': sig},
               sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n')
PY
chmod 600 "$evidence"/owner_disposition*
```

After owner approval, preserve installed module hashes, replace only the four
reviewed modules, and restart the broker so its in-memory adapter is current.
Expected: installed hashes equal the four source hashes; checkpoint and
original ledger hashes still equal the preflight values. Do not use the
general 0A setup/credential repair script for this targeted installation.

```zsh
install -d -m 700 -o root -g wheel "$evidence/installed_before"
for name in boundaries runner protected_verifier protected_recovery; do
  cp -p "$base/runtime/src/edp_lab/operating/$name.py" "$evidence/installed_before/$name.py"
  install -m 644 -o root -g wheel "$repo/src/edp_lab/operating/$name.py" "$base/runtime/src/edp_lab/operating/$name.py"
  cmp "$repo/src/edp_lab/operating/$name.py" "$base/runtime/src/edp_lab/operating/$name.py"
done
test "$(shasum -a 256 "$state" | awk '{print $1}')" = f652eb11e56e4d03e1e6fdb6a454bd21d8ada1ca0e44e29c98a53f2de6179cda
launchctl bootout system/org.edp-lab.policy-broker
launchctl bootstrap system /Library/LaunchDaemons/org.edp-lab.policy-broker.plist
```

Run the transition exactly once with the existing protected grant. The module
checks the signed disposition and all four evidence hashes, original ledger
equality to the checkpoint, 502 completed tasks, ten planned tasks, Queue and
grant pins, and absence of the new ledger reservation. Expected output is
`VERIFIED_PRE_SUBMISSION_RECOVERY`, with `sql-roster` now `PLANNED`; its
`original_external` remains the old uncertain result. Any denial means leave
the Supervisor stopped and investigate without hand-editing the state.

```zsh
grant_id="$("$base/python/bin/python3.12" -c 'import json,sys;print(json.load(open(sys.argv[1]))["grant_id"])' "$state")"
grant="$base/grants/$grant_id.json"
test -f "$grant"
PYTHONPATH="$base/runtime/src" "$base/python/bin/python3.12" -m edp_lab.operating.protected_recovery \
  "$repo" "$queue" "$grant" "$state" "$trust" "$base/private/verifier.pem" \
  "$evidence/owner_disposition.json"
test "$(shasum -a 256 "$original" | awk '{print $1}')" = "$(awk -v p="$original" '$2==p {print $1}' "$evidence/preflight_hashes.txt")"
```

Negative tests before owner installation: alter a **copy** of the disposition
or one evidence file in an isolated test directory, change its checkpoint or
Queue hash, or pre-create the new operation ledger in a test fixture. Each
must deny before a receipt or SQL submission. The repository tests cover
these denials. Run the exact isolated test command below; expected result is
`13 passed`. Never run a negative test against the live protected ledger.

```zsh
cd "$repo"
"$repo/.venv/bin/python" -m pytest -q \
  tests/operating/test_day5_sql_protected_recovery.py \
  tests/operating/test_day5_sql_submission_recovery.py
```

After a successful protected transition, the owner may explicitly resume the
existing stopped Supervisor with
`launchctl kickstart -k system/org.edp-lab.day5-supervisor`. The expected
path is a single new protected SQL reservation, Statement ID capture,
independent terminal `SUCCEEDED`/exact UC readback, signed receipt, then the
remaining ten Queue tasks through the live P13 freeze. A missing ID, failed
statement, different table, uncertain response or missing receipt keeps the
task uncompleted. P14 requires a separate PR, CI, human review and explicit
merge approval; verify the resulting merge on remote `main`.

### Historical owner-terminal procedure — already executed; do not rerun

`scripts/owner_install_day5_p11_sql_recovery.sh` executes the above installation
as one owner-terminal procedure. It captures fresh, unedited authenticated CLI
responses before deriving the four required evidence files. It displays the
bounded disposition and requires the owner to type `SIGN` before using the
protected owner key. It then installs only the four hash-pinned modules, runs
the existing recovery transition, verifies the signed recovery receipt and
unchanged 502 completed tasks, and restarts the existing Supervisor. The owner
must run it from an owner-controlled Terminal; this worktree cannot access the
root-only protected evidence directory or owner key.
