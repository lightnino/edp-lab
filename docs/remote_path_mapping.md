# Remote RAW locations — minimal rule (Day 4 onward)

**Source identity and RAW SHA define a source; a Databricks directory or filename
does not.** This is why searching N450/N750/N500 folders by current registered
SRC name can miss a previously uploaded physical source.

Use one lightweight receipt index, not a second source registry:

```sh
PYTHONPATH=src python -m edp_lab.ingestion.remote_locations \
  --roster proposals/n750-step1-v3/roster.json \
  --evidence proposals/n750-step1-v3/qualification.json \
  --output runs/day4/n750-remote-locations.json
```

The index joins receipts to the approved roster by exact `source_identity`,
`raw_sha256` and `bytes`, retaining **actual remote paths** from receipts.
It does not derive DBFS paths from an SRC ID, source basename or cohort name.
Additional verified receipt lists can be supplied with repeatable `--evidence`.
For future upload batches, retain one normalized receipt per physical source:

```json
{"source_identity":"<physical identity>","raw_sha256":"<64-hex>",
 "bytes":123,"remote":"dbfs:/Volumes/.../<actual object name>",
 "remote_status":"EXACT_REMOTE_BYTES_PASS",
 "actual_sha256":"<same 64-hex>",
 "verified_at_utc":"<UTC time>"}
```

Historical qualification receipts using the existing
`REUSED_PRIOR_REMOTE_READBACK` basis are supported without conversion.
An unresolved source stays `UNRESOLVED`, not `MISSING` or `PASS`.
This index is **historical locator evidence**, not a substitute for a live
Databricks checksum readback.

Before processing, run the same CLI with `--require-complete` and then perform
live byte/SHA verification of every resolved object. Do not process an
unresolved or mismatched source. For objects uploaded in Day 1/2 without
retained exact-path receipts, reconstruct verified receipts once from actual
Databricks objects; never guess paths or declare them missing solely because
they were not found in newer upload folders.

**Step 1 is only metadata admission/cohort freeze**. This locator index is
independent of `cohort_publication.py`; it does not authorize source
admission, upload, processing or schema evolution. No extra approval tier or
remote directory-scanning framework is introduced.
