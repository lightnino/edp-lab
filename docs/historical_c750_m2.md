# Historical C750 additive M2 projection

**HISTORICAL_M2_VALIDATED**. [DEC-000014](../metadata/decision_log.csv) records the owner's explicit mechanical extension from DEC-000013's three witnesses to existing FSDS NUM `value` occurrences in frozen O_C750_M1, including FIN sources. Grammar, DECIMAL(38,4), conversion outcomes and interpretation boundaries are unchanged. This is a validated separately versioned projection, not a Step 9 freeze.

## Actual scope and outcomes

| Measure | Result |
| --- | ---: |
| Actual FSDS sources / completed bindings | 60 / 60 |
| Eligible NUM `value` occurrences (ordinal 9) | 176,060,325 |
| VALID exact Decimal | 169,406,475 |
| BLANK, original TEXT retained / typed value unavailable | 6,653,850 |
| MISSING / NULL_UNRESOLVED / INVALID / SCALE_EXCEEDED / OVERFLOW | 0 each |
| Missing/extra original field occurrences, bidirectional full EXCEPT ALL | 0 / 0 |
| Duplicate technical occurrence keys / independent Decimal-oracle mismatches | 0 / 0 |

The accepted frozen selection excludes superseded BLOCKED entries. Exact 60-source/binding membership, per-binding counts and fingerprints are in [the output reference](../metadata/baselines/O_C750_M2_v1.json). BLANK is an accountable conversion outcome, not a conclusion about source NULL semantics or a dropped/rejected record. No policy expansion was needed for excess scale, invalid text or overflow.

## Persisted output and logical subsets

- Physical eligible-field table: `workspace.edp_lab.typed_c750_m2_historical_20261022_v1 VERSION AS OF 0`; Delta ID `2cb01f9b-9c72-4451-bfb1-d36d415edba4`, UC ID `ca98ccc6-1e42-4234-83fb-72728da5045e`. **54 files / 1,907,726,118 bytes** at build. Schema SHA `66fcce063dcb238df9bf7346701322623a89709c894194ce947f648dbeff8889`; per-binding output fingerprints and their method are recorded in the output reference.
- C750 M2 DATA relation: `workspace.edp_lab.o_c750_m2_records_historical_20261022_v1` preserves every column of the accepted pinned M1 DATA relation and LEFT JOINs the version-0 typed projection by original technical locator. M1 `model_version`/rule/fields remain intact; additional M2 columns carry their distinct versions.
- C300 M2 logical subset: `workspace.edp_lab.o_c300_m2_records_historical_20261022_v1`. All 176,060,325 eligible occurrences belong to its 60 FSDS sources; **no separate C300 ETL job**. N450 contributes **zero** eligible typed occurrences and retains its original fields. The preserved logical populations are the frozen **316,063,821 C750 / 314,164,116 C300 DATA records**: inherited counts plus proven one-to-one join cardinality, not a repeated global population scan. Original CLEAN framing/non-DATA records remain untouched in the frozen input tables; the composed relation retains the accepted M1 DATA-view scope.

## Independent validation and FIN compatibility

The persisted table was reopened at version 0 in a separate job. Per-binding totals match frozen CLEAN counters. Full original field/provenance multisets match in **both EXCEPT ALL directions**, including lexical strings, source/binding/run IDs, source line, byte offset/length, ordinal, names, RAW/member hashes and parser/model/rule context. Unique field and record technical keys prevent join multiplication; source membership is unchanged. Original field/context arrays remain in the pinned M1 relation, not reconstructed from typed values.

Every persisted conversion was checked by an independent native Spark string/Decimal oracle: full ASCII grammar, blank classification, fractional length, significant integer width, outcome/reason and guarded DECIMAL(38,4) cast. It does not call the Python converter and never accepts rounding as parsing. A 20-case runtime transport/oracle probe passed before the historical write. No float intermediate or financial unit conversion.

FIN_001 **2/2 PASS** and FIN_002 **1/1 PASS**, comparing pinned original M1, M2 lexical SQL, M2 `value_decimal` SQL and the C300 logical subset. Exact fixture amounts remain equal, with zero-tolerance equations and FIN_002 wrong-equity difference **1232700000.0000** retained. All **13 source-line/byte/hash/model/rule witnesses** match the original retained FIN evidence. These are the existing approved three financial contexts, not wider financial reconciliation.

All six original CLEAN Delta/UC identities, pinned version-0 schemas, latest metadata version 1, and three original C750 consumer definitions remained unchanged before/after validation. Independent UC metadata also confirmed all six frozen storage locations unchanged afterward. The output Delta/UC identities match between build and readback. Original M1 tables/views were never overwritten, repointed or altered; its SQL inputs and existing FIN outputs remain independently reproducible.

## Execution, exception and reproducibility

Implementation: [historical_c750_m2.py](../notebooks/historical_c750_m2.py), using the **unchanged** Step 5 converter SHA `ae06d39409c2542273f269356a5905553b08621546de2bda6c972b22bc50d507`. Runtime: Python 3.11.10, Spark 4.2.0. One historical projection write from CLEAN; zero RAW replay; no N750 input, separate C300 pipeline or C1500 Stability execution.

| Run | Result | Job wall seconds | Code wall seconds |
| --- | --- | ---: | ---: |
| Initial preflight 693588401750111 | FAILED before output | 123.203 | Not retained separately |
| Build 910030711554960 | SUCCESS | 553.273 | 532.348 |
| Independent verify 426457626095564 | SUCCESS | 801.190 | 782.017 |

The initial preflight required a nonempty SQL storage-location string, but SQL returned an empty field. UC metadata independently matched all six exact frozen IDs/full S3 locations. The repaired guard checks those UC descriptors plus SQL Delta/UC identities and metadata versions while recording the empty field; frozen pins, converter and scope were not changed. Original failure/runtime evidence is preserved. Local converter/source tests: **69 passed**, zero skips; Ruff and whitespace checks PASS. No failed conversion was silently corrected. Resource/monetary usage was not measured.

Retained execution archive: `/Volumes/workspace/edp_lab/raw/day4-m2/historical_v1/historical-c750-m2-evidence-v1.zip`, SHA `85fd7c2be09b98a4852ce376dbf5293f44b13256f6dd3db57f0bf4234522ebf7`, **698,455 bytes**, independently downloaded and SHA-matched. It contains actual run/submission records, original failure, both runtime generations, input query definitions, source catalogs before/after, M1 preflight, runtime probes, build/readback/FIN results, per-binding fingerprints and executed notebook. No full RAW or output dataset is committed; actual M2 data resides in the separately versioned Delta table. Raw verification report SHA `d9855eb7d23903248899f1c6b3a8a9159b6731c07e7f840850db84c74f5f88ee`.

Reproduce by verifying this archive SHA before extraction, then the recorded runtime/notebook/input pins; read the recorded six M1 snapshots and M2 table at explicit version 0. Original accepted query-plan SHA is `17522cb06f354986fac104316bb68401de3255de6225566b84c311c6e205b42d`; original freeze-reference SHA is `be2001860d5900b64bc4bdc3178b7367d54cbb89e7de703e515fd4c9cb1d5a50`. Build uses exclusive creation and is **not** rerun for readback. The notebook's verify phase and saved FIN SQL define the independent checks; its existing views/typed table are retained as the result. Revalidation must reuse persisted outputs and validate stored identities, not overwrite them.

Financial unit meaning, percentage normalization, source equivalence and broader processing remain unapproved. Remote N750 coverage remains 450 VERIFIED / 300 UNVERIFIED; Step 8 verification remains required. **Stopped before Steps 7–9; no merge to main.**
