# Initial scope and current registration

Historical initial inspection covered SEC `SUBMISSION.tsv`, SEC `INFOTABLE.tsv`,
Nasdaq `nasdaqlisted.txt` and `otherlisted.txt`; their manual observations remain
in `metadata/source_inventory.csv` and `metadata/source_profiles/`.

Current physical identities and expected RAW hashes are in the populated
`metadata/corpus_manifest.csv`, not the semantic inventory. Frozen GOLD_V1 has
three physical instances; GOLD_V2 adds SRC000004 and registers 13 logical tables
across four physical instances. See [registration](gold_set_v2_admission.md),
[source identity](source_instance_identity.md) and [parsing freeze](parsing_profiling_freeze_v2.md).
Registration and parser validation do not establish completed production profiling,
business keys, entity resolution or C300 admission. No C300 cohort exists.

Subsequent profiling implementation has executed all five deterministic profiling
functions on all 13 GOLD_V2 tables; see [completion evidence](preflight_exit_checklist.md).
This preserves the registration boundary above. C300 execution still requires
future admission and reviewed parser registration.

SEC 2013 Q2 is a filing dataset and can reference earlier report periods.
The Nasdaq snapshots were generated 2026-10-15 03:03 (unknown timezone).
Do not presume contemporaneous history.
