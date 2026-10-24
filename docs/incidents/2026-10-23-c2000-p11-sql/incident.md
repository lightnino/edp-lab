# Day 5 C2000 — Runtime Recovery / Operability Incident

**Incident ID:** DAY5-C2000-SQL-ROSTER-20261023  
**Current status (updated 2026-10-24):** DAY 5 OPERATION/P13/P14 RECOVERED AND CLOSED; **R7 CLOSED** via reviewed [PR #65](https://github.com/lightnino/edp-lab/pull/65). **R4 OPEN** (Supervisor liveness, stall alerting and safe diagnostics; draft [PR #66](https://github.com/lightnino/edp-lab/pull/66) not complete). **R8 OPEN** (installed preflight/CLI-response regression evidence). Sections 1–8 preserve contemporaneous incident states; the final post-closeout disposition is in §§9–12.  
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

The inspected repository's [SQL write boundary](../../../src/edp_lab/operating/boundaries.py) invokes `databricks api post /api/2.0/sql/statements --json @... -o json` without an explicit `-p edp-lab`. The operator also reported that the installed protected runtime files matched the checkout; final root-cause verification should still inspect the service's **actual effective environment** and captured failure mechanism.

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

**Workflow-spec assessment:** The [Cohort/Model Workflow](../../workflows/cohort_model_lifecycle_v1.md) already defines P11 conditional recovery, uncertain-write independent readback, checkpoint continuation, P13 independent result freeze, and P14 human-reviewed Git closeout. The [Operating Contract](https://github.com/lightnino/edp-lab/blob/12f9549f99a805eb26322c2bc70b94377512164d/docs/agent_operating_contract.md) similarly requires independent receipts and forbids replay of uncertain writes. **No evidence here establishes a Workflow Specification defect.** The observed breakdown is at the protected runtime/adapter, verifier error handling and operability/visibility layers. Candidate liveness/observability acceptance improvements can be considered separately after recovery; no immediate spec edit is authorized by this report.

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


## 9. Post-P14 resolution and independently inspectable evidence (2026-10-24)

**Evidence hierarchy.** The owner executed the protected P11 disposition/install in an owner-controlled terminal; the signed receipts and final result artifacts were committed in [Day 5 PR #64](https://github.com/lightnino/edp-lab/pull/64) and are independently inspectable on remote `main`. Original root-only ledger bytes and live service process environment are not publicly exposed. Do not infer access to unprovided private logs or assert historical zero side effects beyond the evidence. Earlier provisional findings in §§1–8 are retained as a dated record, not the current run status.

| Boundary | Final, scoped evidence | Outcome |
| --- | --- | --- |
| Original uncertain operation | `day5-c2000-roster-v1`, ledger SHA-256 `0c6144e51eeee56ca3dbdbfbc095a44396507a5b6813f9768ae9488bbaa9c3f2`, return code 1, empty stdout, no Statement ID | **PRESERVED**; original ledger not overwritten or replayed |
| Original-call reconciliation | Protected owner CLI: default-profile API call exits 1; explicit `-p edp-lab` succeeds as expected owner; full original-window Query History zero visible entries and no next page; authenticated exact UC target absent before recovery | **SUPPORTED PRE-SUBMISSION**, with residual Query History visibility and delayed-effect uncertainty **accepted by owner**, not a mathematical proof of zero effects |
| Human recovery authorization | Owner reviewed bounded disposition `EDP_SQL_PRE_SUBMISSION_DISPOSITION_V1`, typed `SIGN`, created protected signed owner decision for one distinct operation | **AUTHORIZED**, human integrity decision at the actual uncertain-write boundary |
| Protected one-operation transition | `day5-c2000-roster-v1-recovery-v1`; signed link-receipt SHA-256 `e3b252b234da0475a8e1afe46279ea0d91930785686966467a0260e193097d85`; owner terminal `VERIFIED_PRE_SUBMISSION_RECOVERY` and `VERIFIED_POST_INSTALL_502_COMPLETE_11_PLANNED` | **RECOVERED** without changing the original operation or replaying 502 completed tasks |
| New SQL operation and readback | Signed `metadata/freezes/O_C2000_M2_v1/receipts/sql-roster.json`, SHA-256 `9298818cc39f3ba0d1e932b8f1474fc442238d0a701f2f32c2ea4971c5f843c8`; Statement ID `01f1cf3d-6016-12f2-a7d2-5379704abd92`, terminal `SUCCEEDED`, exact target `workspace.edp_lab.n500_input_roster_day5_v1`, UC ID `2e49534e-278c-4e69-99a0-25f83ad8849f` | **SIGNED VERIFIED**; protected verifier enforces original ledger hash, recovery link and exact Statement ID |
| P13 result | `metadata/freezes/O_C2000_M2_v1/databricks_result_freeze_v1.json`; signed freeze SHA-256 `e1023289fedb3b682e0afe33bc350997e5d84c5aa27e9d00bf34bc760fe93830`; remote evidence SHA-256 `512cecc9170f9c3a6abe46da2d21bce5a5eedb995d89f334d8be9a299ea6aea2` | **PASS**: 2,000 physical sources, 321,188,377 occurrences; FIN_001/002 and TRY_001–004 PASS |
| Final checkpoint and Git P14 | 513/513 COMPLETE, accepted checkpoint SHA-256 `f775e646e849d093d6e5e495a782f45635b2324f5022e68d594944b27fbbe537`; CI passed; PR #64 merged; remote `main` merge SHA **`12874dd2aa581a80086afa24a3d21a0a1aa6f3e4`** | **DAY5_COMPLETE_P14_MERGED** |

The frozen result is a version-pinned source-preserving Databricks view; neither immutable WORM storage nor indefinite remote retention was established. Treasury economic L6-B remains `NOT_IMPLEMENTED_OUT_OF_SCOPE`. Neither limitation invalidates the scoped source-preserving P13 PASS; both must travel with downstream representations.

## 10. Causal analysis: defect, consequence, recovery friction and proof limits

**Probable initial triggering defect, high confidence, not conclusive historical proof.** The protected SQL write adapter used Databricks CLI without the explicit working `-p edp-lab` profile. Under the owner's reproduced protected identity/environment, a real current-user API request **without** the profile failed, whereas the identical authenticated operation **with** `-p edp-lab` succeeded. The original failed SQL invocation's stderr bytes were not preserved as readable evidence; its SHA-256 alone cannot prove the exact historical API/authentication error. Do not turn this into a fully confirmed historical error code.

**Confirmed failure path and liveness gap.** The SQL submission returned exit 1 with no Statement ID and was durably classified `UNCERTAIN_REQUIRES_READBACK`. The independent verifier correctly refused to sign success (`SQL_STATEMENT_ID_MISSING`), but the Supervisor treated this nontransient `Denied` as an unhandled exception and terminated rather than durably exposing a typed blocked state to an operator/reconciler. As of the PR #64 merged `checkpoint_supervisor.py`, unclassified verifier `Denied` exceptions still propagate from the Supervisor loop. **A successful one-off recovery is not proof that this general liveness defect was fixed.** Follow-up hardening remains required, with no silent retry and no weakening of the independent verifier.

**Recoverability and diagnostic defects revealed during remediation.** The first owner installer inspected an invalid `/api/2.0/current-user/me` endpoint and mislabeled its error as an authentication failure; a subsequent version mismatched a genuine CLI “Table ... does not exist” response to an exact `TABLE_DOES_NOT_EXIST` string. Both interrupted the protected pre-signature checks. Later installer revisions corrected the CLI identity call and target-bound authenticated-not-found parsing, and the final signed transition succeeded. These were separate avoidable preflight robustness failures, not evidence of additional SQL submissions. Exact root-only stdout/stderr and safe preflight response classification should be preserved for the next incident; redact credentials.

**Correctly retained safety boundary.** The original write's non-execution was not provable with absolute certainty. The owner therefore explicitly accepted a bounded residual risk and signed a distinct technical recovery identity, which is a justified human integrity gate, **not** evidence that every normal run or transient infrastructure fault needs manual owner intervention. There is no authority to forge a signed disposition or to “reset” an uncertain ledger.

## 11. Follow-up action register and normative documentation decision

| Ref | Closeout assessment | Final status / next acceptance |
| --- | --- | --- |
| R1 — Reconcile original uncertain operation | Original ledger pinned, authenticated readbacks captured, bounded uncertainty disclosed and owner-signed distinct-operation disposition | **CLOSED FOR THIS OPERATION**; preserve provenance and limits |
| R2 — Fix SQL CLI profile | Corrected adapter uses explicit approved profile; root identity reproduced; installed reviewed modules and successful new live write | **CLOSED FOR THIS OPERATION**; retain regression |
| R3 — Statement ID / exact signed readback | New statement's ID is durable and independently matched to signed receipt, terminal SUCCESS and UC object | **CLOSED FOR THIS OPERATION** |
| R4 — Supervisor failure/liveness and diagnostics | Original `SQL_STATEMENT_ID_MISSING` crash observed; generic nontransient verifier exception still exits Supervisor; root-only evidence requires owner mediation | **OPEN OPERABILITY GAP**. New separate code PR should persist typed `PAUSED_WITH_DECISION_PACKET` / blocked reason and retrievable sanitized read-only status, preserve uncertain ledger, prevent automatic replay, and test restart/recovery/alert semantics |
| R5 — Bounded same-checkpoint resumption | 502 completions preserved; distinct owner-authorized recovery; original operation never replayed | **CLOSED FOR THIS OPERATION** |
| R6 — End-to-end freeze and human-approved merge | Signed P13 readback and PR #64 merged/verified at `12874dd2aa581a80086afa24a3d21a0a1aa6f3e4` | **CLOSED — DAY5_COMPLETE_P14_MERGED** |
| R7 — Authority matrix / operating procedure | Current [operating contract](https://github.com/lightnino/edp-lab/blob/12f9549f99a805eb26322c2bc70b94377512164d/docs/agent_operating_contract.md) says uncertain writes require readback and disposition; [guide](https://github.com/lightnino/edp-lab/blob/12f9549f99a805eb26322c2bc70b94377512164d/docs/agent_operating_guide.md) broadly says any failed/uncertain write must obtain human disposition, while 0A/Workflow allows routine bounded technical recovery | **CLOSED IN PR #65 (2026-10-24)**: canonical [cross-lifecycle Operating Contract](../../workflows/agent_operating_contract_v1.md) and [Operating Guide](../../operating/agent_operating_guide_v1.md) merged with an explicit recovery decision matrix; no new installed grant is inferred |
| R8 — Owner installer preflight format and evidence preservation | Incorrect current-user endpoint and too-narrow CLI UC error parser initially blocked legitimate owner inspection; final installer validated | **INITIAL INCIDENT FIXED**, but add installed-environment response-format/preflight tests and retained redacted stdout/stderr regression evidence as an independent acceptance item |

### 11.1 Recovery decision matrix for a separate Operating Contract clarification

1. **Verified existing operation**: independently reconcile the original Statement ID and terminal/UC state; complete only that operation via its matching signed receipt. **Do not resubmit**.
2. **Independently established pre-submission failure and no remote side effects**: a separately protected authority may authorize a **distinct, bounded recovery operation** automatically **only if** the owner-installed standing policy explicitly delegates that exact recovery class, evidence requirements, scope, and immutable audit linkage. Otherwise return an owner decision packet. Zero visible Query History alone does not meet this test.
3. **Unresolved remote state, ambiguous API response, insufficient visibility, delayed-effect possibility or material integrity discrepancy**: keep `VALIDATING`/blocked, retain the original ledger, use read-only reconciliation, **no replay**; request an owner integrity disposition for any fresh non-idempotent write. This is the actual Day 5 case.
4. **Ordinary transient runtime/configuration failure without uncertain write effects**: bounded automatic repair and checkpoint resume within deployed 0A policy; do not turn it into per-run owner signature. Distinguish this from original-operation recovery.
5. **New semantic/business rule, policy enlargement, hard-limit/measurement exception, or P14 Git merge**: independent owner decision under its separate authority; P14 explicit human merge is never delegated by this incident.

A trusted independent signer/verifier, protected ledger, exact operation/request identity, proof hashes, authority separation and persistent state are mandatory for every signed recovery. The Agent cannot self-sign, infer an absent object from an unrelated path, gain root credentials or override an owner-integrity gate.

### 11.2 Separate Protected Recovery Runbook for Operating Guide

Specify: detect typed external state and process liveness → capture original protected ledger/checkpoint/queue/grant hashes and safe CLI stderr → establish real auth identity/profile → exact-window paginated Statement History and UC/remote readback → classify *existing successful*, *confirmed no effect*, *unresolved* → run the Contract decision matrix → if authorized, owner-/broker-signed new operation identity and targeted pinned code deployment → verify original bytes and 502 completed records untouched → independent Statement ID/terminal/UC receipt → resume only from the same checkpoint → record CI, execution and human intervention costs when observed. Any mismatch stops the affected operation. Retain a sanitized, least-privilege owner/agent decision packet, not raw credentials.

### 11.3 Workflow Specification decision

**No new P11 Workflow Specification amendment is justified by this SQL incident on current evidence.** [Cohort/Model Workflow](../../workflows/cohort_model_lifecycle_v1.md) already requires bounded P11 diagnosis, independent readback before uncertain replay, protected standing 0A authority, checkpoint reuse and P13/P14 gates. The missing pieces are **authority-classification precision in the Contract/Guide** and **actual protected-runtime implementation/operability**, not a contradictory workflow stage. Amend P11 in a separate owner-reviewed spec change *only* if a tested recovery scenario demonstrates a missing/contradictory normative requirement after Contract/Guide hardening. Do not retroactively amend the executed Day 5 queue or authorization.

## 12. Independent C3021 RAW staging audit (separate workstream)

The historical Day 2/C3021 RAW staging vs Day 5 actual N500 reuse allegation is **uninvestigated by this SQL incident**. PR #62 already merged the **prospective** single-owner RAW rule into Universe U3/U10 and Cohort P0/P1/P8/P11; it did **not** prove 3,021 historical uploads or implement the protected Cohort RAW-write denial. PR #64 completed the live result, but is not historical pre-Day-5 upload evidence.

After this report's review/merge, run a separate **read-only forensic audit**, against the exact original C3021 inventory and selected Day 5 N500, prior-to-first-Day-5-upload receipt timestamps and remote version/audit evidence. Produce the requested 500-row matrix with historical-presence and Day-5-action as **separate axes**, plus verified duplicate/new/unresolved counts and evidence references. Distinguish historical specification from PR #62's later prospective requirement. Do **not** infer duplicate physical RAW staging from cohort-prefixed directories or missing legacy receipts; do **not** mutate Databricks, the final freeze or protected ledgers. A distinct corrective implementation/negative-tests PR, if the audit demonstrates it, must enforce Acquisition RAW-write vs Cohort RAW-read permissions and avoid unresolved→missing fallthrough. **Do not fold RAW forensic conclusions or an executor rewrite into PR #63.**

**Incident reporting disposition (updated 2026-10-24):** Day 5 execution, this specific P11 recovery, and P14 are closed, with signed evidence. **R7 is CLOSED by PR #65**. **R4 liveness/diagnostic hardening and R8 installed preflight regressions remain OPEN**. PR #63 may be merged as a completed factual postmortem while those clearly labeled corrective actions are delivered in separately reviewed PRs; it must not be described as a complete runtime reliability fix.

## 13. PR #66 acceptance preparation (2026-10-24)

PR #66 adds R4 blocked-state/liveness diagnostics, an independently scheduled
Watchdog candidate, and R8 read-only UC PRESENT/ABSENT preflight. The
[acceptance packet](../../operating/r4_r8_protected_acceptance_packet_20261024.md)
records offline tests, local installed-CLI response hashes, a disposable
protected fixture plan and remaining owner-controlled gates. The original
P11 incident, signed recovery, 513/513 completed Day 5 checkpoint and P13/P14
result remain historical facts; they were not rerun or revised.

**R4 remains OPEN / protected-live BLOCKED:** no owner-approved Watchdog
installation, separate launchd restart/backoff evidence, protected fixture
test, or actual designated-operator alert receipt yet. **R8 remains OPEN /
protected Owner-terminal BLOCKED:** the local installed CLI read-only PRESENT
smoke passed, but owner-protected profile/identity, raw response retention and
negative-format capture have not yet been independently accepted. The later
PR #62 prospective RAW authorization split remains a specification, not proof
of deployment. PR #61 is separate and untouched. No PR #66 merge is implied.

### 13.1 Bounded fixture approval and remaining final execution gate

The Owner subsequently approved preparing an isolated root-owned R4 no-write
fixture and protected read-only R8 preflight, with an explicit final review of
paths, commands, service configuration and notification route before any
privileged installation. The [exact execution review packet](../../operating/r4_fixture_review/owner_execution_packet.md)
is prepared on PR #66. The proposed `/usr/bin/mail` command and Owner email
destination have **not** been approved for activation or used. No root-owned
fixture, launchd job or protected R8 response store has been installed yet.
R4 and R8 therefore remain OPEN/BLOCKED for protected-live acceptance; the
completed historical Day 5 result is unchanged.
