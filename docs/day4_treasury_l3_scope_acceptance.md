# Day 4 Treasury L3 source-preserving acceptance — post-closeout supplement

**Decision scope:** The requesting project owner directed closure of the pending 50 Treasury source/QName dispositions, selecting `PRESERVED_NOT_MODELED` **only** for the original five pinned N750 Treasury feeds (SRC010451–SRC010455). The exact 50 fields and source/RAW identifiers, with the unchanged previously pending inventory reference, are enumerated in [the versioned owner-scope decision](../metadata/evaluations/treasury_l3_owner_scope_decision_v1.json).

This means the original Treasury XML lexical observations and approved additive `DECIMAL(38,4)` representations are retained, *not* accepted as normalized enterprise financial measures. It **does not** approve rate/yield equivalence, cross-feed joins, inferred grain/units/time semantics, canonical mapping, financial equations or economic integration.

## Evaluation after scope decision

Previously executed read-only Databricks TRY_001–TRY_004 all PASS. FIN_001 2/2, FIN_002 1/1, 13 historical witnesses, and eight source-preserving bidirectional SQL comparisons remain PASS as recorded in the unchanged Step 9 V1/V2 evidence. No RAW processing, SQL or table publication was repeated for this decision.

[The additive scoped evaluation V3](../metadata/evaluations/c1500_m2_stability_scoped_v3_owner_acceptance.json) reports:

- `B2.1_SOURCE_PRESERVING = PASS`
- `C1_SOURCE_PRESERVING = PASS`
- `C1500_M2_ECONOMIC_INTEGRATION = NOT_IMPLEMENTED`
- Historical `DAY4_C3.4 = BLOCKED`
- 10× future budget = `PROPOSED_PENDING_APPLICABILITY_APPROVAL`
- `O_C1500_M2 = CANDIDATE` (**not** a result freeze)
- Day 4 exit remains `PARTIAL` due to the remaining operational and result-freeze requirements.

The scope decision and V3 evaluation are new, versioned facts. **Do not rewrite** the original Step 9 V1/V2, the earlier 50-field inventory, or the original Step 13 CANDIDATE assessment; those accurately represent the state at their respective evaluation times.

## GitHub integration

The Day 4 validated implementation, permanent Lossless 6 suite and documentation may be integrated to `main` with explicit **PARTIAL** status. Integration is not a claim of `RESULT_FROZEN` or that C3.4 passed. Future cohorts retain mandatory FIN_001/002 and TRY_001–004 under `LOSSLESS6_SUITE_V3`; the exact historical five-source fixture is immutable, while newly admitted Treasury sources require new independent fixtures and applicable live checks.
