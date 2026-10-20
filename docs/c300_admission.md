# C300 admission and final freeze review

The offline `edp_lab.ingestion.c300_admission` tool verifies the active inventory,
its content-addressed review snapshot, original draft membership, discovery plan,
receipts, relocation chains, existing RAW hashes and GOLD registries. No network,
RAW writes, parsing, entity mapping or Agent functionality is involved.

The current draft is the original 60 SEC_FSDS + 42 SEC_13F + 198
SEC_EDGAR_DAILY_MASTER deliveries: 300 SEC, 300 REAL, 0 CONTROLLED.
Candidate identities and physical delivery identities are explicitly linked; neither
is treated as an existing admitted source ID. Proposed IDs SRC000005–SRC000304
follow the exact existing draft order. Historical GOLD IDs and files are unchanged.

Prepare an exclusive review directory:

```sh
.venv/bin/python -m edp_lab.ingestion.c300_admission prepare --output runs/c300/admission-v2
```

`review.json` includes all 300 members, provenance references and evidence hashes,
composition, eligibility and future nested-prefix checks. `members.csv` is the
concise review table. `C300.proposed.csv` and `corpus_manifest_v3.proposed.csv`
are fingerprinted proposals, not admitted registries. The manifest proposal has
explicit pending timestamps and PROPOSED status; final timestamps and consequently
the final manifest hash cannot exist before actual admission.

Final human authorization must identify the exact SHA-256 of `review.json`, approve
both admission and freeze, and provide actual authority and authorization text.
The authorization record uses `packet_sha256`, `admit_and_freeze: true`,
`approved_by`, `authorized_at_utc`, and `authorization_text`. Never fabricate these
values or interpret policy approval as final membership authorization.

After actual authorization, retain it locally and execute:

```sh
.venv/bin/python -m edp_lab.ingestion.c300_admission freeze \
  --packet runs/c300/admission-v2/review.json \
  --authorization runs/c300/admission-v2/authorization.json \
  --output runs/c300/frozen-v1
```

Publication uses exclusive creation and writes `freeze.json` last. A directory
without that final marker is incomplete, not frozen. No existing destination is
reused or repaired automatically. The frozen package retains exact authorization,
review evidence references, roster, new manifest and their fingerprints. Actual
UTC admission/freeze time is measured at execution. RAW and every pinned evidence
file are rehashed first. Historical manifest rows are copied unchanged.

`verify_registry(root, manifest, check_raw=True, frozen=prior_manifest)` validates
this additive REAL-only version and rejects changed or removed frozen rows.
`verify_nested` rejects replacement even if later draft sizes still match.
Future expansion must explicitly use these checks against the frozen manifest;
there is no automatic expansion or active-registry switch. CONTROLLED admission
requires a separately reviewed implementation, since this draft contains none.
The original validator and all parser freezes remain unchanged. Admission never
extends GOLD parser authority to C300. Local review packets and authorization
remain under gitignored `runs/`; preserve them alongside immutable RAW evidence.

## Executed freeze

The user explicitly authorized packet
`387a20d29f0006dcd6c2b9587e57e5f015358aba50bfbf7fd0cc3f13ca059895`
and roster
`f052599a7cfac3b566a236965e2ab163934d4541e7b09e03da98be728c1541e4`.
Admission and freeze were recorded at `2026-10-20T11:08:51.473469Z`.
The authorization record distinguishes its agent recording time from the unavailable
original message timestamp. No human name or message timestamp was invented.

`runs/c300/frozen-v1/freeze.json` is the completed freeze marker. Its package contains
`C300.csv`, `corpus_manifest_v3.csv`, the exact approved `review.json`, and actual
`authorization.json`, with their content hashes. The manifest has 304 rows: four
unchanged GOLD records plus SRC000005–SRC000304 introduced in C300.
Final manifest SHA-256:
`27ce93f363ebeb234737659e9a411927aed3dd3a674bc8a21b780e05dfdc4bdf`.
The review packet retains its historical preauthorization status; the completed
freeze marker and authorization record establish the subsequent actual state.

Read-only verification, including exact approved roster, 300 membership, 304 manifest
rows, RAW bytes, hash-pinned supporting evidence, unchanged GOLD and future drafts:

```sh
.venv/bin/python -m edp_lab.ingestion.c300_integrity --check-raw
```

Future additive manifests can be checked with `--expansion PATH`; removed or changed
frozen records fail validation. C700 and later remain drafts. No parser or semantic
authority is inferred. The actual local membership test runs when the frozen local
package is present and skips only when these intentionally untracked files are absent.

## Git persistence and repository isolation

Canonical tracked metadata preserves exact existing frozen bytes:
`metadata/cohorts/C300.csv`, `metadata/corpus_manifest_v3.csv`, and
`metadata/freezes/C300_v1/{freeze,authorization}.json`.
`metadata/freezes/C300_v1/references.json` links those copies to the original
freeze and approved review-packet hash. This persistence step does not re-freeze,
regenerate or alter membership, timestamps or source identities. RAW and operational
runs remain gitignored; acquisition receipts and the large local review packet
remain local evidence referenced by their frozen hashes.

`verify_persisted_freeze(root)` checks the Git metadata without private local
files. Local `verify_freeze(..., check_raw=True)` additionally verifies original
supporting evidence, all admitted RAW hashes and future nested drafts. Both checks
are covered by the C300 membership suite; only the local check skips in a checkout
without private evidence.

The unrelated §2.5 tool-adapter files are preserved byte-for-byte in the separate
`feature/section-2-5-tool-adapters` worktree at `/private/tmp/edp-lab-section-2-5`.
They are excluded from the C300 branch changes. No commit, push or merge is made
by this isolation step.
