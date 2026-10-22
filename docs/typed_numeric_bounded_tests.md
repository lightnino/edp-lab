# Bounded additive typed-numeric tests

Current contract status: **M2_CONTRACT_APPROVED**, under append-only [DEC-000013](../metadata/decision_log.csv), recording the owner's explicit approval of PR #38 and bounded Step 5 tests. Formal identity and precise approval time were not supplied; the decision's timestamp is recording time. The [approved proposal](m2_additive_typed_numeric_v1.md) is preserved byte-for-byte (SHA `a65e87be22415def12333e4d5e291a2fc8f4a87e4dc886e0d89a3c7c1f2225cb`); its historical pending label does not override DEC-000013. No installer, authority pin change or new approval mechanism.

Implementation: [typed_numeric_v1.py](../src/edp_lab/materialization/typed_numeric_v1.py), model `M2_ADDITIVE_TYPED_NUMERIC_V1`, conversion `EXACT_DECIMAL_38_4_V1`. Pure TEXT-to-projection function; no I/O, inference, financial conversion, source selector or production publisher. Tests supply the exact approved source scopes and retain context in separate test-only lineage envelopes. M2 output exists only in memory; the independent DuckDB storage checks use a temporary in-memory database.

## Actual source evidence — independently limited statuses

**FSDS_TYPED_VALIDATED** — exactly three retained M1 `num.txt/value` witnesses; no FSDS RAW replay or backfill:

| Witness | Original lexical → exact Decimal | Preserved context |
| --- | --- | --- |
| SRC000060 / line 64698 | `0.0070` → `0.0070` | `pure`, InvestmentBasisSpreadVariableRate, filing `0001280784-24-000026`, us-gaap/2024, ddate `20240930`, qtrs `0` |
| SRC000053 / line 312006 | `0.0010` → `0.0010` | `pure`, InvestmentOwnedPercentOfNetAssets, filing `0001655888-23-000012`, us-gaap/2022, ddate `20221231`, qtrs `0` |
| SRC000054 / line 337467 | `9830000.0000` → `9830000.0000` | USD, InvestmentOwnedAtCost, filing `0001558370-23-008867`, us-gaap/2022, ddate `20230331`, qtrs `0` |

3/3 VALID; original strings and complete supplied field context, including segments/coreg/footnotes, unchanged. SHA-verified retained archive/member references are in [Step 2](dual_source_decimal_requirements.md). Tests preserve source run, binding, original M1 model/parser/rule, RAW/member hashes, byte offset/length, source line and field ordinal. Exactly one output per approved witness; no merge/drop/duplicate.

Existing FIN evidence is reused separately: its archive/member hashes and expected-results fixture hash match the pinned contract; three fixture contexts' exact equations/amounts and the `1232700000.0000` wrong-equity difference agree; 13 retained lineage witnesses and unchanged-view evidence remain recorded. FIN_002's retained five amounts match their exact expected strings. No live FIN SQL replay or M2 conversion of additional FIN lexical occurrences was performed. This validates retained evidence consistency, not new remote snapshot availability.

**TREASURY_TYPED_VALIDATED** — four selected document-order entries per approved XML snapshot, 20 entries total; only the approved property allowlists:

| Snapshot | Entry ordinals (1-based) | Actual numeric VALID | Structurally MISSING evaluations |
| --- | --- | --- | --- |
| SRC010451 | 1, 31, 32, 249 | 58 | 2 (`BC_1_5MONTH`, entries 1 and 31) |
| SRC010452 | 1, 31, 32, 249 | 104 | 8 (four 6WK properties, entries 1 and 31) |
| SRC010453 | 1, 2, 3, 747 | 4 | 0 |
| SRC010454 | 1, 31, 32, 249 | 20 | 0 |
| SRC010455 | 1, 31, 32, 249 | 4 | 0 |

190/190 present numeric texts VALID; 10/10 absent-property evaluations explicitly MISSING with no source text or fabricated RAW/M1 record. All 200 evaluation locators are distinct. Examples: `BC_1MONTH=4.45` → `4.4500`, bill `ROUND_B1_YIELD_4WK_2=4.33` → `4.3300`, `RATE=4.86` → `4.8600`, `TC_5YEAR=1.97` → `1.9700`, real-long-term `RATE=2.48` → `2.4800`; original lexical strings remain unchanged. These are storage zero-padding, not numerical/unit rescaling.

Minimal standard-library XML extraction reads the five files after checking their admitted SHA, then converts only the selected entries/properties. Every result retains source ID/identity/path/SHA, property QName, document-order entry/property ordinal, date text and complete selected-entry property/attribute context (including tenor names, rate type and source Edm type). No property dict flattening/deduplication. SRC010453 entries 1–3 cover the three observed rate types. Every source file and retained M1 archive compares byte-identically after tests. Exact snapshots/hashes and namespace meanings are reused from [Step 2](dual_source_decimal_requirements.md) and [the input plan](../proposals/n750-step1-v3/plan.json), not a new registry.

## Synthetic cases — policy coverage, not source observations

62 synthetic test instances: signed positive/negative/zero, leading zeroes, `0.0001`/`-0.0001`, both signed 34-integer-digit maxima, overflow at 35 integer digits, excess fractional scale (including `1.00000`), scale-before-overflow precedence, explicit absent/null/conflicting-null states, empty/ASCII-whitespace, mixed whitespace, exponent/float syntax, separators, percent/currency, Unicode digits/space, NULL/N/A tokens, nonfinite spellings, adapter NULL/type/flag errors, deterministic repeated occurrences and five independent DECIMAL(38,4) storage round trips. Boundary amounts are exact under a precision-2 Decimal context with arithmetic traps enabled; no rounding or float intermediate is used. Non-TEXT numeric/float/Decimal inputs are rejected.

All seven contract outcomes and corresponding reasons are asserted. Nonconvertible values retain lexical evidence with no typed value; unaccountable adapter states raise rather than fabricating a source outcome. Duplicate synthetic lexical values remain two occurrences. No null-to-zero, implicit token semantics, percent normalization or unit conversion.

## Reproduction, checks and limits

Run `PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python -m pytest -q -s tests/materialization` from the feature checkout. **69 passed, zero skipped, zero failed** locally (62 synthetic, seven source/FIN checks); final focused run 0.14s. Local evidence tests explicitly skip if external pinned archives/RAW are unavailable, and fail on changed hashes. CI skips cannot substitute for the actual local source results above. Initial lint findings were corrected; Ruff and whitespace checks pass. Full repository regression: **474 passed, 77 skipped, zero failed in 81.07s**; skips retain existing environment/scope limitations and do not establish untested outcomes.

Environment: Python 3.12.15, DuckDB 1.5.6; `uv.lock` SHA `62a95abca6cf980c2f68d97fa34fdcdf4330ab1da49bf01e8bed6b36617a1803`. Reproducible code fingerprints:

- Converter SHA `ae06d39409c2542273f269356a5905553b08621546de2bda6c972b22bc50d507`.
- Real-source tests SHA `ccc7516dad43a0a4e3f577c5c35905fea39362a6fef8c0b70204201d40448980`.
- Synthetic tests SHA `e774b8137634566fe3ab3022f5f9173a4a6a76d9aa12fe0cab9660407c5937c1`.

The prior decision log is an exact byte prefix of the current log; only DEC-000013 is appended. The approved contract and tracked M1 code/contracts/frozen outputs compare unchanged against parent `30f46bd5e187e548d84f98b86f1718debeef2a1b`; no M1/RAW writing path was added. This is bounded converter validation, not a new production CLEAN publication, live Delta preservation scan, general XML parser certification, full FSDS precision survey or C1500 PASS. Real negative/zero/invalid/null/overflow numeric source cases were not established here; synthetic checks supply their policy coverage. Repeated real XML property handling is unobserved; synthetic occurrence multiplicity is tested. Financial units, percentage conventions, equivalence and broader semantics remain unresolved. Remote coverage remains 450 VERIFIED / 300 UNVERIFIED, with Step 8 verification still required. Stop before Steps 6 and 8; no main merge.
