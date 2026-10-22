# C750 Day 3 Step 4 V2 — scoped Stability supplemental evaluation runbook

**Purpose:** Reevaluate the existing C750 candidate using the permanent
`LOSSLESS_6_FIN_SUITE_V2` and `STABILITY_M1_V1` contracts. This page is a
**runbook, not a completed V2 scorecard**. Retain PR #23's V1 evidence.

## Reuse, do not replay

- **A:** Reuse PR #23 verified C300 membership, 300 parent RAW hashes,
  732 frozen bindings, version-0 readbacks, FIN_001 (2/2), FIN_002 (1/1)
  and the 13 exact historical lineage witnesses. Original C300/C750
  historical-equivalence evidence had zero differences.
- **B2:** Reuse native N450 full independent verification for 450/450
  bindings, 1,899,705 DATA records, 9,498,525 fields; exact source-aware
  locators and values. Existing Lossless 1–5 evidence remains valid.
- **C1:** Reuse the 108/108 full-schema combined multiset comparison
  receipts and pinned six version-0 snapshots; 750 distinct source identities,
  1,182 bindings, 316,063,821 DATA records and 3,586,787,936 fields.
- No RAW/CLEAN re-ingestion, C300 replay, pipeline redeploy, M1 revision,
  original-evidence rewrite, C750 result freeze or Step 5 processing.

## Exact missing V2 validations (run against retained evidence or targeted read-only queries)

1. **Lossless 6 V2 B2:** inspect the complete 450 binding schema inventory,
   prove the five SEC Daily Master columns are filing-index metadata and have
   zero **modeled** economic measures under M1, inventory and disposition any
   exceptional economic-looking field, and prove that adding N450 contributes
   no FIN_001/002 facts. Outcome is tested applicability/noninterference **PASS**
   only if backed by all-source evidence; never fake a numeric equation for N450.
2. **Lossless 6 V2 C1 + C2.4:** require FIN_001 (both dates) and FIN_002
   (including wrong-equity negative control) on actual pinned historical and
   C750 view definitions, exact independent fixture equality, source/run/locator
   lineage equality for all 13 historical witnesses, and zero bidirectional
   differences. Reuse previously verified matching evidence only after digest/
   view-version checks; a new SQL replay is unnecessary if pins are unchanged.
3. **C2.1–C2.3:** verify source-ID disjointness, exact source/binding/run
   memberships, version-pinned full-schema old/new/combined multiset
   comparators, with zero losses, additions, false merge/split, and historical
   projection differences. Run the offline **intentional bad-merge / duplicate-
   collapse / fanout** negative controls in
   `tests/stability/test_stability_m1_v1.py`. An isolated synthetic check
   cannot replace the full native-query comparison.
4. **C3.1–C3.3:** reconcile all 450 COMPLETE receipts, checkpoint hash pins,
   zero successful-binding reprocess, zero C300 historical reprocessing,
   exclusive-create publication history, final Delta version-0 readbacks,
   and remote successful runs. Preserve original failed attempt evidence.
5. **C3.4:** calculate wall times and throughput from retained execution
   reports, covering full binding processing (~753 s), CLEAN (~520.931 s)
   and QUERYABLE (~8875.574 s) **as previously reported, not fresh
   measurements**. Obtain the pre-existing configured job/runtime budgets or
   separately **owner-accepted** phase limits and compare **actual vs budget**
   for each phase. Report available DBU, executor CPU/RSS, monetary and human
   telemetry; mark absent optional data as UNAVAILABLE, not observed zero.
   Do not invent an ex-post budget merely to obtain PASS.
6. Produce `docs/c750_stability_v2_evaluation.md` and new indexed evidence
   under `runs/c750-stability/v2/` (gitignored run data + tracked references).
   Use status PASS/FAIL/BLOCKED per control, list exact populations,
   reused vs freshly computed artifacts and hash them. **No family-level
   Lossless 6 NOT_APPLICABLE** in the new report.

## Promotion boundary

- A, B2, C1, C2.1–C2.4, C3.1–C3.4 and mandatory FIN V2 must each be verified
  before `C_M1_SOURCE_PRESERVING_PASS`.
- Report `C_ENTERPRISE_SEMANTICS_PASS` **only** if genuine independently
  declared entity/relationship/meaning controls exist and pass. None are
  inferred from lexical identity or the three fixed FIN contexts.
- A/B2 PASS + C1 PASS do not automatically imply combined C2/C3 PASS.
- Do not rewrite `docs/c750_stability_evaluation.md` or frozen Day 2.
  Supplemental V2 can replace it as *current* acceptance without erasing
  original evaluation history.
