# Guarded Databricks Adapter Integration V1 (project Step 2)

**Status:** Implementation PR for the existing signed Runner (#51) and Cohort DAG (#55). This is real executable **Jobs submission and pinned SQL DDL** code, but **not** yet a complete Day 5 autonomous N500→C2000 deployment or acceptance.

## 1. Historical execution patterns reused — without reusing historical authority

| Existing engineering evidence | Generalized capability | Critical unchanged boundary |
| --- | --- | --- |
| Day 3 `scripts/run_n450_m1.py` and `src/edp_lab/materialization/n450_runtime.py` | Fixed Jobs submission with exact notebook, immutable runtime artifacts, idempotency token and bounded timeout; live remote export/cat hash preflight | Historical C750-approved payloads, owner pins and remote destinations cannot authorize a new N500 cohort |
| Day 4 `scripts/publish_n750_step8.py` | Exact pinned `CREATE TABLE ... [USING DELTA] AS SELECT` statement submission | DDL submission is not a validated output; existing remote-readback gate still applies |
| Day 4 `scripts/c1500_m2_freeze_sql.py` / `sql/freezes/o_c1500_m2_v1/result_view.sql` | Exact pinned `CREATE VIEW <catalog>.<schema>.<name> AS SELECT/WITH` for a zero-copy, version-pinned candidate result | No `CREATE OR REPLACE`, `IF NOT EXISTS`, arbitrary target or general-purpose SQL |
| Day 4 `scripts/verify_c1500_m2_databricks_freeze.py` | Live readback requirements remain in the distinct result `freeze_verify` gate | This PR does **not** provide a complete independent SQL/Delta/UC result-freeze verifier |

All new live activity requires an **external owner-signed grant** and a protected Databricks credential holder/broker with an append-only protected operation ledger. No source, model, universe or cohort admission can be inferred merely from the adapter's ability to submit.

## 2. Exact Jobs and remote deployment interface

The DAG plan may provide `guarded_jobs` entries (P7 smoke or P8 processing). Each has:

```json
{
  "stage": "P8",
  "operation_id": "n500-fixed-full-v1",
  "submission_path": "metadata/operating/reviewed/n500-full-job.json",
  "deployment_path": "metadata/operating/reviewed/n500-deployment.json",
  "submission_contract": "job_submission_full",
  "deployment_contract": "deployment_full",
  "databricks_path": "/Shared/edp-lab/approved/n500-runtime",
  "external_receipt": "/protected/verifier/n500-full-terminal.signed.json"
}
```

The exact submission/deployment files must exist in the repository and be byte-pinned by the **queue contracts AND signed owner's grant**. A concrete real N500 payload is **not** provided by this documentation or authorized by the earlier C750 owner record.

An exact Jobs payload supports the Day 3 safe pattern:

```json
{
  "run_name": "n500-approved-v1",
  "timeout_seconds": 3600,
  "idempotency_token": "n500-approved-v1-full",
  "tasks": [{
    "task_key": "full",
    "timeout_seconds": 3600,
    "max_retries": 0,
    "notebook_task": {
      "notebook_path": "/Shared/edp-lab/approved/n500-runtime",
      "source": "WORKSPACE",
      "base_parameters": {"phase": "full"}
    }
  }]
}
```

The second reviewed file is a deployment manifest:

```json
{
  "schema": "EDP_DATABRICKS_DEPLOYMENT_V1",
  "notebook_path": "/Shared/edp-lab/approved/n500-runtime",
  "notebook_sha256": "<64-byte hex SHA-256>",
  "submission_sha256": "<64-byte hex SHA-256>",
  "files": [{"uri": "dbfs:/Volumes/workspace/edp_lab/raw/n500-reviewed-v1/runtime.zip",
             "sha256": "<64-byte hex SHA-256>"}]
}
```

Each listed Notebook and DBFS path must appear **exactly** in the signed grant's `databricks_paths`; every payload and manifest has its own `grant.contracts` version and SHA. There are **no dynamically supplied arbitrary commands, clusters, notebook parameters or retries**. Actual processing code must separately enforce frozen Universe/cohort membership, source binding checks and parser/model/rule contracts; the generic Jobs submitter is not a substitute.

## 3. Exact effect and verification boundary

`databricks_job_submit(... execute=True)`:

1. Reload current owner-signed grant from an independent trust directory (expiry + revocation); verify queue, source/contract pins and exact destination.
2. Read back actual remote Notebook export bytes and **each** pinned DBFS runtime object using Databricks CLI in the **protected** executor profile; compare SHA-256 to the reviewed manifest.
3. Recheck the grant and manifest/payload hashes before writing.
4. Reserve `operation_id` exclusively in the outside-worktree ledger **before** submitting `databricks jobs submit --json @EXACT_PINNED_FILE --no-wait`. Jobs submit is a side effect and cannot be blindly repeated after uncertain return.
5. Record `run_id` if returned; return `SUBMITTED_REQUIRES_READBACK`. No automatic PASS, no processing freeze.

The separate, read-only `inspect_submitted_job(...)` checks the submitted run ID against the protected ledger and re-reads `databricks jobs get-run`. A terminal SUCCESS with the matching Notebook path and task key yields an **UNSIGNED candidate evidence document**; a protected verifier must review and sign it externally to emit `EDP_EXTERNAL_OPERATION_RECEIPT_V1`. The runner's original `VALIDATING` task advances only after validating that signed receipt, including the **same** submitted run ID. A different run, a failed run, a forged signature or an absent receipt cannot progress P8.

This Jobs terminal verification proves **execution termination only**. P8's own trusted processing evidence and downstream P9/P10 Lossless/Stability, P12 C3.4, and P13 LIVE Databricks Result Freeze remain separate mandatory gates.

For SQL, the reviewed JSON statement is SHA-pinned. The preexisting `databricks_write` guarded boundary reserves an operation ID before submitting, and also awaits a separately signed exact request/readback receipt; added `CREATE VIEW` support does **not** write a frozen result by itself.

## 4. Local and real-environment verification

```sh
uv run pytest -q tests/operating/
uv run ruff check src/edp_lab/operating tests/operating/
```

Local CI mocks Databricks CLI: it can establish exact submit argv, hash mismatch rejection, replay denial and signed receipt acceptance rules, **not** Databricks service connectivity. Only an owner-controlled broker can access the actual Databricks CLI credentials and sign reviewed receipts. The adapter honors the optional `EDP_DATABRICKS_PROFILE` set by the protected runtime; it must never be sourced from agent-authored JSON as authority.

Before **real Day 5**: (1) create authorized N500 roster/processing contracts and reviewed deployed runtime; (2) ensure P6 cohort admission and remote files are actually authorized and read back; (3) implement protected, signed full processing and SQL/result verification, including independent Delta IDs/history/row counts/source lineage; (4) establish genuine budget measurement, CI/merge and freeze-readback tests; (5) run a bounded integration pilot under new signed authority. No real N500 operation or new frozen C2000 result occurs in this PR.
