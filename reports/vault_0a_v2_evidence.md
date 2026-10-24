# Reusable Vault 0A V2 preparation evidence

**State at 2026-10-24 14:44 UTC: installed, awaiting protected read-only acceptance.** The owner reported `VAULT_0A_INSTALLED_AWAITING_ELIGIBLE_RUN` and receipt SHA-256 `04b555202469cd1aa9423da7d6f7639900202693c986859e1b229f3d1427c7b2`. The receipt bytes and protected trust are inaccessible to Codex, so their hash, signature and policy remain **BLOCKED** pending the Owner Terminal probe below. This report does not claim `VAULT_0A_INFRA_OPERATIONAL` or live Delta persistence.

## Read-only acceptance results

| Check | Result | Evidence and limit |
| --- | --- | --- |
| Receipt SHA, signature and installed policy | BLOCKED | Owner-reported receipt digest above; protected `receipts/install-v2.signed.json` and `trust/policy.signed.json` require Owner Terminal readback. Reviewed proposal SHA-256 is `7200b417a3321580147c8d135eef99868c5fb79dbe78ae236f54266240fa3316`. |
| Vault schema and eight Delta tables | PASS | Live `databricks schemas get workspace.edp_lab_day6_vault_proto` returned schema ID `3b1d160f-585f-4b56-8a53-4be2b5cfac80`; `databricks tables list workspace edp_lab_day6_vault_proto --omit-columns --omit-properties` returned exactly the eight managed `DELTA` tables and IDs below. Both used profile `edp-lab`, JSON output, read-only. |
| Shared Warehouse and Service Principal permissions | PASS | Live `warehouses get`, `permissions get warehouses 589e80595c7c8cb8`, `service-principals get 72304318628585`, and `grants get-effective` for catalog, Vault schema, eight Vault tables, `workspace.edp_lab` and `workspace.edp_lab.raw`; all used `-p edp-lab -o json`. Warehouse ID/name match, health `HEALTHY`, Vault application ID `87df13c2-1bb7-4a0b-b84a-84e01bdc1764` has only `CAN_USE` on this Warehouse; effective grants are `USE_CATALOG`, `USE_SCHEMA`, and `SELECT, MODIFY` on each Vault table. Day 5 schema and RAW volume effective grants returned `{}`. This is a permissions readback, not a service-principal SQL test. |
| Broker and Executor health; negative authorization | BLOCKED | Installer-reported negative checks are not independent acceptance. Owner Terminal probe contacts both sockets with requests that cannot issue a grant or execute a write, requires two `DENIED` responses, and checks grant and ledger names unchanged. |
| Protected runtime equals reviewed `4485030d23faee7a993cd07969dc1db6dfa2aea9` | BLOCKED | The repo `HEAD` is that commit, but the protected copy needs byte comparison. Owner Terminal probe compares every archived `src/edp_lab` file with the installed runtime and rejects extra source files. |

| Vault table | Unity Catalog table ID |
| --- | --- |
| `h_filing` | `544c4864-620d-4b10-a99f-7563c3dc12c5` |
| `h_concept` | `81c704a6-b172-4e2b-8fde-5ed1088d8ab2` |
| `l_fact_slot` | `306c4fb8-51f2-45fd-9191-19ac158ada32` |
| `r_source_occurrence` | `9e9e0e2c-8a20-4787-9a4d-399272149c1d` |
| `s_fact_assertion` | `ac3908c2-b079-4a16-bfb8-d5e14ac5e3dd` |
| `s_num_m2_value` | `cc9afd09-1540-4ca8-8577-91d10ce268bf` |
| `r_load_event` | `b1a54891-568f-4698-bd3c-d6342eac11e5` |
| `vault_reject_quarantine` | `8e19e22d-06b8-4266-86bd-3e278c0fc910` |

## One Owner Terminal action

After reviewing [the read-only probe](../scripts/owner_verify_vault_0a_readonly.py), run this single command in the Owner Terminal and return its one-line JSON result. It reads protected receipt, trust public keys and runtime source, then sends only an unsupported Broker action and a nonexistent Executor grant path. It does not access the protected OAuth config or private signing keys and contains no installation, rotation, grant or SQL write action.

```sh
sudo /Users/lightnino/Projects/edp-lab-day6-vault-prototype/.venv/bin/python /Users/lightnino/Projects/edp-lab-day6-vault-prototype/scripts/owner_verify_vault_0a_readonly.py
```

Even if this probe passes, eligible-run grant, Service Principal SQL write/readback, restart and rotation remain untested. They are outside this acceptance request; `VAULT_0A_INFRA_OPERATIONAL` remains unclaimed.

## Historical preparation evidence

## Baseline and integration

Worktree `/Users/lightnino/Projects/edp-lab-day6-vault-prototype`, branch `day6/vault-prototype-c1500`, PR #61. Before this V2 change, HEAD was `f5c4e4d55288c4881a95ad98f85f25939f3561b7`. Current `origin/main` was fetched through merge `90dcb10` (PR #62). That merge changes two workflow documentation files; the V2 work changes neither. The approved Vault Contract V1 SHA-256 remains `681c3f6a9a4446b5357c3ab6c6534e6fd5b8cf944f967ea9ab27dcc2c8b5aabe`. The separate C1500 owner exception, existing sample, original load plan and prior Step 2 evidence are retained.

## Prepared controls

- Cohort-neutral, unsigned [standing policy proposal](../metadata/operating/vault_standing_policy_v2_proposal.json) with exact namespace and eight-table allowlist, versioned contract/rule hashes, one-cluster 2X-Small compute, one-hour run/grant caps, 1,000 DATA and 20 synthetic row limits, 100 statements per run, 64 lifetime grants, 2,000 lifetime SQL reservations and zero write retries.
- Owner-terminal [installer](../scripts/owner_setup_vault_0a_v2.py) that checks reviewed commit/policy hashes, an empty isolated target, principal identity and effective `CREATE_SCHEMA` before creating any resource. It provisions a separate service principal, warehouse, Delta schema/tables, protected keys/services, and a signed **installed-awaiting-eligible-run** receipt. It has not run.
- Protected Broker, Executor and independent Verifier modules. The Broker requires an owner-signed cohort approval and separately signed `LIVE_VERIFIED` freeze receipt before registering cohort eligibility. It issues a short-lived exact run grant automatically. The Executor uses insert-only planned writes, a run-specific audit event, durable reservations and no uncertain replay. The Verifier compares exact keyed Delta rows and signs readback. These paths have only local test coverage.
- A fixed-action V2 client requests a grant and submits only its protected grant path. It accepts no caller SQL or credentials. It has not connected to a live Vault service.
- Owner-terminal [credential rotation](../scripts/owner_rotate_vault_credential_v2.py) stages a new service-principal secret, probes the dedicated warehouse and swaps the protected config atomically. No credential or protected store was modified in this worktree.
- The C1500-specific installer/client entry points deny execution during the owner-requested pause. The approved D1–D5 contract is unchanged. Day 5 Supervisor, broker, queue, trust, ledger, credentials and active execution were not touched.

## Historical external gate before installation

Read-only `databricks grants get-effective catalog workspace --principal chengzhu13@gmail.com -p edp-lab -o json` returned only inherited `USE_CATALOG`. `databricks schemas get workspace.edp_lab_day6_vault_proto -p edp-lab -o json` returned “does not exist.” The owner-terminal provisioning principal therefore lacks observed `CREATE_SCHEMA`. No service principal, target schema, Vault 0A protected root, signed standing policy, cohort eligibility receipt or run grant was installed by Codex. The installer requires an independently authorized catalog owner to grant `CREATE_SCHEMA` on `workspace` to that principal, or a separately reviewed provisioning path. It does not use `workspace.edp_lab` as a fallback.

## Historical list of live evidence required

The owner installer must produce its signed installation receipt and demonstrate effective service-principal table privileges and protected-schema/RAW write denials. An independently verified Cohort Freeze and owner-approved scope must be registered as a protected eligibility receipt. A real broker grant, forged/expired/revoked denial checks, restart and credential rotation, bounded write, uncertain-replay denial, independent exact Delta readback and signed run receipt must pass before `VAULT_0A_INFRA_OPERATIONAL`. C1500 execution remains paused until that gate; `VAULT_PROTOTYPE_VALIDATED` additionally requires the original Step 2 real-data gates. Full C2000 integration remains denied pending Step 0 and Step 2 and separate owner scope.

Local validation after the V2 changes: `uv run pytest -q tests/vault/test_standing_v2.py tests/vault/test_day6_vault_0a.py` **41 passed**; `uv run pytest -q` **603 passed, 82 skipped in 91.16 seconds**; `uv run ruff check .` **passed**. The first PR CI run exposed a macOS-only temp path and reliance on ignored local sample manifests in two tests. Both test portability issues were repaired; the V2 renderer now has a self-contained CI test, while the saved C1500 plan parity check runs only where those intentionally ignored artifacts exist. PR CI is rechecked after push. These local PASS results do not imply any live gate passed.
