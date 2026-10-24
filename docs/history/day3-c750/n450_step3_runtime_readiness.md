# N450 / C750 M1 runtime readiness

Historical readiness checkpoint. Subsequent authorized execution and its evidence
are recorded in [N450 / C750 execution evidence](../../n450_c750_execution_evidence.md).

This is preparation only. No processing grant is installed, no remote deployment
or job has run, and no native production CLEAN/QUERYABLE output is claimed.
Original Step 3 scope proposal remains at `runs/n450/step3-scope-v1/`, fingerprint
`1b8d8a66b08793107899b67d7a8c9a7a9d92bdee704fc2f7c6a4786d5e7ff840`.

## Minimal integration

- Extend the existing `n450_authorization.authorize` only for host-approved
  C750 processing/remote-processing. Reuse its OWNER_GRANT_PATH / OWNER_GRANT_SHA256,
  canonical serialization and independent trusted-host installation. No new key,
  approval service, pin architecture, effective-time delay or backup requirement.
  Existing Admission/Freeze records remain byte-identical historical inputs.
- Retain the exact existing M1 packager/schema (`c300_m1.py`, retained source SHA
  `cd2b580b56e819dee2e49933a658161ce92675fd4ba5c1abc2f9ffc3a4e1b2ea`)
  and existing per-binding `lossless_gate.py`. No model/schema change or new parser
  framework. Dormant historical execution functions are not used for N450.
- `n450_runtime.ProcessingAccess` binds the complete approved 450-entry registry,
  exact Universe/admission/C750 identity, paths, sizes and hashes to the existing
  remote objects. The reader/verifier gain an explicit access adapter; their
  registered paths and default local behavior stay intact. No path override or
  RAW relocation is accepted. UC Volume RAW is opened read-only in place.
- DEC-000010 profile/provenance and independent `m1_verifier_v2` are pinned in the
  runtime closure. Only Company Name at the exact approved SRC010128 witness uses
  ISO-8859-1. Source, record, field and byte reconstruction checks are retained.
- Absolute historical authority *metadata* is packaged through explicit
  hash-addressed aliases after byte verification. This is not a RAW fallback and
  does not change Universe v1 or historical scope. The complete frozen C300
  reference closure is packaged; four version-0 CLEAN snapshots are read only.
- Streaming checkpoints reuse existing Parquet packaging and gate checks. COMPLETE
  reuse requires rehash and independent readback; partial attempts fail closed and
  remain preserved. Fixed API idempotency tokens prevent duplicate phase submits.
- All 450 remote RAW hashes precede runtime side effects. Parsing is serial. Smoke
  bindings are SRC010001, SRC010128 and SRC010450; full consumes/reuses those durable
  checkpoints and attempts the other 447. CLEAN publication requires a full-scope
  attempt marker and revalidated COMPLETE checkpoints. Failures have explicit
  FAILED rows and no accepted partial records. No claim of success from counts alone.
- Native Delta publication is exclusive, with exact schema/multiset/occurrence
  validation and retained per-binding Lossless gates. Two-table publication is not
  atomic; partial publication is preserved and cannot be repaired by overwrite.
  Consumer views combine gated N450 with C300 using the existing UNION ALL/view
  mechanism, original run IDs and exact frozen table versions. Full record/field/
  coverage multiset checks are partitioned into explicit binding groups; semantic
  NULLs and economic interpretations remain unmodeled. Test 6 retains the lexical
  NOT_APPLICABLE inventory; old FIN results are not extended to new sources.

Validation groups retain self-checked success receipts bound to exact table versions,
view SQL, contract, owner pin and binding population; changed or failed receipts are
not reusable. Groups target 12 million records / at most 96 bindings, as in the
existing recovery mechanism. Query validation has the existing eight-hour recovery
timeout (the frozen historical query took about 6.6 hours); the other tasks retain
one-hour limits. These are runtime limits, not an effective-time waiting period.
Automatic retries remain zero; failed attempts and incomplete publications survive.

## Exact writes allowed after approval

- Delta: `workspace.edp_lab.clean_n450_m1_records_n450_step3_v1` and
  `workspace.edp_lab.clean_n450_m1_bindings_n450_step3_v1`.
- Views: `workspace.edp_lab.q_c750_m1_records_c750_step3_v1`,
  `workspace.edp_lab.q_c750_m1_fields_c750_step3_v1`,
  `workspace.edp_lab.q_c750_m1_coverage_c750_step3_v1`.
- Derived code/checkpoints/gates/evidence:
  `/Volumes/workspace/edp_lab/raw/n450-m1/n450_step3_v1/`.
- Workspace notebook: `/Shared/edp-lab-n450-m1/n450_step3_v1/runtime`.
- Local preparation/evidence: `runs/n450/`; no RAW bytes or credentials committed.

The controller is an operation allowlist, not a generic CLI/SQL proxy: only the
four reviewed deployment files, fixed notebook path and fixed phase submissions
are accepted. RAW upload, ACL changes, arbitrary jobs/tables/views, overwrites,
MERGE and CREATE OR REPLACE are excluded. Ambient Databricks account privileges
have not been changed or certified as least-privilege IAM; no remote permission
mutation is part of this preparation.

## Runtime and trusted installation

`scripts/prepare_n450_m1_runtime.py <new-local-directory>` deterministically builds
an inactive packet, code closure, fixed submissions and runtime.zip. It never
issues an approved record or installs an owner pin. The original scope is copied
as metadata and hash checked. Historical proposals are not overwritten.

The runtime payload excludes only the existing trusted owner-pin module and the
new approved record. That module is deployed separately from the actual trusted
installation, using the same existing two constants. All other module bytes and
the structural host template are pinned; the template accepts only simple literal
owner assignments, not hidden executable statements. This avoids a circular
record/archive digest while retaining a single existing trust root. Exact expected
installed module bytes are calculated for review; they are not installed by the
builder. The notebook checks host template, owner record, contract and archive;
the controller rechecks deployed artifacts before each job submission.

Owner review covers the exact proposed record and its referenced contract, ordered
450 bindings, 732 reuse bindings, runtime/code hashes, destinations and limitations.
Only the owner/trusted terminal may change status to OWNER_APPROVED with
`edp_lab.ingestion.c300_admission.encoded`, issue the new record at
`metadata/authorizations/n450_processing_v1.json`, and update OWNER_GRANT_PATH /
OWNER_GRANT_SHA256 in the existing `n450_authorization.py`. Preserve the old record.

Use the packet's generated REVIEW.md / install-owner.sh **only after independent
owner approval**. Installation creates no actual execution timestamp. Processing
is immediately eligible after valid installation and source/host checks; actual
start/end times are observed separately. No former Admission timestamp is reused.

`scripts/run_n450_m1.py <prepared-directory> deploy|smoke|full|publish|query` is
inactive until installation validates. It uploads no RAW and never manufactures
owner approval. Do not run it during readiness preparation. Workspace dependency,
permissions, source and output-name checks are enforced during authorized execution;
missing duckdb/pyarrow fails before outputs, with no automatic pip installation.
Actual runtime/dependency versions, CPU/wall time, memory and unavailable telemetry
are recorded. Live Spark/Databricks execution is intentionally NOT_TESTED here.

## Validation scope and stop boundary

Focused tests cover exact complete authorization, missing/forged grants, narrower/
reordered/duplicate scope, outside/holdout/changed identities, hashes/profiles/paths,
C300 version drift, destination/traversal/symlink isolation, template/code tampering,
fixed submissions, direct publication guards, incomplete attempts and verified
idempotent checkpoint reuse. Temporary synthetic artifacts plus full SRC010128 and
one UTF-8 source exercise the actual reader/independent verifier via a simulated
read-only UC mount; no real RAW is copied and no production output is registered.
Host-dependent evidence tests skip only when those local artifacts are absent.
The exact successful test command/count is recorded in the final review packet.

Stop before deployment, Databricks processing and native output writes. No Stability
A/B/C, Performance evaluation, Write Tasks, FIN scope expansion, output freeze,
result merge/Exit or M2 is performed or authorized by this readiness work.
