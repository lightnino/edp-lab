# Historical execution evidence registry

**Purpose:** Index completed cohort/day-specific evidence without confusing it with current rules. Historical records are not authority to run a workflow, submit a Databricks write, change a model or approve a new cohort.

| Historical execution | Evidence index | Authoritative current rules |
| --- | --- | --- |
| Day 3 / N450 → C750 | [Day 3 / C750](day3-c750/README.md) | [Cohort/Model Lifecycle](../workflows/cohort_model_lifecycle_v1.md) and [Validation/Freeze](../workflows/validation_freeze_lifecycle_v1.md) |
| Day 4 / N750 → C1500 | [Day 4 / C1500](day4-c1500/README.md) | Same Lifecycle/Validation rules; approved source/model changes remain separately scoped |

**Migration classification:**
- **MOVED:** Only evidence files with no located live Day 6 PR #61 dependency or pinned owner-decision/freeze path, with inbound links checked and repaired.
- **PINNED_LEGACY_PATH:** Retain the exact original file path when a signed/approved decision, freeze, evidence manifest or unverified external consumer refers to it. Index links only; never duplicate the file as an alternative canonical copy.
- **HISTORICAL_SUPERSEDED_STATE:** A preflight `NO GRANT`, `CANDIDATE` or `BLOCKED` remains correct for the timestamp of that report; consult subsequent accepted freeze/closeout to learn final outcome.

**Zero Day 6 interference:** Do not relocate or modify `docs/vault_load_contract_v1.md`, `metadata/authorizations/`, `metadata/freezes/`, `metadata/operating/`, any `docs/vault_*.md`, Day 6 Vault scripts/runtime/test modules or protected credential/warehouse artifacts. The active [PR #61](https://github.com/lightnino/edp-lab/pull/61) is intentionally out of scope. A later pathname migration for any pinned document requires a separately approved versioned re-pin and consumer migration after Day 6.

See [Documentation Governance Registry](../README.md) and [Incident Registry](../incidents/README.md).
