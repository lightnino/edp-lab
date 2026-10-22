# C300 FD and source-preserving regression — Day 3 closeout

Result: **historical source-preserving regression PASS; business FD regression
NOT_IMPLEMENTED**. No general business FD set was tested or approved for C300,
N450 or C750. This report records that gap rather than inventing FD confidence,
keys or a normalization experiment. It adds no historical replay.

## Population and integrity

| Scope | Physical sources | Logical bindings | DATA records | DATA fields |
| --- | ---: | ---: | ---: | ---: |
| Frozen C300 | 300 | 732 | 314,164,116 | 3,577,289,411 |
| N450 | 450 | 450 | 1,899,705 | 9,498,525 |
| C750 | 750 | 1,182 | 316,063,821 | 3,586,787,936 |

Metadata closeout verifies exact C300+N450 membership, all 750 distinct physical
identities, exact RAW hash/path references, and all admission/cohort-freeze file
hashes against their published markers and owner-record scopes. The additive v4
manifest has 754 registry rows: original 304 unchanged plus 450 new. It is not a
750-row cohort roster. C750 source membership is FROZEN; `O_C750_M1` outputs are
**not frozen** and Step 5C has not started.

Actual RAW integrity reuses the already verified Step 4 evidence for all 750
sources and unchanged input pins. This write task checks metadata references,
not a fresh RAW scan. Original C300 rosters, manifests, M1 references and accepted
Step 4 evidence remain unchanged. No semantic entity equivalence is inferred.

## Profiling, key and FD coverage

| Check | Actual coverage / finding | Limit |
| --- | --- | --- |
| C300 structural evidence | 300 sources; 732 bindings; 7,746 column positions | Reused frozen historical references; no replay |
| C300 optional statistics | 304 full-binding tool-envelope sets; 3,261 column envelopes; 1,670,599 DATA records (0.532%) | Historical partial coverage; resource-limited/NULL-dependent values remain NOT_COMPUTED |
| N450 structural/model fit | 450 full-byte observations; current 450/450 FITS_EXISTING_MODEL after DEC-000010 | Original 449 eligible / one HUMAN_UNRESOLVED result preserved; not a retroactive strict UTF-8 PASS |
| N450 statistics | SRC010001/SRC010226/SRC010450; 11,683 DATA rows; 15 column profiles; 179 excess literal duplicates | Three full selected tables only; 135 NULL-dependent metric positions NOT_COMPUTED |
| Tested key-related observation | SRC010001: 4,997 rows versus 3,096 distinct literal CIK values | CIK is not unique in this table; does not test CIK→Company Name |
| Candidate scans | Existing bounded lexical uniqueness/minimality implementation and historical profiling envelopes | Semantic candidate eligibility stays NOT_COMPUTED under unresolved source NULL rules; no business key approved |
| General FD discovery / FD regression | NOT_IMPLEMENTED; zero declared Day 3 business FD experiments | No determinant/dependent population, confidence, tolerance or business confirmation fabricated |

Exact-row duplicates do not by themselves disprove a value FD. Conversely,
absence of duplicate X values in a sample would not approve a permanent FD.
Source/run/binding/locator uniqueness and schema fingerprints are technical
invariants, not discovered business dependencies. See
[normalization notes](../docs/normalization_notes.md) for the distinctions.

## Processing, Lossless and Stability

M1 remains `M1_LEXICAL_V1`. N450 processing is 450/450 COMPLETE, with zero
failed/blocked/missing final binding outcomes. Frozen C300 contributes its original
732 PASS bindings; C750 exposes three version-pinned views over six version-0
Delta reads. C300's latest table version 1 reflects pre-existing retention metadata,
not rebuilt data; N450's two tables remain at original version 0.

| Evaluation | Actual accepted outcome | Scope and reused evidence |
| --- | --- | --- |
| Lossless 1–5, A | PASS | Historical validated Day 2 evidence, unchanged hashes/snapshots/references |
| Lossless 1–5, B2 | PASS | Actual independent full native 450-binding verification; all 1,899,705 DATA records / 9,498,525 fields |
| Lossless 1–5, C1 | PASS | 108/108 full-schema native multiset comparisons across all 1,182 bindings |
| Lossless 6 V2, B2 applicability/noninterference | PASS | All 450 schemas / 2,250 field positions; zero modeled economic measures; zero N450 native facts eligible for exact FIN scope; no invented numerical equations |
| Mandatory Lossless 6 FIN, A/C1/C2.4 | PASS | FIN_001 2/2 and FIN_002 1/1, wrong-equity signal 1,232,700,000.0000, 13 unchanged lineage witnesses; exact fixture/zero tolerance |
| Stability A / B2 / C1 | PASS / PASS / PASS | Separate populations and checks; neither cohort alone substitutes for combined validation |
| Stability C2.1–C2.4 | PASS | Source identity isolation, no unintended merge/split, unchanged old/new projections, FIN noninterference; false-merge/duplicate-collapse/fanout/locator/namespace negative controls |
| Stability C3.1–C3.4 | PASS | Completion, historical preservation, checkpoint recovery and verified original hard timeouts |
| Overall current Stability | C_M1_SOURCE_PRESERVING_PASS | Under LOSSLESS_6_FIN_SUITE_V2 and STABILITY_M1_V1; enterprise semantics NOT_IMPLEMENTED |

Full native N450 evidence preserves 29,062 equal-looking groups, 58,367 participating
occurrences and 29,305 excess occurrences. There is no deduplication or canonical
entity merge. The V1 combined BLOCKED result and old Lossless 6 applicability
labels remain historical facts; V2 supersedes evaluation coverage under explicit
versioned rules without rewriting those reports. Family-level FIN regression
is mandatory, not waived as NOT_APPLICABLE. Wider economic semantics remain
PRESERVED_NOT_MODELED; three FIN contexts do not prove population-wide economics.

## Performance, recovery and human effort

The accepted [performance report](c750_scale.md) is unchanged from merged
[PR #27](https://github.com/lightnino/edp-lab/pull/27), merge
`8f51a8bf5a8b84f6e2108138da6b4c2d01582503`. Coverage remains PARTIAL_MEASURED:
processing 753.049 s, CLEAN 520.931 s, QUERYABLE 8,875.574 s; successful job-wall
sum including smoke 10,389.201 s; observed smoke-to-query span 30,824.809 s.
The span includes recovery/gaps and is not a cold end-to-end benchmark.
DBUs/cost, executor resources and actual review minutes remain unavailable where
recorded; no source-count linear scaling or staffing conclusion is inferred.

Five indexed successful runs and five failed runs remain reported. The failed
runs have ten task attempts/five backend retries; four setup/guard failures made
no new processing checkpoints and the failed CLEAN write created no tables.
Recovery reused smoke 3 in full and all 450 original checkpoints for publication.
Six stored OWNER_APPROVED authorization versions are not six review events;
actual review count/person/minutes are UNAVAILABLE. The exact field-local encoding
decision and two-line writer correction required real owner authority.

Day 3 changed a scoped parser/verifier profile for one field and runtime/evaluation
controls, while preserving M1 and all historical output. C300 historical replay,
model backfill and historical rebuild volume are zero. Checkpoint pin rollover
changed provenance metadata, not Parquet. Historical validation still reads data;
zero replay does not mean zero compute. Engineering/review and unresolved semantic
issue costs were not measured. No FD-based transformation was implemented.

## Reproducible references

- Membership/manifest: `metadata/freezes/C750_v1/`,
  `metadata/admissions/N450_v1/`, `metadata/corpus_manifest_v3.csv` and
  `metadata/authorizations/n450_execution_v1.json` (admission/cohort-freeze scope).
- Model fit: `metadata/evaluations/n450_b1_v3.json`,
  [B1 assessment](../docs/n450_b1_assessment.md),
  `runs/n450/b1-v1/statistics/SRC010001.json` and the other two selected tables.
- Actual accepted execution: [Step 3 evidence](../docs/n450_c750_execution_evidence.md),
  [Stability V2](../docs/c750_stability_v2_evaluation.md),
  `runs/c750-stability/v2/results.json` SHA-256
  `bc4782b25acd7085139017e3f9294ea9a0730a088c77ddf2cd110d98c2f781fe`.
- Current write-task metadata checks: `runs/c750-write-tasks/v1/metadata-validation.json`;
  performance report SHA-256
  `de5ff14da6ed07db67cb7f5c843043aa4b47920116d77e2233a8dd9583d85b75`.
- [Write Task mapping](../docs/c750_write_tasks.md) records every required artifact,
  equivalent and explicit deferral. No new profiling registry or FD result store.
