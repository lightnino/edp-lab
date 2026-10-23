# Operating guide for a future signed queue

The [contract](agent_operating_contract.md) is binding. This guide describes the implemented local path. Do not use historical N750 SHA-pin modules as a grant issuer.

## Owner setup

On an owner-controlled host outside the agent's writable worktree, create an Ed25519 private key with `openssl genpkey -algorithm Ed25519 -out owner-private.pem` and export `owner_ed25519_public.pem` with `openssl pkey -in owner-private.pem -pubout -out owner_ed25519_public.pem`. Keep the private key inaccessible to the agent. Put the public key and `revoked_grants.json` (initially `[]`) in a separately protected trust directory. Set `EDP_OWNER_TRUST_DIR` to that absolute directory only in the trusted runner environment. The agent must not be able to change that directory or obtain the private key.

Review the proposed queue, exact RAW identities and hashes, parser/model/rule and registry hashes, allowed Databricks paths/tables, output versions, Git operations, budgets and expiry. Sign the canonical `grant` JSON bytes defined in `authority.canonical` using `openssl pkeyutl -sign -inkey owner-private.pem -rawin -in grant-canonical.json -out grant.sig`. The envelope has exactly `{"grant": ..., "signature_base64": ...}`. The private key never enters the repo. A separately signed live receipt has `document` and `signature_base64`. The external-write adapter reloads the grant and revocation list just before execution and keeps its replay ledger outside the worktree.

## Run and resume

Use Python 3.12, OpenSSL 3 and the locked dependencies. From a feature worktree:

```sh
EDP_OWNER_TRUST_DIR=/owner/protected/trust uv run python -m edp_lab.operating.runner metadata/operating/queue.json /owner/approved/grant.json runs/operating/day5 --dry-run
```

Remove `--dry-run` only for a separately signed, authorized real queue and after checking the previous result's live Databricks freeze. Day 4 now has an executed [Databricks freeze V2](../metadata/freezes/O_C1500_M2_v1/databricks_result_freeze_v2.json) merged in PR #50; verify its live availability before relying on it for a new run. Repeat the same command after interruption; `checkpoint.json` and `events.jsonl` preserve status, and completed steps are skipped. A lock prevents concurrent runs for the same output. A failed or uncertain external write is **not** retried: inspect live state and obtain a human disposition. `codex exec` is used for declared local code tasks and independent read-only economic research; its JSONL and session ID are retained for bounded resume. The installed CLI supports `codex exec -s ... --json` and `codex exec resume SESSION_ID --json`; the old `--ask-for-approval` flag is not used.

The signed queue uses `schema: EDP_QUEUE_V1`, `cohort`, `output`, `tags`, `contracts`, and `tasks`. Each task has `id`, `kind` and `depends_on`. The final `freeze_verify` task depends on every prior task. A `PRESERVED_NOT_MODELED` tag requires `economic_research`; applicable registry controls require `validate_controls`. Codex tasks supply a pinned `prompt_path`, `prompt_sha256` and `runtime_seconds`. A dry-run task may contain `simulated_success`, `simulated_packet` or `simulated_receipt`; these never produce an accepted result. Real SQL controls require signed live PASS receipts. A real final freeze requires a signed `EDP_LIVE_FREEZE_RECEIPT_V1` with verified Delta IDs, history, properties, row counts, lineage, version-pinned QUERYABLE definitions, live readback and retained remote receipt hash.

Local proof: `uv run pytest -q tests/operating/test_operating_system.py` exercises signed authority denial, exact scope, changed RAW, expiry/revocation, budgets, unauthorized output, replay prevention, changed-source control selection, simulated retry/resume and forged freeze evidence. The tests create a throwaway key under pytest's temporary directory; they do not create a production grant or make a Databricks call.

## Git and limits

Before a write, inspect main and the worktree, create a feature branch, run tests and Ruff, review the diff, push and open a PR. Merge only after required CI and approvals; verify the merge commit on main. The Git boundary refuses force push and protected branches and requires a signed merge-gate receipt for automated merge. The implementation does not grant production credentials, install a protected gateway, produce a Day 4 live freeze receipt, or prove a real Databricks write/readback. Those are operational deployment steps, not local dry-run outcomes.
