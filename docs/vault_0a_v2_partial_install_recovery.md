# Vault 0A V2 partial-install recovery

On 2026-10-24 the owner installer stopped at its first OAuth secret request,
after creating service principal `72304318628585` and the protected Vault root.
The original installer must not be run again. Its `run()` wrapper raised on a
nonzero CLI result without including stderr, so the historical HTTP response
code and error message are not in the traceback. Do not label the failure as a
permission or propagation error without that evidence.

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

Run only from the owner terminal as root, after reviewing the recovery commit
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
restart and credential rotation remain separate verification steps. C1500 Step
2 may proceed independently of C2000 Step 0 once this Vault verification
passes.
