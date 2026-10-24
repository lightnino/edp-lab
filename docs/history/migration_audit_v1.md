# Phase 2 historical documentation relocation — scoped integrity audit

**Status:** PROPOSED FOR OWNER REVIEW; no merge, deployment, Databricks execution or grant is authorized by this report.
**Compared against remote main:** `6b5ee376da15c8642c10f0329cd75b43aaa9f3fc` (merged PR #67).
**Day 6 exclusion:** PR #61 remains open at `0a55388b29f89183fabc1ef3ba6a20314d50cb6a`; no file from its 42-file change set is edited in this Phase 2 PR. Its protected owner-terminal install is not invoked.

## Safe physical moves

| Old path | New path | Byte-preservation decision |
| --- | --- | --- |
| `docs/n450_step3_runtime_readiness.md` | `docs/history/day3-c750/n450_step3_runtime_readiness.md` | Only existing relative Markdown link changed to resolve the original (unchanged) N450/C750 execution-evidence path; original Git blob `84f088f3460640e1243518d56d722b384ca45d14` retained in Git history |
| `docs/n750_c1500_execution_evidence.md` | `docs/history/day4-c1500/n750_c1500_execution_evidence.md` | Exact Git blob retained: `88f52f1c060ae514dff8b63e6e45c09e7ede339f` |

The parent [documentation registry](../README.md) now routes readers to [historical evidence](README.md), which indexes **all** known Day 3/4 reports, including path-pinned files that stay at the original locations. The link in the existing 10/23 Standing Authorization finding to moved N750 membership evidence is repaired. There are no redirect-stub duplicates.

## Explicitly retained legacy evidence

- `docs/n450_c750_execution_evidence.md` is referenced by **DEC-000011** in `metadata/decision_log.csv`.
- `docs/c750_stability_v2_runbook.md` and `docs/c750_stability_v2_evaluation.md` are referenced by **DEC-000012**; the C750 V2 evaluation is also referenced in `metadata/freezes/O_C750_M1_v1/freeze.json`.
- `docs/n750_step8_execution.md` is referenced by `metadata/evaluations/day4_performance_v1.json`.
- `docs/o_c1500_m2_freeze_assessment.md` remains as a historical CANDIDATE narrative with inbound historical document links; **important:** signed C1500 freeze directly references the separate `metadata/evaluations/o_c1500_m2_freeze_assessment_v1.json`, **not** the similarly named Markdown file. No freeze-path lock is claimed for the Markdown solely because of the matching basename.
- Other C1500 Stability, N450 B1/guardrail and Day 4 closeout records remain indexed, not physically moved where inbound references or SHA/policy dependence has not yet been exhaustively cleared. Do not edit an approved, byte-pinned upstream document merely to change a Markdown link.
- [Vault Load Contract V1](../vault_load_contract_v1.md) remains at its exact approved path and byte SHA-256 `681c3f6a9a4446b5357c3ab6c6534e6fd5b8cf944f967ea9ab27dcc2c8b5aabe`. It is a source-scoped approved semantic contract, not an authorization for Day 6 Step 2.

## Protected metadata / runtime integrity

Git tree comparison of the scoped branch against the baseline shows **zero modified paths** in:

| Protected prefix | Tracked files | Modified |
| --- | ---: | ---: |
| `metadata/authorizations/` | 11 | 0 |
| `metadata/freezes/` | 51 | 0 |
| `metadata/operating/` | 3 | 0 |
| `metadata/evaluations/` | 31 | 0 |
| `metadata/source_universes/` | 7 | 0 |

Also byte-identical Git blobs before/after: `docs/vault_load_contract_v1.md`, `metadata/decision_log.csv`, `metadata/authorizations/day6_vault_load_contract_v1_owner_approval.json`, `scripts/day6_vault_contract_v1.py`, `docs/workflows/agent_operating_contract_v1.md`, `AGENTS.md`. Source, signed freeze and Databricks data are not regenerated.

The new `tests/docs/test_phase2_history_navigation.py` checks the two relocated blobs, moved-file Markdown links, obsolete-path references in tracked text, and approved Vault V1 content SHA. These local/CI gates **do not** claim independent protected-host deployment or remote Databricks validation; none is needed for this documentation-only migration.

**Exit condition:** CI PASS, exact diff reviewed, remote main unchanged until explicit owner PR approval. Leave other pinned legacy paths in place until after Day 6 or a separate reviewed, versioned re-pin migration.
