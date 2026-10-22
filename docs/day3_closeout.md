# Day 3 final result and exit

Day 3 Exit: **COMPLETE for the declared experimental M1 source-preserving scope**.
Result: **O_C750_M1_V1 FROZEN**, retaining `M1_LEXICAL_V1`,
`LOSSLESS_6_FIN_SUITE_V2` and `STABILITY_M1_V1`.
This does not establish enterprise semantic integration, production readiness,
cost efficiency, staffing efficiency or downstream business correctness.

The owner explicitly authorized final result freeze, conditional on actual
integrity checks, and GitHub closeout. The existing authorization/references/final
marker convention is reused; no new host pin, approval framework or future
effective time is introduced. Operational timestamps are actual recording times.

## Accepted result and exit mapping

| Requirement | Actual result | Authoritative reference |
| --- | --- | --- |
| Historical C300 | 300 sources / 732 bindings; unchanged O_C300_M1; zero historical processing replay/backfill | [Original seal](../metadata/freezes/O_C300_M1_v1/freeze.json) and unchanged original references |
| N450 admission | 450 approved physical sources, exact IDs/RAW paths/hashes | [Admission](../metadata/admissions/N450_v1/admission.json) |
| C750 cohort | 750 distinct identities = disjoint 300+450; original input freeze unchanged | [Cohort marker](../metadata/freezes/C750_v1/freeze.json), exact roster and bindings |
| B1 | 450/450 eligible under approved profiles; M1 retained | [B1 v3](../metadata/evaluations/n450_b1_v3.json); DEC-000010 exact field-local exception |
| N450 CLEAN | 450/450 COMPLETE; 1,899,705 DATA records; 9,498,525 fields | [Step 3](n450_c750_execution_evidence.md), retained original checkpoint/readback evidence |
| C750 QUERYABLE | 1,182 bindings; 316,063,821 DATA records; 3,586,787,936 fields; 108/108 multiset checks | Original pinned three view definitions and accepted native receipts |
| Lossless 1–6 | Required scoped controls PASS for C300/N450/C750, including FIN V2 | [Stability V2](c750_stability_v2_evaluation.md): mandatory FIN_001 2/2, FIN_002 1/1 with wrong-equity control, 13 lineage witnesses; N450 applicability/noninterference over 450 schemas/2,250 fields |
| Stability | Separate A, B2, C1, C2.1–C2.4 and C3.1–C3.4 PASS; C_M1_SOURCE_PRESERVING_PASS | Accepted [PR #26](https://github.com/lightnino/edp-lab/pull/26) |
| Performance | PARTIAL_MEASURED; processing 753.049 s, CLEAN 520.931 s, combined QUERYABLE validation 8,875.574 s | [Scale report](../reports/c750_scale.md), accepted [PR #27](https://github.com/lightnino/edp-lab/pull/27) |
| Write Tasks | Delivered / existing equivalents / explicitly deferred or not implemented | [Full mapping](c750_write_tasks.md), [FD report](../reports/c300_fd_regression.md), accepted [PR #28](https://github.com/lightnino/edp-lab/pull/28) |
| Result freeze | FROZEN with verified evidence retrieval and bounded original-snapshot readbacks | [Final marker](../metadata/freezes/O_C750_M1_v1/freeze.json), [exact references](../metadata/freezes/O_C750_M1_v1/references.json) |
| Day 3 Exit | COMPLETE in the declared acceptance scope | [Machine-readable exit](../metadata/evaluations/day3_exit_v1.json) |

Prerequisite artifacts were checked against current GitHub main, revision
`4d4aec8ee844d69c299f3f2342e93bb8cbff8149`; all three PRs are MERGED.
The consumed 1,135 Stability input hashes, 84 indexed V2 evidence files and 928
Performance input hashes match. Overlapping indexes are not counted as distinct
source populations. No accepted processing, Lossless, Stability or Performance
evaluation was rerun; only freeze-specific hash, metadata and retrieval checks ran.

## Snapshot preservation and evidence retention

All six managed Delta table/UC identities match accepted evidence. Their consumer
data snapshots remain explicitly **version 0**. All six current metadata versions
are **1**: C300's pre-existing retention operation is unchanged; only the two N450
tables received new `SET TBLPROPERTIES` operations for this result freeze.
No record, field, checkpoint Parquet or consumer SELECT definition changed.

The existing C300 convention was applied to N450: 90-day Delta log/data retention,
append-only, and effective table-level predictive optimization disabled. An initial
catalog/schema-only guard observed inherited ENABLE; table-level inspection proved
all four historical C300 tables already had explicit DISABLE overrides. Only N450
needed new overrides. The failed preliminary guard and its resolution are retained;
there was no historical data/protection discrepancy or hidden waiver.
One bounded version-0 read per table PASS supplements the unchanged accepted
full-population verification. These retrieval witnesses are not a new full scan.

The evidence archive contains 1,853 indexed files: accepted operational evidence,
exact runtime archives/contracts and owner pins, source/receipt references, reports,
scripts and actual metadata/retention readbacks. It contains no RAW, Parquet or
database payload. It was uploaded without overwrite to the existing managed Volume
and retrieved with every indexed member hash and complete archive SHA verified.

- URI: `/Volumes/workspace/edp_lab/raw/n450-m1/final_freeze_20261022_v1/o-c750-m1-evidence-v1.zip`
- Bytes: `12616145`
- SHA-256: `be023e2415077f1611dcab6c5416671ab61287d80d3ceeed79b0e80414fc6082`
- Local operational records: `runs/c750-freeze/v1/`; generated evidence stays outside Git.

The [freeze references](../metadata/freezes/O_C750_M1_v1/references.json) pin actual
parser/code/configuration/rule/authorization versions, storage locations, view SQL
hashes, original run IDs, exact counts, accepted evaluation references, retention
owner/review date and retrieval/reproduction instructions. The final marker is
written exclusively and last, after integrity and archive retrieval checks PASS.

## Accepted limitations and maintenance

Enterprise semantic integration and general business FD testing remain
**NOT_IMPLEMENTED**; normalized mini schema remains **DEFERRED**. Broader economic
fields are PRESERVED_NOT_MODELED; FIN acceptance is scoped, not universal economic
reconciliation. Source NULL/business-key meaning remains unresolved, bounded
profiling remains partial and DEC-000010 remains the single exact encoding
exception. Original failed attempts and the V1 combined BLOCKED result are preserved.

Performance retains its original coverage and denominators: successful job-wall
sum including smoke 10,389.201 s, observed smoke-to-QUERYABLE span 30,824.809 s.
The span includes recovery/gaps and is not a cold end-to-end benchmark. Missing
DBU/dollar/executor and human-review count/time telemetry is unavailable, not zero.

Managed storage is not WORM or an independent disaster-recovery copy. Privileged
owners can change properties or delete tables/RAW/evidence, and workspace loss
remains a risk. Retention is finite: review/extend N450 preservation by the date
in the freeze references; the original C300 review deadline remains **2027-01-18 UTC**.
No destructive VACUUM, overwrite, DROP or baseline-writer changes are permitted by
this closeout. No full recovery after workspace loss is claimed. These limitations
are explicit within the existing experimental retention convention, not production
durability acceptance.

There are no outstanding required integrity blockers. **Day 4: NOT STARTED.**
