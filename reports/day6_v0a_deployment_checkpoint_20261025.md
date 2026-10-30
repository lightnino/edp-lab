# Day 6 V0A deployment checkpoint — 2026-10-25

**Remote technical repair completed:** The authenticated Owner admin added `WORKSPACE_ACCESS` to the existing run-as service principal `72304318628585` / `87df13c2-1bb7-4a0b-b84a-84e01bdc1764`. Independent Databricks readback shows both `WORKSPACE_ACCESS` and `DATABRICKS_SQL_ACCESS`. Effective UC readback confirms catalog `USE_CATALOG`, target schema `USE_SCHEMA` and `CREATE_TABLE`, and source schema `USE_SCHEMA`. The original Job `1067818802179598` / run `665044227934897` remains terminal `FAILED`, with no retry. The eight historical Delta tables are present; no V3 target was observed in the latest named inventory.

**Executable staged:** The new fixed V0A smoke and scoped V3/V9 service are in PR #75. The wheel is deployed at `/Workspace/Shared/edp-lab/day6-c2000-v3-e2e-v3/edp_lab-0.1.0-py3-none-any.whl`; a separate workspace export and local file both hash to `7812da896eec9a3152bc4a213113d0152930c3724ff6e52ff292b504301f025e`. The canonical V3 request retains `job_submissions_max=10000000` and pins that wheel and the V2 deployment manifest. The original failed request and old wheel path remain unchanged.

**One unavoidable OS step:** The installed signer, ledger and service directory are root owned. This API session cannot use `sudo -n` (`sudo: a password is required`); no agent write to that protected store has occurred. From the Owner terminal, run this **once** after PR #75's current commit is reviewed and the worktree is clean:

```sh
sudo /usr/bin/env PYTHONPATH=/Users/lightnino/Projects/edp-lab-day6-vault-prototype/src /private/var/db/edp-lab-day6-vault/python/bin/python3.12 /Users/lightnino/Projects/edp-lab-day6-vault-prototype/scripts/owner_install_day6_v0a.py "$(git -C /Users/lightnino/Projects/edp-lab-day6-vault-prototype rev-parse HEAD)"
```

That fixed entry point checks the reviewed commit and installed trust, independently reconciles and signs the original failed PARTIAL if still pending, signs the exact standing scope, uses the existing run-as and deployed wheel for an isolated Spark/Delta smoke, independently reads back its persisted row, signs `VAULT_E2E_READY`, and installs a root-owned socket service. Each mutation has a distinct durable checkpoint. An uncertain Job or write stops for readback; rerunning the command never blindly resubmits it. The service provides agent-facing `status`, `run`, `reconcile` and `freeze` actions and preserves the root-only keys and ledger.

**Current gate:** V0A is not PASS until the Owner command returns `VAULT_INFRA_E2E_READY` and the Agent independently reaches the protected service through its socket. After that, the Agent will run V3, adopt the persisted result at scoped V4, complete V5/V6/V8, request the service's live V9 freeze, audit, closeout, CI and merge. No full C2000 integration is claimed from the four-family bounded prototype.
