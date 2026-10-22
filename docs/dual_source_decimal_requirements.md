# Dual-source exact-decimal requirement evidence

Status: **TWO_REQUIREMENTS_EVIDENCED**. Read-only requirement discovery on 2026-10-22, based on `day4/additive-m2` commit `3521aaeb42c50a7c09f6ae22260096a4f61645c9`. Both sources evidence a need to interpret numeric text exactly; sharing a numeric primitive does not establish shared financial semantics or authorize M2 implementation.

## FSDS NUM — OBSERVED

Reuse: three existing M1 CLEAN field witnesses, deliberately chosen for contrasting USD/pure and reporting contexts, not a random or population-representative sample. No FSDS RAW replay or new profiling run. All three are `num.txt`, `M1_LEXICAL_V1`, run `num_recovery_20261021_v1_recovery`, parser/rule `C300_FSDS_NUM_QUOTE_BOUNDARY_V1`. Original fields: `adsh, tag, version, ddate, qtrs, uom, segments, coreg, value, footnote`.

| Source / physical member | Line; byte offset; length | adsh / taxonomy | ddate / qtrs / uom | tag | Actual `value` | Decimal coefficient digits / scale |
| --- | --- | --- | --- | --- | --- | --- |
| SRC000060 / 2024q4.zip!num.txt | 64698; 9197940; 287 | `0001280784-24-000026` / `us-gaap/2024` | `20240930` / `0` / `pure` | `InvestmentBasisSpreadVariableRate` | `0.0070` | 2 / 4 |
| SRC000053 / 2023q1.zip!num.txt | 312006; 42739663; 181 | `0001655888-23-000012` / `us-gaap/2022` | `20221231` / `0` / `pure` | `InvestmentOwnedPercentOfNetAssets` | `0.0010` | 2 / 4 |
| SRC000054 / 2023q2.zip!num.txt | 337467; 46589850; 244 | `0001558370-23-008867` / `us-gaap/2022` | `20230331` / `0` / `USD` | `InvestmentOwnedAtCost` | `9830000.0000` | 11 / 4 |

All three values parse directly as finite Python `Decimal` without binary float, rounding or unit conversion; all are positive, scale 4. Coefficient digits means `len(Decimal(text).as_tuple().digits)` (leading fractional zeroes excluded, trailing zeroes retained), not an approved SQL precision. `0.0070` needs fractional capacity 4 despite having two coefficient digits. Required fixed precision/scale and overflow policy remain open.

`coreg` and `footnote` are present empty strings in each witness; `segments` is nonempty quoted investment context containing literal tabs. No missing field, blank `value`, explicit NULL token, or invalid numeric `value` occurs in these three records. This does not establish absence elsewhere or that blank equals NULL. Reporting evidence is the literal `ddate`/`qtrs` above; no date alignment, period-duration inference, issuer mapping or amendments policy is introduced. `pure` is preserved as supplied, not converted to percent or treated as USD.

FIN applicability: the three example records are not the frozen FIN fixture. Reuse [FIN_EVAL_V1](../metadata/evaluations/fin_eval_v1.json) and [expected results](../sql/reconciliation/fin_eval_v1/observed_expected_results.csv) for `SRC000055`, `2023q3.zip!num.txt`, binding `341ce895a89fe164c1cc14af2679aa0b4637f593c6887e5c4d3a74bc49bbebcd`, run `main_recovery_20261021_v4_full`, literal rule, pinned CLEAN Delta versions 0. FIN_001: accession `0000002178-23-000082`, dates `20221231` and `20230630`, assets `384159000.0000` and `343482000.0000`, existing 2/2 PASS. FIN_002: `0000002969-23-000037`, `20230630`, assets `30929500000.0000`, existing 1/1 PASS; parent-only versus including-NCI equity yields the recorded wrong-equity difference `1232700000.0000`. These are retained DECIMAL(38,4) query results, not newly inspected lexical spellings. Existing scope: `us-gaap/2023`, USD, qtrs `0`, empty segments/coreg, exact tag/cardinality predicates. Both remain mandatory regression requirements for later candidates containing C300; no new FIN execution occurred and no applicability to Treasury is asserted.

Evidence integrity and lineage: local retained archives under `/Users/lightnino/Projects/edp-lab/runs/c300-m1/` were hashed before reading. `closeout-review-v1/supporting-evidence-v1.zip` SHA `0903bb24047b95e6203eebca6b5af83441f8b94ab4a0b5addc136e9a18367e10` and its member `runs/c300-m1/reconciled_recovery_20261021_v2/warehouse-witness-result.json` SHA `d5d8ae37317f9861fb075507f428218bc591e5d3bdce1888a8fa346709dbc9ae` match [baseline references](../metadata/baselines/O_C300_M1.json). FIN archive `fin_eval_v1/fin-eval-v1-evidence.zip` SHA `9d0fc256970bf3815a9020bf628c960ee7f601ac6fd03596121ed211b758916d` matches the FIN contract; reused members are `replay-2/{FIN_002-amounts-result,lineage-corrected-result,verification}.json` beneath `runs/c300-m1/fin_eval_v1/`. The latter has 13 source-line/byte/hash witnesses. Source 055 RAW/member hashes are in the FIN contract.

Exact identity and SHA lineage for the three lexical witnesses (identity is the frozen physical RAW parent directory name, not an entity identifier):

- **SRC000060**: identity `facea18c20840730963feeeb7a5bd5981e57237b97a14549e2d4a1bffe72f574`; RAW SHA `9a2cbbaf39c94aa642b33d512f4def92b198d3bfd12d2267bcd27abe55b9902d`; member SHA `7db50fd666194d39dcec620c0e8057a9adf159174b5aa88becbe2ec5ea9cd3e5`; binding `14cc8d86190f4f92ab040925bf388b0430aa96a31fb2d27b7575ddc550f9cd32`.
- **SRC000053**: identity `9f55638840a04f32c8da6f5c9c5fc3acb904d3b498898e517179fd3eaf94bd4a`; RAW SHA `479638c1be4088fa2ae42d2947468913eaff5ad0f093c412ba4340af8a8f791e`; member SHA `0751898bc31acb5309660f2acc1a4e692d98ee7a0e2f21e269570ce7758e3c76`; binding `3e019d6dbfcc45c13c8fd27156d83192c1e38ef14524da21e58d2e17e6540912`.
- **SRC000054**: identity `cfadad1a865b19429da10c1fc805dccda9cf4a5a352610385beee743f88b172e`; RAW SHA `f028f1e8d24313e7619aa87c7c683a459452e7e81a8e5ba72d7ce39ddf62bda9`; member SHA `72b948228b2d692e8e36353e8c02c9a7845fa5ddbc7d644b8f7b4661db05d4ba`; binding `54c47c4f0d6793d327c3bb998d6c8b6a1393a819014c601a0f0a55d53cad8fd5`.

Existing [profiling tools](profiling_tools.md) preserve lexical values and leave semantic NULL-dependent metrics unresolved. The local retained `stats_recovery_20261021_v2/collected-full/column_profiles.parquet` contains no computed NUM envelopes (`envelope_json` absent for NUM), so no numeric distribution or whole-table parseability is claimed from it. The reader's GOLD registration does not grant a new C300 RAW scan. Reused CLEAN witnesses suffice for this bounded requirement; blank/invalid frequency and source-wide precision maxima remain UNRESOLVED.

## Treasury XML — OBSERVED

Exactly the five admitted 2025 files were read locally, with SHA verified against [the approved plan](../proposals/n750-step1-v3/plan.json) before standard-library `xml.etree.ElementTree.fromstring`. Their registration/identity/path/SHA are also in [N750 bindings](../metadata/admissions/N750_v1/bindings.json). No network lookup, upload, CLEAN publication or persistent parser was added.

Structure: Atom `feed/entry/content/m:properties/d:*`; namespaces `a=http://www.w3.org/2005/Atom`, `m=http://schemas.microsoft.com/ado/2007/08/dataservices/metadata`, `d=http://schemas.microsoft.com/ado/2007/08/dataservices`. Rates carry `m:type="Edm.Double"`; this is source metadata, not a requirement to convert through floating point. Dates carry `Edm.DateTime`. Grain below describes observed XML structure, not a business key. Every feed covers date text `2025-01-02T00:00:00` through `2025-12-31T00:00:00`.

| Source / file suffix (`daily_treasury_…_2025.xml`) | Entries / numeric leaves | Observed structure and entry[1] examples |
| --- | --- | --- |
| SRC010451 / yield_curve | 249 / 3,704 | Date-wide `NEW_DATE`; `BC_1MONTH=4.45`, `BC_10YEAR=4.57`, `BC_30YEAR=4.79`, `BC_30YEARDISPLAY=4.79`. Field labels include 1, 2, 3, 4, 6 MONTH; 1, 2, 3, 5, 7, 10, 20, 30 YEAR; later `BC_1_5MONTH`. |
| SRC010452 / bill_rates | 249 / 6,848 | Date-wide `INDEX_DATE`, also `QUOTE_DATE`, `CF_NEW_DATE=01/02/2025`. `ROUND_B1_CLOSE_4WK_2=4.26`, `ROUND_B1_YIELD_4WK_2=4.33`; separate `CS_4WK_CLOSE_AVG=4.26`, `CS_4WK_YIELD_AVG=4.33`. Tenor labels 4, 6, 8, 13, 17, 26, 52 WK. Entry[1] `MATURITY_DATE_4WK=2025-02-04T00:00:00`, `CUSIP_4WK=912797NF0`, `CF_WEEK=202501`; these are not rate fields. |
| SRC010453 / long_term_rate | 747 / 747 | Date/type-long observations, three RATE_TYPE values: `BC_20year`, `Over_10_Years`, `Real_Rate`; entry[1] `Id=1525`, `QUOTE_DATE=2025-01-02T00:00:00`, `RATE_TYPE=BC_20year`, `RATE=4.86`. |
| SRC010454 / real_yield_curve | 249 / 1,245 | Date-wide `NEW_DATE`; `TC_5YEAR=1.97`, `TC_7YEAR=2.11`, `TC_10YEAR=2.23`, `TC_20YEAR=2.40`, `TC_30YEAR=2.48`. |
| SRC010455 / real_long_term | 249 / 249 | Date and `RATE`; entry[1] `QUOTE_DATE=2025-01-02T00:00:00`, `RATE=2.48`. Entry id URL ends in empty `id=`; do not use it as a unique identifier. |

Bounded measurement method: within each file, collect the union of property names carrying `m:type="Edm.Double"`; examine each entry for these fields; preserve `.text` and attributes, separately count absent element, empty text, `m:null="true"`, and failed/nonfinite `Decimal(text)`. Inspect all such numeric leaves only in these five files, not the rest of C1500. Result: **12,793/12,793 present numeric texts** parse as finite exact Decimal; coefficient precision 3, scale 2, all positive; no explicit sign characters, zero or negative values. No invalid, empty, or `m:null="true"` numeric leaf was observed. This does not justify rejecting signed values in future inputs.

Missing is observable separately: `BC_1_5MONTH` is absent in entries 1–31 of SRC010451 (31 slots). SRC010452 lacks all four 6WK rate fields (`ROUND_B1_{CLOSE,YIELD}_6WK_2`, `CS_6WK_{CLOSE,YIELD}_AVG`) in entries 1–31 (124 slots). These counts use the per-file union of observed fields, not a claim that every date must supply every tenor. The other three files have zero missing numeric fields under this method. SRC010452 has 249 present empty `BOND_MKT_UNAVAIL_REASON` elements; SRC010453 has 747 literal `EXTRAPOLATION_FACTOR=N/A` elements. Neither is a numeric RATE and neither was converted or silently treated as zero/NULL.

Units: inspected XML supplies rate/yield names and Edm types but no explicit percent/basis-point/fraction unit declaration. Preserve source lexemes and field labels; percent interpretation, scaling by 100, bill discount-versus-yield conventions, day-count and nominal/real comparability remain UNRESOLVED. Equal-looking `CS_*`/`ROUND_*` or `BC_30YEAR`/`BC_30YEARDISPLAY` values are not declared semantically equivalent or deduplicated.

Treasury reproducible lineage: local RAW base `/Users/lightnino/Projects/edp-lab/` plus each plan `raw_path`; each witness locator is `a:feed/a:entry[1]/a:content/m:properties/d:<field>` with the date/type above. Source file identity and exact SHA below resolve to that approved plan without any new path mapping.

- **SRC010451**: identity `63d9d0beb1bbee0079928bfb710339f0032859cc0ecbf5cccafe3b49429d0581`; RAW SHA `fb2f64bcaa9c2041f5601460f5d67bf2ebf51083331e75192a7d48ece0db3ed9`.
- **SRC010452**: identity `be4ecba6635cccaa39f23a4a3905198433e25a60040cc3a64e686fcf60731f9c`; RAW SHA `5f20dd1fad2627facce863a2a3d3258278f2119fef61028e85e0cf75a244df16`.
- **SRC010453**: identity `567fe9b2558e4fbfd6655b72e5ea00ae6f3f750986ce2c253bd589ddb7280805`; RAW SHA `c5ecec4d443cf0e160ea42e585e3f1abb237587c5a8094ee33ce7c9fc350b2f8`.
- **SRC010454**: identity `3d78318e471a446a4e49022d13f7642cce3dbb94cb15dd5360561f19622750be`; RAW SHA `68f58df186f47f20c349d276ae501b97c94cfb2a09cc36453f4c95288322ec66`.
- **SRC010455**: identity `59a456d521bc98ef7375758272f827cb50bf90f3218b415eb49678e99cf860ae`; RAW SHA `e58a45134fe5a857028f7ee3381d07fbc56a7aa248dfd45df5721478e67d5a1e`.

## Requirements and unresolved interpretations

| Requirement | Evidence-supported need | Separate interpretation retained |
| --- | --- | --- |
| REQ_FSDS_TYPED_AMOUNT | Exact optional decimal projection from NUM `value`, preserving original lexical spelling, scale and field/occurrence lineage. USD `9830000.0000` and the frozen FIN exact-amount regressions support it. | `uom`, tag/taxonomy, filing, period, segments/coreg and FIN-specific predicates remain source context; `pure` facts show NUM is not uniformly monetary. No business key or canonical entity is inferred. |
| REQ_TREASURY_TYPED_RATE | Exact optional decimal projection from identified rate/yield XML property text, retaining property QName, source type, entry/date/type/tenor context and RAW lineage. `4.45`, `4.33`, `1.97`, `2.48` support it. | Structural grain, absent/empty/N/A distinctions, source-specific units and rate conventions remain separate. Dates/IDs/CUSIPs are not automatically numeric measures. |

**Conclusion:** both justify a shared `value_decimal` capability for finite exact decimal representation alongside the unchanged lexical value and provenance. This is a requirement finding only, not a conversion contract, schema choice, implementation or semantic approval. Open questions for later human review: which finite lexical grammar and precision/scale/overflow policy should a later contract approve; how should absent/empty/NULL/invalid states be represented; what documented Treasury units/conventions apply; which source-specific fact/period/tenor rules are authorized? No rounding, null-to-zero, unit conversion, date alignment, record merge or entity equivalence was executed.

Coverage limits: three existing FSDS lexical witnesses plus the existing three-context FIN results; five admitted Treasury files only. No all-FSDS claim, negative-rate coverage claim, new financial reconciliation or full-corpus profiling. Remote status remains 450 VERIFIED / 300 UNVERIFIED; verification before Step 8 processing remains required and is not a Step 2 blocker. Step 3, M2 implementation and main merge remain excluded.
