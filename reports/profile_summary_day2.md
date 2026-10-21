# Day 2 measured workload and recovery

See [Performance Finding FND-DAY2-PERFORMANCE-TIMEOUT-001](day2_performance_finding.md).
Original run **427800138450251** timed out at **8 hours**, with **348/720** main
bindings staged. Actual wall was 28836.501 seconds.
Observed partial staging rates were 7,325.321 records/s, 78,437.111 fields/s and
915,403.919 uncompressed member bytes/s. These were not successful end-to-end rates.
Measured parsing/packaging was 3,922.388 seconds and independent verification
24,355.719 seconds. Verification dominated that serial prefix; lower-level CPU
versus I/O cause remains NOT_ESTABLISHED. The unchanged oracle was not weakened.

Recovery reused **429** valid completed checkpoints and parsed only **291**
missing/incomplete bindings. Final new staging: 37,393,269 DATA occurrences,
548,137,213 fields, 3,700,945,266 uncompressed member bytes in 2859.117
seconds of actual final-stage job wall. Rates: 13078.607 records/s,
191715.559 fields/s, 1294436.452 member bytes/s.
This differs from the original FSDS-heavy prefix and excludes cached429; no linear
speedup or fresh whole-C300 benchmark is inferred.
Unique physical parent inputs (compressed archives plus plain Daily Master files)
were 956,694,309 bytes: 334611.808 parent-file bytes/s
over the same new-staging wall denominator. This is distinct from uncompressed
member throughput and does not claim total read/hash I/O or upload throughput.

The recovery job span was **24096.738 seconds**, from first recovery job start
through last observed terminal job end, including setup failures, the controlled
stop to avoid repeating a smoke binding, orchestration gaps and concurrent stages.
Initial preparation before the first recovery job has no continuous timer. Worker
times and overlapping job wall times are not summed as end-to-end elapsed time.

| Job | Result | Wall seconds |
| --- | --- | --- |
| `427800138450251` (c300-m1-lexical_20261020_v3-full) | TIMEDOUT | 28836.501 |
| `653857229258835` (c300-m1-num_recovery_20261021_v1) | SUCCESS | 8115.352 |
| `686073592751900` (c300-m1-checkpoint_recovery_20261021_v1) | SUCCESS | 127.152 |
| `579155785972496` (c300-m1-main_recovery_20261021_v1-stage) | FAILED | 57.613 |
| `625828136264800` (c300-m1-main_recovery_20261021_v2-stage) | FAILED | 59.807 |
| `476248727361002` (c300-m1-main_recovery_20261021_v3-stage) | CANCELED | 1741.802 |
| `200272186433720` (c300-m1-checkpoint_recovery_20261021_v2) | SUCCESS | 39.041 |
| `758804395366009` (c300-m1-main_recovery_20261021_v4-stage) | SUCCESS | 2859.117 |
| `1020644587126998` (c300-m1-main_recovery_20261021_v4-publish) | SUCCESS | 582.678 |
| `246744902888746` (c300-m1-main_recovery_20261021_v4-clean) | SUCCESS | 1401.885 |
| `1023109119094548` (c300-m1-main_recovery_20261021_v4-gate) | SUCCESS | 33.358 |
| `1124391195675962` (c300-m1-main_recovery_20261021_v4-query) | SUCCESS | 7270.038 |
| `281723002176292` (c300-m1-main_recovery_20261021_v4-finish) | SUCCESS | 176.910 |
| `184529929826922` (c300-m1-stats_recovery_20261021_v2) | SUCCESS | 3257.648 |
| `1038195776467698` (c300-m1-reconciled_recovery_20261021_v2-prepare) | SUCCESS | 37.721 |
| `595117225032028` (c300-m1-reconciled_recovery_20261021_v2-query) | SUCCESS | 8313.719 |
| `340155733982688` (c300-m1-reconciled_recovery_20261021_v2-finish) | SUCCESS | 33.405 |

Full validated output: 314,164,116 DATA occurrences,
3,577,289,411 fields, 732 bindings/300 physical inputs. Delta output
size/file metadata and billing snapshot are retained in `benchmark.json`.
Billing is reported usage by queried run ID only; recent missing records are not
zero and billing can arrive later. Actual invoiced monetary cost is UNAVAILABLE;
no DBU-to-dollar conversion is inferred. Shared SQL warehouse/storage/egress
costs are not attributed to these jobs without evidence.

Actual available billing usage snapshot:

| run_id | sku_name | usage_unit | usage_quantity | first_usage_start | last_usage_end | snapshot_time |
| --- | --- | --- | --- | --- | --- | --- |
| 1020644587126998 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 0.968132690316218720 | 2026-10-21T04:00:00.000Z | 2026-10-21T05:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 1023109119094548 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 0.006270075000000000 | 2026-10-21T04:00:00.000Z | 2026-10-21T05:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 1124391195675962 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 8.071300784674404740 | 2026-10-21T04:00:00.000Z | 2026-10-21T06:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 200272186433720 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 0.006184325000000000 | 2026-10-21T03:00:00.000Z | 2026-10-21T04:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 246744902888746 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 3.507478750009376600 | 2026-10-21T04:00:00.000Z | 2026-10-21T05:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 427800138450251 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 5.046672925000000000 | 2026-10-20T16:00:00.000Z | 2026-10-21T01:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 476248727361002 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 0.610830500000000000 | 2026-10-21T02:00:00.000Z | 2026-10-21T04:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 579155785972496 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 0.029277150000000000 | 2026-10-21T02:00:00.000Z | 2026-10-21T03:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 625828136264800 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 0.032232900000000000 | 2026-10-21T02:00:00.000Z | 2026-10-21T03:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 653857229258835 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 5.497519700000000000 | 2026-10-20T17:00:00.000Z | 2026-10-20T20:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 686073592751900 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 0.022430975000000000 | 2026-10-21T02:00:00.000Z | 2026-10-21T03:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 758804395366009 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 1.001603400000000000 | 2026-10-21T03:00:00.000Z | 2026-10-21T05:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 936395894045097 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 0.323613721428571429 | 2026-10-20T15:00:00.000Z | 2026-10-20T16:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 985816639856819 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 0.007089250000000000 | 2026-10-20T16:00:00.000Z | 2026-10-20T17:00:00.000Z | 2026-10-21T09:09:49.410Z |
| 986372310789815 | PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO | DBU | 0.077476875000000000 | 2026-10-20T15:00:00.000Z | 2026-10-20T16:00:00.000Z | 2026-10-21T09:09:49.410Z |

Returned usage totals by unit: `{'DBU': '25.208114021428571489'}`, covering
15 usage rows across 20
queried run IDs, including the retained earlier smoke/probe runs. Missing run IDs:
`['1038195776467698', '184529929826922', '281723002176292', '340155733982688', '595117225032028']`. This is a partial observed usage snapshot,
not the final total execution cost. Snapshot: `['2026-10-21T09:09:49.410Z']`.

Optional statistics completed 304 full-binding
tool-envelope sets and 3261 column envelopes, with
732 table-status rows/7,746 column positions. Boundaries: 2,000,000 member bytes,
120 seconds/worker, 8 GiB address space and a 1,800-second threshold for admitting
new statistical workers. Checkpoint I/O, export and artifact hashing continue
after that threshold and are included in the actual job wall time. Completed
prior envelopes were reused, including the 1,499-row/36-column probe. Every computed
statistic covers its declared full binding; samples are EXACT_SAMPLE, not population
substitutes. Resource-limited and semantic NULL-dependent metrics/candidate-key
eligibility remain NOT_COMPUTED. No extra RAW parse was used for statistics.
Actual attempt outcomes: `{'COMPLETE:REUSED_VERIFIED_PROBE': 1, 'NOT_COMPUTED:RESOURCE_BUDGET_MEMBER_BYTES': 257, 'COMPLETE:None': 303, 'NOT_COMPUTED:RESOURCE_LIMIT_TOTAL_STATISTICAL_TIME': 171}`. COMPLETE means the declared
full-binding tool-envelope set completed; semantic NULL-dependent/key eligibility
metrics inside those envelopes remain explicitly NOT_COMPUTED.

Actual runtime: `{'duckdb': '1.5.0', 'peak_rss_platform_units': 2486616, 'platform': 'Linux-6.1.188-233.386.amzn2023.aarch64-aarch64-with-glibc2.35', 'pyarrow': '14.0.1', 'python': '3.11.10', 'spark': '4.2.0'}`. Executor CPU/memory, scratch/disk high water,
Spark-task retries, spill/shuffle and active human review minutes are UNAVAILABLE
or UNMEASURED where not exposed. No per-record manual edit/intervention occurred.
The legacy publication `delta_commit_seconds` timer includes terminal RAW hashes
and metadata assembly; pure commit latency is not separately measured. Validation
and query worker-time sums are distinct from the concurrent phase job wall times
in the table above. Finalization timers do not measure the whole pipeline.

Scaling implications: size work by records/fields and member bytes, retain a
verified binding checkpoint before scheduling successors, include every prior
completed scope in resume inventory, and budget source verification separately
from Delta/query validation. Parallelism trades wall time against measured resource
usage; these mixed workloads do not prove linear scaling, a fixed speed target,
or the ~10-person staffing hypothesis. Protected historical retention remains the
unverified freeze gate; no final global Day 2 PASS/freeze is declared.

Detailed evidence: `runs/c300-m1/day2_completed_recovery_20261021_v1/benchmark.json` and
`profile_run_manifest.json`. See [baseline](C300_baseline.md) for exact acceptance
and artifact mapping. No commit, push or merge was performed.

## Closeout measurement scope

| Measurement | Value | Classification and denominator |
| --- | --- | --- |
| Statistical job wall | 3,257.648 s | MEASURED, run 184529929826922; partial statistical population |
| Statistics loop plus export | 2,218.705 s | MEASURED, stats summary; excludes earlier setup/later manifest hashing |
| Final Main V4 stage-start to finish-end | 12,478.429 s | DERIVED from retained job timestamps; 429 checkpoints reused |
| Original Main start to combined completion | 59,552.911 s | DERIVED execution-history span; not a cold end-to-end timer |
| Unique RAW parent footprint | 7,632,930,175 bytes | DERIVED sum of 300 physical-evidence entries; not total read I/O |
| Logical member volume | 38,399,105,140 bytes | DERIVED main plus NUM completion; includes framing |
| Final V4 parent scopes touched | 211; 265.676 parent scopes/hour | DERIVED V4 plan / 2,859.117 s; remaining bindings, not full cold sources |
| NUM complete-job throughput | 5,270.078 records/s; 0.747 MB/s; 5.323 sources/hour | DERIVED 42,768,535 records, 6,063,050,101 member bytes, 12 parents / 8,115.352 s |
| Main recorded process RSS maximum | 4,347,604 Linux KiB (4.146 GiB) | MEASURED RUSAGE_SELF high-water; maximum across saved binding records, not cluster memory |
| NUM recorded process RSS | 2,505,656 Linux KiB (2.390 GiB) | MEASURED RUSAGE_SELF high-water; not comparable cluster peak |
| Cold full-C300 end-to-end, actual total I/O, complete dollar cost, active human time | NOT_MEASURED | Not recoverable from existing counters |

MB means 1,000,000 bytes. Main staging-only 13,078.607 records/s and NUM
complete-job 5,270.078 records/s include different stages and are not a speedup
comparison. Main/NUM summed parse-package timers are 5,630.546/1,478.775 s; summed
independent verification timers are 36,587.600/5,172.273 s. These are DERIVED from
saved execution-evidence.json binding timers, not concurrent wall durations.

Evidence is retained under the Main/NUM/statistics/combined bases indexed in
`metadata/baselines/O_C300_M1.json`; benchmark.json pins job timestamps and run
references. Performance remains PARTIAL measurement coverage. Statistical sets
cover only 1,670,599 records (0.532%), not the entire 314,164,116-record output.
The user has now authorized a local Day 2 closeout commit; this does not authorize
a final baseline seal or establish retention protection.
