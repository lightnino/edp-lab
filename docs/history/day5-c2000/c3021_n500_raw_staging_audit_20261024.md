# Day 5 C3021 / N500 — RAW staging: execution, audit, resolution

**Record type:** Historical RAW-staging audit and architecture follow-through. This is **not a new security incident**, not a new processing authorization, and not a request to rerun Day 5. The contemporaneous Day 5 results are preserved. Findings below are bounded to the inspected receipts, Databricks workspace history, and local forensic evidence; unobserved history is not converted into a fact.

## What happened

- The original C3021 acquisition established **3,021 local physical sources**: **3,015 new verified downloads**, plus **six already local**.
- Before the Day 5 upload, available historical receipts and inspected Databricks RAW volume established **1,500 / 3,021** sources with remote-upload evidence; **1,200 / 3,021** have independent remote SHA-256 readback evidence. A complete reusable historical remote locator index for the other **1,521** sources was not available to the audit.
- The **actual Day 5 N500** comprised **500** selected physical source instances from the original approved Universe, distinct from other historical cohorts that might also be named N500. Its original Queue assigned a *new cohort-specific remote RAW destination* for every source.
- The Day 5 RAW adapter checked its newly assigned destination; it did **not** reconcile every N500 identity and SHA against prior C3021 acquisition receipts and cross-cohort remote RAW locators. **500 `DAY5_UPLOADED`** actions wrote **179,462,305 source bytes**, starting **2026-10-23 19:21:51.038 UTC**. These were actual Day 5 uploads, not proof that the bytes were absent elsewhere.
- Day 5 C2000 execution later completed **513 / 513** tasks, accepted its independently verified P13 result freeze and merged the P14 closeout in [PR #64](https://github.com/lightnino/edp-lab/pull/64). The Day 5 Supervisor was stopped before this forensic investigation.

## What the read-only audit found

- The **500-row N500 reconciliation matrix v4** records **500 `DAY5_UPLOADED`** and **500 `NO_PREEXISTENCE_EVIDENCE`** observations. The reported matrix SHA-256 is **`4b2fbe7bc2086847c96fa883ef138d821029d387601dfe9ce5213921f447f0fe`**. No new source-level evidence justified changing any row, so no v5 matrix was created.
- A broader, time-bounded historical search found **zero pre-Day-5 paths identifying those exact 500 physical sources**, no second RAW volume in the inspected accessible workspace, and no visible delete/move/copy event in the inspected history.
- **No redundant-upload bytes are established by the evidence.** This does **not** prove there were no redundant uploads. Absence of an indexed old location/receipt is not proof that an earlier copy was absent. No monetary, DBU or redundant-runtime savings can be calculated reliably from the available evidence.
- The identified **execution-design gap** is that the old RAW adapter only checked a newly selected Cohort destination and had no cross-history resolver/locator-handoff lookup. This explains **why historical reuse was not attempted**; it does not establish that a reusable historical copy existed for any particular N500 source.
- Remaining inaccessible/unresolved evidence includes historical locators for 1,521 sources, direct storage/object versions, other-workspace records, arbitrarily named earlier copies, and complete independent C300 readbacks. These limits are recorded, not silently classified as remote absence.

## Resolution and the operating boundary now recorded

1. **Standing protected authorization — [PR #59](https://github.com/lightnino/edp-lab/pull/59), MERGED.** Implemented the signed standing **0A policy / independent protected broker** and exact run-grant mechanism. It removed repeated per-cohort human grant installation for authorized runtime stages; retained protected write/identity limits. **It did not itself implement a complete Acquisition-only RAW writer / Cohort RAW-read-only separation.**
2. **Single owner for RAW staging — [PR #62](https://github.com/lightnino/edp-lab/pull/62), MERGED (workflow specification).** The binding intended separation is:
   - **Acquisition / Universe U3** resolves existing immutable remote RAW by exact physical identity, SHA-256, bytes and real remote location across historical inventories and receipts; verifies readbacks and stages missing bytes only with separate Acquisition write authority.
   - **Universe U10** supplies a verified immutable RAW locator / SHA / byte size / readback receipt as the **handoff** to downstream Processing.
   - **Cohort P0/P1/P8/P11** **only reads** this handed-off RAW. Missing, mismatched or unresolved input returns `RAW_HANDOFF_BLOCKED`; Cohort requests separately authorized **Acquisition remediation** and resumes from the verified handoff **without** independently uploading, copying, moving or restaging RAW.
   - Protected runtime enforcement must deny Cohort RAW upload/copy/move/overwrite/restage, including a negative authorization test. **This technical split is an outstanding implementation/verification obligation, not code delivered by PR #62.** The current historical Runner still contains a `raw_stage` operation route; don't represent the architecture contract as deployed protection until its broker, adapter and credential isolation are verified.
3. **Do not apply new requirements retroactively.** PR #62 postdates the actual Day 5 N500 staging; the audit classifies historical implementation and evidence, not a retroactive policy violation. The read-only audit neither changed the original signed Queue/checkpoint/ledger nor re-uploaded RAW.

## Evidence provenance and retention

The forensic investigator generated the following **local** records. The repository's `.gitignore` ignores `runs/**`, so these paths are **provenance pointers**, not claims that their bytes are present in GitHub:

- `runs/audits/c3021_day5_raw_reuse_20261024/report.md` — original narrative report.
- `runs/audits/c3021_day5_raw_reuse_20261024/n500_reconciliation_matrix_v4.csv` — 500-row matrix; SHA-256 stated above.
- `runs/audits/c3021_day5_raw_reuse_20261024/final_disposition_addendum_20261024.md` — additional time-bounded search/results.
- `runs/audits/c3021_day5_raw_reuse_20261024/inaccessible_evidence_register_v1.json` — specific sources of missing historical evidence.

**Evidence handling:** This committed narrative records the supplied audit findings but does **not independently attest the hash of files accessible only in the owner's local run directory**, nor substitute for retaining the local matrix/addendum/register as immutable evidence. To archive the complete raw evidence later, explicitly stage the exact verified bytes in a separate reviewed evidence-only commit; do not fabricate/reconstruct a 500-row CSV from narrative counts.

## Separation of work and outcome

- Historical **Day 5 C2000 P13/P14 is already closed** and must not be replayed.
- **PR #66** covers the unrelated P11 R4/R8 Supervisor/CLI protected-runtime acceptance and remains its own owner-reviewed workstream.
- **Day 6 PR #61** and approved [Vault Load Contract V1](../../vault_load_contract_v1.md) are untouched by this record.
- The remaining RAW optimization is a **prospective Acquisition Resolver + Receipt Index + Cohort read-only protected grant/negative-test implementation**. Treat it as a separate future change, not an excuse to alter or restage historical Day 5 RAW.

References: [Universe Lifecycle](../../workflows/universe_lifecycle_v1.md), [Cohort/Model Lifecycle](../../workflows/cohort_model_lifecycle_v1.md), [Day 5 P11 incident](../../incidents/2026-10-23-c2000-p11-sql/incident.md), and [historical Day 5 C2000 live closeout](../../../reports/day5/c2000_live_closeout_20261024.md).
