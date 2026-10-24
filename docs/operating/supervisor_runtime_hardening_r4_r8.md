# Supervisor Reliability Hardening — R4 + R8 (P11 incident)

**Implementation status:** proposed code + offline tests on [PR #66](https://github.com/lightnino/edp-lab/pull/66). **NOT INSTALLED**, **NOT LIVE VERIFIED**. Does not change the original Day 5 signed queue, result freeze, protected ledger, owner authorization or P11 Workflow. Owner PR review does not itself activate the protected runtime.

## R4 — Supervisor liveness / stalled progress

- `checkpoint_supervisor.py` emits a private `supervisor_status.json` (schema V2) with PID, sanitized reason, current task, completed count, exact checkpoint digest, heartbeat and last progress times. It does **not** mutate the signed Runner checkpoint or original uncertain SQL ledger.
- A nontransient `Denied` or unexpected error produces `PAUSED_WITH_DECISION_PACKET` and **nonzero exit 2**, never process exit 0 or false `COMPLETE`. Successful accepted queue returns 0.
- `python -m edp_lab.operating.supervisor_health STATE_DIR --heartbeat-seconds H --progress-seconds P` is a **separate read-only-check / private-alert writer** for owner-installed scheduled invocation. It checks trusted status + PID, last heartbeat and actual checkpoint progress separately. It returns 3 on alert, prints sanitized JSON only, and stores private `supervisor_watchdog_alert.json` with mode 0600. It NEVER restarts the Supervisor, posts SQL, signs receipts or clears an uncertain ledger.
- Thresholds **must** be installed explicitly by the owner, bounded to actual approved operation runtime limits. A lengthy legitimate Databricks invocation may delay the Supervisor heartbeat; detect and report **UNRESPONSIVE**, do not infer execution outcome from the timer. Stale/untrusted status is not proof of remote non-submission.
- Do not give the agent direct root/ledger/key access. The state directory and diagnostic surface must be protected; only a specifically permitted least-privilege read-only operator should see sanitized status.

**Not completed by this PR:** owner-controlled launchd service/independent watchdog schedule; process restart/backoff policy; actual end-to-end alert delivery outside the owner's terminal; protected-host file permissions; kill -9 / real hung process integration; independent installed-runtime audit. These remain **R4 LIVE BLOCKERS**. Tests simulate dead worker, stale heartbeat/progress, blocked state, no replay and nonzero exit; this is **OFFLINE VERIFIED ONLY** when CI passes.

## R8 — installed-environment CLI preflight regression

New pure parser `src/edp_lab/operating/cli_preflight_r8.py`, unit fixtures and an **owner-terminal, read-only** smoke entrypoint `scripts/owner_preflight_cli_r8.py`.

- `databricks current-user me -p PROFILE -o json` **must** return the owner-specified expected principal. Default profile/cached auth assumptions are not accepted.
- Query History uses an exact owner-specified time window, enforces response shape and **complete token pagination**. A visible zero count is *not* proof that no backend submission occurred.
- Exact UC `TABLE_DOES_NOT_EXIST` accepts the narrowly documented Databricks CLI formatted error or JSON error **only for the exact table identity**. Permission denied, unauthenticated, ambiguous/mismatched target or incomplete history fails closed.
- Output is sanitized `READONLY_EVIDENCE_ONLY` with SHA hashes and `write_or_recovery_authorized=false`; neither the positive unit suite nor an installed smoke delegates the integrity disposition required by R7.

**Owner-controlled smoke example (do not run for the historical already-closed Day 5 P11 operation):**

```sh
# Illustrative only: supply currently approved identity, exact UC target and justified time window.
.venv/bin/python scripts/owner_preflight_cli_r8.py \
  --profile APPROVED_PROFILE --expected-user EXPECTED_PRINCIPAL \
  --table CATALOG.SCHEMA.TABLE --start-ms START --end-ms END
```

The original `scripts/owner_install_day5_p11_sql_recovery.sh` is **historical and must never be reexecuted**. R8 smoke is strictly read-only, with no signing, installation or recovery side effects.

## R4 + R8 acceptance gates before declaring CLOSED

1. Offline tests and lint PASS; staged code reviewed and source SHA pinned.
2. Owner installs a *separately protected* Supervisor/monitor identity and periodic watchdog schedule; verifies normal accepted, blocked `Denied`, unexpected exception, SIGKILL/dead process, hung/no progress, service restart/backoff, monitor failure and owner-visible alert delivery. Every failure must preserve exact ledger, approved queue, complete tasks and versioned Delta/UC state.
3. Owner runs read-only R8 preflight on the **actual installed Databricks CLI + effective approved profile**, retaining redacted command results, stderr/return codes and negative response formats, including paginated Query History and UC target identity. No premature absence inference.
4. Independent receipt/readback and identity evidence is linked to the original incident; only then update its existing R4/R8 states to CLOSED. No change to P11 Workflow Specification or general recovery delegation is implied.

Related rules: [Agent Operating Contract](../workflows/agent_operating_contract_v1.md), [Agent Operating Guide](agent_operating_guide_v1.md), [P11 incident](../incidents/2026-10-23-c2000-p11-sql/incident.md).
