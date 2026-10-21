# Day 2 profiling notes

All 732 lexical execution scopes are validated; protected retention remains
UNVERIFIED, so no final freeze/global Day 2 PASS is issued. See the baseline,
performance report, recovery contract and Performance Finding.

Original parser/materialize/independent verifier bytes remain unchanged. Recovery
uses verified COMPLETE checkpoint content, exact existing binding fingerprints,
bounded parent-scoped jobs and disjoint exact CLEAN/QUERYABLE comparisons. Original
RAW, GOLD, C300 freeze, historical errors and all run versions remain unchanged.
Only 291 missing/incomplete bindings were parsed after reusing 429 completed ones.

Five profiling functions are unchanged. Optional workers consume complete verified
Parquet bindings, never a substituted sample or new RAW parse. Bounds are two
million member bytes, 120 seconds per worker, 8 GiB virtual address space and a
1,800-second threshold for admitting new statistical workers. Later checkpoint
I/O, exports and artifact hashing are additional measured job work. Completed
envelopes are reused; unavailable metrics preserve
NOT_COMPUTED reasons. Source NULL semantics and candidate-key eligibility remain
unresolved. Lexical values/multiplicity/locators are preserved, not interpreted.
Historical lexical-only Lossless 6 remains NOT_APPLICABLE in the original run
evidence. The later FIN_EVAL_V1 overlay is SCOPED_PASS for FIN_001/FIN_002 only;
see `reports/C300_baseline.md` and `metadata/evaluations/fin_eval_v1.json`.

Contracts/runtime packages and controller snapshots retain exact model/rule,
code/dependency/input hashes, versions, source references, parameters, configuration,
SQL, job IDs and telemetry limitations. Original three-family smoke replay and
bounded NUM replay remain scoped evidence; unchanged GOLD/C300 checks were reused.
No Stability A/B/C, semantic integration, final freeze or Git publication occurred.

## Actual coverage at closeout

Structural profiling is COMPLETE: 732/732 outcomes, 7,746 column positions and
732 schema fingerprints (12 distinct lexical hashes). Statistical profiling is
PARTIAL: 304/732 complete binding sets and 3,261/7,746 column envelopes. Those
sets cover 1,670,599/314,164,116 DATA records (0.532%) and 19,079,503/3,577,289,411
fields (0.533%); binding coverage is not record coverage. Counts are derived from
the retained table/column profile exports indexed in `metadata/baselines/O_C300_M1.json`.

Missing statistics: 257 bindings/3,630 positions exceed the 2,000,000-byte member
budget; 171 Daily Index bindings/855 positions were not scheduled before the
global threshold. No NUM, PRE, TAG or 13F INFOTABLE binding has a completed
statistical set. FSDS SUB has 25/60; six smaller 13F datasets have 252/252; Daily
Index has 27/198. Completed envelopes still leave semantic NULL metrics and key
eligibility NOT_COMPUTED. These limitations may be accepted for a scoped historical
baseline; they cannot be relabeled full statistical PASS.
