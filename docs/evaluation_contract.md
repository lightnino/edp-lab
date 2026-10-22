# Evaluation Contract

**Status:** Specification / acceptance contract. A documented requirement is not evidence that its implementation or test already exists.

**Purpose:** Evaluate whether source information is faithfully preserved through integration (**LOSSLESS**) and whether the integrated representation remains correct as both the source population and model evolve (**STABILITY**). Preserve fixed experimental evidence as cohorts grow (**CUMULATIVE SCALE / EXPERIMENTAL INTEGRITY**).

**Scope:** Admitted RAW source instances; RAW → CLEAN / integrated transformation; dependent QUERYABLE outputs; new-source onboarding; controlled model/code/mapping evolution. This contract does **not** authorize automatic business-key selection, entity merges, equivalence judgments, or canonical mappings.

**Terms:** `C300` = frozen cohort of 300 admitted source instances; `N450` = 450 additional source instances; `C750 = C300 ∪ N450`. `M1` and `M2` are identifiable versions of the relevant model and transformation rules. `O_C300_M1` is the preserved result of the indicated cohort/model combination. Counts are illustrative planned cohort sizes, not claims about existing datasets or test execution.

## 1. Evaluation Boundary — Two Distinct Questions

| Evaluation | Question | Does not establish by itself |
|---|---|---|
| **LOSSLESS** | For a fixed source corpus and declared model/rules, did RAW → CLEAN preserve and account for source values, occurrences, meaning and origin, faithfully executing the declared rules? | That the declared entity-resolution or relationship rules are correct about reality |
| **STABILITY** | When sources or models change, does the previously accepted representation remain justified and does the combined corpus stay semantically coherent? | That every transformation was faithfully implemented unless the required Lossless tests also pass |
| **EXPERIMENTAL INTEGRITY** | Are input cohorts, source identities, hashes, ground truth and previous run results frozen rather than rewritten during evaluation? | Business correctness by itself |

**Example — overlapping observations:** Two source records appear to describe the same event. Ground truth indicates they are distinct. An accepted rule mistakenly says `DUPLICATE`; the pipeline executes the declared `2 → 1` operation while preserving both RAW inputs and complete lineage. The *execution fidelity* check can pass against the declared rule, but the *semantic correctness* of the rule fails in Stability Test C. Some broader Lossless semantic or reconciliation controls may also detect the consequence; the checks are not logically mutually exclusive. Conversely, a correct `NON_DUPLICATE` rule executed through a silent `SELECT DISTINCT` fails Lossless even if the intended business rule was correct.

## 2. LOSSLESS — Normative Requirements L1–L9

**Invariant:** RAW → CLEAN / integrated must not silently lose a source record or meaningful attribute, distort a value or its meaning, change record/field structure, lose lineage, or break a declared reconciliation. **Lossless is not `RAW row count = CLEAN row count`:** one-to-many / many-to-one transformations can be valid when explicitly defined and traceable.

### L1 — Record Accountability

Every **source-record occurrence** has exactly one recorded admission outcome: `ACCEPTED`, `REJECTED`, or `QUARANTINED`. `REJECTED` requires a verified invalidity rule; `QUARANTINED` means the evidence is insufficient to integrate safely. All three outcomes retain original RAW evidence. No `DISAPPEARED` status.

- **Control:** `raw occurrences = accepted + rejected + quarantined` at the recorded source-instance scope; verify per-record outcomes, not just totals.
- **Evidence:** source instance/record locator, admission status, reason/rule, responsible run, and downstream targets where accepted.

### L2 — Attribute Accountability

For each meaningful attribute of every **ACCEPTED** record, record one and only one primary disposition:

| Disposition | Meaning | Required evidence |
|---|---|---|
| `DIRECT_MAP` | Same declared business meaning and value, possibly renamed | Source field, target field, mapping version; no undeclared conversion |
| `TRANSFORMED_MAP` | Declared conversion/split/merge produces the mapped result | All contributing raw values/context, target(s), rule and version |
| `PRESERVED_NOT_MODELED` | Not promoted into CLEAN, but retained in immutable RAW | Original field reference, exclusion rationale, preservation reference |

**Control:** `meaningful accepted attributes = explicitly accounted-for attributes`. Excluding from CLEAN does not delete from the project. Unknown fields cannot silently disappear from the field inventory.

### L3 — Reconciliation

Every relevant numeric/economic field has an explicit **reconciliation disposition**; not every numeric value is additive and no universal sum-check applies to all fields.

| Disposition | Intended check |
|---|---|
| `RECONCILE_EXACT` | Conserved measure with zero declared tolerance |
| `RECONCILE_WITH_TRANSFORM` | Expected value after documented unit/scale/conversion |
| `RECONCILE_WITH_TOLERANCE` | Comparison under explicitly justified tolerance |
| `DERIVED_RECOMPUTE` | Recalculate derived measure from its components |
| `NON_ADDITIVE_NOT_SUMMABLE` | Preserve a documented non-additive treatment; do not sum blindly |
| `PRESERVED_NOT_MODELED` | Retained in source, not promoted as an integrated measure |

**Required control inventory:** original field and unit, business meaning, eligibility to reconcile, grain, group-by dimensions, time basis, conversion rule/version, tolerance, expected equation, observed result, and exception status. Compare compatible populations only. A price, ratio or portfolio weight cannot be reconciled by an indiscriminate SUM.

### L4 — Provenance

Every integrated output/value must identify **the contributing source evidence**, including multiple contributing records/fields where appropriate: `source_instance_id`, RAW file/snapshot and record locator, original value/context, and relevant run/mapping references. Table-level source attribution alone is insufficient to explain a particular output value.

### L5 — Reproducibility

Given the same admitted RAW snapshot, model/transformation/code versions, dependencies and relevant configuration, the defined result must be reproducible. Capture or normalize non-deterministic operational fields (e.g. processing timestamps) when comparing outputs. Record input fingerprints, run identifiers, version set, and comparison result.

### L6 — RAW Immutability

For each admitted source instance, preserve `source_instance_id`, original RAW bytes, `raw_path`, filename, and SHA-256. Verify:

```text
SHA256(current_admitted_RAW) == SHA256(recorded_source_instance)
```

No in-place correction or silent replacement of the admitted RAW. Audited storage relocation may change a physical location reference only through an explicit relocation record; source identity and bytes remain unchanged.

### L7 — No Silent Distortion / Value Fidelity

For each accepted/modeled target:

```text
target_value(s) = declared_transform(source_value(s), source_context)
```

For a `DIRECT_MAP`, the declared transformation is identity. For a `TRANSFORMED_MAP`, retain source field/value, source context, rule, rule version, target field/value and unit. Protect **leading zeros, NULL vs 0/empty/missing, data type, scale/unit, precision/rounding, enum meaning, identifier namespace, effective/report/filing dates and time semantics**. Source representation may change; source information and meaning may not change **silently**.

**Structural fidelity is included:** `1 field → N`, `N fields → 1`, `1 record → N`, and `N records → 1` require declared rules plus complete contribution/target lineage. Accidental join fan-out and undeclared split/merge are failures.

### L8 — Multiplicity Fidelity

Do not silently collapse repeated source occurrences because their visible fields are equal. Intentional deduplication requires external/business evidence appropriate to the declared rule, original occurrence count, rule/version, and all source-to-result relationships. The system must distinguish **two equal-looking legitimate observations** from **two records representing one event**; deciding which is which belongs to semantic/model validation, not automatic `DISTINCT`.

### L9 — Reconstructability / Information Accountability

- **Backward:** `CLEAN → exact contributing RAW record(s)/field(s)/values + transformation + version`.
- **Forward:** `RAW → ACCEPTED/REJECTED/QUARANTINED → DIRECT_MAP/TRANSFORMED_MAP/PRESERVED_NOT_MODELED → relevant targets`.
- **Reconstruction:** Where declared, integrated representation plus lineage recovers the required source representation. Where byte-exact reconstruction is not defined or practical, every meaningful source detail still has a recorded disposition and the immutable original remains retrievable.

`EXCLUDED_FROM_CLEAN ≠ DELETED_FROM_PROJECT`.

### 2.1 Executable Lossless 1–6 — The Original Test Grouping

**L1–L9 are requirement clauses, not nine unrelated execution gates.** The six required *test families* from the original learning framework are:

| Test | Name | Contract clauses | Core test |
|---|---|---|---|
| **Lossless 1** | Record accountability | L1, L8 | Every source occurrence has an explicit outcome; no silent drop/collapse |
| **Lossless 2** | Field accountability | L2, L9 | Every meaningful accepted field has a declared disposition |
| **Lossless 3** | Value fidelity | L7, L8 | Values, meaning, representation and structure follow declared transformations |
| **Lossless 4** | RAW/hash immutability | L6 | Admitted artifact hash matches frozen manifest |
| **Lossless 5** | Lineage + reconstructability/accountability | L4, L5, L9 | Bidirectional attribution and declared reconstruction, with version evidence |
| **Lossless 6** | Numeric/economic reconciliation | L3 | All applicable measures have documented grain-aware control dispositions and pass relevant equations |

`L5 — Reproducibility` is also a cross-cutting requirement: a passing run must be reproducible under its declared versioned inputs; it is not a seventh original Lossless test family. Likewise, multiplicity protection is enforced within the original record/value fidelity families rather than being invented as a separate seventh family.

**Scope rule:** Whenever a candidate model/corpus requires revalidation, apply the same applicable Lossless 1–6 to the **old scope**, **new scope**, and **combined scope**, as specified by the replay/validation decision below. A pass on separate cohorts does not imply the combined corpus passes.

### 2.2 Mandatory Lossless 6 financial regression suite — FIN V2

**Current evaluation requirement, effective after the Day 2 FIN_EVAL_V1 closeout:** FIN_001_V1 (two filing/date contexts) and FIN_002_V1 (one filing/date context, including the wrong-equity negative control) are permanent, mandatory **Lossless 6** regression cases for any candidate corpus containing the frozen C300. This includes C750 and every later nested cohort. They are not optional examples or merely a historical annotation. The pinned SQL, expected fixture, source/run/snapshot scope and evaluation evidence remain `metadata/evaluations/fin_eval_v1.json` and `sql/reconciliation/fin_eval_v1/`. This changes the **evaluation-suite version**, not the M1 lexical data/model version.

The versioned application contract is `metadata/evaluations/lossless6_fin_suite_v2.json`. For each expansion:

- **A / old C300:** execute or verify the three FIN cases on the original pinned Day 2 snapshots; independently require exact expected values, zero tolerance, negative-control detection and unchanged lineage.
- **B2 / new-only sources:** execute a **Lossless 6 measure-applicability and noninterference check** against the actual newly admitted structures. Inventory economic measures and declared reconciliation rules; fail if an applicable measure is silently omitted. Where new sources are filing-index-only, verify that zero modeled economic measures are eligible and that their identifiers cannot accidentally enter FIN equations. Report this check as `PASS` **only with verified zero-eligible-measure evidence**; this means applicability/noninterference PASS, **not** an invented numeric-equation PASS for the new sources.
- **C / combined corpus:** execute FIN_001/002 on the actual combined candidate and original C300, compare the three numeric results and their source/run/locator/lineage witnesses in both directions, and require zero difference. A positive result is `PASS` for the **fixed FIN regression suite**, separate from the coverage of other economic measures.
- Every wider economic field requires a declared grain/unit/date/metric control under L3 or an honest `PRESERVED_NOT_MODELED` disposition. The three FIN cases do not prove enterprise-wide financial reconciliation.

This FIN V2 rule **supersedes older applicability-only presentation of Lossless 6 in current/future scorecards**, but never mutates historical Day 2 execution results, previously signed evidence, or their SHA-256 references. Do not label the **mandatory FIN suite** `NOT_APPLICABLE` merely because a new cohort contributes no modeled economic measure; instead report its applicability and noninterference checks explicitly. Do not fabricate a numerical reconciliation or a `PASS` before the required checks execute.

Cross-source Stability C2 and operational Stability C3 remain **separate** from Lossless 6. Within M1's source-preserving scope, start with the bounded C2 regression controls of source-ID disjointness, no implicit merge/deduplication and C300-vs-combined FIN value/lineage invariance. Do not infer enterprise entity equivalence without declared rules. C3 requires real execution/recovery measurements and explicit acceptance thresholds; FIN_001/002 alone cannot establish operational acceptance.


## 3. STABILITY — Normative Requirements S1–S9

**Invariant:** Growth in the admitted source population or model evolution must not silently destroy accepted identities, semantics, relationships, outputs or consumer contracts. New evidence can justify correcting a wrong previous abstraction. Stability does **not** mean M1 or its output is permanently correct or unchangeable.

**Two axes:** (1) *Corpus expansion* — `C300 → C750 → ...`; (2) *Model evolution* — `M1 → M2 → ...` **only when required**.

### S1 — Identity Stability
Previously accepted enterprise identities may not silently merge, split, change meaning or be reassigned. Corrections require evidence, versioning and affected-scope review.

### S2 — Semantic Stability
Meaning of previously accepted fields, relationships, grain, units, dates and business rules must not silently change. Changed semantics require explicit versioned contracts and downstream evaluation.

### S3 — Mapping Stability
Previously accepted mappings remain valid within their declared scope unless explicitly corrected/superseded. Preserve old mappings and evidence, including effective-time assumptions.

### S4 — Query Compatibility
Existing queries must continue to run **and mean the same thing** where backward compatibility is promised; otherwise identify, document and approve the breaking consumer change. Mere successful SQL execution is insufficient.

### S5 — Test Compatibility
Previously accepted tests for unaffected behaviors must still pass. Where a deliberate correction changes expected results, preserve the old test/ground-truth evidence and version new expectations; do not silently rewrite the frozen benchmark.

### S6 — Additive Extension
Prefer fitting the existing representation, then additive extension, before redesign. Do not protect a demonstrably wrong identity or business abstraction simply to avoid a version change.

### S7 — Explicit Model Evolution
Preserve M1/model/code/mappings/outputs and evidence; identify defect and blast radius; create justified M2; replay/backfill **the affected historical scope where required**; rebuild dependent CLEAN/QUERYABLE results; compare and classify differences; validate old, new and combined scopes before promotion.

### S8 — Historical-Version Preservation

```text
C300 + M1 → O_C300_M1   [historical processing truth]
C300 + M2 → O_C300_M2   [candidate/corrected representation]
```

Keep both outputs with their model/code/transform versions, raw fingerprints and tests. A corrected current interpretation does not erase how prior versions actually processed the evidence.

### S9 — Regression Accountability
Compare historical outputs only at comparable grain, time and contract scope. Preserve old/new model versions, old/new result references, expected/actual differences, reason, blast radius, review and approval. Every material change must have a disposition; merely assigning a category is not automatic approval.

**Change classifications** (the full studied taxonomy):

| Classification | Expected behavior |
|---|---|
| `UNCHANGED` | Protected historical behavior/output identical |
| `EXPECTED_COMPATIBLE_EXTENSION` | New fields/sources/features; old contracted outputs remain equivalent |
| `BUG_FIX` | Deliberately correct faulty code/transformation logic; affected values may change |
| `DATA_CORRECTION` | Repair erroneous, missing or misattributed historical source/event data; corrected outcomes may differ |
| `OLD_ABSTRACTION_WRONG` | Replace no-longer-valid/inadequate business modeling assumption; compare impacted outcomes against corrected expectations |
| `COMPATIBLE_INFRASTRUCTURE_MIGRATION` | Physical storage/routing changes; same logical state at the same comparison time |
| `BREAKING_CHANGE` | Intentional change to schema/interface/semantic contract, with explicit consumer migration and approval |
| `KNOWN_COMPATIBILITY_LIMITATION` | Known gap in legacy-to-new behavior, bounded and declared; acceptability is use-case dependent |
| `UNEXPLAINED_REGRESSION` | Unexpected/unjustified change; blocks promotion |

### 3.1 Replay Is Conditional, and Replay Is Not Validation

| Change | Historical RAW replay? | Expected old-output comparison |
|---|---|---|
| **Keep M1** — N450 fits M1 | **No** merely because N450 arrived; reuse validated old CLEAN/results | Old results unchanged; verify validity within C750 |
| **Additive M2** | **Only if** old historical coverage/derived structures require backfill or reprocessing | Existing contracted fields equivalent; newly added fields may appear |
| **Corrective M2** | **Yes for affected scope**, after blast-radius determination; rebuild affected CLEAN and dependent QUERYABLE | Unaffected outputs unchanged; affected outputs equal declared corrected expectations |

If the defect is only in an analytical mart, rebuild affected QUERYABLE outputs; if the RAW→CLEAN logic is wrong, replay affected RAW and downstream dependencies; if foundational identity is wrong, the affected historical scope can extend throughout the identity domain. If RAW itself is corrupted or unavailable, re-ingestion may be necessary rather than replay of retained RAW.

**Replay** produces candidate corrected data. **Validation** checks Lossless and semantic/system correctness. One never substitutes for the other.

## 4. CUMULATIVE SCALE / EXPERIMENTAL INTEGRITY — SC1–SC7

### SC1 — Frozen Nested Cohorts

```text
C300 ⊂ C750 ⊂ C1500 ⊂ C2000 ⊂ C3000
C750 = C300 ∪ N450
```

Every larger cohort retains all prior admitted source instances; record the exact membership/version.

### SC2 — No Cohort Replacement
Do not remove, swap, silently regenerate or replace difficult earlier sources when expanding the corpus. An alternative experimental cohort needs a distinct version/name; it cannot retroactively redefine a frozen cohort.

### SC3 — Stable Source Identity
An admitted `source_instance_id` stays bound to that exact admitted source instance. A later changed delivery is a new instance, not an overwrite with the same ID.

### SC4 — Cross-Cohort RAW Immutability

```text
SHA_C300(source_001) = SHA_C750(source_001) = SHA_C1500(source_001) = ...
```

Any unexplained mismatch is a frozen-input contract failure.

### SC5 — Frozen Ground Truth
Controlled-case truth is fixed **before** viewing model/agent outcomes. No post-hoc relabeling to improve performance; a demonstrable label error is corrected in a separately versioned benchmark, preserving the original.

### SC6 — Historical Runs and Outputs Remain Available
Preserve model versions, mappings, run configurations, output artifacts, test results and agent results. Do not overwrite `O_C300_M1` with M2 results or retcon historical evaluations.

### SC7 — New-Source Onboarding Outcome
Every new source receives exactly one explicit assessed outcome (with unresolved/rejected cases not silently promoted):

| Outcome | Decision |
|---|---|
| `FITS_EXISTING_MODEL` | Keep M1; process N450 and validate combined result |
| `ADDITIVE_EXTENSION_REQUIRED` | Version compatible M2 extension; backfill old only where necessary |
| `REVEALS_OLD_MODEL_DEFECT` | Correct M2; replay affected historical RAW; rebuild dependencies; regression-check |
| `SOURCE_INCONSISTENT` | Investigate with retained raw evidence; reject/quarantine where justified; M2 not automatically needed |
| `HUMAN_UNRESOLVED` | Hold semantic admission for human judgment; do not guess entity equivalence |

## 5. STABILITY EVALUATION — Frozen Contract + Tests A/B/C

**The S1–S9 principles are evaluated through the following actual test structure, not through nine independent, interchangeable checks.**

### Pre-check — SC1–SC6

Freeze cohort membership, source IDs, raw hashes, ground truth, mappings, code/model versions and historical `O_C300_M1`. If the baseline is not frozen, later comparison is invalid.

### Test B1 — Determine the New Cohort's Model Fit

Assess `N450` relative to M1, using schemas, identifier namespaces, relationships, business meaning, units and time. Classify under SC7. This **decision stage** selects whether M1 stays, compatible M2 is created, corrective M2 is required, or human/source review blocks admission. It does **not** constitute the final new-cohort pass.

### Test A — Old Cohort Regression (`C300` fixed)

| Check | Pass condition |
|---|---|
| **A1 — Lossless 1–6** | Required for the C300 scope under a new M2; existing verified M1 outputs may be reused when M1 is unchanged and no replay is warranted |
| **A2 — Regression** | Compare old/new identities, mappings, semantics, query outputs and accepted tests at comparable scope |
| **A3 — Blast radius** | Differences confined to affected scope; unaffected outputs unchanged |
| **A4 — Classification** | Every material difference evidenced, classified, versioned and dispositioned |

**Order for corrective M2:** determine defect → blast radius → preserve M1 outputs → **replay affected C300 RAW under M2** → **rebuild dependent CLEAN/QUERYABLE** → perform A1–A4. Do not perform the old/new regression against stale, unreconstructed downstream outputs.

- M1 unchanged: no compulsory historical replay; check that old verified outputs remain valid in the combined result.
- Additive M2: compare old fields/contracts for equivalence; backfill only if needed.
- Corrective M2: unaffected old outputs remain equivalent; affected old outputs must match the **expected correction**, not the incorrect M1 result.

### Test B2 — Validate the New Cohort (`N450` under chosen M1/M2)

| Check | Pass condition |
|---|---|
| **B2.1 — Lossless 1–6** | Records, fields, values/structures, raw hashes, lineage and numeric controls pass |
| **B2.2 — Identity / mapping** | Entities/relationships supported by evidence; no invented equivalence |
| **B2.3 — Semantics** | Units, grains, periods, dates and definitions interpreted correctly |
| **B2.4 — Resolution** | Required model changes reviewed; critical source conflicts and human-judgment cases resolved or explicitly withheld from semantic promotion |

New-cohort evaluation may discover a defect that triggers a return to Test A, as in the corrective M2 path. Tests A/B can be iterated; their labels describe **scope**, not a mandatory chronological sequence.

### Test C — Full Combined Corpus (`C750` under chosen M1/M2)

**A and B passing separately never implies C passes.** Validate C750 as an integrated system; reuse previously verified old CLEAN data when allowed — a combined test does not always require full RAW replay.

| Check | Coverage |
|---|---|
| **C1 — Combined Lossless 1–6** | Rerun applicable six tests across old + new, including all-input lineage and declared numeric/economic reconciliation |
| **C2 — Cross-source integration integrity** | Cross-source identity collisions; false merges/splits; overlapping/duplicate observations; referential integrity; relationship cardinality; consistent grain, units, semantics, temporal interpretation; model-version coherence; old-cohort interactions; query/test compatibility |
| **C3 — Operational evaluation** | Runtime/throughput/resources; human-review volume; mappings changed/model churn; historical replay/backfill and downstream rebuild cost, against declared thresholds |

Example: C300 has `NASDAQ:ABC`, N450 has `NYSE:ABC`; both pass individual Lossless checks. A combined join merges the entities solely because ticker text equals `ABC`. **C2 fails** unless independent evidence actually establishes equivalence.

### 5.1 Permanent M1 source-preserving C2/C3 minimum — STABILITY_M1_V1

For M1 with **no approved canonical entity/enterprise semantic integration**, the permanent cross-cohort acceptance is the versioned **C2.1–C2.4** and **C3.1–C3.4** in `metadata/evaluations/stability_m1_v1.json`. Apply to C750 and later nested cohorts, retaining the previous frozen cohort as a historical regression baseline. These checks do **not** narrow or replace the broader enterprise semantic obligations of C2 when a business-semantic model and its rules are introduced.

- **C2.1 Identity isolation:** previous/new source-instance namespaces disjoint; identities, binding-to-source mappings and RAW hashes immutable; no namespace collision.
- **C2.2 No false merge/split:** combined CLEAN/QUERYABLE preserve full source/locator-aware **multisets**, including cross-source equal-looking values and intra-source repeats; one deliberate collision/deduplication-negative-control test must fail when source identity or occurrence is dropped. The synthetic negative control supplements, but does not substitute for, actual-C750 binding/record/field multiset comparisons.
- **C2.3 Historical projection:** projecting combined output onto the exact old binding/run/source population yields the frozen historical multiset, including original lineage and source locators; zero differences in **both** directions. Prove the added cohort is exact too.
- **C2.4 FIN noninterference:** run mandatory `FIN_001_V1` (2 contexts) and `FIN_002_V1` (1 context plus negative control) on frozen historical and combined candidate; require identical expected amounts, zero-tolerance equations and historical lineage witnesses. Reuse immutable `LOSSLESS_6_FIN_SUITE_V2`; this is an **additional cross-cohort regression assertion**, not a replacement for Lossless 6.
- **C3.1 Completion:** all eligible new bindings have exactly one verified terminal COMPLETE outcome with no missing/extra checkpoint.
- **C3.2 Historical preservation:** no unnecessary replay/rewrite of previously frozen processing, tables or version-pinned historical query results; any justified replay needs a separately approved change and blast radius.
- **C3.3 Recovery/idempotency:** interrupted runs reuse verified checkpoints; failed publication attempts do not create duplicate tables/records, while successful outputs have exact readback.
- **C3.4 Operational acceptance:** record measured stage wall times, source/data throughput, available CPU/resource/cost telemetry, human-review and retry volume; explicitly inventory absent provider metrics. Check completion and runtime against **versioned, owner-accepted phase budget(s)** or configured hard time limits; do not manufacture a threshold after observing a result. No unsupported blanket CPU/DBU/cost PASS.
  
**Status convention:** `C2_M1_SOURCE_PRESERVING_PASS` or `C3_M1_OPERATIONAL_PASS` may be reported only after their respective evidence-backed checks complete. `C_M1_SOURCE_PRESERVING_PASS` requires A, B2, combined Lossless 1–6, C2.1–C2.4 and C3.1–C3.4 to pass within declared scope. It is **not** `C_ENTERPRISE_SEMANTICS_PASS`. Retain immutable historical Step 4 V1 evidence; publish a separate V2 evaluation with new fingerprints and links, never rewrite signed old results. Step 5A may supply the performance/budget acceptance evidence before C3.4 is final.


## 6. Promotion and Result Reporting

| Scenario | Promotion condition |
|---|---|
| **Continue M1** | Frozen SC1–SC6 + required A/B/C pass; C750 validated under M1; no old replay solely because cohort grew |
| **Promote additive M2** | Frozen inputs + compatible old-output validation + N450 and C750 pass + required historical backfill completed |
| **Promote corrective M2** | Frozen inputs + documented defect/blast radius + affected historical RAW replay and dependent rebuild + classified approved M1/M2 differences + A/B/C pass |
| **Block / hold** | Critical semantic uncertainty, unexplained regression, failed Lossless/cross-source controls, undeclared incompatible version mixing, unapproved changes or unacceptable operational thresholds |

**Test status:** `PASS`, `FAIL`, `BLOCKED/HUMAN_UNRESOLVED`, `NOT_IMPLEMENTED`, or `NOT_APPLICABLE` with a documented reason. Never report a missing test as passed. A quarantined source's raw-accountability checks can pass while its semantic admission remains blocked.

**Minimum evaluation evidence:** source/cohort manifest and hashes; model/code/mapping versions; recorded record/field outcomes; applicable numeric-control inventory; lineage references; preserved old/new outputs; difference classification/approval; Test A/B/C results; decision to promote, hold or reject. Keep failures and historical outputs; do not overwrite evidence to make a later run appear more successful.

**Implementation boundary:** This contract describes required behavior and validation structure. As of its creation, only repository/environment smoke checks and the RAW hash verification already executed have been demonstrated; the semantic integration model, cohort experiments, Lossless 1–6, and Stability A/B/C still require implementation and must not be recorded as PASS.
