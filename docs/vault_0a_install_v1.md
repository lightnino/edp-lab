# Day 6 Vault Dev 0A installation packet

**Historical C1500-specific proposal, paused by the owner priority revision.** The old installer and agent client entry points now deny execution. Use the [reusable Vault 0A V2 packet](vault_0a_reusable_v2.md) for new infrastructure work. This file retains the original Step 2 preparation evidence and command for audit only; do not execute its command.

This packet preserves historical [Day 6 read-only evidence](../reports/day6_vault_prototype_evidence.md). It does not revise the approved Vault Contract V1. The C1500 exception was `WITHDRAWN_UNEXERCISED`; its file and the obsolete unsigned C1500 policy proposal were removed from the current branch. This historical command is not eligible for execution.

## Protected boundary

The owner-terminal installer creates `/private/var/db/edp-lab-day6-vault`, its own Ed25519 owner, broker and verifier keys, trust store, durable ledger and two root launchd services. It installs a dedicated Databricks OAuth service principal and 2X-Small, one-cluster warehouse. The eight Delta tables live only in `workspace.edp_lab_day6_vault_proto`. The service principal receives `USE CATALOG`, `USE SCHEMA`, and `SELECT, MODIFY` on those eight tables. The owner administrator creates the schema and tables once; the execution principal receives no schema DDL permission. The active Day 5 `/private/var/db/edp-lab` tree and services are outside this installer.

The broker signs one bounded grant after rechecking the C1500 sample, regenerated SQL plan and three protected read-only RAW ZIP copies. The executor accepts only that grant and the fixed plan. It records a durable stage reservation before every write, runs an immutable-component precheck, performs an insert-only Delta MERGE and reads back the stage count. Uncertain submissions stop for disposition; there is no blind retry. A separate verifier reads all eight tables, checks exact selected rows and Delta table IDs, then signs a final receipt. This is the existing `edp_lab.operating.authority` grant and signature model with separate Vault services and trust material.

The signed policy pins the 127 selected DATA occurrences and six labelled synthetic negative controls. Its cap is 60 SQL statements, 3600 seconds, zero automatic statement retries and one 2X-Small warehouse cluster. The nine planned MERGEs write 20 Filing, 24 Concept, 76 Slot, 127 Occurrence, 127 Assertion, 127 scoped M2, 254 load-event and six quarantine records. The 254 events cover first delivery and replay. The policy expires on 2026-11-01 UTC. No USD cost cap is claimed; actual usage must be recorded from the live run.

## Current privilege boundary

On 2026-10-24, `databricks grants get-effective catalog workspace --principal chengzhu13@gmail.com -p edp-lab` returned `USE_CATALOG` only. The target schema does not exist. The installer therefore requires an independently authorized catalog owner or administrator to grant `CREATE_SCHEMA` on `workspace` to `chengzhu13@gmail.com`, or to use a different separately reviewed provisioning principal. The installer checks effective `CREATE_SCHEMA` before creating anything. It will never try to use `workspace.edp_lab` as a write target.

After that privilege is independently established, the owner runs the pinned installer from a trusted terminal as root, using the exact reviewed commit SHA and policy SHA supplied in the Step 2 closeout:

```sh
sudo /Users/lightnino/Projects/edp-lab-day6-vault-prototype/.venv/bin/python /Users/lightnino/Projects/edp-lab-day6-vault-prototype/scripts/owner_setup_day6_vault_0a.py COMMIT_SHA POLICY_SHA256
```

The installer needs the owner's existing `edp-lab` CLI profile via `sudo -u lightnino`; it does not copy or print its credentials. It creates a new protected service-principal secret and does not expose that secret to the worktree. It refuses any prior or partial installation, changed tracked files, changed policy, unexpected principal, existing Vault objects or missing privilege. A partial failure needs owner review of the newly created Vault-only resources before another install attempt; do not delete or reuse active Day 5 infrastructure.

Only a signed `VAULT_0A_INFRA_OPERATIONAL` receipt, a verified protected grant and negative authorization checks establish infrastructure readiness. After installation, continue the same Step 2 using `uv run python scripts/day6_vault_0a_client.py execute`. That call cannot supply SQL, target tables, source IDs or credentials. It must return a signed exact-row readback receipt before the prototype can be marked validated. The final verifier currently requires one inline result chunk per table; a truncated or multi-chunk response fails closed and needs a reviewed reader change.
