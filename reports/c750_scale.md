# C750 scale — Day 3 Step 5A measured performance

Performance coverage: **PARTIAL_MEASURED**. N450 processing and the declared
M1 source-preserving Stability evaluation completed. This report reuses actual
Steps 2–4 measurements; no ingestion, historical replay or benchmark rerun was
performed. Model: `M1_LEXICAL_V1`; N450 rule: `C300_LITERAL_IDENTITY_V1`.
Enterprise semantic integration remains NOT_IMPLEMENTED.

Conventions follow [Day 2 measured performance](profile_summary_day2.md) and
[the timeout finding](day2_performance_finding.md): MEASURED values are retained
counters/timers, DERIVED values state their denominator, and UNAVAILABLE or
NOT_MEASURED values are never treated as zero. Bytes are decimal bytes; DATA
records exclude framing. Binding counts differ from physical source counts.

## Workload and composition

| Scope | Physical sources | Bindings | DATA records | DATA fields | Physical input bytes | Logical member bytes, including framing |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen C300, reused | 300 | 732 | 314,164,116 | 3,577,289,411 | 7,632,930,175 | 38,399,105,140 |
| Incremental N450 | 450 | 450 | 1,899,705 | 9,498,525 | 166,225,261 | 166,225,261 |
| Combined C750 | 750 | 1,182 | 316,063,821 | 3,586,787,936 | 7,799,155,436 | 38,565,330,401 |

Counts reuse verified full output evidence. Byte volumes are DERIVED footprints,
not cumulative hash/read/write I/O. C300 bytes use the retained Day 2 physical and
member totals; N450 bytes sum all 450 original checkpoint verification byte
counters, independently equal to the 450 Step 2 descriptor sizes. C750 adds the
disjoint cohorts; it was not freshly ingested as a 750-source workload.

C300 physical families: 198 SEC EDGAR Daily Master files, 60 SEC FSDS archives
and 42 SEC 13F archives (cohort joined mechanically to the frozen v3 manifest).
Its 732 logical tables contain 7,746 column positions, including separate Main
720 and NUM 12 processing scopes. N450 adds only Daily Master: one ordered
five-column TEXT schema (`CIK`, `Company Name`, `Form Type`, `Date Filed`,
`File Name`), 2,250 column positions. C750 contains 648 Daily Master physical
inputs plus the unchanged 60 FSDS and 42 13F archives, with 9,996 column positions.
No new source/schema family was demonstrated by this increment.

N450 adds 150% as many physical sources as C300, but only **0.605%** as many
DATA records, **0.266%** as many fields and **2.178%** as many physical input
bytes. These composition effects preclude a source-count scaling conclusion.

## Profiling and parsing measurements

| Measurement | Actual value | Tested scope and limits |
| --- | ---: | --- |
| Step 2 local observation/profiling wall | 13.467970 s | 450 full-byte structural observations; 449 complete lexical sources; one binding held on invalid UTF-8; three complete statistical tables |
| Step 2 local RSS high-water | 73,285,632 bytes | macOS process; not Databricks memory |
| Step 2 scoped encoding recovery/control wall | 11.308749 s | SRC010128 (8,530 DATA records / 42,650 fields) plus three UTF-8 control sources; 449 existing fingerprints reused |
| Original N450 checkpoint timer sum | 406.858058 s | 450 unique checkpoints, including smoke; parse/package, native verification and post-parse RAW hash combined |
| Fresh 447 checkpoint timer sum within full run | 403.443324 s | Remaining 447 bindings; 1,882,782 DATA records / 9,413,910 fields / 164,796,384 bytes |
| Pure parsing versus independent verification time | NOT_MEASURED separately | Runtime has a combined per-checkpoint timer; it excludes the initial pre-parse RAW hash and does not time each substage |

The original observation held all of SRC010128, rather than promoting its partial
decode counters to successful output. DEC-000010 later resolved precisely one
Company Name field. Statistical coverage is 3/450 tables, 11,683 DATA records and
15 column profiles; 135 semantic NULL-dependent metric positions remain
NOT_COMPUTED. Neither 13.468 s nor 11.309 s is a full Databricks processing timer.
No separate statistical-only timer or full-C750 profiling run was recorded.

## Databricks runtime and throughput

MEASURED runtime wall is the saved phase timer. Job wall includes additional
job startup/teardown. DERIVED rates below divide the declared DATA population by
runtime wall; repeated comparator reads are not counted as extra throughput.

| Phase / run ID | Runtime wall s | Job wall s | DATA records/s | Fields/s | Population |
| --- | ---: | ---: | ---: | ---: | --- |
| Smoke `181758407473778` | 92.698 | 130.170 | — | — | Three checkpointed bindings; included in the final 450 |
| Processing `879442057562865` | 753.049 | 789.068 | 2,522.686 | 12,613.430 | All 450 outcomes; freshly packages 447 and revalidates/reuses smoke 3 |
| CLEAN publication/validation `1100860214974411` | 520.931 | 558.359 | 3,646.750 | 18,233.751 | N450 only; all checkpoints independently reverified; two Delta tables created/read back |
| C750 QUERYABLE/validation `368063299510003` | 8,875.574 | 8,911.604 | 35,610.523 | 404,118.999 | Combined population; three views and 108 full-schema multiset groups |
| Step 4 independent native evaluation `332981126328686` | 879.079 | 904.934 | — | — | Full 450 native binding verification plus combined metadata/accountability; extra evaluation, not ingestion |

Processing scope throughput is **220,736.450 input bytes/s** and
**2,151.256 source outcomes/hour**, using 166,225,261 bytes and 450 outcomes
over 753.049 s. Using the whole job denominator instead gives 2,407.530 DATA
records/s, 210,660.249 bytes/s and 2,053.055 source outcomes/hour.
These include checkpoint reuse. Restricting the numerator to fresh 447 work over
the same full-phase runtime gives 2,500.213 records/s, 218,838.993 bytes/s and
2,136.914 newly packaged sources/hour; that denominator also includes reuse work.
There is no isolated cold-450 processing rate.

CLEAN and QUERYABLE rates describe validation scope processed per phase wall,
not streaming input bandwidth or pure SQL execution speed. Applying original RAW
bytes to those phases would misrepresent their repeated Parquet/Delta reads.
Pure Delta commit, SQL-only latency, actual I/O bytes, per-query latency
distribution and sustained/concurrent consumer throughput are NOT_MEASURED.

| Incremental elapsed quantity | Seconds | Interpretation |
| --- | ---: | --- |
| Successful smoke + processing + CLEAN + QUERYABLE runtime sum | 10,242.251 | DERIVED phase sum; excludes failures, gaps and Step 2/4 evaluation |
| Same successful jobs' wall sum | 10,389.201 | DERIVED job sum; not an end-to-end timer |
| Smoke job start to QUERYABLE job end | 30,824.809 | DERIVED observed span; includes failed CLEAN, authorization/redeployment recovery and orchestration gaps |
| First indexed setup failure start to QUERYABLE job end | 34,000.472 | DERIVED broader indexed history span; not all preparation or all Steps 2–4 |
| Continuous total incremental Steps 2–4 wall | NOT_MEASURED | No continuous timer spanning local preparation, human review, all SQL/evaluation and orchestration |

The successful phase job sum is dominated by combined QUERYABLE validation
(8,911.604 of 10,389.201 s). The 108 full-schema comparisons deliberately revisit
historical data. Low recorded driver CPU does not establish executor CPU versus
storage/network bottleneck attribution. The existing hard timeouts were 3,600 s
processing, 3,600 s CLEAN and 28,800 s QUERYABLE; actual phase and job times fit.
This establishes completion within those configured limits, not a production SLA.

## Compute and cost

| Successful phase | Driver CPU seconds | Peak RSS, original platform units |
| --- | ---: | ---: |
| Smoke | 9.254080 | 2,509,628 |
| Processing | 239.417952 | 2,476,496 |
| CLEAN | 163.455433 | 2,503,592 |
| QUERYABLE | 51.902765 | 2,393,812 |

Retained runtime: Python 3.11.10, Spark 4.2.0, PyArrow 14.0.1. RSS is the
process high-water counter, not available cluster memory, executor memory or an
additive phase allocation; retain original units rather than inventing a normalized
cross-host comparison. Available RAM/capacity, executor CPU/RSS, executor-hours,
scratch/disk high water, spill/shuffle and detailed task resource telemetry are
UNAVAILABLE in this measurement scope. Driver CPU is not total cluster CPU.

N450/C750 run-attributed DBUs and monetary cost are UNAVAILABLE in the retained
Steps 2–4 evidence. No new billing query or inferred DBU-to-dollar conversion was
used. Day 2 does retain **25.208114021428571489 DBU**, a partial snapshot at
2026-10-21T09:09:49.410Z: 15 usage rows across 20 queried run IDs, five IDs missing,
including earlier smoke/probes. It is not a complete C300 cost total and cannot be
compared with missing N450 usage. Invoiced dollars and shared warehouse, storage
and egress attribution remain UNAVAILABLE for both cohorts.

## Reliability, automation and human workload

Final N450 processing: **450 COMPLETE, zero missing/extra outcomes, zero failed
or blocked bindings**, zero accepted partial bindings. All 450 native verification
results PASS; 29,305 excess duplicate occurrences across 29,062 groups are retained.
Publication and validation pass, with C300 reused unchanged. The original Step 2
449 eligible / one held outcome and its later approved resolution remain recorded.

The ten indexed remote runs contain five SUCCESS and five FAILED runs. This is an
execution-history count, not a 50% binding failure rate or an account-wide census:

- Four setup/guard failures (DuckDB boot, inventory, historical storage location,
  exact RAW path validation) created no new processing checkpoints.
- CLEAN run `997643049038042` failed before table creation on `errorifexists`;
  corrected `error` retained exclusive-create semantics and reused all checkpoints.
- Each failed run records attempts 0 and 1: ten failed task attempts, five backend
  retry attempts. Successful runs each have one attempt and no retries. Backend
  retries remain visible despite the submissions' configured zero retries.
- A local DNS monitoring interruption reattached to the same QUERYABLE run without
  resubmission. No completed processing checkpoint was rerun; smoke 3 were reused
  in full, and all 450 were reused for publication recovery.

The five failed job walls sum to 1,171.344 s (DERIVED indexed overhead), excluding
unmeasured diagnosis/review time. This sum is not added to the timestamp spans,
which already include failures occurring within their respective boundaries.

Automated work includes deterministic hash/identity/locator verification,
checkpoint reuse, occurrence preservation, publication gates, full-schema multiset
comparisons, applicability inventory and negative-control checks. Semantic/authority
decisions remained human-reviewed: the exact encoding exception, processing scope
and runtime correction were not inferred by automation. Six stored OWNER_APPROVED
processing authorization versions are evidence artifacts, **not six human-review
events**. Actual decision denominator, automated-versus-reviewed decision ratio,
human-review count, people count and review minutes are UNAVAILABLE. No per-record
manual rewrite is recorded; this does not imply zero human engineering effort.

## Day 2 comparison and model evolution cost

The compatible workload definitions are physical footprint, logical member bytes,
bindings, DATA records and DATA fields. Their complete-cohort values appear above.
There is no compatible cold full-cohort runtime pair supporting a speedup ratio.

| Day 2 measured component | Actual observation | Comparison boundary |
| --- | --- | --- |
| Initial Main timeout | 28,836.501 s; 348/720 staged; 211,236,619 DATA records; 26,397,046,033 member bytes | Partial unsuccessful prefix; 7,325.321 records/s is not successful end-to-end throughput |
| Final Main new staging | 2,859.117 s; 291 newly parsed bindings; 37,393,269 DATA records; 548,137,213 fields; 3,700,945,266 member bytes | Reused 429 other bindings; 13,078.607 records/s / 1,294,436.452 member bytes/s are this remaining staging subset only |
| NUM complete job | 8,115.352 s; 12 bindings; 42,768,535 DATA records; 6,063,050,101 member bytes | 5,270.078 records/s includes different stages and quote-boundary recovery scope |
| Final Main publication / CLEAN / QUERYABLE jobs | 582.678 / 1,401.885 / 7,270.038 s | Separately checkpointed jobs; N450 CLEAN combines publication and validation; query population/plan differs |
| Combined C300 reconciliation QUERYABLE job | 8,313.719 s | Historical-only combination, different population and query plan from C750's 108 comparisons |
| Day 2 optional statistics job | 3,257.648 s | 304/732 full-binding envelope sets; 3,261/7,746 column envelopes; 1,670,599 DATA records (0.532%) |

Day 2 independently saved Main/NUM parse-package timer sums were
5,630.546 / 1,478.775 s and verification sums 36,587.600 / 5,172.273 s.
N450 has only combined checkpoint timers, so a parse-only or verification-only
speed comparison is unavailable. Day 2's serial prefix verification dominated its
measured stages; C750's successful job sum is dominated by combined validation.
Neither observation identifies a lower-level hardware bottleneck without telemetry.
Local Day 3's three-table statistics cannot be compared to Day 2's partial
Databricks statistics as equivalent profiling work.

Incremental evolution kept **M1 unchanged**. The new field-local parser profile
and provenance/oracle support for DEC-000010 resolved one source, with 11.309 s
of bounded validation measured; engineering/review duration is NOT_MEASURED.
Runtime fixes addressed dependency/inventory/storage/path guards and the exact
two-line writer-mode correction. V2 versioned FIN/Stability evaluation controls
added checks without changing historical model output. These are real changes;
unchanged M1 does not mean zero implementation cost.

Historical replay/backfill during Day 3: **zero C300 sources / zero bindings /
zero records rebuilt**. Frozen historical outputs were reused; query/FIN checks
still incurred read/validation work, so reuse does not imply zero compute cost.
All 450 checkpoint metadata pins rolled over with original receipts retained and
unchanged Parquet/digests; no processing replay resulted. Historical rebuild cost
was not measured because no rebuild ran. Actual monetary cost of fixes, review,
unmodeled semantics, missing telemetry and other unresolved issues is UNAVAILABLE.
Enterprise integration and broader economic semantics remain outside implemented
scope; no staffing/productivity or linear 300→750 scaling claim follows.

## Evidence and reproducibility

Fresh work for Step 5A consists solely of reading saved JSON/CSV/Markdown,
verifying the consumed evidence pins and deriving arithmetic. No RAW data was
read or altered, no remote job/SQL was submitted and no historical result rewritten.
The derivation and its 928-input hash index remain under ignored
`runs/c750-performance/v1/` (`derive.py`, `measurements.json`, `input-index.json`).
The consumed original receipt hashes also match their provenance-rebind manifest;
Step 2 summary matches the recovery's prior-summary pin; retained Step 4-indexed
inputs match their saved hashes. Existing processing pins and full validation
datasets were reused, not executed again.

| Evidence | SHA-256 |
| --- | --- |
| `runs/c750-performance/v1/derive.py` | `3e042b544674d95a4e199cd83fc13fd6802529190b125c2c0e27a3a4c3406b3d` |
| `runs/c750-performance/v1/measurements.json` | `47e777e67ac747d4530fbd63cdac4fbaa4a8f9458d1ac3ed08f89f6236eb2bfb` |
| `runs/c750-performance/v1/input-index.json` | `28a8f867f4d73a44b4e0a98fa8ec44fa4364d441a5f29cf043edd4987d4f4319` |
| Reused Step 4 V2 `results.json` | `bc4782b25acd7085139017e3f9294ea9a0730a088c77ddf2cd110d98c2f781fe` |

Primary retained references:

- `runs/n450/b1-v1/summary.json`, 450 `sources/*.json` and
  `runs/n450/src010128-recovery-v3/validation.json`: local profiling scope/timers.
- `runs/n450/step3-exact-path-v1/{smoke,full}-result.json`: original processing.
- `runs/n450/step3-clean-write-fix-v1/{publish,query}-result.json` and
  `checkpoint-provenance-rebind.json`: actual publication, query and receipt pins.
- `runs/c750-stability/v2/{results,c3-retained-execution}.json` and `live-jobs/`:
  verified scope, runtime limits, run timestamps, failure/attempt history.
- `runs/c750-stability/v1/remote-mechanical-result.json`: independent native
  verification and duplicate multiplicity counts.
- `/Users/lightnino/Projects/edp-lab/runs/c300-m1/day2_completed_recovery_20261021_v1/benchmark.json`:
  Day 2 job measurements and partial billing snapshot; supporting interpretation
  remains in the unchanged Day 2 reports.

See [Step 4 V2 evaluation](../docs/c750_stability_v2_evaluation.md) for the
source-preserving acceptance boundary and deployed/snapshot pins. Step 5A ends
with this performance report; no C750 result freeze or further phase is performed.
