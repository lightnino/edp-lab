# Vault 0A V2 partial-install recovery

## Current checkpoint: after secret, before shared-compute permission

The owner completed the single OAuth secret request. Secret metadata count is
one; the root-owned `private/databrickscfg`, matching identity file, refreshed
runtime and original runtime backup exist. The earlier recovery stopped at
`_warehouse_v2()` without retaining CLI stderr. Do not run the original
installer or the earlier `owner_recover_vault_0a_v2.py` command again.

The owner selected the existing `Serverless Starter Warehouse`, ID
`589e80595c7c8cb8`, for this one Vault installation. No second Warehouse is
authorized. The post-secret resume verifies the exact ID and name, reads the
current ACL, adds only `CAN_USE` for application ID
`87df13c2-1bb7-4a0b-b84a-84e01bdc1764` if absent, and verifies all other
ACL entries remain unchanged. It does not delete, resize, stop, rename or
reconfigure the Warehouse. The protected runtime is refreshed from reviewed
HEAD while preserving the earlier runtime copies.

Read-only checks on 2026-10-24 found no `EDP Vault Dev V2` warehouse. The
installed Databricks CLI v1.21.0 accepts the warehouse creation flags used by
the installer. Workspace warehouse configuration enables serverless compute
and PRO warehouses. Those checks do not establish why the earlier create
failed; the original CLI stderr is unavailable.

`scripts/owner_resume_vault_0a_v2.py` is limited to this exact checkpoint. It
checks the reviewed commit and shared-compute policy hash; the root-owned protected
config, identity and runtime backup; one secret metadata entry; exact principal
and active workspace assignment; working credentials without printing them;
and exact shared Warehouse and target schema. CLI errors are bounded and redacted.
An error or timeout stops with no automatic retry. Successful verification uses
the existing installation functions for schema, tables, grants, signed policy,
services, negative checks and signed receipt. The signed receipt names the
shared-compute mode, Warehouse ID and name, and `CAN_USE` scope. The owner
reviews the committed code and runs the exact pinned command supplied with
that review. Protected execution has not occurred.

## Historical pre-secret checkpoint

On 2026-10-24 the owner installer stopped at its first OAuth secret request,
after creating service principal `72304318628585` and the protected Vault root.
The original installer must not be run again. The owner later supplied the
failure text `Could not parse request object: Error parsing Duration`.
Inspection of the recovery command found `--lifetime 604800`. The CLI accepts
that flag as a string, and the API rejected the bare value as a Duration.
The corrected command passes an explicit JSON body
`{"lifetime":"604800s"}`, avoiding any flag conversion ambiguity.
The [Databricks API reference](https://docs.databricks.com/api/authentication/v1/service-principal-secret-proxy)
defines `lifetime` as a string Duration and illustrates the `s` suffix.

Read-only Databricks checks found:

- Service principal `72304318628585`, application ID
  `87df13c2-1bb7-4a0b-b84a-84e01bdc1764`, display name
  `edp-lab-vault-dev-v2`, active in both workspace SCIM and account identity.
- Direct, active assignment to workspace `7474654544694838`.
- No OAuth secret metadata from `service-principal-secrets-proxy list`.
- Effective `USE_CATALOG` only for the principal on `workspace`; no Vault
  table grants yet. Owner administrator has `CREATE_SCHEMA` and `USE_CATALOG`.
- No `EDP Vault Dev V2` warehouse and no
  `workspace.edp_lab_day6_vault_proto` schema.

The protected root exists with the expected empty `private`, `trust`, `grants`,
`approvals`, `eligibility`, `receipts` and `ledger` directories, plus copied
Python and runtime trees. The empty root-owned directories could not be opened
by the unprivileged inspection user; the owner recovery rechecks their exact
contents before any remote mutation. No Day 5 path or service is touched.

`scripts/owner_recover_vault_0a_v2.py` is restricted to this checkpoint. It
requires the reviewed recovery commit and unchanged original standing-policy
SHA, confirms original installer commit `d841204782f21402d4cd8553a1a5b425cda68655`
is an ancestor, checks the owner administrator, direct workspace assignment,
all remote absences and protected directory state, then requests one secret for
the existing principal. It never creates another principal. A nonzero result
now reports bounded CLI stderr; an ambiguous result is never retried. If a
secret appears without a saved protected config, stop for owner reconciliation
because Databricks does not reveal the secret value again. Before warehouse or
schema creation, the recovery checks their absence again. The original
one-time installer functions then complete warehouse, eight-table, policy,
service and signed installation-receipt setup.

Before the corrected secret request, recovery stages the reviewed Git `HEAD`
runtime code inside the existing protected root and keeps the original code
tree as `edp_lab-original-d841204`. This ensures the eventual protected
services enforce the reviewed C2000 artifact pins without recreating the root.

The following historical command applied only before the secret was created;
it must not be run at the current checkpoint. It ran from the owner terminal
as root after reviewing the recovery commit
and confirming the Databricks profile is authenticated. Supply the commit SHA
of that reviewed recovery commit and the unchanged policy hash:

```sh
sudo /Users/lightnino/Projects/edp-lab-day6-vault-prototype/.venv/bin/python \
  /Users/lightnino/Projects/edp-lab-day6-vault-prototype/scripts/owner_recover_vault_0a_v2.py \
  RECOVERY_COMMIT_SHA \
  0deae5164d9276987d5beabad25afc86082a0ea72983588135a870440e53edc0
```

The command is one-shot. If it fails, preserve the stderr and read-only remote
metadata; do not issue another OAuth create request or run the original
installer. The signed install receipt is still an installation result, not an
operational PASS. Live negative checks, eligible grant, Delta write/readback,
restart and credential rotation remain separate verification steps. The C1500
exception was withdrawn unexercised. C2000 Step 2 requires its own owner
scope approval and protected eligibility receipt after operational readiness.
