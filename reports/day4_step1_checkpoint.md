# Day 4 Step 1 — N750/C1500 execution checkpoint

Status: **BLOCKED — waiting for exact Codex selection, trusted grant and authoritative publication**.
Do not treat this checkpoint as a cohort freeze, admission or completion marker.

## Completed in GitHub

- Step 0 baseline verified against merged Day 2/3 freeze artifacts: `reports/day4_step0_baseline.md`.
- Reusable, cohort-parameterized admission/freeze code and synthetic/current-C750-layout tests merged into this **Day 4 branch** by PR #30.
- Legacy Day 2/3 N450/C750 code and accepted freeze bytes remain unchanged.
- PR #30 CI: 348 passed, 124 skipped; Ruff PASS. (Read current workflow result for authoritative status.)

## Source-selection facts reported by the existing Codex run, NOT independently reproduced here

- Qualified proposed increment: 750, comprising 5 Treasury XML + 745 SEC Daily Master.
- 269,323,425 source bytes; zero C750 overlap, all 41 holdouts preserved.
- Combined 1,500 proposed physical identities.
- Base v4 corpus manifest 754 existing registration rows; new v5 would have 1,504 registration rows.

## Missing authoritative inputs and execution results

- Codex local `runs/day4/n750-selection-v1/selection.proposed.json` and `result.json`.
- Codex local `proposals/n750-execution-v1/REVIEW.md`, exact owner record, registration mapping and expected output SHA-256 values.
- Trusted owner approval and installation for the final, regenerated exact scope.
- Actual published `metadata/admissions/N750_v1` and `metadata/freezes/C1500_v1` with independent readback.
- Databricks LIVE source/checksum evidence cannot be accessed through the available GitHub connector.

The previously proposed owner-record SHA-256 was `217124dc2d0947f813892dd7f5d19dc257386b0bc18b23b9e37d4bcd92bede6a`. Do not use it if the final review packet or output bytes have changed.

**Step 1 exit remains NOT ACHIEVED.** Next action: put the exact proposal/qualification files onto this branch (without RAW files), regenerate the owner-approved scope against the generic publisher, obtain trusted installation, execute admission and freeze, verify exact published bytes, and only then declare `C1500_COHORT_PASS`.

Do not start Step 2. Do not merge Day 4 into main before the final Day 4 Step 14 exit.
