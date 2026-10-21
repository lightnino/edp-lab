# Exact N450 Admission / C750 Cohort Freeze owner review

This packet is **not an authorization, admission, ID reservation or freeze**.
Only metadata planning was performed using the existing implementation at
`1b08f4dd2d3fedb6c7bbb03b4037dc765b3debd7`. No implementation was rebuilt.

## Exact record and proposed host pin

The complete ordered record is `owner-record.proposed.json`, SHA-256:
`4680686dc77e92e7ef74c7e61d68a6140a4e0527ee15ea22a2d2b9fe5ccdcbc9`.
It has `status: PENDING_OWNER_REVIEW`; no approver is fabricated. All 450
physical-to-registration mappings and both complete ordered action scopes are
included, along with every proposed output file digest and destination.

The existing gate consumes **one independently approved record containing two
separate scopes**, rather than two separate host pins. The exact proposed approved
variant changes only `status` from `PENDING_OWNER_REVIEW` to `OWNER_APPROVED`, using
`edp_lab.ingestion.c300_admission.encoded` (JSON indent=2, sort_keys=True, trailing
LF). Its proposed host pin is:
`0262c7ba235701a8f8dcf5a44de39d3b9a034f79877bbe4015668d22fdb6712f`.
Those approved bytes have NOT been issued or installed by the Agent. The active
owner record does not exist, and `OWNER_GRANT_SHA256` remains `None`.
Any change to a mapping, timestamp, storage decision, prerequisite or scope requires
regenerating and reviewing the record and its pin. Output changes require fresh
output commitments too.

## Owner decisions embodied in the draft

- Approve N450 Admission and C750 Cohort Freeze only. Both complete ordered
  bindings and exact versioned metadata destinations are in the record.
- Approve the proposed unused registration IDs `SRC010001`–`SRC010450`, in exact
  roster order. These were checked against current metadata/proposals/docs/scripts/
  tests text and the preserved registry; no registered identity was changed.
- Explicitly accept or revise the proposed effective registration timestamp
  `2026-10-21T16:12:08Z` (2026-10-22 00:12:08 Asia/Shanghai). This is a planning
  value required by the existing deterministic output contract, not an observed
  execution time. If actual publication time must populate that field, refresh
  and reapprove the commitments instead of treating this value as an event time.
- Explicitly accept the stated storage limitation for metadata-only registration
  and cohort freeze: existing remote UC paths are writable; fresh exact-byte hashes
  and a hash-bound metadata snapshot do **not** establish immutable RAW storage.
  If immutable RAW protection is required, provide an approved mechanism first;
  this packet authorizes no upload, duplication, relocation or RAW mutation.
- Confirm Day 2 completion and Exit Check before execution. No Day 2 result or
  completion was inferred or modified here.

## Preflight and actual state

All five user-specified fingerprints matched. The production packet validator
confirmed 450 Universe-v1 eligible additions, no unchanged-C300 overlap, holdouts
or outside-universe sources, and the exact C300 + N450 union of 750. The proposed
additive manifest has 754 rows: 304 preserved GOLD/C300 rows plus 450 additions.
All original historical manifest rows and original C300 roster bytes are preserved
in the planned bundles. The plans were computed in memory, not published.

A metadata/path-existence check found **0/300 historical C300 RAW files present at
the exact worktree-relative paths required by `verify_historical_bytes`**. The
complete missing registered-ID list and pinned binding reference are in
`review.json`. No C300 RAW hash scan was run and no alternative paths were inferred.
Even with a valid owner grant, Freeze cannot pass that gate until the exact
historical bindings are available for validation. No hash check may be skipped.
The owner must direct an authorized access arrangement if these paths remain
unavailable; this packet does not permit copying RAW or rewriting historical paths.

Remote RAW verification was **not rerun** because the independent authorization
boundary precedes it. The preserved prior evidence remains 450/450 exact-byte PASS
at SHA-256 `8b46ce38d970be771ad56bbfd1a86d8eb60438852f3e9b5fe98fa57ac10f844b`.
Fresh verification of every exact ledger path, size and SHA-256 is mandatory after
valid authorization and before reuse. That check would be read-only; no compute
job, upload or copy is authorized.

Actual N450 admissions: **0**. Actual frozen C750: **none**. Existing accepted C300:
300; preserved corpus v3: 304 including GOLD. No new manifest or freeze path exists.
All hashes in the proposed scopes are **future output commitments**, not evidence
of publication. `review.json` lists those commitments without materializing them.

## Minimal next owner/host action — stop boundary

1. Independently review and approve the exact record and explicit decisions above,
   including confirming the Day 2 prerequisite, or request precise revisions.
2. An owner/trusted host maintainer must issue the approved record at
   `metadata/authorizations/n450_execution_v1.json` and install its independently
   approved digest in `OWNER_GRANT_SHA256` through the trusted deployment workflow.
   For the exact status-only variant above, the digest is `0262c7ba235701a8f8dcf5a44de39d3b9a034f79877bbe4015668d22fdb6712f`.
   This Agent has neither issued that record nor installed the proposed pin.
3. Resolve the missing C300 binding availability before requesting Freeze, without
   weakening historical checks or the no-copy/no-relocation boundary.

After those conditions are met, revalidate authority and exact bytes, perform the
fresh remote verification, and invoke the existing guarded entrypoints. This
review packet itself cannot activate those operations. No profiling, M1/CLEAN,
QUERYABLE, Lossless, Stability, M2 or merge is authorized.
