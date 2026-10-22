# Day 4 Step 10 — Agent V2 quality regression

**Result:** `AGENT_QUALITY_MEASURED` on the unchanged, curated 23-case engineering benchmark. This measures bounded candidate answers and evidence quality. It is not blinded human adjudication, production accuracy, canonical entity integration or semantic approval.

## Frozen benchmark and reproduction

The input and truth files exactly match ground-truth commit `31fd869c697e3afd6611838794513a3fcf64e927`. Ground-truth SHA-256 is `9ba83190b260b1bb5ac7feb0043fa7591b9da846f49a40be0d7fe6c4428477fd`. `scripts/evaluate_agent_v2.py` regenerated and validated all 23 frozen proposals, original code and input/proposal fingerprints, and fixed score: result fingerprint `9a108f56e606f45541e209237dcadcfbfbc306a2bef42697d09cfcedfacd035d`. No labels, case IDs, questions, truth reasons or original proposals changed. Full per-case truth reason, prediction, state, source/hash/locator witnesses, compatibility, transformation, conflict/support, review routing and fingerprints are in `metadata/evaluations/agent_v2/quality_regression_step10_v1.json`.

The benchmark includes STTM 11, Crosswalk 4 and ER 8; truth labels are MATCH 7, NON_MATCH 10, UNRESOLVED 6. The cases were fixed before candidate implementation, but were curated in the same engineering context, without blinded independent human labels or a held-out production sample. A MATCH is relative to its exact question: typed representation, native token, technical occurrence or bounded schema candidate. It does not imply canonical legal entity/security/issuer equivalence.

## Confusion matrices

Rows are fixed truth; columns are predicted MATCH / NON_MATCH / UNRESOLVED.

| Population | Truth MATCH | Truth NON_MATCH | Truth UNRESOLVED | Correct |
| --- | --- | --- | --- | ---: |
| Overall | `7 / 0 / 0` | `0 / 10 / 0` | `0 / 0 / 6` | **23/23** |
| STTM | `4 / 0 / 0` | `0 / 5 / 0` | `0 / 0 / 2` | **11/11** |
| Crosswalk | `3 / 0 / 0` | `0 / 1 / 0` | `0 / 0 / 0` | **4/4** |
| ER | `0 / 0 / 0` | `0 / 4 / 0` | `0 / 0 / 4` | **8/8** |

Against these fixed labels, Agent V2 has **zero** false MATCH, false NON_MATCH, premature UNRESOLVED resolution or excessive abstention. All six ambiguous cases S08, S11, E05, E06, E11 and E12 remain unresolved. Native-token and occurrence results are not scored as canonical-entity truth. The contemporaneous **name-only heuristic**, which was not Agent V1, scored 8/23; its five false matches were S10/E03/E07/E09/E10, four question-scoped false non-matches were S01/S02/S05/S06, and it prematurely resolved all six ambiguous cases.

STTM accepted only the two bounded Decimal representation questions and two scoped source/schema proposals; S05/S06 remain `PROPOSED`. Five STTM measure/role incompatibilities were rejected, and two measure relations withheld. The exact Decimal candidate retains original text and source-specific unit, grain and time labels without claiming a unit conversion. Crosswalk preserved native identifier namespaces, accepting three literal-token questions and rejecting CIK versus CUSIP. ER rejected four distinct technical occurrence/token questions and left four canonical relationships unresolved. No canonical positive ER case was independently available.

## Proposal authority, review and observed defect

Numeric confidence is **`NUMERIC_CONFIDENCE_NOT_EMITTED`**. Five `VALIDATED` states are confined to typed representation or exact native-token checks; none claims semantic validation. There were zero canonical promotions, automatic approvals, production writes, source-identity conflations or unsupported transformation claims. All 23 proposals retain two source witnesses with RAW SHA and locators, unit/grain/time compatibility, and an explicit transformation requirement. Eight proposals require review: S05, S06, S08, S11, E05, E06, E11, E12; all eight have a review question and at least two alternatives. The existing artifact sent three consequential requests, E05/E06/S08, with zero recorded responses and no semantic approval. DEC-000015 remains UNRESOLVED; active review time is **UNMEASURED**. Silence was not treated as approval.

**Observed failure:** S09's original NON_MATCH label was correct for `ROUND_B1_CLOSE_4WK_2=4.26` versus `ROUND_B1_YIELD_4WK_2=4.33`, but the structured `conflicting_evidence` array was empty despite its reason relying on the unequal values. This is an evidence-completeness defect in one case, not a measured false match or demonstrated financial conversion error. The focused `EDP_CANDIDATE_AGENT_V2_EVIDENCE_V2` wrapper adds the explicit source property/value conflict only for a bounded CLOSE/YIELD NON_MATCH with unequal text. On the exact same 23 questions, **only S09's structured conflict evidence changed**; labels, states and 23/23 matrix did not. The original V1 implementation and frozen proposals remain intact. The remaining, more consequential *unvalidated* risk is canonical security/manager and temporal identity outside this benchmark.

Agent V1 provided bounded key/functional-dependency observations on a five-row FSDS sample and contextual attachments. It did not emit compatible STTM/Crosswalk/ER decisions on these same 23 questions: **`NEW_CAPABILITY / NO_COMPARABLE_BASELINE`**. No V1→V2 improvement percentage is calculated. The name-only score is a same-case heuristic comparison only.

## Safety checks and limits

The existing read-only adapter, governance and Agent negative tests reject label leakage, tampering, forged approval, unauthorized promotion and write requests. Focused Step 10 tests reproduce the frozen benchmark, verify the S09-only correction and reject a forged canonical promotion. No LLM/API call, retrieval system, new production store, cross-source mapping, canonical ID, deduplication or approved business join was introduced. Original source evidence remains at its recorded witness/hash scope; this evaluation did not broadly rehash every external RAW artifact. The previous local candidate-and-scoring interval was 0.003174 seconds, excluding evidence preparation/imports and active human review; it is not a production throughput measure.
