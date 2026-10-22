# C750 Stability V2 supplemental evaluation

Result: **PASS — `C_M1_SOURCE_PRESERVING_PASS`** under
`LOSSLESS_6_FIN_SUITE_V2` and `STABILITY_M1_V1`.
`C_ENTERPRISE_SEMANTICS_PASS` is **not established**; enterprise semantic controls
remain NOT_IMPLEMENTED. This is M1 source-preserving acceptance, not entity
integration, a performance SLA, a result freeze or permission for Step 5.

Authority: [V2 runbook](c750_stability_v2_runbook.md),
[evaluation contract](evaluation_contract.md),
[FIN V2](../metadata/evaluations/lossless6_fin_suite_v2.json) and
[M1 stability minimum](../metadata/evaluations/stability_m1_v1.json).
The evaluation started from main revision `c50173e68be8adc95e3409b3516690742306fa7b`.

## Separate results

| Evaluation | Result | Population and basis |
| --- | --- | --- |
| A — historical regression | PASS | 300 sources / 732 bindings; verified frozen M1/RAW/identity evidence, unchanged live definitions and snapshots, exact mandatory historical FIN results |
| B2 — new-source Lossless | PASS | 450 bindings / 1,899,705 DATA records / 9,498,525 fields; full independent native Lossless 1–5 reused; complete new FIN V2 applicability/noninterference audit PASS |
| C1 — combined Lossless | PASS | 750 identities / 1,182 bindings / 316,063,821 DATA records / 3,586,787,936 fields; 108/108 full-schema native multiset receipts reused, with mandatory FIN V2 PASS |
| C2 — M1 cross-source stability | PASS | All C2.1–C2.4 source/locator-aware controls and required negative controls pass; detailed scope below |
| C3 — operational acceptance | PASS | All C3.1–C3.4 completion, preservation, recovery and pre-existing hard-timeout checks pass; unavailable optional telemetry is explicit |
| Overall M1 source-preserving stability | PASS | Every required A/B2/C1/C2/C3/FIN V2 condition verified; not inferred from cohort counts or FIN alone |

Historical [V1 evaluation](c750_stability_evaluation.md), its BLOCKED outcome,
old applicability presentation and all frozen Day 2 evidence remain byte-identical.
V2 adds the required checks under explicitly versioned current acceptance rules;
it does not retroactively change V1, M1 or the original data.

## Reused evidence and current pins

Reused: frozen A and Day 2 gates; native N450 450/450 independent readback;
108 combined full-schema record/field/coverage multiset receipts; actual historical
and combined FIN SQL outputs and 13 lineage witnesses; original execution reports,
failed attempts, COMPLETE receipts, configured submissions and version-0 readbacks.
Their indexed hashes and exact binding populations were verified, not reprocessed.

Fresh read-only checks confirm:

- All three historical and three C750 consumer definitions are unchanged.
- All six original Delta/Unity Catalog table identities are unchanged. Consumer
  reads remain at version 0; C300's latest version 1 is its pre-existing retention
  metadata, while both N450 tables remain latest version 0 with one CREATE TABLE
  AS SELECT operation.
- Deployed archive, contract, installed owner record and host-module bytes match
  all four retained hashes. No deployment or authorization change was performed.
- Five successful retained runs and five failed retained runs have their expected
  terminal states. The failed attempts remain available and are not relabeled.

No ingestion, C300 replay, full native verification or full multiset run was
repeated. Targeted current SQL reads only metadata, the 450-row N450 binding table,
and the exact FIN eligibility predicate on pinned native output.

## Lossless 6 V2 — applicability and mandatory FIN regression

**B2 applicability/noninterference: PASS.** All 450 registered schemas and all
2,250 field positions match the five ordered SEC Daily Master columns. The live
binding table also matches every source/binding/run/header/hash/profile reference.

| Column | Applicability finding under the declared M1 |
| --- | --- |
| CIK | Source filing identifier text; numeric-looking identifiers are not economic measures or summable amounts |
| Company Name | Filing-index name text; no entity-resolution or economic measure is modeled |
| Form Type | Filing-form string; no economic measure |
| Date Filed | Source filing-date string; no reporting-period alignment or measure conversion |
| File Name | Filing document reference/path; no economic measure |

Every field retains its original economic `PRESERVED_NOT_MODELED` disposition;
lexical DIRECT_MAP fidelity is independently preserved. There are **0 modeled
eligible economic measures**, **0 uncovered/exceptional economic fields**, and
**0 native N450 records eligible for the exact FIN source/binding/run scope**.
The source/binding namespaces are disjoint. No numeric equation was invented for
N450, no field was silently omitted and no identifier was promoted into a FIN sum.
DEC-000010 remains only its previously approved SRC010128 field-local exception.

**Mandatory A/C1/C2.4 FIN regression: PASS.** On each actual retained historical
and C750 result, FIN_001 passes both contexts and FIN_002 passes its context,
including wrong-parent-equity detection (`1232700000.0000`). Independent exact
fixture equality, zero tolerance and all 13 source/run/locator/lineage witnesses
were reverified. Numerical and lineage differences in both directions are zero.
Current definition and table pins are unchanged, so the already executed matching
SQL evidence was reused; no additional FIN SQL replay was needed. Mutating the
retained candidate amounts with an offsetting drift, or erasing its wrong-equity
signal, is rejected by the independent comparator.

FIN V2 family acceptance is PASS on these tested applicability and mandatory
regression controls. It is not a claim of N450 numeric-equation reconciliation or
population-wide economic interpretation. Other economic fields retain the honest
existing retained-not-modeled boundary; three fixed contexts do not prove broader
financial or enterprise semantic coverage.

## C2.1–C2.4

| Control | Result | Actual evidence |
| --- | --- | --- |
| C2.1 — identity isolation | PASS | Exact old/new source, binding, original-run and hash memberships across 1,182 coverage rows; 300/450 source sets disjoint; zero collisions/reassignment |
| C2.2 — no unintended merge/split | PASS | 108 full-schema, binding/source/locator-aware bidirectional native comparisons, zero differences. Mandatory false-merge, duplicate-collapse, fanout and locator/namespace negative controls detect the intentional defects |
| C2.3 — historical/new projections | PASS | Records/fields retain byte-identical original historical SQL branches; new branch exactly matches pinned native N450 projection. Coverage has identical original table/version/binding sets; only IN-list order differs. Exact disjoint old/new predicates cover 732/450 bindings per view, so verified multiset equality yields zero differences in both projections |
| C2.4 — FIN noninterference | PASS | Mandatory three actual FIN contexts, wrong-equity control and 13 witnesses equal the fixed independent fixture on both consumers; live N450 exact FIN eligibility count is zero |

Synthetic negative controls supplement the full native proof; they do not replace
it. Reused N450 native verification preserves 29,062 equal-looking groups,
58,367 participating occurrences and 29,305 excess occurrences at distinct source
locators. No entity-level duplicate-event judgment or canonical key is inferred.

## C3.1–C3.4

| Control | Result | Actual evidence |
| --- | --- | --- |
| C3.1 — execution completeness | PASS | Exactly 450 unique eligible COMPLETE receipts; zero missing/extra/error outcomes; all receipt, Parquet and ordered-digest pins reconcile to the independent native evidence |
| C3.2 — frozen historical preservation | PASS | Original C300 source/Delta/UC/version-0/output references unchanged; zero historical processing replays or model backfills |
| C3.3 — recovery/idempotency | PASS | Three smoke checkpoints reused in full; 447 remaining bindings created once. All 450 original/current receipt pairs preserve identical Parquet bytes and verification digests through the approved pin-only metadata rollover. Zero successful-checkpoint reprocessing or duplicate output effects; exclusive version-0 publication and exact native readback |
| C3.4 — operational thresholds | PASS | Every original reported phase runtime and full job elapsed is below its own verified pre-existing configured hard timeout; measurements/configuration provenance below |

These are **retained actual measurements**, not fresh performance measurements.
The configured limits are in the approved submissions inside the actually executed,
hash-pinned runtime archives, checked against submission receipts, task definitions,
reported archive hashes and corresponding remote run IDs. They were not selected
retroactively for this scorecard.

| Phase / run | Runtime wall (s) | Job elapsed (s) | Existing limit (s) | Scope DATA records/s | Scope fields/s |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full processing / `879442057562865` | 753.049 | 789.068 | 3,600 | 2522.686 | 12613.430 |
| CLEAN / `1100860214974411` | 520.931 | 558.359 | 3,600 | 3646.750 | 18233.751 |
| QUERYABLE validation / `368063299510003` | 8875.574 | 8911.604 | 28,800 | 35610.523 | 404118.999 |

Throughput is scope units divided by that original phase wall time, not a count of
all repeated comparator I/O or a production benchmark. Full processing includes
validation/reuse of the three already completed smoke bindings. The separate smoke
run consumed 92.698 seconds of reported runtime (130.170 seconds job elapsed);
it is not hidden inside the full-phase throughput denominator.

Available driver CPU seconds and peak RSS in the original recorded platform units:

| Phase | Driver CPU (s) | Peak RSS (original platform units) |
| --- | ---: | ---: |
| Processing | 239.418 | 2,476,496 |
| CLEAN | 163.455 | 2,503,592 |
| QUERYABLE | 51.903 | 2,393,812 |

The ten explicitly indexed remote runs contain five successful runs with one task
attempt each and **five earlier failed runs with ten failed task attempts** (one
backend retry each). Four are pre-parsing setup/guard failures and one is the
unsupported writer-mode publication failure; those failed tasks created no new processing checkpoints
or published outputs. The failed CLEAN run is `997643049038042`; successful resumed
CLEAN is `1100860214974411`. All original failure and recovery records remain.
Actual provider attempts are reported even though submitted `max_retries` was zero;
successful-run retries are zero. This is the indexed pipeline scope, not an account-
wide job-history census.

Human telemetry: six persisted OWNER_APPROVED processing-authorization versions
are observable artifacts, not a count of distinct people or review decisions.
Actual human-review event/person/duration telemetry is **UNAVAILABLE**. DBUs,
executor CPU, executor peak RSS and monetary cost are **UNAVAILABLE**, not measured
zero. C3 PASS covers the declared completion/recovery/configured-timeout controls;
it does not assert human-efficiency, cost, provider-resource or production-SLA
acceptance. No Step 5 measurement study was performed.

## Evidence, checks and remaining limitations

New indexed evidence is under `runs/c750-stability/v2/`:

- `retained-input-index.json`: 1,135 verified retained input hashes and pinned
  main/authority revisions; original V1 authority checked against its historical
  Git object rather than rewritten to the new contract.
- `lossless6-applicability.json`: all 450 bindings and 2,250 field dispositions.
- `live-pin-checks.json`, `deployed-pin-checks.json`, `live-sql/`, `live-jobs/`:
  actual current definition/table/archive checks, new-cohort applicability queries
  and original run/retry metadata; no processing job was submitted.
- `fin-v2-reuse.json`, `c2-native-projection-proof.json`,
  `projection-sql-identity.json`: exact fixture/negative controls and source-aware
  native old/new/combined projection proof. The 108 original receipts remain at
  `runs/n450/step3-clean-write-fix-v1/queryable-checks/`.
- `c3-retained-execution.json`: 450 receipt pairs, original phase timing/budget
  provenance, recovery counts and disclosed unavailable telemetry.
- `focused-tests.json`: permanent evaluator and FIN contract tests: **12 passed,
  1 skipped**; Ruff passed. The legacy FIN test's expected host-local directory is
  absent in this worktree; its actual retained values and both mutation checks were
  independently executed at their existing V1 location, without copying/replaying
  historical processing to make the skip disappear.
- `results.json`, `evidence-index.json`: separate current statuses, metrics,
  provenance and new evidence hashes. Generated results and data are gitignored;
  this report commits their reproducible references, not RAW/Parquet/result files.

Limitations persist: no enterprise business keys/entity equivalence, false-entity-
merge ground truth, relationship semantics, generalized grain/unit/date alignment,
source NULL semantics or wider financial interpretation is established. Changes to
model, source identity/hash, snapshot, SQL meaning or affected rules invalidate the
relevant reuse and require a scoped reevaluation. The versioned acceptance minimum
changed; the data/model and historical evaluation facts did not.

Stop after **Day 3 Step 4 V2**. No ingestion reruns, C300 replay, M1 changes,
historical evidence rewrite, O_C750_M1 freeze or Step 5 work occurred.

| Evidence reference | SHA-256 |
| --- | --- |
| V2 runbook | `d4840e505e427c6bcac13a4612f6850c31b8758c723888a0de676c9e45b9cf9e` |
| Current evaluation authority | `bd304aab84d71dfdd5323c4c7edd9c8de6f8fc2b267d87f4e79e31cf55c771e1` |
| LOSSLESS_6_FIN_SUITE_V2 | `1442b9b33eb8066c03c20d736697ae53ff3696ea4f7315a46df1293b1794c994` |
| STABILITY_M1_V1 | `f23febdc07ae8497214f70b36e222795a44d2449fbf8ceb6362d2dd80178df1a` |
| Results | `bc4782b25acd7085139017e3f9294ea9a0730a088c77ddf2cd110d98c2f781fe` |
| Evidence index | `d1e4ec1dbc9712db0c3f9e92f1754e12ff6d42a3cc8d26df6268c4dc5fc4e28c` |
| Retained-input index | `db02a4c22884f7c9e63d50f9e539ee097574239237081a65a0dcd3e6c3ab091e` |
| Preserved V1 report | `577e48b73d2ca4dbb586fa4d281c06cc9a4be8f72d17414319a0d07a95af7a3f` |
