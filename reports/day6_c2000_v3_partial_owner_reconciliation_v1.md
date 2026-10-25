# Day 6 V3 failure: protected Owner reconciliation packet

**Scope:** Original one-shot Job `1067818802179598`, run `665044227934897`, task run `844558996680731`, and existing grant `day6-c2000-v3-one-shot-20261025-v1`. The grant and submission allowance remain consumed. This packet creates no recovery authority and does not change the approved Vault workflow or semantics.

## Observed failure and preflight gap

Jobs readback reported `TERMINATED` / `FAILED` / `UNAUTHORIZED_ERROR`, task attempt `0`, and zero execution duration: the run-as service principal lacked Databricks Workspace access. A fresh workspace assignment readback for principal `72304318628585` returned only `DATABRICKS_SQL_ACCESS` in `effective_entitlements`; the service principal is active and directly assigned, and the basic access detail reports `ACTIVE`. The service principal's SCIM entitlements likewise list only `databricks-sql-access`. [Databricks' entitlement documentation](https://docs.databricks.com/aws/en/security/auth/entitlements) states that Workspace access covers Jobs, while Databricks SQL access covers SQL features. The [workspace assignment API](https://docs.databricks.com/api/iam/v2/account-workspace-assignment) exposes the effective entitlement union.

At the 2026-10-25 08:40 UTC read-only recheck, individual Unity Catalog GET calls again found all 23 V3 targets absent and all eight historical Delta tables present. Their IDs, version property `0`, and metadata counts matched the prior [PARTIAL per-table record](../metadata/evaluations/day6_c2000_vault_v3_one_shot_partial_20261025.json). The original Job remained terminal `FAILED`. These remote checks do not read the protected ledger or substitute for the Owner-signed receipt.

The V2 V0A recovery preflight verified active/direct assignment but did not inspect `effective_entitlements`. The V3 installer verified service principal existence, UC privileges and the saved Job's run-as setting, but also omitted that effective entitlement. Those checks allowed a saved Job and one-shot grant that could not start its wheel. This is an implementation preflight gap under the existing workflow's effective-authority requirement; no specification change or new business decision is needed.

The V3 Owner entry point now requires `WORKSPACE_ACCESS` in the effective assignment and an active matching principal before install/resume-install, grant issuance and submission. It fails closed on an absent/malformed entitlement list. This guard changes only future protected checks; it cannot restore the consumed one-shot grant.

## Exact Owner disposition action

After reviewing the final PR commit, the Owner runs **only**:

```sh
sudo /Users/lightnino/Projects/edp-lab-day6-vault-prototype/.venv/bin/python scripts/owner_reconcile_day6_v3_partial.py <reviewed-commit-SHA>
```

The script requires root and the reviewed clean commit, verifies the installed trust, existing signed install receipt and grant, immutable reservation and submission ledgers, original saved Job/run/task output, individual absence of all 23 V3 targets, and the eight historical Delta table IDs/version properties/metadata counts. It then writes one signed `PARTIAL_RECONCILE_AND_STOP` verifier receipt under protected `receipts/`. It never edits the original grant or ledger, changes a Databricks object, or submits a Job. If any check disagrees or the receipt already exists, it stops without signing. The Owner should retain the root-only receipt and provide a sanitized signed-envelope path/hash or independent verification result; private ledger bytes and keys stay outside Git.

The signed disposition records that fresh SQL row digests and Delta histories for the eight historical tables remain **not freshly verified**. Their prior accepted 127-row result is preserved. The terminal run and 23 absent targets support no accepted V3 load. V4–V9 stay stopped until a distinct operation succeeds and receives independent signed readback. The separate [Owner authorization packet](day6_c2000_v3_distinct_owner_authorization_v1.md) describes that later operation; this PARTIAL receipt itself grants no write authority.
