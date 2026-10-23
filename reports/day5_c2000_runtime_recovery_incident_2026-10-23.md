# Day 5 C2000 — Runtime Recovery / Operability Incident

**Incident ID:** DAY5-C2000-SQL-ROSTER-20261023  
**Status:** OPEN — blocked pending uncertain-write reconciliation and protected recovery  
**First observed failure:** 2026-10-23 21:42:29 UTC  
**Live diagnosis:** 2026-10-23 22:15 UTC; additional operator checks on 2026-10-24 (Singapore time)  
**Scope:** Existing Day 5 C1500→C2000 `CORPUS_ONLY` run, protected Supervisor / Databricks SQL write and independent verifier  
**Document type:** Post-incident evidence record and recovery follow-up; **not** an amendment to Workflow Specification, grant, queue or authorization  
**Evidence provenance:** Owner-supplied Mac Terminal, protected-supervisor diagnostic and Databricks read-only query outputs, supplemented by source inspection on the then-current `main` (`90dcb105a1ae25ddb92dd8e5d8db0d0ae6529cdd`). The protected host and remote Databricks state have not been independently accessed by this report's author.

## 1. Summary and impact

An autonomous Day 5 run stopped after P6 input-cohort freeze and while validating the `sql-roster` Databricks write. The supervisor process exited with code 1 following `SQL_STATEMENT_ID_MISSING`; it did not remain alive to poll or progress the queue.

At the observed checkpoint, **502/513 queue tasks were COMPLETE**; `sql-roster` was `VALIDATING`. This is a queue-task count, **not** a percentage of total P0–P14 effort or evidence of P13/P14 completion.

The original SQL invocation returned code 1, with empty stdout, no Statement ID and an `UNCERTAIN_REQUIRES_READBACK` ledger entry. There was no matching visible query in the inspected Databricks Query History window and no target table in the read-only Unity Catalog check. **Remote non-execution / absence of side effects is NOT yet proven.** No retry, remote write, Supervisor restart or ledger reset was performed during the reported diagnosis.

**Observed outcome:** Day 5 progress halted. No accepted C2000 P13 result freeze or P14 merged closeout was established by this diagnostic.

## 2. Exact run and protected evidence

| Field | Observation |
| --- | --- |
| Route | `CORPUS_ONLY`; C1500→C2000 |
| Signed queue SHA-256 | `e43cf9984e1c54b17cbdc44917954bf802acba3241168ea353b302ec41076e34` |
| Queue progress | 502/513 COMPLETE |
| Last confirmed stage | P6 `COMPLETE_AFTER_READBACK` |
| Current task / kind | `sql-roster` / `databricks_write` |
| Checkpoint state | `VALIDATING`; attempts = 0 |
| External operation ID | `day5-c2000-roster-v1` |
| Supervisor | launchd `not running`; no PID; runs = 1; last exit code = 1 |
| Final event | `sql-roster WAITING_EXTERNAL_READBACK`, 2026-10-23 21:42:29.434 UTC |
| Supervisor stderr | `SQL_STATEMENT_ID_MISSING`, 2026-10-23 21:42:29 UTC |
| Ledger path | `/private/var/db/edp-lab/ledger/day5-c2000-roster-v1.json` |
| Expected receipt | `/private/var/db/edp-lab/receipts/sql-roster.json` — absent at diagnosis |
| Target checked | `workspace.edp_lab.n500_input_roster_day5_v1` — absent in reported read-only Unity Catalog GET |

Read-only protected-ledger inspection returned:

```json
{
  "status": "UNCERTAIN_REQUIRES_READBACK",
  "statement_id": null,
  "remote_state": null,
  "returncode": 1,
  "submitted_at_utc": "2026-10-23T21:42:29.403568+00:00",
  "stdout_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "stderr_sha256": "ba416ff94762e46c9cdfc34fe26a40ea54e89cf6dced5a9e44a77d2fe3bcfaa5"
}
```

Ledger mtime: `2026-10-23T21:42:29.430785+00:00`. The SHA-256 of stdout matches empty output; the stored stderr hash does **not** reveal the actual stderr message. The operator observed one CLI submission invocation, returning code 1; no recorded Statement ID/Job Run ID. Do not infer an idempotent or successful submission from `attempts=0`.

### Timeline (UTC)

| Time | Recorded event / observation |
| --- | --- |
| 2026-10-23 21:42:23 | P6 `AUTHORIZED` |
| 21:42:26 | P6 `WAITING_EXTERNAL_READBACK` |
| 21:42:29 | P6 `COMPLETE_AFTER_READBACK`; `sql-roster AUTHORIZED` |
| 21:42:29.403 | Ledger records unsuccessful, uncertain SQL submission |
| 21:42:29.434 | `sql-roster WAITING_EXTERNAL_READBACK`; supervisor verifier raises `SQL_STATEMENT_ID_MISSING`, process exits |
| 22:15 diagnostic | launchd not running; no further poll; 502/513 tasks COMPLETE |

## 3. Read-only Databricks and authentication checks

**Query History:** The first filtered CLI query returned `[]`. A second read-only Query History API request used server-side interval **2026-10-23 21:35:00–21:50:00 UTC** with pagination:

```text
PAGES: 1
TOTAL_VISIBLE_QUERIES: 0
WAREHOUSE_MATCHES: 0
CANDIDATES: 0
PAGINATION_COMPLETE: True
```

This establishes **zero query records visible to that caller within that filter**, not a definitive statement that the backend never accepted a request. Visibility/permissions, endpoint scope and other remote telemetry may require further review.

**Authentication reproduction:** With the same protected configuration file and private HOME used for diagnosis:

- `databricks auth describe` **without** `-p`: **failed** (`default auth: cannot configure default credentials`; effective profile `default`).
- `databricks auth describe -p edp-lab`: **succeeded** (effective profile `edp-lab`, auth type `databricks-cli`).

The inspected repository's [SQL write boundary](../src/edp_lab/operating/boundaries.py) invokes `databricks api post /api/2.0/sql/statements --json @... -o json` without an explicit `-p edp-lab`. The operator also reported that the installed protected runtime files matched the checkout; final root-cause verification should still inspect the service's **actual effective environment** and captured failure mechanism.

## 4. Assessment: confirmed, probable, unresolved

| Classification | Finding |
| --- | --- |
| **CONFIRMED: incident** | Supervisor exited (code 1); no subsequent polling observed; `sql-roster` remained `VALIDATING`. |
| **CONFIRMED: failed local invocation** | CLI returned 1, stdout empty, Statement ID missing; ledger recorded `UNCERTAIN_REQUIRES_READBACK`. |
| **CONFIRMED: configuration mismatch** | Protected CLI defaults to an unauthenticated profile; explicitly selecting `edp-lab` authenticates successfully. |
| **PROBABLE: immediate cause** | The protected SQL write adapter omitted an explicit working CLI profile, producing an authentication/submission failure. Confirm against original process environment and failure evidence before marking root cause final. |
| **CONFIRMED: liveness gap** | The verifier's missing-ID exception coincided with process exit; the supervisor did not continue polling or surface an autonomous recovery resolution. |
| **IMPLEMENTATION RISK TO VERIFY** | The inspected write boundary stores result/status and stdout/stderr hashes but does not itself show durable Statement ID extraction. Verify actual broker/verifier result handoff and successful-submission persistence before recovery. Do not claim this separately caused the initial failed submission. |
| **UNRESOLVED** | Whether Databricks accepted/partially executed the original non-idempotent SQL request, and the exact permissible ledger disposition/recovery route. |

**Workflow-spec assessment:** The [Cohort/Model Workflow](../docs/workflows/cohort_model_lifecycle_v1.md) already defines P11 conditional recovery, uncertain-write independent readback, checkpoint continuation, P13 independent result freeze, and P14 human-reviewed Git closeout. The [Operating Contract](../docs/agent_operating_contract.md) similarly requires independent receipts and forbids replay of uncertain writes. **No evidence here establishes a Workflow Specification defect.** The observed breakdown is at the protected runtime/adapter, verifier error handling and operability/visibility layers. Candidate liveness/observability acceptance improvements can be considered separately after recovery; no immediate spec edit is authorized by this report.

## 5. Containment and recovery gate

**Containment at diagnosis:** Fail closed. Do not restart the stopped supervisor, re-run the same SQL, clear/overwrite the original operation ledger, fabricate a receipt, alter signed queue/grants, or infer safety from empty Query History.

Required safe path, subject to the **existing** Workflow and recovery authority:

1. Preserve the original ledger, checkpoint, queue hash, event log and available local/remote forensic evidence.
2. Reconcile original SQL submission and possible remote effects using approved read-only Databricks/ledger/history evidence; if uncertain, obtain the required owner disposition **before any fresh write**.
3. Confirm the exact protected CLI profile defect; patch explicit approved authentication context and verify Statement ID capture plus independent exact-operation receipt linkage.
4. Test failure/replay denial, successful submission/readback, uncertainty handling, bounded recovery and checkpoint preservation. Prevent an unhandled missing-ID verifier exception from silently terminating autonomous progress; retain fail-closed semantics.
5. Apply a minimal authorized protected deployment and, where permitted by the evidence and authority, reconcile/resume **this existing run** from its checkpoint. Never reset or replay the completed 502 tasks.
6. Complete the remaining signed DAG and independent P13 freeze. Carry out **separate P14 PR/CI/human review/explicit merge approval/verified-main closeout** per the existing contract.

This report is **not** the owner disposition or approval for a new write, protected deployment, restart, grant change or Git merge.

## 6. Corrective-action tracking (proposed; not yet implemented)

| Item | Acceptance evidence | Status |
| --- | --- | --- |
| R1 — Original uncertain-write disposition | Independent remote reconciliation, preserved original ledger, explicit authorized decision | OPEN |
| R2 — Protected CLI profile selection | Recorded effective approved profile; success/failure tests in installed environment | OPEN |
| R3 — Statement ID and readback handoff | Durable exact submitted ID, signed receipt matching operation + request SHA and verified remote object | OPEN |
| R4 — Supervisor failure handling and visibility | Controlled fail-closed escalation on missing ID; live service/status/log and no silent crash; alert/status reporting | OPEN |
| R5 — Bounded resume | Same queue/checkpoint, already-COMPLETE tasks untouched, authorized recovery, no blind replay | OPEN |
| R6 — End-to-end Day 5 exit | Independently frozen P13 and approved, merged, verified P14 `main` commit | OPEN |
| R7 — Post-closeout operability review | Review liveness, failure-classification, escalation and progress-visibility requirements; amend spec only via separate review if a demonstrated gap remains | DEFERRED |

## 7. Closure criteria and exclusions

Keep this incident **OPEN** until R1–R5 have evidence-backed dispositions and the resumed run's outcome is recorded. Distinguish incident remediation closure from overall Day 5 P13/P14 completion; report both explicitly. The current supported run state is **DAY5_PARTIAL_BLOCKED**, not `DAY5_COMPLETE_P14_MERGED`.

No code was deployed, supervisor restarted, remote write submitted, ledger altered, Workflow Spec revised, P13 freeze accepted, or P14 merged **by creating this report**. Day 6 Vault prototype/PR #61 and the already-merged prospective RAW handoff specification PR #62 are out of scope.

**Evidence update rule:** Add subsequent independently verified recovery/closeout references when they exist. Do not backfill success or transform provisional hypotheses into confirmed root causes without additional evidence.


## 8. Follow-up at 2026-10-24 06:47 SGT — Recovery preparation, human gate versus operability gap

**Source and qualification:** Additional owner-provided Codex execution report, not an independently verified protected-host readback. This update is documentary only; it does not grant permission to resume or retry.

- Reported live checkpoint: **502/513 COMPLETE**, `sql-roster` still `VALIDATING`, P13 `PLANNED`; protected Supervisor stopped.
- Reported narrow correction prepared in a **local commit `0fb6242`**: explicit Databricks profile, Statement ID ledger persistence/synchronization, fail-closed uncertain submissions and exact Statement ID receipt matching. The full commit and recovery packet are **not yet independently accessible through the remote GitHub repository** at the time of this update; do not represent the reported fix as deployed or merged.
- Reported test evidence: 55 operating tests pass; 562 tests pass / 82 skipped across the full suite; Ruff passes. This validates the tested checkout, **not** actual protected runtime installation or live recovery.
- Local recovery packet reported at `docs/operating/day5_c2000_sql_recovery_packet_20261024.md`. Its contents, required owner procedure and exact deployment pins must be reviewed from the local checkout before executing privileged actions; no undocumented command should be inferred here.
- Protected runtime **not updated**. Original operation ledger and 502 COMPLETE tasks remain untouched; no SQL retry, protected deployment, P13 acceptance or P14 merge.
- Reported checkpoint operating counters: 503 operations, zero retries, 6,863 cumulative runtime seconds; actual monetary cost unavailable. These counters are neither a certification of 503 remote writes nor a P13/14 completion measure.

### Human-intervention classification

| Situation | Intended treatment | Incident significance |
| --- | --- | --- |
| Routine CLI authentication selection / service configuration | Protected, pre-authorized 0A runtime configuration and regression tests; no per-run owner signature | **Preventable runtime defect**; part of this incident |
| Verifier raises for a missing Statement ID and launchd Supervisor stops without a durable actionable state | Record typed fail-closed state, notify/observe liveness, preserve checkpoint, allow safe read-only reconciliation | **Operability/liveness gap**; part of this incident |
| A write is mechanically and independently proven not executed with no remote side effect, and a standing-policy recovery is explicitly authorized | Bounded automated disposition/retry via independently trusted components, with unique attempt identity and complete audit evidence | **Candidate autonomy improvement**, but do not assume this authority/path currently exists or is approved |
| Original non-idempotent write cannot be proven safe to retry after independent remote reconciliation | Fail closed and obtain explicit owner disposition before any new submission | **Justified human safety gate**, not itself a defect |
| P14 review and merge | Mandatory human review and explicit merge approval | **Intended workflow gate** |

The presence of a justified **human uncertain-write disposition** must not be conflated with the avoidable **human debugging, root-only readback access bottleneck, lack of safe automated forensic assistance, and Supervisor crash**. A protected agent should never gain unrestricted root access or permission to self-authorize an uncertain-write replay. Improved trusted read-only diagnostic interfaces and independently verified recovery can reduce routine owner intervention while preserving separation of duties.

### Decision and lifecycle

- **Incident report:** Submit and retain this draft PR now as a factual OPEN record. The draft report is not a fix, an approved recovery, or a workflow amendment.
- **Day 5 execution:** Review the local recovery packet, perform the minimal owner-only forensic/disposition/deployment steps actually required by the protected contract, then resume the same checkpoint under approved authority. Finish P13 and the separate P14 review/merge gate.
- **Incident completion:** After Day 5 P14, update this incident with independently observed root cause, disposition, deployed fix SHA, service resume evidence, P13 freeze and P14 merge; review and merge the incident PR. Do not mark `RESOLVED` if material R1–R5 safety/operability evidence remains missing.
- **Workflow changes:** None now. Open a separately reviewed spec-change proposal **only if** the post-recovery evidence demonstrates an actual missing/contradictory normative requirement, rather than an implementation shortfall against existing P11/0A and operating contracts.
- **C3021 RAW audit:** Independent, later investigation; not a prerequisite for SQL recovery, Day 5 closeout, or a supported incident report.
