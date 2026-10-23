# EDP Lab autonomous pilot — project-specific C3.4 reference

**Status:** Owner-directed **EDP Lab project pilot parameter**, *not* an amendment to the generic workflow specification, a signed runtime grant or a historical result. The values are versioned in [the numeric pilot config](../../metadata/operating/edp_lab_pilot_c3_4_budget_v1.json).

## Why Day 4 is a *pilot numeric anchor*, not a universal baseline

The generic [Validation + Freeze contract](../workflows/validation_freeze_lifecycle_v1.md) says to use the first accepted/frozen cohort's trustworthy complete **per-phase** timing as the baseline. The first cohort's Day 2 record contains successful recovery phase measurements, but not an independently measured, comparable single end-to-end RAW→CLEAN→QUERYABLE total; an earlier 8-hour partial timeout is not a successful complete benchmark. **Do not invent Day 2 timings.**

For the **EDP Lab autonomous Day 5 experiment and later project runs**, the owner explicitly chose available *measured Day 4 N750 Step 8 phases* as an operational trial reference. This is a project-scoped, prospective bootstrap/special reference until stronger measured/approved references exist. It does **not** assert that Day 4 was the first frozen cohort for the generic lifecycle, or that Day 4 is a true universal processing baseline.

The original Day 4 approval [C3.4 budget v1](../../metadata/authorizations/day4_c3_4_budget_approval_v1.json) and technical `C3.4_BLOCKED` result remain unchanged. The project pilot grants a separately documented, prospective experiment-specific comparison rule; installing it in the autonomous executor still requires external scoped trust and grant controls.

## Exactly what is measured

Source of truth: [operational_budget_v1.json](../../metadata/evaluations/operational_budget_v1.json), local monotonic and Databricks SQL request-to-result evidence for **N750 Step 8**, not an integrated C1500 total. Representative source: 750 physical N750 sources, remote verified 269,323,425 bytes, 3,047,639 SEC DATA records, 15,238,195 SEC DATA fields, 21,616 XML properties; 450 previously verified remote RAW / 300 uploaded.

| Day 4 phase (measured reference) | Reference (s) | >5×: warning starts (s) | >10×: owner block starts (s) |
| --- | ---: | ---: | ---: |
| Remote RAW resolution + readback | 675.667 | 3,378.335 | 6,756.670 |
| Local CLEAN build + readback | 45.890 | 229.450 | 458.900 |
| SQL table creation | 55.145 | 275.725 | 551.450 |
| SQL Delta validation | 91.842 | 459.210 | 918.420 |
| SQL views + counts | 27.862 | 139.310 | 278.620 |
| SQL coverage + lineage | 43.465 | 217.325 | 434.650 |
| **SQL-phase total (derived, nonoverlapping)** | **218.314** | **1,091.570** | **2,183.140** |

Boundary semantics: **≤5× = PASS**; **>5× and ≤10× = PASS + nonblocking WARNING**, continue; **>10× = BLOCKED**, hold promotion/obtain owner approval. The tabulated warning/block values are thresholds; equality at 5× does **not** warn and equality at 10× does **not** block. Record both phase ratio and real elapsed time. The SQL total is a *derived sum of the four underlying SQL intervals*, not a separate wall timer or full pipeline total, so do not sum it again with component timers.

## How Agent A should apply this at Day 5, 6, 7, ...

1. Before running, load the separate project config and the **actual independent signed execution grant**. This text and a JSON file alone are not credentials, owner signatures or write authorization.
2. For matching **operations and clock definitions**, pin the actual Day 4 observed seconds and project thresholds. Compare present workload size/mix (including reused vs fresh RAW), selected model branch, replay/backfill and environment; record deviations and explain interpretation. The owner specifically chooses to test this reference as a *pilot yardstick* beyond the original N750-only scenario, not to pretend that workloads have identical scale.
3. During execution, record start/end per stage, wall/job and retry/recovery receipts. **≤5× PASS**; **5×<t≤10×** issue visible **WARNING, but PASS** and continue within the granted bounds. **>10×** means performance is **BLOCKED** pending a real owner decision; do not self-extend hard limits.
4. For a newly introduced stage with **no equivalent Day 4 phase** (e.g. corrective historical replay, fully integrated end-to-end lifecycle, independent whole-corpus Stability), do not invent a numeric threshold. Measure stage timing, create a decision packet, and establish a separate versioned benchmark/approval before claiming technical C3.4 PASS on that stage.
5. Keep every prior frozen result and historical C3.4 state as-is. New measurements may support a later upgraded project-scoped reference. **Never rewrite the generic workflow to hard-code Day 4.**

## What this does not change

- No change to [the universal Lifecycle specification](../workflows/README.md).
- No retroactive Day 4 `C3.4_PASS`.
- No approval of missing Treasury economic Lossless 6 tests or data semantics.
- No authorization to exceed signed grant wall/cost caps, Databricks job timeouts or storage quotas.
- No assertion that the Day 5 C2000 autonomous runner, source cohort admission or actual Databricks result freeze has already executed.

**Project-scoped status:** reference numbers retained and proposed policy recorded for future autonomous runtime binding; technical deployment and negative threshold tests remain to be implemented in the separate orchestration PR.
