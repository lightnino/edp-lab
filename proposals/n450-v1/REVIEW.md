# Proposed N450 — owner review required

This directory is a proposal, not a cohort registry, admission, freeze, approval or processing grant. Branch `day3-authorized-n450-v1` starts at local `origin/main` commit `e81544ad235f3811d96c720dc1059f938e30d250`. No historical branch was merged or executed. The current local main reference was used; no claim of a freshly fetched remote main is made.

## Authority and proposed membership

Universe `EDP_LAB_ORIGINAL_SOURCE_UNIVERSE`, version `1`, manifest SHA-256 `2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c` and owner authorization SHA-256 `3307ff5c234e20b48a7a2ced6de7c54d504eb475de8ae90d4509cfd49002823d` verified by the production loader, including all pinned historical binding evidence. Original inventory hash verified; 3,021 members and 41 reserved holdouts confirmed.

Exact 450 proposed physical source identities, original acquisition candidate IDs, editions, paths, hashes, URLs and receipt references are in `roster.json`. No new SRC identifiers are assigned. `c750-proposed.json` enumerates the exact 750-member union as a proposal only (SHA-256 `f7994d3a4db77c3d16f8f3c805f57bd23755b165b120740b153d97b0d523eee6`). All 450 are `SEC_EDGAR_DAILY_MASTER`; 166,225,261 bytes. Selection follows original pinned review order and takes the first 450 eligible daily-master sources. This bounded single-family selection tests the increment mechanism; it makes no claim of source-family diversity or semantic representativeness. Historical Day 3 selected 395 daily files, five Treasury files and 50 newly acquired outside-universe files; that historical composition is not required or reused as authority here.

Roster SHA-256: `1567d32bb1db1fedfcf5bafb4538cbbdf4bba06af460c3eb6cb075f590a5a08b`.
Qualification SHA-256: `656a27c1fc994cb340b9b818ed9eb2adfd2527be79fadda1c2f8ede67949c084`.

`qualification.json` preserves all 300 C300 delivery identities, 41 holdout identities, 800 excluded registered identities, and input evidence digests. All original universe hashes are disjoint from the retained 800 hashes. Proposed sources have unique physical IDs, paths and RAW hashes; none overlaps frozen corpus v3 hashes (including GOLD). Existing status, physical-format evidence, candidate/plan/delivery agreement, receipt digest, publisher URL, successful transfer, timestamps, size and actual current local SHA-256 pass for each selected object. No payload parsing or profiling occurred. Existing physical-format evidence is historical mechanical qualification, not parser approval.

## Minimal execution integration proposal

1. Preserve Universe v1 and the historical GOLD/C300 sidecar byte-for-byte. Do not append this proposal to either one. Keep candidate artifacts outside `metadata/cohorts` and frozen directories.
2. Owner reviews this exact roster digest and evidence, then supplies an independent authorization record binding Universe ID/version/digest, roster digest, qualification digest, preserved C300 roster digest `f052599a7cfac3b566a236965e2ab163934d4541e7b09e03da98be728c1541e4`, and exact permitted actions. Agent-generated files never establish approval.
3. After that review, implement and review a separate host-pinned cohort grant, with its own owner-record digest and exact physical bindings. Add explicit N450 and C750 membership (C300 union N450, exactly 750); allocate registration aliases only during authorized admission. Pin the resulting additive manifest and complete roster. Existing historical bindings and grants remain unchanged. The production loader currently has no extension point: changing host loading code is a reviewed deployment, not a caller-supplied grant path or version override.
4. Rebuild only the small necessary entrypoints; do not run historical preparers, uploaders or profilers. Check host authority, inventory, owner grant, whole explicit input list, identity/path/hash, duplicates and holdouts before admission output, freeze publication, any transfer or any RAW reader. A new freeze must bind the independently approved exact packet; no self-authored permission text. Future uploads must be missing-only, never overwrite, and be separately authorized for an exact destination and bytes.
5. Remote consumers need a deployable pinned grant and complete explicit object list checked before RAW access; path/prefix discovery cannot authorize files. Recheck exact bytes or enforce storage version protection. The existing unguarded native notebook remains excluded. Parser rule/version and format scope require a separate explicit owner grant; registration does not authorize parsing, semantic NULL rules or canonical integration.
6. Validate positive and negative entrypoint behavior when implementing this later integration. The focused test here proves current denial; it does not certify future upload/profile/remote code.

## Negative authorization check

The first retained outside-universe object, `SRC000705`, was locally rehashed against its recorded exact digest. Passing it to the actual `edp_lab.ingestion.universe.processing` entrypoint for N450 returns `OUT_OF_SCOPE / AUTHORIZATION_REQUIRED`, reason `NOT_IN_APPROVED_UNIVERSE`, DENY, Human Review. The test asserts no downstream side-effect callback runs. No upload, admission, freeze, parser or RAW processing consumer was invoked. No override or agent approval interface exists. An eligible proposed source is independently denied as `NOT_IN_PINNED_COHORT` for N450.

Validation: `PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python -m pytest -q tests/authorization/test_n450_proposal.py` — 1 passed. Ruff for both new scripts and the test passes. The test depends on local retained evidence and explicitly skips elsewhere if missing; no missing-evidence PASS is claimed.

## Remote evidence and limitations

Historical upload completion evidence from Day 3–5 is read only for exact-hash object location, never admission or approval. All 450 proposed hashes have historical remote readback receipts: 395 in `n450-raw-v1-4a4585f6b03d` and 55 in `n750-raw-v1-83e49f67ddb0`. `remote.json` preserves the initial sandbox attempt: all 450 failed credential access, so it proves no live availability. `remote-live.json` records the subsequent credential-enabled explicit read-only byte verification: **450/450 EXACT_REMOTE_BYTES_PASS**, 166,225,261 bytes. Every remote object matched local expected SHA-256 and size. Zero objects currently need upload if guarded exact-object reuse is approved. A protected-location copy, if required, is a separate authorization decision. No remote mutation or compute job is used. Downloaded bytes are temporary hash-verification files only.

A hash match establishes current byte identity, not storage immutability or processing authority. The UC paths are existing writable volume locations; object immutability/version enforcement is unresolved. Owner may approve guarded reuse of the exact paths and hashes or require authorized copying to a protected destination. No object should be uploaded solely because it has a source registration. Any unverified/missing/mismatched object must remain blocked pending a specific upload/reuse decision. The remote ledger lists exact locations and per-object outcomes.

## Required owner decisions — stop here

Please review the roster and choose whether to approve these exact 450 physical instances as N450, with C750 defined as unchanged accepted C300 plus this increment. Approve a new independent cohort authorization and subsequent guarded admission/freeze implementation explicitly; proposal preparation itself grants none of these actions.

Separately specify whether exact verified historical remote objects may be reused and what immutability/pre-read integrity controls are required. Authorize any necessary upload by exact object list, digest and destination only after that inventory is resolved. Approve bounded lexical parser/profile/processing rules and versions independently before any execution. No semantic mappings, keys, NULL interpretation or RAW changes are requested.

Day 2 C300/M1 evidence and baseline freeze remain independent and untouched. C750 processing, Lossless comparisons and Stability A/B/C must wait for the relevant frozen Day 2 baseline; no historical result is accepted as that baseline here. No admission, freeze, upload, profiling, processing, commit or publication has occurred.
