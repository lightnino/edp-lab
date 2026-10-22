# Day 4 Step 0 — Historical M1 baseline

Status: **BASELINE_VERIFIED (reused accepted Day 2/Day 3 freeze evidence)**

- Day 2: `metadata/freezes/O_C300_M1_v1/freeze.json` = FROZEN, exit `COMPLETE_WITH_ACCEPTED_PARTIAL_RESULTS`.
- Day 3: `metadata/freezes/O_C750_M1_v1/freeze.json` = FROZEN, exit `COMPLETE`, with 30 pinned repository evidence files.
- Authoritative result references: `metadata/freezes/O_C750_M1_v1/references.json`.
- Day 3 acceptance: `metadata/evaluations/day3_exit_v1.json`; blockers = empty. `docs/day3_closeout.md` records the scope.
- C300 300 physical / 732 bindings, N450 450 physical, C750 750 physical / 1,182 bindings.
- Historical Lossless 1–6 PASS **for declared source-preserving/FIN scope**; Stability A/B2/C accepted as `C_M1_SOURCE_PRESERVING_PASS`.
- C750 QUERYABLE: 316,063,821 DATA records, 3,586,787,936 fields and 108/108 multiset comparisons.
- Performance remains `PARTIAL_MEASURED`; general enterprise semantics, business FDs and normalized mini-schema were not accepted as implemented.
- Historical C300/C750 RAW, CLEAN, QUERYABLE and M1 evidence remain immutable inputs to Day 4; no replay, reinterpretation, or overwrite is authorized by this baseline review.

**Basis:** read-only verification of the accepted, merged GitHub freeze and exit artifacts from Day 2/Day 3. This review reuses the original documented Databricks snapshot/hash readbacks and does not claim to have repeated live remote validation.

Day 4 Step 1 remains separate and needs **actual** N750 admission and C1500 cohort freeze. No processing authorization is implied.
