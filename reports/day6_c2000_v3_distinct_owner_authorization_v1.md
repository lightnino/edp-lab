# Day 6 distinct V3 one-shot: Owner authorization packet

**Decision requested:** After the original Job `1067818802179598` / run `665044227934897` has a protected signed PARTIAL/failure receipt, authorize adding `WORKSPACE_ACCESS` only to existing service principal `72304318628585` (`87df13c2-1bb7-4a0b-b84a-84e01bdc1764`) and authorize one **distinct** bounded V3 Job/grant/submission. This is an authority change for a new operation, not a replay or extension of the consumed grant. No new warehouse, cluster, broker, service principal, source, model or business semantic is requested.

## Fixed scope and reuse

- Original [bounded request](../metadata/operating/day6_c2000_vault_v3_bounded_request_v1.json), approved semantic contract pins, 10 selected sources, 2,047 DATA occurrences, 24 in-memory negatives, 23 `v3_` targets and eight read-only historical prototype tables remain unchanged.
- Reuse the deployed wheel SHA `eada999db14a7db4b5590ab34b4296127e4231fe5289a04180bcf410238cafc9` and the existing deployed selection/oracle artifacts. The new derived request changes only `protected_grant_id` to `day6-c2000-v3-distinct-20261025-v1` and is stored separately; the original request, Job, grant, reservation, submission and signed PARTIAL remain intact.
- The distinct saved Job uses the same serverless wheel and run-as, one task, one concurrent run, 3,600-second timeout, zero task retries, disabled auto-optimization retries and queue disabled. Its only new workspace artifact is its derived request. One new protected ledger reservation precedes at most one `jobs run-now` call. Uncertain or partial effects stop for independent reconciliation; there is no replay.

## Owner execution boundary

From a clean, reviewed PR #75 worktree, with the final reviewed commit SHA substituted below, the Owner executes these protected steps in order:

```sh
sudo .venv/bin/python scripts/owner_reconcile_day6_v3_partial.py <reviewed-commit-SHA>
sudo .venv/bin/python scripts/owner_day6_v3_successor.py entitle <reviewed-commit-SHA>
sudo .venv/bin/python scripts/owner_day6_v3_successor.py authorize <reviewed-commit-SHA>
sudo .venv/bin/python scripts/owner_day6_v3_successor.py execute <reviewed-commit-SHA>
```

The first command signs only the original failed run's PARTIAL disposition after independently reconciling the protected ledger, Job, all 23 absent targets and eight historical table identities/metadata. `entitle` adds only `WORKSPACE_ACCESS` to the existing direct `DATABRICKS_SQL_ACCESS` assignment, then verifies effective access; any other entitlement state fails closed. This entitlement is a genuine Owner authority gate. `authorize` checks the signed PARTIAL, installed original artifacts/Job, effective Workspace access, UC privileges and empty V3 target set before creating a separate saved Job and signing a separate one-hour grant. `execute` repeats those checks, reserves a new root-only ledger, and submits that distinct Job once. The original one-shot path remains exhausted and cannot be invoked again.

The Owner should approve or decline the exact entitlement and distinct one-shot operation before running these commands. A failure after any protected mutation stops at its observed checkpoint for read-only reconciliation; do not rerun `authorize` or `execute` blindly. The Owner should return only sanitized status, new Job/run IDs and signed-envelope references/hashes, keeping private ledger, grant and key bytes outside Git.

## Downstream acceptance

A successful Job result is not V3 PASS. An independent protected verifier must compare the distinct ledger/grant and terminal run to all 23 Delta IDs, versions/history, exact row digests and per-source counts, the 24 negatives, and the unchanged eight-table historical baseline, then sign a V3 successor receipt. Only then may scoped V4 adopt the persisted result without another load, followed by applicable V5/V6/V8 and prototype-only V9 live freeze. V7 is conditional on failure. Final PR merge remains a separate explicit Owner approval, followed by remote `main` SHA verification.
