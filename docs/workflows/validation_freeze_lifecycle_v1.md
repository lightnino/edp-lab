# Validation, Stability, Live Freeze + Git Exit V1

**Status: PROPOSED FOR OWNER REVIEW — acceptance specification, not evidence of an executed test or a deployable DAG.**

**Purpose.** The **shared acceptance/control specification called by the Cohort + Model Lifecycle**, for the initial model and for `CORPUS_ONLY`, `ADDITIVE` and `CORRECTIVE` changes. It is **not a second independent end-to-end data processing workflow or a second Agent**. Rules must be independently enforced by source/model/field-derived applicability and versioned oracles, not “whatever tests the agent happened to list.”

**Call interface:** Cohort P9 → §2 Lossless 1–6 (including conditional economic research); Cohort P10 → §3–4 Stability A/B2/C1/C2/C3; Cohort P12 → §5 C3.4 performance/budget; Cohort P13 → §6 live Databricks result freeze; Cohort P14 → §7 Git Exit. The Cohort workflow controls sequencing/branch selection; **this file owns detailed test applicability, oracles, thresholds and freeze evidence**. Applicable tests are invoked on pinned candidate data already produced by Cohort P8; they do **not** automatically redo RAW→CLEAN→QUERYABLE. Detailed branches in Cohort are caller contracts, not competing PASS criteria.

**Canonical authorities:** `docs/evaluation_contract.md` (normative L1–L9; original executable Lossless 1–6 grouping; FIN V2; Stability C2/C3), `metadata/evaluations/lossless6_fin_suite_v2.json`, `metadata/evaluations/stability_m1_v1.json`, existing FIN/TRY SQL fixtures, `metadata/freezes/O_C300_M1_v1/`, `metadata/freezes/O_C750_M1_v1/`, and `metadata/freezes/O_C1500_M2_v1/databricks_result_freeze_v2.json`. Preserve original historical results even when later versions strengthen acceptance.

## 1. Order of work and integrity boundary

**Proposed logical sequence:** `Pinned RAW → provisional CLEAN → provisional QUERYABLE → complete Lossless 1–6 → branch-specific Stability A/B2/C → accepted QUERYABLE → live Databricks result freeze → Git PR/CI/Merge → verified Exit`.

- During processing, use exclusive **candidate** output namespaces and immutable run-specific references. A candidate QUERYABLE can be constructed/read for validation; it is **not** an accepted consumer output before required gates pass.
- Early source/binding safety preflights (RAW SHA, source identity, parsing sanity, write-once/approval checks) still apply **before** any remote write. “Lossless after QUERYABLE” does not authorize knowingly invalid data or unguarded publication.
- Native accepted historical runs sometimes applied per-binding Lossless gates *before* consumer-view creation. Those histories stay unchanged. Future testing may compare provisional downstream results before final gate/promote.
- Every stage records `source/cohort/model versions`, required/observed count, actual SQL/query/receipt hashes, `PASS/FAIL/UNRESOLVED` and scope limits. Never infer PASS from a plan, owner marker or pure Python unit tests.

## 2. Lossless 1–6 — required controls and exact consequences

| Test | Required positive proof | Negative / missing-control behavior |
| --- | --- | --- |
| **Lossless 1 — Record accountability** | Per source and original occurrence: an exactly explainable disposition (`ACCEPTED` / `REJECTED` / `QUARANTINED`); source total = sum of dispositions with exact multiplicity, including headers/framing handled under their declared representation. | Dropped occurrence, unsupported implicit filter or unaccounted status fails. |
| **Lossless 2 — Field accountability** | Every meaningful source field has declared `DIRECT_MAP` / `TRANSFORMED_MAP` / `PRESERVED_NOT_MODELED` (or explicitly governed source exception), full source field/ordinal/provenance reference. | Silent omission, undocumented new field or 50 “missing model features” mislabeled as data errors fails. |
| **Lossless 3 — Value/meaning/structure fidelity** | Unchanged lexical values for direct maps; exact declared functions for transformations; ordered fields, NULL/blank/missing/zero distinction, precision, units/context/time semantics; declared split/merge multiplicity and traceable contributors. | Leading-zero loss, incorrect unit/date interpretation, rounding without rule, `DISTINCT` collapse, fan-out, field drop or changed sign/value are detected by negative fixtures and real comparisons. |
| **Lossless 4 — RAW hash/identity immutability** | SHA-256 of each *consumed* physical original/source member matches admitted manifest/owner scope; paths and source IDs are pinned; remote copies verified where processed. | Wrong identity, path redirection, source/member/record hash mismatch is `FAILED_INTEGRITY`, not retryable semantic repair. |
| **Lossless 5 — Bidirectional lineage and reconstruction** | Exact source-instance/member/record/field/byte locator; parser/rule/model versions; output-to-RAW and RAW-to-outcome links; independent reconstruction/accountability and exact full-schema multiset comparisons. | Orphan target, fateful missing source occurrence, unidentified contributing fields or irreversible unexplained structural change fails. |
| **Lossless 6 — Numeric/economic reconciliation** | Comprehensive numeric-field disposition inventory + all **approved applicable** source-native/exact/transform/tolerance/derived financial controls by correct grain, grouping, units and dates. Mandatory FIN regression for all nested C300 cohorts, plus approved source-family TRY/other controls when applicable. | Missing mandatory economic control **does not** become blanket `NOT_APPLICABLE`. Trigger economic-research branch; unapproved claims remain `PROPOSED`/`NOT_IMPLEMENTED`. Any *in-scope required* economic failure blocks full acceptance; approved scoped source-preserving acceptance must name its limit. |

The nine normative L1–L9 sections of `evaluation_contract.md` map to the original six executable groups. Do not invent a new seventh group or mistakenly equate original Lossless 6 with full enterprise-wide economic correctness.

### 2A. Mandatory financial/economic applicability

1. For every expansion containing original C300: FIN_001 has two fixed filing/period contexts; FIN_002 has one plus deliberately wrong parent-only equity negative control (the negative difference is 1,232,700,000). Check independent expected fixture, exact values/zero tolerance and all relevant source/run/locator lineage in **historical and combined** results; original definitions and pins may be reused after independent readback verification.
2. For new-only sources: inventory actual fields and measure eligibility. If e.g. SEC Daily Master five fields are filing-index metadata with **zero modeled eligible economic measures**, validate the zero-eligibility and FIN noninterference with actual schema/pins. This passes *applicability*, not fabricated numeric reconciliation.
3. Treasury approved source-native TRY controls and 50 owner dispositions must be selected whenever their pinned sources appear. All 155 structural `MISSING` outcomes remain preserved/explicit; an absent six-week rate is not a corrupt value. L6-B cross-feed economic meaning is not thereby approved.
4. Each new numeric field must have a controlled `measure disposition` and a reason. `PRESERVED_NOT_MODELED` retains RAW/source-native reference and must not silently become economic `PASS`.

### 2B. Conditional Economic Test Creation — part of L6

The Cohort lifecycle's E path is mandatory when the population inventory finds economically meaningful fields lacking tests:

`INSPECT SOURCE + BUSINESS CONTEXT → RESEARCH CANDIDATE EQUATION(S) → PRODUCE PRECISE READ-ONLY DATABRICKS SQL + FIXTURES/NEGATIVES → RUN BOUNDED TEST → PRESENT OBSERVED RESULT + BUSINESS MEANING + LIMITATIONS → HUMAN APPROVE / REJECT / DEFER → VERSION RULE + REGISTER FOREVER → RERUN TARGETED L6 AND DEPENDENT CHECKS`.

Rules:
- An autonomous research subagent can propose multiple independent business interpretations and test SQL; it must explain why a consuming business/Agent B might care. It cannot establish canonical economic meaning just because SQL happens to return zero.
- Allow sound relationship candidates (e.g. fixed-cashflow bond price–yield relation *only* with known instrument terms and convention; Treasury bill discount/price/yield under documented dates/denominators). **Principal ≠ price**, and ratios/yields cannot be indiscriminately summed.
- Before approval, candidate SQL is isolated, read-only, exact-pinned and labeled `EXPERIMENTAL_NOT_SEMANTIC_AUTHORITY`. Inadequate independent source context → `UNRESOLVED`, not self-approved.
- After approval, pin the exact SQL, rule version, independent oracle, negative tests, source/field applicability and implementation hash in the permanent registry. Rerun new L6 plus affected A/B2/C, not the full RAW pipeline unless dependency analysis requires it.
- Existing `metadata/operating/validation_registry_v1.json` is only an initial registry. **Registry completeness requires comparing selected tests to the actual frozen schema/source/measure/control inventory**, not trusting optional queue tags alone. A previously approved FIN/TRY rule must be auto-discovered on every eligible future cohort.

## 3. Stability — common structure (all growth runs)

First verify B1 decision, accepted old model, exact approved new source identity and model/rule versions. Then apply A, B2, and the *independent combined* C family.

| Control | Required operational proof | Applies to |
| --- | --- | --- |
| **A — Historical old cohort** | Historical source identity/hashes, original Delta/UC/version references, original lexical/legacy SQL results/FIN/lineage; branch-specific approved changed-field oracle if necessary | Every growth run with prior frozen result |
| **B2 — New only** | N-only distinct membership, all registered binding outcomes, source-native/full-schema Lossless, declared typed/semantic applicability, real queryable readback and negatives | All nonempty increments |
| **C1 — Combined source-preserving** | Exact old∪new membership, disjoint source namespaces, source/binding/record/field coverage, full-schema **bidirectional multiset** old/new/combined comparison, original multiplicity preserved | Every growth run |
| **C2.1 — Identity isolation** | No source-id, binding, run/technical locator collisions or cross-namespace reassignment | All |
| **C2.2 — No unintended merge/split** | Detect false merge, duplicate collapse, accidental fanout, changed cardinality; positive full-population multiset AND bounded intentional negatives | All |
| **C2.3 — Projection compatibility** | Separate historical/new unchanged projections and approved new/corrected projections, exact versions and expected delta | All, branch-specific comparison oracle |
| **C2.4 — Financial noninterference** | FIN fixed fixture and lineage across original and combined scopes; new-only applicability; prevent numeric contamination | Nested C300 cohorts; plus newly approved economic suite |
| **C3.1 — Completion** | Complete/failed/quarantine/blocked receipts reconciled to exact frozen roster and all mandatory candidate stages | All |
| **C3.2 — Historical preservation** | Baseline original artifacts, snapshots, lineage, code/config references and statuses not rewritten; approved changed projections separately versioned | All growth runs |
| **C3.3 — Recovery/idempotency** | Valid checkpoint reuse, no duplicate external write, independent output verification after retry/recovery; retain failed-attempt evidence | All; run actual recovery or bounded negative fixture |
| **C3.4 — Operational budget** | First **fully measured, accepted/frozen cohort** establishes a pinned per-phase performance baseline; after approval of the prospective policy, ≤5× baseline = PASS, >5× and ≤10× = PASS with performance warning, >10× = BLOCKED pending owner decision. Record real stage timing, job limits and missing telemetry. | All stages with valid independently evidenced baseline and comparable phase definitions; unavailable baseline or incomparable work is UNRESOLVED until scope/budget is established. |

**A/B2 PASS does not imply C PASS.** FIN alone does not establish cross-source C2, and source-preserving C PASS does not establish canonical enterprise semantics.

## 4. Branch-specific stability / expected difference oracles

| Path | Test A (old cohort) | Test B2 (new cohort) | Test C1/C2/C3 (combined) | What MUST remain unchanged |
| --- | --- | --- | --- | --- |
| **INITIAL_MODEL** | `NOT_APPLICABLE` — no old processed/frozen baseline | Evaluate whole initial cohort for first Lossless and source-native semantics; label this first-population check, not fabricated incremental B2 | First baseline exact source/field/multiset/accountability, no historical regression claim; C2/C3 applicable initial controls | Admitted original RAW bytes/physical identity |
| **CORPUS_ONLY** | Bit/semantic-equivalent historical projections and FIN; old Delta pinned, **no backfill** | New N under unchanged approved M1/M2, all eligible rows/fields and zero/unmodeled financial scope proven | Disjoint `UNION ALL` composition; exactly old+new occurrences, C2.1–C2.4 and C3.1–C3.4 PASS | All historical queryable values, schema meaning, inputs, IDs and lineage |
| **ADDITIVE** | Compare **legacy projected columns and original query semantics exactly** across M_old vs M_new; *separately* evaluate new typed field on eligible old data and exact approved transformation outcome. New field increases projection; do **not** require entire M_old and M_new rows to be identical. | New N, including parser branches/new fields; exact representation, source context, typed outcomes, edge negatives, full L6 applicability | Old legacy + new legacy remain exact; added field has expected eligibility/null/missing/invalid results and bounded historical backfill; FIN and full C1/C2/C3; historical original M_old remains frozen | Original M_old records, lexical representations, original columns, legacy consumer SQL, fixed financial facts/lineage |
| **CORRECTIVE** | Two simultaneous comparisons: (1) original old frozen output still exists unchanged; (2) corrected old projection matches **approved changed-source/query/field/expected-delta manifest**, and **all unaffected old observations equal exactly**. A true historical correction may intentionally change affected output; old/new global equality is wrong. | New N under approved corrected rule; source-native correctness, old erroneous negative FAIL and corrected positive PASS, independent fixture and required Lossless | Combined C output uses only approved corrected versions on affected keys and intact unchanged paths elsewhere; no double-counting of old+corrected rows; exact approved impact and all C2/C3/FIN noninterference | Original immutable M_old and everything outside approved impact scope |
| **PARSER_EXCEPTION / UNRESOLVED** | Before/after exact source/record/field blast-radius control; no schema-wide/global fallback | Isolate affected bindings; original evidence retained, approved targeted fix with negative mismatch tests; unresolved remains held | Combined source-preserving outputs cannot claim full coverage for a held binding; scope-specific acceptance only | All unaffected source/parser/model outcomes |

For **CORRECTIVE**, the complete acceptance oracle requires `(old source key, old result, corrected result, expected delta, evidence, owner decision, downstream dependencies)` and independently validated affected-versus-unaffected partitions. If a wrong semantic rule is merely *hypothetical*, label it `CONTROLLED_CORRECTION_CANDIDATE`, not a real M2 repair. The two independent Day 5 RAW investigations found **NONE FOUND** for a proven approved M2 error.

For **ADDITIVE**, derive required historical backfill from actual old/new consumers and field dependencies. If frozen CLEAN contains sufficient source evidence, build new versioned typed/semantic projection from that; avoid RAW replay. Do not force historical backfill if no historical consumer requires the new field, but record reason.

## 5. Operational/recovery and standing budget rule

- A technical environment/path/memory/Spark-mode failure gets bounded diagnosis and fix in already authorized scope; record original receipt and error. Successful immutable checkpoints are reused, never silently repeated. Interrupted or uncertain external writes require **remote readback** before deciding whether to resubmit.
- Authorization failure, hash mismatch, forged/revoked grant, protected branch bypass, business-key/economic meaning change and exhausted meaningful grant scope → `FAILED_INTEGRITY` / `NEEDS_HUMAN_DECISION`. No agent may approve its own new semantic rule.
- No artificial wait/time lock or per-day owner step approval. A consolidated owner-signed grant covers exact approved work, but work is still bounded by cancellation, resource/retry/operation limits and a separately protected signing key, Databricks/Git credentials and write ledger. An agent-editable Python guard alone is not a security boundary.
### C3.4 — first frozen cohort baseline, 5× alert, 10× owner gate (proposed generic policy)

**Policy status:** `PROPOSED_PENDING_OWNER_APPROVAL_AND_VERSIONED_INSTALLATION`. This is the owner's newly requested **future generalization**, not an already effective replacement for historical Day 4 [PR #49](https://github.com/lightnino/edp-lab/pull/49) standing approval. Existing `metadata/authorizations/day4_c3_4_budget_approval_v1.json` governs only the explicitly approved comparable N750-like scope until a **new versioned owner-approved policy**, baseline pins and deployment are installed. Historical Day 4 C3.4 remains `BLOCKED`; none of its original assessments is backdated.

1. **Create baseline once per phase:** at the **first accepted/frozen cohort with independently retained, complete, successful performance evidence** for each stage, retain actual observed wall/job time, phase start/end and processing scope. Required phase inventory includes source/RAW resolution or execution, CLEAN materialization, QUERYABLE construction, full verification/validation and result-freeze work **where measured and comparable**, not just one end-to-end total. Distinguish per-stage wall from an end-to-end elapsed clock; overlapping job times are never added together and reported as true elapsed time.
2. **If an initial frozen cohort lacks a usable stage measurement:** record `BASELINE_MISSING_<PHASE>`, **do not invent or backfill timings**. That phase cannot mechanically PASS the 5×/10× rule. Obtain one separately approved bootstrap/reference determination from a later independently measured complete cohort or phase, preserving the true chronology and original evidence; after that, reuse the pinned reference for future eligible workloads. Other stages with valid initial measurements can already be benchmarked.
3. **Before each subsequent run:** check the incoming phase's definition, start/stop measurement method, code/runtime, data volume, source composition and model/backfill/replay scope against its reference. Pin a comparable baseline and any permitted applicability/scaling rule *before* observing this run's outcome. Workloads with materially different phase definitions require a separately established baseline or owner-approved applicability rule; a source count alone does not prove comparability.
4. **Automatic C3.4 decision for each applicable phase, using actual measured elapsed `T` and pinned baseline `B > 0`:**

| Actual phase time | C3.4 decision | Agent / human behavior |
| --- | --- | --- |
| `T ≤ 5 × B` | `PASS` | Record scope, elapsed, baseline and ratio; proceed if other controls pass |
| `5 × B < T ≤ 10 × B` | `PASS_WITH_PERFORMANCE_WARNING` (**technical C3.4 PASS**) | Surface a performance alert for later human inspection and continue; **no hold, mandatory reapproval or retry solely for the warning** |
| `T > 10 × B` | `C3.4_BLOCKED_NEEDS_HUMAN_APPROVAL` | Stop promotion of the affected phase/result pending owner review or revised prospective grant/budget; retain accurate timing and partial outputs |
| No eligible `B`, missing `T`, or non-comparable stage | `BASELINE_OR_MEASUREMENT_UNRESOLVED` | Do not claim technical C3.4 PASS; obtain reference/measurement or explicit scoped acceptance |

5. **Bounds are not authorizations:** the 10× C3.4 acceptance envelope never overrides an independent earlier signed-grant budget, actual Databricks job timeout, quota or security limit. The agent must respect whichever narrower execution restriction applies. Crossing >5× is an **alert only**, not a scheduled approval requirement; crossing >10× requires an owner decision and is not automatically a human override.
6. **Keep provenance and sustainability evidence:** report wall and job times, work volumes, throughput, checkpoint reuse, source mix, CPU/DBU/$ where actually measured, operating overhead and human interventions. Missing costs/CPU are `UNAVAILABLE`, not zero or evidence of efficiency. An applicable elapsed-time PASS does not assert absent resource metrics passed.

**Baseline semantics:** “first cohort” means the first **actually accepted/frozen cohort whose particular phase was completely measured and can serve as a trustworthy reference**, not a hard-coded Day 2/Day 4 label or automatically the most favorable sample. Record an original first frozen cohort with absent timing as a gap; never relabel its missing evidence as a benchmark. This new general rule requires explicit owner adoption and runtime wiring before autonomous enforcement.
- Record complete actual wall time, configured hard timeout, phase throughput, missing DBU/CPU/cost metrics as `UNAVAILABLE`, not zero; report human steering, intervention, approvals and operating overhead separately.

## 6. Databricks Result Freeze — actual executable operation plan

There are **two separate freezes**: input cohort membership freeze after admission and **output/result freeze only after validation**. A Git-only “frozen” JSON is not proof of Databricks result preservation.

| Step | Action / actual evidence | Exit |
| --- | --- | --- |
| F0. Verify old frozen result | Check old population, RAW source/hash, referenced model/schema/rules, SQL fingerprints, actual Delta/UC object IDs, original readable version pins, table property state | `OLD_FREEZE_VERIFIED` |
| F1. Verify new Delta source outputs | Read new physical table catalog and Delta history; pin exact table UUID/version/snapshot, rows, fields, binding outcomes and source lineage | `NEW_SNAPSHOTS_VERIFIED` |
| F2. Protection/retention | Verify and, when explicitly authorized, set approved append-only/table metadata and effective predictive-optimization/retention properties; independently re-read old **data** snapshots to ensure no data change | `DELTA_PROTECTION_VERIFIED` |
| F3. Publish candidate final view | Publish a **new**, uniquely named source-preserving zero-copy QUERYABLE/Result view referencing pinned approved physical snapshots where the platform supports syntax; verify view definition hash and UC object identity; no overwrite | `VERSIONED_VIEW_PUBLISHED` |
| F4. Live Databricks checks | Query exact old/new/combined physical source counts, bindings, occurrence/multiset/lineage, transformation outcomes and applicable FIN/TRY/stability, against actual pinned inputs; independently compare to expected fixtures | `LIVE_RESULT_EVALUATED` |
| F5. Retain native operation receipts | Retain real API/SQL statement IDs, response SHA, table UUIDs, Delta history/version pins, protected path, SQL text SHA, result view ID and exact run execution references | `FREEZE_RECEIPTS_RECORDED` |
| F6. Independently verify and attest | A trusted separate verifier reviews remote live readback and evidence bytes, produces independently protected/signed receipt without requiring human to sign *each* read; signed receipt must be tied to actual remote artifacts, not just self-asserted `VERIFIED` strings | `DATABRICKS_RESULT_FROZEN` |
| F7. Post-freeze repo closeout | Versioned references/marker, actual PR changes, tests/Ruff, required CI, merge and verify main SHA; original frozen data/metadata untouched | `FINAL_DELIVERY_VERIFIED` |

The Day 4 PR #50 implementation is the precedent: `workspace.edp_lab.o_c1500_m2_result_frozen_v1`, version-0 sources, zero-copy, **68 real SQL receipts**, 1,500 physical sources/1,932 bindings/319,151,239 occurrences; 12,793 VALID and 155 structural MISSING Treasury evaluations. It does **not** prove future arbitrary SQL syntax or indefinite snapshot retention.

Finite 90-day log/data retention and append-only are *not* WORM, disaster recovery, guaranteed long-term replay, or control over a privileged workspace administrator. This personal lab does not require a duplicated full materialization or separate backup for these acceptance claims. Record maintenance/review horizon and real limitations.

## 7. Git and autonomous final exit

Proposed future execution lifecycle:

1. Before edits: inspect upstream main/worktree, create an isolated feature branch/worktree. No unrelated Codex session edits to that worktree.
2. During planning/development: local deterministic tests and exact config/statement code pins, approved patch scope, staged changes and status trace.
3. After live result freeze: produce versioned evidence references; check accepted scope, no red/unresolved required validations, no prohibited merge/override.
4. Push under guarded Git adapter, create PR, wait for required CI, collect and verify actual commit SHA/checks/owner requirements, merge only if the independent required gates are satisfied.
5. Verify actual merge commit on `main` and matching result-freeze artifact pins; report human approvals, steering and resumed/failed attempts.

**The PR #51 generic runner does not yet implement this entire DAG.** Its `freeze_verify` final-task restriction and limited Databricks/Git adapters must be extended in a later implementation PR. Signed grants, protected credential holder, automatically generated trusted external readback and true C2000 live evidence must exist before reporting `AUTONOMOUS_END_TO_END_PASS`. A standalone Codex terminal finishing manually directed tasks does not, by itself, establish runtime-autonomous execution.

## 8. Exit statuses and scope truthfulness

Report separately: `COHORT_INTEGRITY`, `PARSER_MODEL_VERSION`, `DATA_PROCESSING`, `LOSSLESS_1_6`, `STABILITY_A`, `STABILITY_B2`, `STABILITY_C1`, `STABILITY_C2`, `STABILITY_C3`, `ECONOMIC_SEMANTICS`, `OPERATING_EVIDENCE`, `LIVE_RESULT_FREEZE`, `GIT_MERGE`, `AUTONOMY_TRACE`.

- A `PASS` only attests its tested scope. `NOT_APPLICABLE` requires demonstrated lack of applicable measure/control. `NOT_IMPLEMENTED` is not a PASS. `BLOCKED` is not a repair instruction by itself.
- A known approved owner **scoped exception** may permit `PARTIAL_ACCEPTED_WITH_EXCEPTIONS` for a well-defined source-preserving result, but never retroactively claims an unexecuted historical test passed.
- `DATABRICKS_RESULT_FROZEN` requires retained verified live remote evidence, distinct from a Git-only owner approval marker.
- `AUTONOMOUS_END_TO_END_PASS` also requires an actual end-to-end authorized run with a durable trace and independently observed frozen output and merged PR.
- No history is rewritten by this specification or future acceptance rule enhancements.

**Proposal only: no actual cohort processing, control execution, table/view changes, receipt signatures, freeze operations, or Git result merge are authorized by this text.**
