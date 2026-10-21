# Day 2 Performance Finding — FND-DAY2-PERFORMANCE-TIMEOUT-001

Original run **427800138450251** timed out at **8 hours** with **348/720 main
bindings staged**. Actual job wall was 28836.501 seconds.
The retained prefix contains 211,236,619 DATA occurrences, 2,261,851,840 fields
and 26,397,046,033 uncompressed member bytes. Partial staging throughput was
7,325.321 records/s, 78,437.111 fields/s and 915,403.919 member bytes/s.
These are not successful end-to-end rates.

Measured serial stage sums were 3,922.388 seconds parsing/packaging and 24,355.719
seconds independent verification. Verification dominated those measured stages.
The established immediate cause was a serial corpus task exceeding its fixed
execution limit; lower-level CPU versus I/O attribution remains NOT_ESTABLISHED.
The independent oracle and approved source/processing semantics were preserved.

Recovery verified reusable COMPLETE checkpoints, excluded them from new parsing,
and split staging, publication, CLEAN validation, gating and QUERYABLE validation
into bounded checkpointed jobs. Final staging reused **429** bindings and parsed
only **291**, with 37,393,269 DATA occurrences, 548,137,213 fields and
3,700,945,266 uncompressed member bytes in **2859.117 seconds**.
Measured rates were 13078.607 records/s,
191715.559 fields/s and 1294436.452 member bytes/s.
This mixed workload differs from the original prefix; no linear speedup is claimed.

Recovery's observed job span was **24096.738 seconds**, including orchestration
gaps, overlapping stages, setup failures 579155785972496 and 625828136264800, and
the controlled stop of recovery 476248727361002 to avoid repeating a completed
Daily Master smoke binding. Its 80 COMPLETE bindings were retained and verified.
The NUM 12/12 run remained unchanged. No known completed binding was reparsed.
All 732 execution scopes subsequently passed required lexical CLEAN/QUERYABLE
checks; Test 6 remains explicitly NOT_APPLICABLE under M1_LEXICAL_V1.

Exact job timings, runtime, Delta output bytes/files and available run-attributed
DBU usage appear in [the measured report](profile_summary_day2.md) and
`runs/c300-m1/day2_completed_recovery_20261021_v1/benchmark.json`. Recent missing billing rows are not zero;
invoiced monetary cost and shared warehouse/storage/egress attribution remain
UNAVAILABLE. Worker-time sums are not end-to-end wall time. Executor CPU/memory,
spill/shuffle and scratch high-water telemetry were not exposed where indicated.

Scaling requires workload sizing by records/fields and member bytes, complete
checkpoint inventories, independently budgeted verification and query phases, and
measured resource/concurrency tradeoffs. This experiment establishes neither linear
scaling nor the staffing hypothesis. Historical protected retention remains
UNVERIFIED; no final freeze/global Day 2 PASS or Git publication is issued.

Finding Schema v1 record and final measured companion:
`runs/c300-m1/day2_completed_recovery_20261021_v1/performance-finding-v2.json` and
`performance-finding-metrics-v2.json`. Original finding/metrics and every failed,
interrupted, completed and timed-out run remain retained under their original paths.
