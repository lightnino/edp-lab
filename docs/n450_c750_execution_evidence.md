# N450 CLEAN and C750 QUERYABLE execution evidence

Status: Step 3 PASS. CLEAN publication and C750 QUERYABLE validation completed.

## Scope and preservation

The approved scope is 450 N450 processing bindings, reused with frozen C300's
300 physical sources / 732 logical bindings. C750 therefore covers 750 physical
sources and 1,182 logical bindings. M1 remains `M1_LEXICAL_V1` with
`C300_LITERAL_IDENTITY_V1`. RAW and frozen C300 were not rewritten or replayed.
No output freeze or Step 4 work is authorized or claimed.

N450 processing completed in run `879442057562865` after smoke run
`181758407473778`. The publication recovery reused all 450 verified checkpoints;
neither job was rerun. The earlier CLEAN run `997643049038042` failed at the
first write because Spark Connect rejected `errorifexists`; no Delta tables
were created by either failed attempt.

The owner explicitly approved the exact two-line correction to `mode('error')`,
retaining exclusive-create semantics, followed by the required runtime pin update
and redeployment. The corrected archive changes only those two lines of runtime
code; its other changes are the failed-publication submission token and retained
prior authority evidence. The original checkpoint receipts were retained
byte-for-byte as `complete.owner-v5.json`; current receipts reference their hashes
and original owner pin. Checkpoint Parquet bytes were not rewritten. The original
full-phase marker is retained as `phases/full.owner-v5.json`. CLEAN independently
reverified every checkpoint before publication; provenance rollover was not a
processing replay.

## CLEAN validation

Run `1100860214974411` passed. Both tables are at Delta version 0:

- `workspace.edp_lab.clean_n450_m1_records_n450_step3_v1`
- `workspace.edp_lab.clean_n450_m1_bindings_n450_step3_v1`

There are 450 COMPLETE bindings and 450 Lossless PASS results, with no checkpoint
errors, zero record multiset differences and zero binding multiset differences.
Readback contains 1,902,855 total lexical occurrences, including 1,899,705 data
records and 9,498,525 fields, with 1,902,855 unique source-line locators counted
within their bindings. Lossless tests 1–5 PASS; test 6 is NOT_APPLICABLE for lexical
M1. This does not establish semantic NULL rules or economic interpretation.

Measured CLEAN publication/validation: 520.9309268589999 seconds wall time,
163.455432549 seconds driver CPU. Observed Python 3.11.10, Spark 4.2.0,
PyArrow 14.0.1. DBUs, executor CPU and executor peak RSS were unavailable.

## QUERYABLE validation

Run `368063299510003` passed. All 108 full-schema multiset validation groups
(36 per view) PASS with zero differences; each receipt's fingerprint, exact binding
population, view SQL, execution pin, contract and Delta versions were independently
checked against the saved plan. A local DNS interruption affected monitoring only;
the same remote run was reattached without resubmission.

Observed native view counts match the frozen-input expectations:

| View | Count |
| --- | ---: |
| `workspace.edp_lab.q_c750_m1_records_c750_step3_v1` | 316,063,821 data records |
| `workspace.edp_lab.q_c750_m1_fields_c750_step3_v1` | 3,586,787,936 fields |
| `workspace.edp_lab.q_c750_m1_coverage_c750_step3_v1` | 1,182 bindings |

The coverage view contains 750 distinct source instances. All 450 N450 bindings
passed applicable Lossless gates; frozen C300 contributes its 732 historical PASS
bindings. Original run IDs, RAW references, hashes, record locators and field
provenance are preserved by the version-pinned UNION ALL definitions and full-schema
multiset comparisons. No semantic integration, broader FIN result or new model is
claimed. QUERYABLE validation measured 8,875.573632139 seconds wall time and
51.902764899 seconds driver CPU; DBU/executor telemetry remains unavailable.

All consumer reads explicitly pin the six Delta data snapshots to version 0.
Final metadata inspection separately confirms both N450 tables' latest version is
0, and all four C300 tables' latest version is 1 from the documented pre-existing
retention/append-only property changes. Those C300 operations predate this execution
and match `metadata/freezes/O_C300_M1_v1/references.json`; their original Delta/UC
identities and frozen version-0 inputs are unchanged. No C300 write or replay was
performed.

## Reproducible references

Operational evidence is intentionally excluded from Git under `runs/`:

- `runs/n450/step3-exact-path-v1/`: original processing results and failed CLEAN evidence.
- `runs/n450/step3-clean-write-fix-v1/`: corrected archive/contract, approval and pin update,
  checkpoint provenance rollover, CLEAN evidence and QUERYABLE run evidence.
- Remote derived evidence: `/Volumes/workspace/edp_lab/raw/n450-m1/n450_step3_v1/`.
- Frozen C300: `metadata/freezes/O_C300_M1_v1/`; its original version-0 references
  and gate remain the source of C300 reuse, without a replay.

| Fingerprint | SHA-256 |
| --- | --- |
| Publication owner pin | `de242d3754688288cb174fbfde2f8cbc6594fc80b36a8d6281726ca9479322e7` |
| Processing owner pin | `3fd9c5a6ccb62ffd79610a84dc8ac8cb78f674581a2edcfbd23d18da50e91654` |
| Contract | `962bdc573320dfd88d05481f871e4a23c463859873c8dd3f86a288d1645aaf0e` |
| Runtime archive | `49034e47e11104517da632fda0b48a3f4eb3802374b07ac66ec897b9114ebb47` |
| CLEAN Lossless gate | `ae89f2cb59912862691ce5bfd3e0d0c0624725b15c5363b9f5e829b5a1a1d332` |
| M1 verifier | `bf49c22204f67a2c2de7f9f5fefce7924145becb01a6232cf53f13191354afe2` |
| CLEAN runtime | `af903fb7d959c8985d0d8473c8a7d98360ed2a8b2d0ad5c33501264146c1d518` |

Local verification: 424 tests passed, 29 skipped; Ruff passed. The publication
submission-token check was also rerun after aligning the offline packet builder
with the approved recovery token (1 passed). GitHub CI and merge are recorded in
the associated pull request. Operational results/Parquet/RAW are excluded from Git;
only code, governance authorization records and this evidence index are committed.

Final evidence manifest: `runs/n450/step3-clean-write-fix-v1/step3-final-evidence.json`,
SHA-256 `5612387ed5632b52d18b9914eb7bf8a39980218056c01ecf88f93a308ece1e82`.
The manifest indexes all 108 receipts, final table metadata and the lineage/plan
checks. Step 4 was not started and no output freeze was issued.
