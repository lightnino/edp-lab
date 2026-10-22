# C750 M1 Stability — A / B2 / C

Evaluation authority: [evaluation contract](evaluation_contract.md), especially
§§2.1, 3.1, 5 and 6. These are separate scope results, not an inferred combined PASS.

| Evaluation | Status | Accepted scope |
| --- | --- | --- |
| A — historical C300 regression | **PASS** | Frozen accepted M1 lexical baseline and the existing FIN_EVAL_V1 scoped results |
| B2 — N450 Lossless | **PASS** | Actual native N450 M1 outputs; applicable Lossless 1–5 PASS; Lossless 6 NOT_APPLICABLE |
| C — full combined C750 stability | **BLOCKED** | Tested structural/lexical controls PASS; required enterprise semantic/cross-source controls NOT_IMPLEMENTED, so full promotion is withheld |

No failed data comparison or unexpected historical output difference was observed
within the tested scopes. No enterprise semantic integration PASS is claimed.
Publishing this report records the BLOCKED C outcome; it does not promote C750
or waive any NOT_IMPLEMENTED control. The evaluation ends at Day 3 Step 4:
O_C750_M1 is not frozen and Step 5 is not started.

## Tested population and model

| Population | Physical sources | Logical bindings | DATA records | Fields |
| --- | ---: | ---: | ---: | ---: |
| Historical C300 | 300 | 732 | 314,164,116 | 3,577,289,411 |
| New N450 | 450 | 450 | 1,899,705 | 9,498,525 |
| Combined C750 | 750 | 1,182 | 316,063,821 | 3,586,787,936 |

Model: `M1_LEXICAL_V1`. The compatible frozen rule set is
`C300_LITERAL_IDENTITY_V1` plus the already approved historical
`C300_FSDS_NUM_QUOTE_BOUNDARY_V1` scope. Every coverage row was checked against
its original run, binding, source, RAW/member hashes, model and rule reference.
This is one M1 with its documented scoped rules, not an unreviewed M1/M2 mixture.
All six CLEAN data snapshots are read at Delta version 0. C300's previously
recorded version-1 retention metadata is not a data/model revision.

Fresh Databricks evaluation run: `332981126328686`, SUCCESS. Mechanical checks
measured 879.079 seconds wall time. The evaluation wrote only its isolated evidence
and temporary native-format validation export; production CLEAN, QUERYABLE, RAW,
O_C300_M1 and original checkpoint receipts were not changed.

## A — Historical C300 regression: PASS

**Reused evidence.** The frozen Day 2 per-binding Lossless 1–5 evidence covers all
732 historical bindings. Its accepted lexical and financial limitations remain
unchanged. Full Step 3 combined record/field/coverage multiset evidence was reused
only after checking all 155 indexed evidence fingerprints, including all 108
validation-group identities/receipts. No full historical ingestion was repeated.

**Recomputed checks.** Original C300 membership and all O_C300_M1 frozen file
references match; current remote RAW SHA-256 matches for all 300 physical sources.
Original Delta/Unity Catalog identities and version-0 readability were checked.
The three historical QUERYABLE definitions match the hash-verified saved baseline.
The original FIN_001/FIN_002 SQL and independent expected-results fixture were
hash verified and replayed on both historical and C750 views at the same binding,
original run, filing/date contexts, DECIMAL(38,4) type and zero tolerance.

- FIN_001: **2/2 PASS**, exact amounts, dates and both equations match the fixture.
- FIN_002: **1/1 PASS**, exact amounts and negative control match. The incorrect
  parent-only equity choice still produces the expected nonzero difference
  `1232700000.0000` and is detected.
- All **13 lineage witnesses** match the frozen result; historical-versus-C750
  result/lineage differences are **0**.

This bounded SQL replay is three approved contexts, not historical RAW ingestion
or a population-wide financial replay. A PASS is relative to the frozen accepted
scope; it does not establish all historical units, economic fields, entity meanings
or arbitrary consumer SQL contracts. Other historical economic fields retain their
frozen PRESERVED_NOT_MODELED boundary.

## B2 — N450 Lossless: PASS

The current native version-0 N450 Delta records were exported into an isolated
validation directory. The existing pinned independent M1 verifier read every
exported record against the original RAW intervals; earlier checkpoint files were
not substituted for native output readback. Resulting full-file reconstruction,
counts and ordered record digests also match the preserved processing evidence.

| Lossless family | Status | Actual check/population |
| --- | --- | --- |
| 1 — occurrence accountability | PASS | All 1,902,855 physical lexical occurrences; 1,899,705 DATA occurrences ACCEPTED; 3,150 framing occurrences preserved separately; no missing/extra locator or digest mismatch |
| 2 — field accountability | PASS | Every one of 9,498,525 fields has the exact expected name, ordinal, value and DIRECT_MAP disposition |
| 3 — lexical value/structure/multiplicity | PASS | Exact values and ordered-record digests for all 450 native bindings; duplicate occurrences preserved |
| 4 — RAW integrity | PASS | Current hashes match all 450 frozen physical source identities; native verification also checks before/after source hashes |
| 5 — lineage and reconstruction | PASS | Every record's source/binding, byte interval, line and model/rule checked; concatenated intervals reconstruct each exact member SHA-256 |
| 6 — economic/numeric reconciliation | NOT_APPLICABLE | All 450 sources are the approved five-column SEC Daily Master filing-index structure; no economic measure is modeled. CIK/date/filing reference strings are preserved, not summed or promoted into financial controls |

The independent duplicate diagnostic found **29,062 equal-looking groups** with
**58,367 participating occurrences** and **29,305 excess occurrences**. All are
retained at distinct source locators; this is lexical multiplicity, not a judgment
that the business observations are duplicate events.

**Exception:** DEC-000010 applies only to the exact SRC010128 Company Name witness.
Its ISO-8859-1 bytes, approved derived string, locator and decoding provenance were
independently checked. All other fields retain their approved profile behavior.
No RAW correction, source omission, broader encoding fallback or M2 was introduced.
Source NULL meaning and enterprise identifier/date semantics remain unmodeled and
withheld from semantic promotion.

## C — Combined stability: BLOCKED

C was assessed independently, including full combined coverage, live definitions,
all-source hashes and historical behavior through the combined consumer.

| Combined control | Status | Evidence/coverage |
| --- | --- | --- |
| Exact membership | PASS | Fresh 1,182-row coverage read; exactly 750 distinct frozen physical identities; C300/N450 membership preserved and disjoint |
| Record/field/source accountability and applicable lexical Lossless 1–5 | PASS | Exact per-binding expected counts and lineage; all 750 current RAW hashes; 108 full-scope Step 3 multiset receipts reused under identical current definitions and pinned data snapshots; fresh native B2 verification |
| No unintended collapse or omission | PASS | Exact binding/source sets, UNION ALL plan, full-schema multiset comparisons and locator/multiplicity checks; no business deduplication applied |
| Source namespaces/lineage | PASS | Each source-instance ID remains bound to its exact frozen identity, path/hash and original binding/run; no binding-key collision or namespace reassignment |
| Historical SQL/test compatibility | PASS | Same historical definitions and exact FIN results/lineage through both consumers, within the approved fixture scope |
| Model-version coherence | PASS | One M1; each binding retains its approved literal or scoped NUM rule and parser provenance |
| Combined Lossless 6 | NOT_IMPLEMENTED for the full economic scope | FIN_EVAL_V1 three contexts PASS; N450 non-economic structure NOT_APPLICABLE; broader unmodeled economic/semantic controls NOT_IMPLEMENTED |
| Enterprise cross-source integration integrity | NOT_IMPLEMENTED | Canonical entities, business keys, false merge/split truth, relationship/referential/cardinality rules, compatible business grain/units/time and semantic alignment are not implemented |
| Operational threshold acceptance | NOT_IMPLEMENTED | Actual elapsed times are recorded; no declared resource/throughput acceptance thresholds or complete DBU/executor telemetry support an operational acceptance claim. No downstream performance study was started |

**Disposition:** full C promotion is BLOCKED under the evaluation contract. Passing
A, B2 and the combined source-instance/lexical controls cannot establish the missing
C2 semantic controls. No mapping, enterprise identity or business duplicate rule
was invented to turn these gaps into PASS. Available timings are observations, not
performance acceptance. No combined semantic/economic PASS is inferred from the
three FIN contexts.

## Differences, exceptions and limits

| Classification | Affected scope | Observed difference/cause |
| --- | --- | --- |
| UNCHANGED | Frozen C300 contracted outputs and scoped FIN behavior | Zero unexpected differences; frozen data snapshots, original identities, historical definitions and tested fixture/lineage results preserved |
| EXPECTED_COMPATIBLE_EXTENSION | N450 addition under lexical M1 | 450 new source instances added with all bindings and occurrences retained; no enterprise merge or semantic scope expansion |
| BUG_FIX | Previously approved CLEAN writer-mode spelling | Publication-only correction preceded the evaluated outputs; no lexical schema/value change. Earlier failed publication attempts produced no outputs to compare |

These classifications do not approve missing business semantics. Population-wide
numeric reconciliation, source NULL interpretation and enterprise semantic
integration remain outside demonstrated coverage. No historical RAW replay,
model change, promotion, output freeze or later Study Notes work was performed.

## Reproducible evidence

- `runs/c750-stability/v1/local-preflight.json`: frozen membership/references,
  Step 3 evidence fingerprints, 49 frozen FIN evidence files and fixture checks.
- `runs/c750-stability/v1/notebook.py`, `notebook.sha256`, `submit.json`, `run.json`,
  `output.json`: exact fresh evaluation code, job scope and execution result.
- `runs/c750-stability/v1/remote-coverage.json`, `remote-raw-integrity.json`,
  `remote-n450-native-lossless.json`: full populations and per-binding verification.
- `runs/c750-stability/v1/fin-historical/`, `fin-combined/`,
  `fin-regression-result.json`: actual SQL requests/results and complete fixture/
  lineage comparisons. The candidate changes only the view reference.
- `runs/c750-stability/v1/results.json` and `evidence-index.json`: separate A/B2/C
  statuses, checked/reused populations, limitations and artifact fingerprints.
- Remote derived evidence:
  `/Volumes/workspace/edp_lab/raw/n450-m1/n450_step3_v1/evaluations/c750-stability-v1/`.

Operational results, exported Parquet and RAW remain excluded from Git. The above
paths preserve the reproducible evidence without altering historical artifacts.

| Reference | SHA-256 |
| --- | --- |
| Evaluation authority | `692a1a034d2508e2c1c8862682722efc1915d5cb5873c7687e80d50ef7329593` |
| Results | `ab63f0a41c7593e1fdb6209e593a4e5defb6fdde1082cb152305adf67f2fb4a3` |
| Evidence index | `8f7fc038568c37a0ce04e383045e0d72abde0d42891a106181066be35ccacfdb` |
| Fresh evaluation notebook | `a87f3561dce4c564cdce188eed5a1d850c5d885a02a3dd32792c6a7a195740df` |
| Frozen O_C300_M1 | `db710f6152c6ffe33ee2d0371e7dadc8f9ff76e67af3a8e82d807a4c7923542c` |
