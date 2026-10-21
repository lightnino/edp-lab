# Day 2 C300/M1 checkpoint recovery V1

Authority: the user's explicit instruction after main run `427800138450251`
timed out. Necessary recovery/performance changes and new Databricks jobs are
approved; no business, parser, model or lexical verification semantics change.
NUM run `653857229258835` remains a separately validated twelve-binding output.
No prior evidence, RAW or frozen registry is overwritten. Git publication and
historical retention protections are not established by this instruction.

Recovery verification run `686073592751900` completed SUCCESS. It checked all
348 original COMPLETE receipt hashes, actual stored Parquet hashes/sizes/schema/
row counts and original independent-oracle results. All 348 are valid and reused;
zero source records were parsed. All 300 frozen RAW parent hashes matched.
Detailed evidence: `runs/c300-m1/checkpoint_recovery_20261021_v1/`.
These stored checkpoints are retrievable and content verified; protected historical
retention remains UNVERIFIED, so this is not a freeze claim.

`main_recovery_20261021_v1` partitions only the 372 missing main bindings into
17 deterministic parent-scoped batches, targeting at most 512 MiB and 96 bindings
per batch (a single parent group stays intact). Four dependency lanes bound
concurrency; each task has a one-hour timeout and every successful binding writes
an exclusive, hash-checked Parquet checkpoint followed by a COMPLETE receipt.
Task completion markers follow all binding receipts. The original lexical
`materialize`, `verify_parquet` and parser module bytes are unchanged.

Publication occurs only after exact 720-binding membership and all batch completion
markers verify. It references the original 348 checkpoints in place, plus new
missing-binding checkpoints; no completed binding is parsed again. It writes new
exclusive Records and Bindings Delta tables, and emits all 732 binding outcomes.
The validated NUM tables and original main/NUM runs remain unchanged.

CLEAN exact multiset comparisons, uniqueness/count checks and downstream exact
record/field/coverage comparisons run in disjoint groups (target 12 million records
and at most 96 bindings). Each group is checkpointed. A retained gate is created
only after all main validation groups pass; consumer views use explicit gate PASS
membership and pinned Delta versions. Lossless 6 retains the approved lexical-only
NOT_APPLICABLE boundary with its full per-header inventory. No economic PASS is
inferred. Full reconciliation receives a new versioned contract pointing to the
new main snapshots and the unchanged NUM snapshots; the earlier prepared v3
contract remains unmodified. Combined SQL uses disjoint UNION ALL and all 732
binding outcomes, followed by independent partitioned exact multiset comparisons.

Optional statistics remain separate from mandatory CLEAN correctness. Failed or
resource-limited metrics are NOT_COMPUTED; source NULL semantics/key eligibility
remain unresolved. Timings, actual scope, runtime/code/input hashes, job IDs,
missing telemetry and original timeout are retained. Successful lexical gates do
not establish protected retention, economic integration or Stability A/B/C.

## Subsequent checkpoint-plan versions

V1 setup failed before parsing because the batch parent directory was absent.
V2 failed before record emission because the package omitted frozen reference
JSON. V3 restores the original runtime metadata closure, verified by the actual
frozen-metadata loader against an isolated extraction. Both failures and all
overhead are retained. V3 then produced 80 valid COMPLETE checkpoints.

The original Daily Master smoke binding SRC000173 was outside the timeout's
348-binding set. Its later V3 batch had not started. Only the new V3 recovery
run 476248727361002 was stopped to prevent repeating that previously completed
binding; the original timeout and NUM runs were untouched. All 80 new COMPLETE
checkpoints passed subsequent content verification. Verification run
200272186433720 inherits the unchanged original348 checks and verifies those
80 plus the Daily Master smoke, yielding 429 reusable checkpoints. No completed
binding was reprocessed. Uncheckpointed interrupted work is incomplete, preserved
and included in recovery overhead, not reported as successful completion.

V4 run 758804395366009 assigns only the remaining 291 bindings to eleven bounded
tasks. It explicitly excludes all three original smoke bindings, the original348
and the 80 new COMPLETE bindings. Each task has max_retries=0; source/processing
semantics remain unchanged. Reconciliation and statistics descriptors were
versioned to reconciled_recovery_20261021_v2 and stats_recovery_20261021_v2,
pointing to the new V4 main snapshots; prior descriptors remain unmodified.
Host controller invocations retain source snapshots and action receipts.
