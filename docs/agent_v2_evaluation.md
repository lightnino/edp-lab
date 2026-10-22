# Bounded Agent V2 candidate evaluation

Status: **AGENT_PROPOSALS_EVALUATED**. Scope is candidate discovery only; canonical promotions: **0**. No Step 8/9 execution or merge to main is authorized here.

## Evidence and independence

[Ground truth](../metadata/evaluations/agent_v2/ground_truth_v1.json) and [source observations](../metadata/evaluations/agent_v2/inputs_v1.json) were fixed in commit `31fd869c697e3afd6611838794513a3fcf64e927` **before** candidate implementation and evaluation. Labels were derived from source evidence, not candidate output. Ground-truth SHA-256: `9ba83190b260b1bb5ac7feb0043fa7591b9da846f49a40be0d7fe6c4428477fd`. See [label methodology](agent_v2_ground_truth.md).

This is temporal independence, not independent human adjudication: one host prepared a curated set and subsequently implemented deterministic rules in the same session. There is no blinded, held-out or general canonical-ER accuracy claim. No independently approved cross-source canonical positive was available; native-token and schema positives must not be represented as canonical identity truth.

The 23 cases comprise 11 STTM, four crosswalk and eight ER cases: seven MATCH, ten NON_MATCH and six UNRESOLVED. Every case points to exact witness fields, source identity, context and locators; artifact references include file/member hashes. Existing frozen FSDS M1 witnesses and cached profiles were reused. Treasury observations come from the existing five-feed evidence report; no new XML processing occurred. Supplementary GOLD 13F, GOLD FSDS sub and Nasdaq observations create no new C1500 admissions. A few 13F occurrences were read after archive/member hash verification; no broad profiling or historical M2 replay occurred.

## Candidate results

[Full proposals](../metadata/evaluations/agent_v2/proposals_v1.json) record source field → candidate target, transformation requirements, literal unit/grain/time compatibility, supporting/conflicting evidence, review questions and state. Missing compatibility evidence remains unknown. Existing Agent V0 states, canonical hashing and read-only adapter conventions are reused. The added pure functions perform bounded checks; they neither load sources nor invoke an LLM/API or publish mappings.

| Case | Evidence question | Label / state |
|---|---|---|
| S01 | FSDS USD `9830000.0000` → approved Decimal representation | MATCH / VALIDATED |
| S02 | Treasury `BC_1MONTH=4.45` → approved Decimal representation | MATCH / VALIDATED |
| S03 | FSDS amount versus Treasury rate | NON_MATCH / REJECTED |
| S04 | Historical 13F VALUE versus FSDS USD fact | NON_MATCH / REJECTED |
| S05 | CIK/cik namespaced TEXT field alias; distinct roles retained | MATCH / PROPOSED |
| S06 | Two period fields, same accession and `30-JUN-2012` text | MATCH / PROPOSED |
| S07 | Filing date versus reporting period | NON_MATCH / REJECTED |
| S08 | `BC_30YEAR` versus `BC_30YEARDISPLAY`, both 4.79 | UNRESOLVED |
| S09 | Bill `CLOSE4WK=4.26` versus `YIELD4WK=4.33` | NON_MATCH / REJECTED |
| S10 | FSDS `pure` versus USD | NON_MATCH / REJECTED |
| S11 | Real-curve `TC_5YEAR` versus long-term real RATE | UNRESOLVED |
| E01 | Same accession token in submission/cover page | MATCH / VALIDATED |
| E02 | CIK versus CUSIP namespace | NON_MATCH / REJECTED |
| E03 | Same CUSIP, different holding occurrences | NON_MATCH / REJECTED |
| E04 | Same literal CUSIP token across those holdings | MATCH / VALIDATED |
| E05 | Canonical security equality across filing times | UNRESOLVED |
| E06 | Mirae USA/Hong Kong canonical manager merger | UNRESOLVED |
| E07 | Different accessions, shared prefix/report period | NON_MATCH / REJECTED |
| E08 | Same CIK token in two submissions | MATCH / VALIDATED |
| E09 | Same CIK, different filing occurrences/periods | NON_MATCH / REJECTED |
| E10 | Full Nasdaq `AAC.U` versus `AAC.W` native tokens | NON_MATCH / REJECTED |
| E11 | Shared symbol stem implies canonical security equality? | UNRESOLVED |
| E12 | Two blank FIGIs imply canonical equality? | UNRESOLVED |

VALIDATED means a mechanical representation/native-token check only. S05/S06 remain business-schema proposals. No unit conversion, percentage normalization, reporting-date alignment or source equivalence was performed.

[Scoring evidence](../metadata/evaluations/agent_v2/evaluation_v1.json): contextual candidates agree with 23/23 fixed labels; exact-field-name-only baseline agrees with 8/23. Baseline false matches: S10/E03/E07/E09/E10; false splits: S01/S02/S05/S06; premature resolutions: all six unresolved cases. These are curated experiment results, not population estimates. Schema/native-token false splits are not demonstrated canonical-entity false splits.

A concrete false-merge risk is CUSIP `037833100` in holding locators 170 and 316: SKs `59198261` and `46369807`, distinct accessions, reported values 230 and 213. Shared identifier text supports a token match while preserving both occurrences. CIK is not CUSIP; `AAC.U` and `AAC.W` have different full symbols and class descriptions. None establishes canonical-security equivalence or a deduplication rule.

## Candidate ERD and human review

The [bounded candidate ERD](agent_v2_candidate_erd.md) covers only MANAGER, FILING, ISSUER, SECURITY, LISTING, IDENTIFIER, HOLDING and REPORTING_PERIOD. Keys and cardinalities are explicitly questions, with source support, alternatives and consequences. No keys, canonical tables, production joins or semantic merges are adopted.

[Human-review record](../metadata/evaluations/agent_v2/human_review_v1.json): three consequential questions were sent (E05, E06, S08); zero responses or semantic approvals were observed at recording. All remain pending. S11/E11/E12 also remain unresolved; S05/S06 remain proposed. Active review time is **UNMEASURED**, not inferred from waiting time. DEC-000015 in the existing decision log records this unresolved boundary. Silence and a preselected UI choice are not approval. Candidate evaluation can complete without publishing these interpretations.

## Validation and reproducibility

Five focused tests cover deterministic results, complete case accounting, namespace/occurrence distinctions, tampering/label leakage, pure execution and the permission boundary. The focused negative test sends write/promotion requests through the existing read-only profiling adapter: forged approval is BLOCKED, unsupported publish tools fail, and synthetic mapping/crosswalk/identity stores remain byte-identical. This demonstrates the current API boundary using fixtures; it is not an OS sandbox penetration test or proof about nonexistent production stores.

Observed checks: **91 passed, 1 skipped**, including Agent V0, adapters and governance; Ruff PASS. Candidate generation/validation/scoring took **0.003174 seconds** locally, excluding imports/evidence preparation and human review. No LLM spend, source processing job or canonical promotion occurred. Uncovered boundaries include out-of-sample matching, independently adjudicated canonical positives, temporal canonical identity and production-scale accuracy.

Reproduce the fixed proposals, fingerprints and scores without rewriting artifacts:

```sh
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python scripts/evaluate_agent_v2.py
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python -m pytest -q tests/agents/test_candidates_v2.py tests/agents/test_analyst_v0.py tests/tool_adapters tests/governance
```

The verifier checks both fixed input files against the pre-evaluation Git commit and requires exact regenerated proposal/score equality. No full C1500 processing, N750 processing, M2 replay, canonical promotion or downstream step is included.
