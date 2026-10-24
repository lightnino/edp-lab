# Day 6 bounded Vault summary

| Milestone | Result | Evidence |
| --- | --- | --- |
| Step 0 C2000 baseline | PASS: signed, version-pinned C2000 result freeze | [Step 0 evaluation](../metadata/evaluations/day6_step0_c2000_v1.json) |
| Step 0A Vault deployment | COMPLETE: existing schema and eight Delta tables; protected read-only acceptance PASS | [0A evidence](../reports/vault_0a_v2_evidence.md) |
| Step 2 C2000 bounded prototype | **COMPLETE: `VAULT_PROTOTYPE_VALIDATED`** | [Live closeout](../reports/day6_c2000_vault_step2_closeout_v1.md), [evaluation](../metadata/evaluations/day6_c2000_vault_step2_v2.json) |
| Full C2000 Step 3 | NOT STARTED | Separate scope and policy required |

Step 2 used the Owner-authorized direct DEV profile on the existing shared Warehouse and existing Vault namespace. It loaded exactly three supported FSDS `num.txt` sources, 127 DATA occurrences and six synthetic negatives through the seven pinned business/quarantine stages, then recorded 127 load events. The persisted exact-row checks passed for all eight tables. The protected V2 Broker/Executor workflow was not exercised by this path, and no protected run receipt was asserted.

The former [Owner gate packet](day6_c2000_step2_owner_gate_v1.md) and [C2000 rebaseline](vault_c2000_rebaseline_v1.md) remain historical evidence. The bounded DEV execution model for this completed prototype was: fixed source and contract hashes, fixed seven-stage plan, existing Warehouse and eight-table allowlist, one run journal, 60-statement and 3,600-second caps, no automatic uncertain-write retry, and exact persisted readback before PASS. Its terminal failed first load-event statement was reconciled as zero persisted rows before the corrected event write; no successful stage was replayed. This authority applies only to the completed C2000 bounded Step 2 and does not extend to Step 3.
