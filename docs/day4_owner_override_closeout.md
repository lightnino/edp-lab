# Day 4 — explicit owner override, bounded result freeze and exit (2026-10-23 SGT)

## Decision

The requesting owner explicitly ordered (1) standing authorization for the Day 4 C3.4 10× budget, (2) forced **O_C1500_M2** result freeze by human intervention, and (3) Day 4 exit and main integration. This is a **new**, append-only decision after the historical PARTIAL closeout, not a rewrite of that closeout or of the test results.

**O_C1500_M2 = FROZEN_BY_EXPLICIT_HUMAN_OVERRIDE — Git evidence/approval marker, source-preserving scope only.**
**Day 4 = COMPLETE_BY_HUMAN_OVERRIDE_WITH_EXCEPTIONS.** Live Databricks version-0 outputs are pinned from prior receipts; this interaction has NOT created a durable runtime archive, installed Delta retention protections, or performed a new live readback. This is not a physical WORM/production-data freeze.

## Why the earlier 50 decisions are not bad data

PR #48 already approved **50/50 source/QName L3 fields** as `PRESERVED_NOT_MODELED`; Step 9 scoped V3 records **B2.1 and C1 PASS**. The N750 M2 numeric layer has **12,948 evaluations**: **12,793 VALID**, **155 verified structural MISSING** (31 SRC010451 / 124 SRC010452). TRY_003 found no false missing, invalid representation or join discrepancy. Do not fill or amend those 155 absent source properties.

## Standing C3.4 authorization

The original tenfold benchmark from [budget V1](../metadata/evaluations/operational_budget_v1.json) is adopted into a **standing owner-approved policy** at [approval V1](../metadata/authorizations/day4_c3_4_budget_approval_v1.json), effective **2026-10-23 SGT**, until explicitly superseded. It applies to comparable future N750-like workloads with the same measured phase definitions, source mix, runtime and scale. For another workload (including Day 5 N500), record a comparability decision or obtain new scoped approval. It is not an all-workloads SLA and cannot turn earlier BLOCKED into a retrospectively observed technical C3.4 PASS.

## Freeze evidence and exclusions

- Frozen membership: 1,500 sources / 1,932 execution bindings; exact roster, RAW hashes, SQL SHA, historical M1 snapshots, historical typed FSDS table and four N750 version-0 Delta tables are cited in the original [Step 13 assessment](../metadata/evaluations/o_c1500_m2_freeze_assessment_v1.json).
- Source-preserving checks: FIN_001 **2/2**, FIN_002 **1/1**, Treasury TRY_001–004 **4/4**, historical lineage witnesses **13/13**, combined bidirectional multiset directions **8/8 zero differences**.
- Approval: [C3.4 owner policy](../metadata/authorizations/day4_c3_4_budget_approval_v1.json), [freeze authorization](../metadata/freezes/O_C1500_M2_v1/authorization.json), [references](../metadata/freezes/O_C1500_M2_v1/references.json), [freeze marker](../metadata/freezes/O_C1500_M2_v1/freeze.json) and [post-acceptance V2](../metadata/evaluations/o_c1500_m2_freeze_assessment_v2.json).
- **Not approved:** Treasury economic L6-B, canonical business identity/relationships, cross-feed units/grain/reconciliation, or assumptions of unlimited Delta retention. No new processing, RAW mutation, fake data repair, or semantic promotion.

## Exit / merge boundary

[Day 4 Exit V2](../metadata/evaluations/day4_exit_v2.json) closes the **bounded experiment** by explicit human exception; the original [V1 PARTIAL exit](../metadata/evaluations/day4_exit_v1.json) remains immutable. Main integration must be evidenced by the actual merged PR and passing CI; a JSON declaration alone does not prove the merge.

## Live Databricks result freeze V2

The owner had already approved all **50/50** Treasury source/QName L3 dispositions as `PRESERVED_NOT_MODELED`; B2.1 and C1 source-preserving acceptance are PASS. The 12,793 VALID and 155 structurally MISSING evaluations need no data repair. Treasury economic L6-B remains `NOT_IMPLEMENTED` and outside this freeze.

The separate, queryable Unity Catalog view `workspace.edp_lab.o_c1500_m2_result_frozen_v1` (object ID `43e16098-b123-4689-83d5-4d942bbe4dfc`) now represents the complete occurrence-level C1500 result. Its [source SQL](../sql/freezes/o_c1500_m2_v1/result_view.sql) directly pins ten physical Delta data inputs at version 0, including all six historical M1 dependencies, historical typed M2 and the three N750 occurrence tables. The N750 coverage table is separately pinned and checked. The view does not refer to a mutable historical or latest view. Five inputs received metadata-only `delta.appendOnly=true`; six historical M1 inputs already had it. No data copy, RAW replay, CLEAN rebuild or M2 reprocessing occurred.

Live SQL verified 1,500 physical sources, 1,932 operational bindings, 319,151,239 occurrence rows across the four approved classes, and Treasury 12,793 VALID / 155 MISSING. The [versioned evaluation](../metadata/evaluations/o_c1500_m2_databricks_freeze_v2.json) indexes 68 live SQL receipts with statement IDs and response hashes. The [Databricks marker](../metadata/freezes/O_C1500_M2_v1/databricks_result_freeze_v2.json) distinguishes this executed freeze from the earlier Git-only owner marker. The unchanged Step 9 bidirectional comparisons, FIN results and 13 lineage witnesses were revalidated by evidence hashes; their full scans were not rerun.

Version 0 was readable at verification time. Append-only does not guarantee unlimited time travel against future retention or privileged deletion. Historical Day 4 C3.4 remains BLOCKED as a technical result under the documented owner exception. [Day 4 Exit V3](../metadata/evaluations/day4_exit_v3_databricks.json) records this narrower executed Databricks outcome; the GitHub merge event remains separate evidence.
