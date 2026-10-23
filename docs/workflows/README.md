# EDP Lab Workflow Specification V1 — Owner Review Index

**PROPOSED. Not approved, not executable, and not an authorization to process data.**

This PR defines the workflows before we implement a runtime DAG on top of the already merged PR #51 policy-governed runner. The owner reviews/approves this specification first. **Do not merge the PR without explicit owner review.** A separate later implementation PR must independently prove executable adapters, negative tests, true guarded Databricks writes/readbacks and end-to-end C2000 readiness.

| Spec | What it standardizes | Historical source |
| --- | --- | --- |
| [Universe Lifecycle](universe_lifecycle_v1.md) | Initial source universe (0→1) and expanded universe (1→2); membership, provenance, holdouts, scope approval, immutability | Approved Universe v1 + 800-outside-universe incident |
| [Cohort + Model Lifecycle](cohort_model_lifecycle_v1.md) | Initial M1, Corpus-only, Additive, Corrective, conditional Parser Exception, L6 economic research, minimal backfill/replay and one bounded authorization | Day 2 C300; Day 3 N450; Day 4 N750/M2; revised autonomous Day 5 |
| [Validation + Freeze Lifecycle](validation_freeze_lifecycle_v1.md) | Actual Lossless 1–6, A/B2/C1/C2/C3 with branch-specific oracles, economic test promotion, pre-approved comparable performance budget, live Databricks freeze and Git exit | FIN/TRY/Stability controls + Day 2/3 freezes + PR #50 |

## Owner review checklist

- [ ] Candidate work order is **RAW → CLEAN → provisional QUERYABLE → full Lossless → Stability → accepted Result Freeze**; pre-write integrity checks and consumer isolation remain mandatory.
- [ ] Parser Exception and Checkpoint Recovery are *conditional subpaths*, not required ordinary steps.
- [ ] Additive requirements may have **1..N drivers**, from old and/or new sources; no hard-coded two-source assumption.
- [ ] Corpus-only / Additive / Corrective are **alternative branches**, each with precise Stability A/B2/C and history-equivalence/approved-delta tests.
- [ ] Missing L6 economic logic triggers evidence research, bounded read-only Databricks SQL tests, owner semantic approval, **permanent versioned test registration**, targeted L6 rerun and automatic later applicability.
- [ ] If evidence is absent, explain `PRESERVED_NOT_MODELED` vs `NOT_IMPLEMENTED` vs genuinely corrupted data; Treasury 50 approved dispositions/155 structural missing are preserved.
- [ ] A pre-approved **10× performance envelope** may mechanically pass only in genuinely comparable future N750-like phases; original Day 4 C3.4 remains BLOCKED and unrelated limits are not changed.
- [ ] Historical accepted M1/M2 and old freeze references never overwritten. Version-pinned readback and actual Databricks freeze are required, not a Git-only claim.
- [ ] The Owner approves source-estate or new business-meaning decisions. After one bounded workflow grant, Agent A may run permitted mechanical operations without repeatedly asking for each step.
- [ ] **Day 5 only** targets the full autonomous C1500→C2000 experiment now. Day 6 Vault and Day 7 Universe v2 are initially manual/agent-assisted to discover approval boundaries; promote their reusable flows later.

## Evidence and scope

Reviewed against actual historical [Day 2 PR #19](https://github.com/lightnino/edp-lab/pull/19), [Day 3 PR #29](https://github.com/lightnino/edp-lab/pull/29), [Day 4 live freeze PR #50](https://github.com/lightnino/edp-lab/pull/50), and [PR #51 runner](https://github.com/lightnino/edp-lab/pull/51), as well as source-specific decision and exception records. Proposed acceptance steps are *not* historical assertions: early Day 2 lacked the later fully approved Universe v1 gate; the historical Day 2 downstream gate order differed; Day 4's historical C3.4 was not retrospectively repaired.

**Excluded from this PR:** executable DAG/queue, production credential/key configuration, new grants, N500 roster/admission, economic-rule promotions, Vault design/load, Universe v2, Databricks writes/freeze, and Git merge. The PR itself remains **DRAFT** until owner content review.
