# Reusable cohort admission and freeze (Day 4 onward)

Use `edp_lab.ingestion.cohort_publication` for **new** corpus increments and
input cohort freezes. The Day 3 `n450_admission` / `n450_authorization` modules
remain historical, version-pinned implementations and must not be extended with
new hardcoded cohort names.

The reusable entry point accepts a reviewed `COHORT_ADDITIVE_V1` plan containing:
- Existing frozen baseline: cohort ID, exact roster/bindings/manifest/freeze
  paths and approved SHA-256 fingerprints.
- New increment / combined IDs, expected counts, exact source identities,
  proposed registration IDs, registered and physical RAW paths, hashes,
  source families and admission UTC.
- Explicit manifest version and versioned admission/freeze destinations.

`prepare(root, plan)` validates the baseline and Universe v1 membership,
rejects holdouts and overlaps, and returns deterministic output bytes without
writing files. A plan is **not** authorization.

`publish(root, plan_raw, grant_raw, trusted_grant_sha256, action)` performs
exact approved-scope publication with exclusive paths. The SHA-256 argument must
come from the owner's **existing trusted installation procedure**, independently
of the proposal. An uninstalled/changed owner record is rejected. Do not derive
this trusted SHA from the proposal in agent code. Actions: `admission`, then
`freeze`. Freeze requires byte-exact readback of completed admission.

Day 4 target:
`C750_v1 + N750_v1 -> C1500_v1`, successor to the accepted v4 manifest.
Future authorized increments require a **new approved plan/grant, not a code change**.
Synthetic sizes and the actual Day 3 C750 input-layout contract are tested in
`tests/authorization/test_cohort_publication.py`.

Boundaries:
- This is a metadata publication implementation; it does **not** upload RAW,
  approve sources, authorize processing, or freeze an M1/M2 output result.
- Step 1 admission requires verified local RAW identity, SHA-256, provenance,
  Approved Universe v1 membership, disjointness, holdout exclusion, historical
  preservation and exact owner-approved metadata publication/readback.
- Remote RAW availability and SHA verification are mandatory before Step 8
  processing, rather than before Step 1 metadata publication. Unverified sources
  must not be processed. Remote status must retain its actual evidence coverage.
- Never claim Step 1 PASS without actual N750 admission, C1500 input freeze
  and post-publication verification.
- Step 14 is the only planned Day 4 -> main merge boundary.
