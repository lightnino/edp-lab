# Canonical domain and tool contracts

Approved technical or semantic contracts remain at their **actually pinned locations** until a reviewed successor and all consumers are migrated. An index is a link to the original—not a duplicate specification and not approval to run a new workload.

| Contract / invariant | Canonical path | Status / scope |
| --- | --- | --- |
| Source identity / physical lineage | [Source-instance identity](../source_instance_identity.md) | Reusable identity/provenance rules; distinguish physical source identity from enterprise business identity |
| Governance authority boundary | [Ownership/approval boundaries](../ownership_approval_boundaries.md) | Human semantic and signed authorization boundaries |
| C300 source-specific admission proposal | [Corpus admission policy](../corpus_admission_policy.md) | **Historical proposal**, not generalized standing approval |
| Parser/profiling interface | [Parsing & Profiling Contract V1](../parsing_profiling_contract_v1.md), [Profiling output contract](../profiling_output_contract.md) | Version/snapshot scoped; source-specific exceptions remain separate |
| Typed read-only agent profiling tools | [Profiling Tool Contract V1](tools/profiling_tool_contract_v1.md) | Implemented in `src/edp_lab/tool_adapters/` with tests; not obsolete, **does not** grant Databricks writes |
| Additive typed numeric M2 | [M2 typed numeric V1](../m2_additive_typed_numeric_v1.md) | Source-/field-/version-scoped; no general economic semantics |
| **Vault Load Contract V1** | [Approved Vault Contract V1](../vault_load_contract_v1.md) | **Owner-approved D1–D5 semantic contract** (PR #60); FSDS NUM source-scoped; byte/path pins retained. Approval alone does NOT authorize Step 2/Step 3 Databricks writes |

Vault references: [immutable owner approval](../../metadata/authorizations/day6_vault_load_contract_v1_owner_approval.json), [source scope evidence](../../reports/day6_vault_d1_d5_evidence.md). The contract contains an as-of-approval Day 6 Step 0 prerequisite; the later signed **C2000 P13 freeze exists** via [PR #64](https://github.com/lightnino/edp-lab/pull/64). The contract's historical text is left **byte-for-byte unchanged** to preserve SHA-256 `681c3f6a9a4446b5357c3ab6c6534e6fd5b8cf944f967ea9ab27dcc2c8b5aabe` and current runtime/standing-policy pins.

**Rules for future consumers:** Reference an exact contract ID/version/path/SHA; run independent source and output validation; request separate bounded owner data scope and protected 0A authorization. To change the semantic contract, issue a new version with signed owner approval and update consumers under a reviewed migration—not an in-place edit to V1.
