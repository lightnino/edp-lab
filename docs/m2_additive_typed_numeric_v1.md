# M2_ADDITIVE_TYPED_NUMERIC_V1

Status: **M2_CONTRACT_PROPOSED_PENDING_APPROVAL**. Proposed 2026-10-22 against `day4/additive-m2` commit `591e15f31830ffe1824415a852c19bd64b6c0e91` (B1 PR #37). Owner approval of this conversion contract is **not established**. Documentation merge, mechanical checks, prior lexical approvals and N750 admission do not authorize its execution. No M2 implementation, parser activation, processing or backfill is authorized here.

Evidence: [Step 2 observations and exact source/hash/locator references](dual_source_decimal_requirements.md), [B1 classifications](decimal_model_fit_classification.md), [accepted M1 representation](day2_c300_m1_readiness_v1.md#approved-m1-representation), [FIN contract](../metadata/evaluations/fin_eval_v1.json). OBSERVED statements below reuse those artifacts; all new conversion/output rules are **PROPOSED engineering choices**, not established source meanings. Existing [ownership boundaries](ownership_approval_boundaries.md) and [decision-log process](decision_log.md) apply; no new approval mechanism is introduced.

## Fields, scope and versions — PROPOSED

Publish a separate M2 projection relation with one accountable outcome per selected source-field occurrence, preserving multiplicity. This relation does not replace, update or extend an existing M1 table/view in place. Minimum logical fields:

| Field | Contract |
| --- | --- |
| `value_decimal` | Optional `DECIMAL(38,4)`; non-NULL only for `VALID`. Its SQL NULL means no typed projection, **not** a conclusion that the source is semantically NULL. |
| `lexical_value` | Exact original decoded TEXT for a present value, including empty/whitespace text and original scale/sign; no trimming or normalization. Absent XML property has no lexical text; present empty element has empty text, not an absent property. M1 strings remain unchanged and never become SQL NULL. |
| `conversion_outcome`, `conversion_reason` | Required explicit outcome and reason from the rules below; never infer outcome from `value_decimal IS NULL` alone. |
| `model_version` | Exactly `M2_ADDITIVE_TYPED_NUMERIC_V1`. |
| `conversion_rule_version` | Exactly `EXACT_DECIMAL_38_4_V1` for this proposed grammar/range/outcome policy. |
| `source_rule_version` | `FSDS_NUM_VALUE_SCOPE_V1` or `TREASURY_RATE_QNAME_SCOPE_V1`; these identify separate selection/context rules, not financial equivalence. |
| Source/occurrence lineage and context | Preserve or reference exact source ID/identity, RAW path/SHA, member/SHA where applicable, source field name/QName and occurrence locator, original context and source parser/rule versions. Record M2 run ID, input snapshot references, effective scope, contract SHA, implementation revision and dependency/config fingerprints using existing run conventions. M2 versions supplement rather than relabel M1 versions. |

**FSDS initial eligible scope:** only `num.txt` field `value` at the three retained M1 witnesses: SRC000060 line 64698, SRC000053 line 312006, SRC000054 line 337467. Exact run/binding/RAW/member hashes, byte locators and lexical values are in Step 2. Field identity includes its ordinal (9), original name and existing technical locator `(run_id, binding_sha256, source_line)`; no inferred business key. This deliberately bounded proposal does not grant conversion of all FSDS NUM or historical backfill. Existing FIN fixtures remain preservation/validation evidence; adding their lexical occurrences to a later M2 evaluation requires explicit scoped selection, not silent expansion.

**Treasury eligible snapshots:** only SRC010451–SRC010455, the five admitted 2025 XML files with exact identities and SHA in Step 2 and the [approved input plan](../proposals/n750-step1-v3/plan.json). Only the following exact property local names, in namespace `http://schemas.microsoft.com/ado/2007/08/dataservices`, are eligible under `a:feed/a:entry/a:content/m:properties` (`a`/`m` namespace URIs as recorded in Step 2):

| Source | Explicit property allowlist (brace notation expands only the listed members) |
| --- | --- |
| SRC010451 | `BC_{1MONTH,1_5MONTH,2MONTH,3MONTH,4MONTH,6MONTH,1YEAR,2YEAR,3YEAR,5YEAR,7YEAR,10YEAR,20YEAR,30YEAR,30YEARDISPLAY}` |
| SRC010452 | `ROUND_B1_{CLOSE,YIELD}_{4,6,8,13,17,26,52}WK_2` and `CS_{4,6,8,13,17,26,52}WK_{CLOSE,YIELD}_AVG` (Cartesian expansion of the listed choices only). |
| SRC010453 | `RATE` |
| SRC010454 | `TC_{5YEAR,7YEAR,10YEAR,20YEAR,30YEAR}` |
| SRC010455 | `RATE` |

No wildcard inference from `Edm.Double`, numeric-looking text or future fields. Dates, IDs, CUSIPs, `CF_WEEK`, `RATE_TYPE`, `EXTRAPOLATION_FACTOR` and reason fields are excluded. Retain property QName, source attributes (including Edm/null markers), document-order entry and property occurrence positions, exact RAW reference, and date/tenor/rate-type context. Preserve repeated properties as separate occurrences; no uniqueness or deduplication is inferred. A future adapter must demonstrate deterministic RAW-resolvable XML locators before use; its gap remains separate from this numeric contract. An absent allowlisted property is represented as a `MISSING` evaluation for that entry/property position, explicitly marked absent with no fabricated source text; it is not an extra RAW/M1 record. Selected coverage and absent evaluations must be counted separately from present source occurrences.

## Numeric conversion — PROPOSED

**Precision/scale:** use signed `DECIMAL(38,4)`, at most 34 significant integer digits and four fractional places; maximum absolute value `9999999999999999999999999999999999.9999`. OBSERVED: the existing FIN contract uses DECIMAL(38,4); FSDS examples include `9830000.0000` and `0.0070`; Treasury's 12,793 present rate/yield texts have scale 2. This supports exact representation of the inspected values and existing FIN results, not every value in those sources or future data. FIN numeric result scale is not proof of original lexical scale. Corpus-wide precision maxima are unmeasured.

Parse the **unchanged original TEXT**, never a float or a float-derived string. Require full ASCII grammar `[+-]?[0-9]+(?:\.[0-9]+)?` (entire string, no terminal-newline exception). Optional sign and leading zeroes are proposed engineering allowances, not observations that all variants occurred. No exponent, separators, currency/percent signs, underscores, Unicode digits, `NaN`, infinity, `.5`, `1.` or surrounding whitespace. No locale inference or fallback cast. Determine sign, significant integer digits and fractional length from text; use exact decimal/integer operations that cannot round through a default arithmetic context.

Accept fractional length 0–4 only. Storing a lower-scale value in scale 4 explicitly pads fractional zeroes without changing its numeric value (`4.45` -> `4.4500`); original `4.45` remains in `lexical_value`. This is the sole proposed storage-scale adaptation, not multiplication, division or a unit conversion. Never silently quantize or remove fractional digits: even `1.00000` is `SCALE_EXCEEDED`, although numerically representable. No rounding, truncation or numeric rescaling. Leading zeroes/sign survive in lexical text; the decimal field need not preserve positive/negative-zero spelling.

Evaluate outcomes in the order below; each non-VALID outcome has SQL NULL `value_decimal` and retains its source evidence. Outcomes describe projection availability, not record admission or source correctness.

| Condition | Outcome / reason | Observation versus proposal |
| --- | --- | --- |
| Selected property/field is structurally absent | `MISSING` / `SOURCE_FIELD_ABSENT` | Treasury absent tenor properties were observed; withholding a typed value while accounting for absence is proposed. Missing required FSDS fields remain an upstream structural failure, not silently fabricated CLEAN values. |
| Explicit source null marker (`m:null="true"`) or an independently declared input null state; no conflicting nonblank text | `NULL_UNRESOLVED` / `SOURCE_NULL_MARKER_UNINTERPRETED` | No numeric XML null marker was observed. Preserve marker/state and withhold conversion; no financial NULL interpretation or new FSDS null-token rule is approved. An unexplained adapter NULL is a contract failure, not automatically this outcome. |
| Null marker conflicts with nonblank text | `INVALID` / `CONFLICTING_NULL_MARKER` | Proposed fail-closed projection rule, not an observed anomaly or authority to drop the occurrence. |
| Present TEXT is empty or consists entirely of ASCII space, TAB, CR, LF, FF or VT | `BLANK` / `EMPTY_TEXT` or `WHITESPACE_ONLY` | Empty context fields were observed; blank numeric policy is proposed. Do not trim mixed whitespace/numeric text. Empty XML elements without null marker are BLANK, not NULL. |
| Present nonblank TEXT fails full grammar | `INVALID` / `LEXICAL_GRAMMAR` | Proposed. Literal `NULL` and `N/A` have no approved numeric null-token meaning and fail grammar; preserve them verbatim. Observed `N/A` was an excluded Treasury context property. |
| Grammar valid, fractional length >4 | `SCALE_EXCEEDED` / `FRACTIONAL_DIGITS_GT_4` | Proposed conservative policy; no such inspected numeric witness. Check this before range so multiple issues have deterministic precedence. |
| Grammar valid, scale <=4, significant integer digits >34 | `OVERFLOW` / `INTEGER_DIGITS_GT_34` | Proposed; no observed overflow. Ignore only leading integer zeroes for the range test, not in stored text. |
| Grammar valid, scale <=4, range fits | `VALID` / `EXACT_PROJECTION` | Exact parseability of inspected witnesses is observed; this grammar and eligibility policy are proposed. |

Retain all outcomes and counts by source/rule; invalid/overflow is not zero, source rejection or silent row loss. A run with nonconverted occurrences cannot claim every selected value converted; explicitly expected missing/blank states remain accounted outcomes. Unexpected integrity/hash changes, missing lineage, ambiguous input state, parser failure or loss of occurrence accounting stop the affected output before publication under existing fail-closed rules. These checks do not infer source financial inconsistency.

## Separate interpretation boundaries and compatibility

FSDS: preserve literal `uom`, tag, taxonomy/version, filing `adsh`, `ddate`, `qtrs`, segments, coreg and footnote context. `pure` is not assumed USD or multiplied by 100. Treasury: preserve the original property/date/tenor/rate-type and nominal/real feed context; `RATE`, `CLOSE`, `YIELD`, display and average properties are not declared equivalent. Missing XML properties are neither zero nor intrinsically invalid. No percent/fraction convention, day count, cross-source aggregation, date alignment, entity identity, business key, financial correction or amendment precedence is approved by sharing Decimal storage.

M1 schemas, types, names, exact values, empty strings, field order, rows/multiplicity, framing/accounting, acceptance/failure behavior and frozen outputs remain unchanged. Preserve RAW immutability, source/binding/member identities and hashes, cohort manifests, existing locators and lineage. Publish M2 with distinct versioned output references; do not overwrite or repoint accepted M1 tables/views. Independent M1 reproduction uses its original code/rules/snapshots; independent M2 reproduction uses those pinned input references plus its own contract/scope/rules/code/config/dependencies. Neither model depends on a mutable “current” view or silent authority-pin change.

M1 SQL and FIN_001/FIN_002 remain reproducible at their original pinned source/run/snapshot scope, exact expected values, zero-tolerance equations and 13 lineage witnesses, including FIN_002's wrong-equity negative control. Later compatibility validation must compare unaffected fields and results; no fresh PASS is asserted here. M2 projection failures cannot mutate M1 outcomes. No historical backfill is required by this document; any later validation requiring historical M2 coverage must name its bounded input scope and authority first.

## Exact owner decisions pending under the existing process

| Approval question | Minimal recommendation | Alternative and consequence |
| --- | --- | --- |
| Approve DECIMAL(38,4), grammar, explicit zero-padding and excess-scale/range precedence as `EXACT_DECIMAL_38_4_V1`? | Approve the exact policy above for the bounded snapshots only. | Defer precision/grammar selection: no typed execution. A wider/variable scale or acceptance of excess trailing zeroes needs a revised explicit contract; do not silently broaden V1. |
| Approve outcome taxonomy and SQL NULL solely as “no projection,” with no source null tokens? | Retain each occurrence, distinguish absent/blank/explicit-null/invalid/scale/overflow, and leave financial NULL meaning unresolved. | Fail the whole run on conversion failure: simpler binary success, but withholds valid projections too. Mapping blanks/NULL/N/A to a financial missing value or zero requires separate evidenced owner interpretation; not recommended here. |
| Approve the three FSDS witnesses, five exact Treasury snapshots and explicit property lists, source-rule versions, absent-field accounting and RAW-resolvable XML locator requirement? | Approve only these bounded selection/context rules; adapter implementation/validation and execution remain later work. | Defer Treasury or narrow the allowlist: reduced coverage; broaden FSDS/FIN coverage only through an explicitly scoped later decision. No parser approval is inherited from physical admission. |
| Approve separate M2 publication/versioning and the stated M1 preservation guarantees? | Add a separate typed projection while leaving accepted M1 untouched. | Defer M2: retain M1 plus existing query-local FIN casts, without satisfying the reusable typed capability requirement. |

Financial questions remain UNRESOLVED and outside this proposed mechanical conversion: documented Treasury units/rate conventions, any source-specific NULL interpretation or unit conversion, and broader fact/period/tenor semantics. They require evidence and explicit owner decisions before dependent interpretation, not guesses to populate this contract. No approval identity/time or decision-log APPROVED entry is invented. A PR merge records this proposal only. Current status remains **M2_CONTRACT_PROPOSED_PENDING_APPROVAL**; stop before Step 5 and all M2 processing, with no Day 4 merge to main.
