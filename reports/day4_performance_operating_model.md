# Day 4 performance and operating model

**PERFORMANCE_MEASURED** for retained phase timings and source-preserving workload counts. This is an evidence consolidation; C1500 was validated as a logical combined candidate, not processed in one new end-to-end run. The machine-readable [scorecard](../metadata/evaluations/day4_performance_v1.json) records the exact values and references.

| Scope | Physical sources / bindings | Source DATA records | Original fields/properties | Derived M2 evaluations |
| --- | ---: | ---: | ---: | ---: |
| C750 | 750 / 1,182 | 316,063,821 | 3,586,787,936 | 176,060,325 historical typed occurrences |
| N750 | 750 / 750 | 3,047,639 SEC DATA | 15,238,195 SEC fields + 21,616 XML properties | 12,948 Treasury (12,793 VALID; 155 MISSING) |
| C1500 logical | 1,500 / 1,932 | 319,111,460 | 3,602,047,747 | historical and new projections above, not additional source fields |

The 745 SEC Daily Master files also contain 3,052,854 physical lines including framing; five Treasury XML sources contain the property occurrences. Historical typed counts arise from 60 FSDS bindings. C750 RAW bytes are **UNAVAILABLE_IN_COMPARABLE_AGGREGATE** in the inspected tracked summaries. The frozen [roster](../metadata/freezes/C1500_v1/freeze.json), [Step 8 report](../docs/n750_step8_execution.md), [Step 9 evaluation](../docs/c1500_m2_stability_evaluation.md) and [historical M2 baseline](../metadata/baselines/O_C750_M2_v1.json) establish these denominators.

## Timed phases and throughput

| Executed phase | Seconds | Measurement / scope |
| --- | ---: | --- |
| N750 remote RAW resolution/readback | 675.667 | Local monotonic interval; 750 independently SHA-verified remote objects, 269,323,425 bytes |
| N750 local CLEAN build/readback | 45.890 | Local interval; 3,047,639 SEC DATA rows, 15,238,195 fields, 21,616 XML properties |
| N750 SQL table creation | 55.145 | Warehouse request-to-result interval |
| N750 SQL Delta validation | 91.842 | Warehouse request-to-result interval |
| N750 SQL views/counts | 27.862 | Warehouse request-to-result interval |
| N750 SQL coverage/lineage | 43.465 | Warehouse request-to-result interval |
| SQL intervals total | 218.314 | Sum of the four recorded SQL intervals; not internal Spark executor time |
| Historical M2 failed preflight / successful build / verify job walls | 123.203 / 553.273 / 801.190 | Runs 693588401750111 / 910030711554960 / 426457626095564; failed preflight excluded from successful build duration |

Remote verification throughput = 269,323,425 / 675.667 = **398,603.787 verified bytes/s** and 750 / 675.667 × 3600 = **3,996.051 verified sources/hour**. Local CLEAN throughput = 3,047,639 / 45.890 = **66,411.833 SEC DATA records/s** and (15,238,195 + 21,616) / 45.890 = **332,530.203 original fields/properties/s**. These denominators cover their own phases only. Independent M2 conversion throughput and true N750/C1500 end-to-end elapsed time are **UNAVAILABLE**. Source admission, profiling, combined Stability and Agent V2 have no separately comparable complete timing in the inspected records.

The retained [RAW completion](../docs/n750_step8_execution.md) has SHA-256 `c58a1a36d99b71d79948ea5a41b82069df40d78d8797611411516de52255ac86`; local [CLEAN completion](../docs/n750_step8_execution.md) has `a95af935e8b1bdc043e2e458a01a582130642746a4cb1b8579b922bec6560fbb`. Runtime receipts remain ignored under `runs/n750/step8-v1/`; tracked reports are summaries, not the receipts themselves.

## Reliability, resources and people

N750 completed 750/750 source scopes, with 450 verified remote objects reused and 300 originals uploaded; all 750 RAW hashes matched. Four Delta tables were published once at version 0, with no overwrite. No failed-job recovery occurred during Step 8; internal provider retry telemetry is **UNAVAILABLE**. Historical M2 had one observed failed preflight followed by a successful build and separate verification. The [N450/C750 stability report](../docs/c750_stability_v2_evaluation.md) records five earlier failed remote runs/ten failed task attempts, then successful checkpointed recovery; its run scope and workload differ from N750. N450/C750 phase job elapsed values were 789.068, 558.359 and 8,911.604 s respectively, with measured driver CPU 239.418, 163.455 and 51.903 s. Peak RSS values 2,476,496, 2,503,592 and 2,393,812 are retained in original platform units. They are not N750 cost measures. Day 4 CPU, memory, DBU and monetary cost, and historical M2 DBU/cost are **UNAVAILABLE**.

Agent V2 produced 23 candidate proposals; eight required review, three consequential requests were recorded, zero responses and zero semantic approvals were observed. Active review minutes and manual operating minutes are **UNMEASURED/UNAVAILABLE**; silence is not zero work. [Step 10](../docs/day4_step10_agent_v2_quality_regression.md) bounds the benchmark. M2 evolution added exact Decimal rules, Treasury adapter, historical FSDS typed projection, N750 M2 output, Delta/QUERYABLE publication, permanent FIN/TRY numeric controls, Stability checks and agent evaluation. No time allocation by development activity was recorded. Previously accepted M1 work and avoided RAW/historical replay are distinct from incremental M2 work.

The [prospective 10× budget](../metadata/evaluations/operational_budget_v1.json) remains **PROPOSED_PENDING_APPLICABILITY_APPROVAL**. Phase maxima are 6,756.670 / 458.900 / 551.450 / 918.420 / 278.620 / 434.650 s in the table order above. Day 4 C3.4 remains **BLOCKED**; these future limits do not score it retrospectively. Day 2/3 named files `reports/day2_performance_finding.md`, `reports/profile_summary_day2.md`, and `reports/c750_scale.md` are absent from this checkout. Available historical N450/C750 and M2 reports show different source mix, verification and Databricks execution environments, so no linear scaling, speedup, cost or staffing savings are inferred.
