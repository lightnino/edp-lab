# Day 5 C2000 SQL recovery packet (2026-10-24 SGT)

**Disposition:** `PAUSED_WITH_DECISION_PACKET`. This records the stopped existing run;
it is not a SQL retry, a P13 freeze, or P14 closeout. The active signed Queue remains
SHA-256 `e43cf9984e1c54b17cbdc44917954bf802acba3241168ea353b302ec41076e34`.
PR #62's later workflow amendment is prospective and does not change that signed Queue.

## Current protected checkpoint

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
