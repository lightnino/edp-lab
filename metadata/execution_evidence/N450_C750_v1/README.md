# N450 Admission and C750 Cohort Freeze — executed

Authorized code revision: `326ec18b164d85a8b24068ff387308af7c3d868d`.
Approved record/runtime pin:
`50507c7fcde3d5d7295bfa396cd216587402c6852eb5e6d827ee3ad53beb3a48`.
The owner issued the record and installed the pin from the trusted local terminal.
The execution agent observed both installed before the approved effective time,
`2026-10-21T18:00:00Z`; that observation is preserved inside `execution.json`.
No installation timestamp was inferred from a proposal timestamp.

## Verification recovery

The first verifier completed at `2026-10-21T18:17:50.600900+00:00` and durably saved
all 450 results in `remote_verification.json`: 433 PASS, 17 READ_FAILED. Failures
were TLS handshake timeouts, connection resets and 180-second read timeouts;
no hash mismatch was reported. The process exited without Admission or Freeze.

On resumption, all saved per-object identity/path/size/hash bindings were checked
against the pinned roster and historical remote ledger. The 433 valid results
were reused; only the 17 failed reads were repeated. Every retry returned PASS.
`remote_retry_attempt_1.jsonl` durably records each retry, and
`remote_verification_complete.json` contains the complete ordered 450/450 PASS
result set plus SHA references to the original failures and retry checkpoint.
Remote verification used `databricks fs cat <exact pinned path> -p edp-lab`, hashing
stdout bytes in memory. No RAW was uploaded, copied into persistent local storage
or changed. Databricks jobs and SQL processing were not executed.

## Publication and readback

The unchanged guarded entrypoints `n450_admission.admit` and
`n450_admission.freeze` revalidated authority and current local source hashes
before publishing only to the approved versioned destinations:

- `metadata/admissions/N450_v1/`
- `metadata/freezes/C750_v1/`

Actual Admission completed: `2026-10-21T18:28:17.544021+00:00`.
Actual Cohort Freeze completed: `2026-10-21T18:28:26.312596+00:00`.
These actual event timestamps are separate from the approved 18:00 effective
registration timestamp recorded in the committed manifest.

All published files were read back and matched every approved output commitment.
Counts: unchanged C300 300; N450 450; intersection 0; C750 750 unique registered
and physical source identities. The additive manifest has 754 rows: the original
304 GOLD/C300 rows, preserved exactly as rows and in the original-byte snapshot,
plus 450 N450 rows. The C750 roster excludes the four original GOLD instances.
All 450 new registration mappings match the complete ordered owner grant.

The existing freeze guard verified all 300 C300 physical source identities,
registry aliases, pinned physical paths, inventory sizes and SHA-256 hashes.
All pre-existing tracked metadata hashes, including Universe v1, C300 and Day 2
frozen artifacts, were checked unchanged after publication. `execution.json`
records counts, actual event times, protected hashes and every output readback hash.
A separate readback after the workflow exited confirmed these results again
without rescanning unchanged RAW.

| Output | SHA-256 |
| --- | --- |
| `corpus_manifest_v4.csv` | `79660035d807306b111d88be0c0f899c5ee410077e2ffe5caa27d4d9af4d372a` |
| `admission.json` | `bd8cd434868515a30bcc4e0812fe392fe62b92a7f084dd39cc88bcea16ad305f` |
| `C750.csv` | `81162007d42146333e2822d8c9ed2a720ebdd36422db6649291e51bd25e0d85d` |
| `freeze.json` | `2d03baebe0627e612a5d823838e06bf9189d74ec6047ba85ba59b62ef47b4559` |

This is a physical Admission and Cohort Freeze only. Existing RAW locations remain
writable; RAW immutability is not established. No profiling, M1/CLEAN processing,
QUERYABLE outputs, Stability or O_C750_M1 output freeze was performed. The
historical Universe sidecar and active legacy metadata were not rewritten to grant
new processing scope. Original proposal documents remain historical review records;
the installed approved record and this execution evidence establish the actual
outcome.
