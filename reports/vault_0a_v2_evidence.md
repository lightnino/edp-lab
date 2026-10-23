# Reusable Vault 0A V2 preparation evidence

**State: code under local validation; protected installation not performed.** This report tracks the reusable infrastructure priority revision separately from the paused [C1500 Step 2 evidence](day6_vault_prototype_evidence.md). It does not grant authority or assert live Delta persistence.

## Baseline and integration

Worktree `/Users/lightnino/Projects/edp-lab-day6-vault-prototype`, branch `day6/vault-prototype-c1500`, PR #61. Before this V2 change, HEAD was `f5c4e4d55288c4881a95ad98f85f25939f3561b7`. Current `origin/main` was fetched through merge `90dcb10` (PR #62). That merge changes two workflow documentation files; the V2 work changes neither. The approved Vault Contract V1 SHA-256 remains `681c3f6a9a4446b5357c3ab6c6534e6fd5b8cf944f967ea9ab27dcc2c8b5aabe`. The separate C1500 owner exception, existing sample, original load plan and prior Step 2 evidence are retained.

## Prepared controls

- Cohort-neutral, unsigned [standing policy proposal](../metadata/operating/vault_standing_policy_v2_proposal.json) with exact namespace and eight-table allowlist, versioned contract/rule hashes, one-cluster 2X-Small compute, one-hour run/grant caps, 1,000 DATA and 20 synthetic row limits, 100 statements per run, 64 lifetime grants, 2,000 lifetime SQL reservations and zero write retries.
- Owner-terminal [installer](../scripts/owner_setup_vault_0a_v2.py) that checks reviewed commit/policy hashes, an empty isolated target, principal identity and effective `CREATE_SCHEMA` before creating any resource. It provisions a separate service principal, warehouse, Delta schema/tables, protected keys/services, and a signed **installed-awaiting-eligible-run** receipt. It has not run.
- Protected Broker, Executor and independent Verifier modules. The Broker requires an owner-signed cohort approval and separately signed `LIVE_VERIFIED` freeze receipt before registering cohort eligibility. It issues a short-lived exact run grant automatically. The Executor uses insert-only planned writes, a run-specific audit event, durable reservations and no uncertain replay. The Verifier compares exact keyed Delta rows and signs readback. These paths have only local test coverage.
- A fixed-action V2 client requests a grant and submits only its protected grant path. It accepts no caller SQL or credentials. It has not connected to a live Vault service.
- Owner-terminal [credential rotation](../scripts/owner_rotate_vault_credential_v2.py) stages a new service-principal secret, probes the dedicated warehouse and swaps the protected config atomically. No credential or protected store was modified in this worktree.
- The C1500-specific installer/client entry points deny execution during the owner-requested pause. The approved D1–D5 contract is unchanged. Day 5 Supervisor, broker, queue, trust, ledger, credentials and active execution were not touched.

## Observed external gate

Read-only `databricks grants get-effective catalog workspace --principal chengzhu13@gmail.com -p edp-lab -o json` returned only inherited `USE_CATALOG`. `databricks schemas get workspace.edp_lab_day6_vault_proto -p edp-lab -o json` returned “does not exist.” The owner-terminal provisioning principal therefore lacks observed `CREATE_SCHEMA`. No service principal, target schema, Vault 0A protected root, signed standing policy, cohort eligibility receipt or run grant was installed by Codex. The installer requires an independently authorized catalog owner to grant `CREATE_SCHEMA` on `workspace` to that principal, or a separately reviewed provisioning path. It does not use `workspace.edp_lab` as a fallback.

## Live evidence still required

The owner installer must produce its signed installation receipt and demonstrate effective service-principal table privileges and protected-schema/RAW write denials. An independently verified Cohort Freeze and owner-approved scope must be registered as a protected eligibility receipt. A real broker grant, forged/expired/revoked denial checks, restart and credential rotation, bounded write, uncertain-replay denial, independent exact Delta readback and signed run receipt must pass before `VAULT_0A_INFRA_OPERATIONAL`. C1500 execution remains paused until that gate; `VAULT_PROTOTYPE_VALIDATED` additionally requires the original Step 2 real-data gates. Full C2000 integration remains denied pending Step 0 and Step 2 and separate owner scope.

Local validation after the V2 changes: `uv run pytest -q tests/vault/test_standing_v2.py tests/vault/test_day6_vault_0a.py` **41 passed**; `uv run pytest -q` **603 passed, 82 skipped in 91.16 seconds**; `uv run ruff check .` **passed**. The first PR CI run exposed a macOS-only temp path and reliance on ignored local sample manifests in two tests. Both test portability issues were repaired; the V2 renderer now has a self-contained CI test, while the saved C1500 plan parity check runs only where those intentionally ignored artifacts exist. PR CI is rechecked after push. These local PASS results do not imply any live gate passed.
