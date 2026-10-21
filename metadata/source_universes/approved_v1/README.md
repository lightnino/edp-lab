# Approved Source Universe v1 — owner approved, inactive

Universe ID: `EDP_LAB_ORIGINAL_SOURCE_UNIVERSE`, version `1`.
Incident: EDP-INC-2026-10-21-001. Prepared on branch
`fix/source-universe-admission-gate` over guardrail commit `0f883e3`.

`manifest.json` preserves the exact owner-approved authority bytes. Explicit owner
approval of this digest is **APPROVED** in the separate, versioned
`owner_authorization.json` (record version 1, 2026-10-21). Agent assertions are in `verification.json`; they are
not owner authorization. Do not edit or regenerate the manifest in place. Changes
require a new reviewed version/digest. The generator uses exclusive creation.

SHA-256 of the complete canonical manifest:
`2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c`.

## Schema and reproduction

Schema identifier: `SOURCE_UNIVERSE_AUTHORITY_V1`. The root object contains
`universe_id` (string), `universe_version` (string), `member_count` (integer),
`inventory_reference` and `inventory_sha256` (v2 path and lowercase SHA-256),
`original_inventories` (v1/v2 path/hash objects), `canonicalization` (string),
`approval_reference` (separate owner-record path), `holdout_policy`,
`outside_universe_policy`, `qualification_evidence` (evidence/policy objects), and
`members` (exact 3,021-member array).

Each member contains `identity` (original inventory_id, unique and nonempty),
`raw_sha256` (64 lowercase hex characters), `raw_path` (exact v2 final_path), and
`holdout` (boolean). Only the two original SEC Bulk entries additionally contain
`qualification`: disposition, missing receipt/digest status, independent publisher
verification flag and null Source Instance ID. No IDs are allocated. No registered
identity crosswalk or cohort processing grant is installed by this universe task.
The C300 read-only crosswalk is evidence in `verification.json`.

Canonical bytes: UTF-8 JSON, lexicographically sorted object keys, comma/colon
separators with no spaces, Unicode unescaped, exactly one final LF. Members are
sorted by original inventory identity. Hash the entire file; its digest lives
outside the hashed document to avoid self-reference.

Read-only checks:

```sh
shasum -a 256 metadata/source_universes/approved_v1/manifest.json
cd metadata/source_universes/approved_v1
shasum -a 256 -c manifest.sha256
```

`scripts/prepare_source_universe_v1.py` documents and reproduces the deterministic
construction and assertions from pinned local evidence. It refuses to overwrite
this version. Original operational inventories remain in the original worktree;
their full absolute locators and expected hashes are pinned in the manifest.
No expanded corpus manifest supplies universe authorization.

## Verification and scope

All checks PASS; exact file hashes and all 300 individual C300 identity/hash
crosswalks are in `verification.json`.

- Both original inventories contain exactly 3,021 rows, unique identities and
  well-formed expected hashes; identity/hash populations match exactly.
- v1 SHA-256: `99f09213dc17d845a4ea6e97dfd6b99fabf7e4a7f5cb618253f7040fa706ca6c`.
- v2 SHA-256: `1dcf16137a3a3cd0be3c4f025d9e6274e2a9bba34163e121004a97b1961bc45a`.
- All 41 holdouts are members: CFTC_COT 28, NYC_TLC_TRIPS 12,
  ECB_REFERENCE_RATES 1; development use is denied. Historical policy also reserves
  ECB_SDMX, which has zero original entries. The policy reference and hash are pinned.
- The incident's retained-reference document enumerates exactly 800 outside
  Source Instances. Their recorded hashes are disjoint from the original universe;
  they remain excluded and must be retained without modification or automatic admission.
- C300: 300/300 exact frozen packet delivery IDs resolve to original inventory
  identities with matching expected RAW hashes and paths. Zero outside-population
  source-ID overlaps; zero holdout overlaps. Frozen roster, manifest, authorization,
  freeze marker and original review-packet hashes match their historical pins.
  Original inventories and historical tracked metadata were rechecked unchanged.
- Both SEC Bulk candidates are INCLUDED and **QUALIFIED — OWNER_ATTESTED_PROVENANCE**.
  Step 2 evidence is read from incident commit
  `787b473a78f5bcce814bafd8675ce1a9c5edea65`, section 16; no merge.
  Original download receipts and independent publisher digests remain unavailable.
  Owner attestation is first-party evidence, not independent publisher verification.
  No additional provenance barrier is imposed; actual admission still requires all
  other applicable mechanical and cohort authorization checks.

These checks compare inventory and frozen evidence, not a fresh scan of RAW bytes
or remote retention. No RAW was read or changed, no admission or parser execution
occurred, and no cohort or Day 2 freeze was run. No Step 5 regressions were run.
The active authority path and deployment pin remain absent/unset. Activation and
registered/cohort grants are separate implementation steps after review.

## Recorded owner statement

> I approve EDP_LAB_ORIGINAL_SOURCE_UNIVERSE version 1, manifest metadata/source_universes/approved_v1/manifest.json, SHA-256 2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c, as the exact 3,021-member Source Universe authority. This includes both SEC Bulk candidates qualified by owner-attested provenance, reserves the 41 Day 13 holdouts from development cohorts, and excludes the 800 outside-universe sources while retaining their RAW. This approval authorizes universe membership only; it does not authorize new admissions, cohort freezes, parser scope or processing.

The owner explicitly supplied this approval in the current conversation on 2026-10-21.
`approval_verification_v1.json` records the manifest/approval linkage and file hashes.
The preparation script intentionally continues to generate a PENDING placeholder;
owner authorization is a separate action and cannot be generated by preparation.
Universe membership alone is authorized. Guardrail activation, new admissions,
cohort freezes, parser scope, processing, push, merge and Step 5 remain unauthorized.
