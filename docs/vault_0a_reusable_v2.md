# Reusable Vault Dev 0A V2 — installation and authority packet

**Status: partial installation at OAuth secret creation; live verification pending.** The existing service principal and protected root are handled by the [bounded owner recovery](vault_0a_v2_partial_install_recovery.md). The C1500 exception is `WITHDRAWN_UNEXERCISED`; its prior read-only [evidence](../reports/day6_vault_prototype_evidence.md) remains historical. The C2000 Step 2 preparation is in [the rebaseline packet](vault_c2000_rebaseline_v1.md). The approved [Vault Contract V1](vault_load_contract_v1.md) and all Day 5 services remain unchanged.

## Separation of concerns

| Layer | Boundary |
| --- | --- |
| Installation | Owner terminal creates one protected Vault root, dedicated OAuth service principal, 2X-Small one-cluster warehouse and eight tables in `workspace.edp_lab_day6_vault_proto`. It has no cohort/sample input. |
| Standing policy | Owner signs [V2 policy proposal](../metadata/operating/vault_standing_policy_v2_proposal.json) into protected trust. It pins approved contract and serializer hashes, table allowlist and per-run ceilings; it names no cohort. This proposal cannot self-authorize. |
| Cohort eligibility | A separate protected verifier must sign a `VERIFIED_FROZEN` receipt with approved freeze, source roster, owner approval, exact source hashes, input/plan hashes and versioned contract/rule pins. The reusable `render_v2` function builds a cohort plan from an approved source projection and independently measured table counts; audit events stay outside that plan. This is per independently approved cohort, not per routine write. No receipt is installed yet. |
| Run grant | The protected Broker checks the receipt and pinned run request/plan, then signs a one-hour exact grant automatically. Different eligible cohorts can run successively without reinstalling 0A or asking the owner to sign each statement or run. |
| Execution | The Executor accepts only a broker-signed, current, nonrevoked grant and fixed insert-only business plan. It generates a separate insert-only `R_LOAD_EVENT` stage from the pinned occurrences and run ID, reserves each operation before submission, never blindly retries an uncertain write, and checks persisted stage counts. This lets a replay use a new run ID without a new owner signature. |
| Verification | A separate verifier process reads keyed Delta rows, compares exact lexical values and multiplicity, checks Delta table IDs and signs a run receipt. Credential rotation stages and probes a new service-principal secret before an atomic swap; installation stays in place. |

The default per-run ceiling is 1,000 DATA occurrences, 20 synthetic rows, 100 SQL statements, one 2X-Small cluster, one hour and zero automatic write retries. The protected policy also has durable lifetime caps of 64 issued grants and 2,000 reserved SQL statements; a failed or uncertain reservation consumes capacity. These are hard bounds, not a claim that every future source/rule is approved. New contracts, mapping rules, production namespaces, C2000 integration or larger limits require an owner-signed policy change. RAW writes, Day 5 resources and destructive SQL are denied. A one-year policy expiration requires renewal; it is independent of the November 1 C1500 proposal expiration.

The cohort eligibility registration requires a protected, signed owner scope approval **and** a separate protected `LIVE_VERIFIED` freeze receipt that pins the same Cohort Freeze SHA. The approval identifies the already approved source hashes, input and load plan; it is not signed for each retry. This preserves the owner-controlled material cohort boundary. The installer and broker never stage or mutate RAW; the acquisition-owned verified handoff in merged PR #62 remains the source route. Full C2000 integration is currently denied by the policy and needs its separate Step 0/Step 2 gates and an owner-controlled policy amendment. The services do not need reinstallation for that amendment.

## Provisioning prerequisite and one-time installation

The read-only effective-grant check for `chengzhu13@gmail.com` shows `USE_CATALOG` only, and the isolated schema does not exist. An independently authorized `workspace` catalog owner must grant `CREATE_SCHEMA` to the owner-terminal provisioning principal, or provide an equivalently authorized administrator. The narrowly scoped SQL is:

```sql
GRANT CREATE SCHEMA ON CATALOG workspace TO `chengzhu13@gmail.com`;
```

Codex does not run this grant or the privileged installer. Once the privilege is effective, the owner runs `scripts/owner_setup_vault_0a_v2.py` as root from a trusted terminal with the reviewed Git commit SHA and policy-proposal SHA. The installer checks both pins, a clean tracked tree, principal identity, effective UC privilege, absent target schema and absent Vault root before creating anything. It uses the owner's existing `edp-lab` profile without printing it, creates a separate root-owned OAuth profile, then gives the service principal only `USE CATALOG`, `USE SCHEMA` and `SELECT, MODIFY` on the eight tables. It checks effective table grants and denial of write privilege on `workspace.edp_lab`.

The installer prints `VAULT_0A_INSTALLED_AWAITING_ELIGIBLE_RUN`, **not** `VAULT_0A_INFRA_OPERATIONAL`. An independently signed eligibility receipt, real protected grant, service-principal read/write checks, live negative authorization checks, restart/rotation and readback must still pass. The installer refuses partial reinstallation; owner review is required if its provisioning sequence fails after creating Vault-only resources.

Once an eligible cohort receipt exists, `scripts/vault_0a_v2_client.py grant RUN_REQUEST.json` requests a short-lived grant and `scripts/vault_0a_v2_client.py execute RUN_REQUEST.json` submits it to the protected Executor. The run request path is repository-relative; the client accepts no SQL, table name, warehouse ID or credential. The Executor independently verifies the broker signature and all pins before any write.

The credential rotation helper is `scripts/owner_rotate_vault_credential_v2.py`. It creates a new seven-day service-principal secret through owner-controlled Databricks access, probes the dedicated warehouse with the staged secret and swaps the protected config only on success. The old secret is not printed or reused by the helper and expires by its Databricks lifetime. Rotation must be exercised in the protected installation before an operational claim.

## Current verification coverage and limits

Local tests cover cohort-neutral policy, two independently eligible cohort receipts, grant windows, modified freeze/contract/rule pins, out-of-scope namespace/tables, RAW and Day 5 flags, destructive SQL, forged/expired/revoked grants, budget limits, uncertain replay, stale socket restart and atomic credential replacement after a successful probe. These tests simulate signed-receipt inputs and do not substitute for protected installation. No live signed cohort receipt, real grant, Delta write or independent readback has run.

The C1500-specific installer and client remain disabled. The old unsigned C1500 policy proposal and active exception file were removed from this branch. Step 0 can now use the accepted C2000 freeze; Step 2 still needs installation, operational tests and a separate C2000 scope approval. Full Step 3 integration needs an owner-approved standing-policy, capacity and write-scope change.
