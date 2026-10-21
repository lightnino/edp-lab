# SRC010128 encoding exception: diagnosis v1 / B1 v2

**HOLD / HUMAN_UNRESOLVED; N450 processing eligibility remains 449/450.**
The original B1 v1 finding is preserved. No decoder, parser profile, authorization,
RAW, frozen C300 or cohort membership was changed. No M2 or Step 3 job was started.

## Exact source and failure

The sealed Universe/registration binding resolves `master.20120104.idx`, identity
`d0dc0ef10dabfaff1d02bb75b5efae1ef047e938418f08fb8cb92c1cb332e7f7`, to the
original repository RAW location. Full read-only inspection verified 708,188 bytes
and SHA-256 `5869c2d2e76ec56302291d7812add9d8cc1a0b9788478050344e40d14927e71d`
before inspection and again afterward. No new remote RAW transfer was necessary.

There is exactly one non-ASCII byte, `c3`, and one invalid UTF-8 sequence. Physical
line 6215 starts at zero-based offset 516310; the invalid byte is at record offset
34 / absolute offset 516344. It occurs in field 2, Company Name, in byte context
`GEST c3 4f 20 44 45` (spaces here separate diagnostic tokens). Byte `4f` is ASCII
`O`, not a UTF-8 continuation. Record SHA-256 is
`0204d6e8cca1a45efd0ef5956cfe49766ea7ee5a1e3143e3d5a60a7eaa60591a`.
All 8,537 physical records have LF terminators. All 8,530 DATA records have five
pipe-delimited fields: 42,650 field positions. Framing and multiplicity are intact.
This proves invalid UTF-8; it does not prove publisher corruption or intended text.

The hash-verified acquisition receipt reports `application/octet-stream`, with no
charset attestation. Diagnostic Latin-1 and Windows-1252 strict decode/re-encode
both reconstruct the exact source hash and agree on this file's byte repertoire.
That bijection does not establish the publisher's intended character meaning.
Neither codec was adopted as a registered parser rule.

## Actual M1 compatibility and remaining decision

`docs/day2_c300_m1_readiness_v1.md` specifies literal strict UTF-8 text and DIRECT_MAP
STRING values. The retained actual native M1 implementation and runtime manifest
were verified against the frozen O_C300_M1 baseline fingerprints. Synthetic Parquet
fixtures exercised its real packaging/readback oracle: valid UTF-8, including
Japanese text and duplicate occurrences, passes; the reversible Latin-1 carrier
fails because that oracle independently strict-decodes the original RAW bytes.
This was a synthetic compatibility test, not N450 CLEAN processing.

Surrogate escape is byte-reversible but cannot be stored as a valid Arrow STRING.
Hex/base64 or a different-codec Unicode carrier changes the DIRECT_MAP lexical
contract. Therefore no evidence-supported runtime fix satisfies the unchanged
contract today. Character semantics remain explicitly unresolved. No full SRC010128
text parse or output Lossless PASS is claimed from successful byte framing.

The precise remaining decision is authoritative evidence establishing this source's
encoding/character interpretation, or explicit approval of a versioned opaque-byte
transport value contract and matching native verifier policy. A schema-driven M2
requirement has not been demonstrated. Until that decision, retain this one source
as held without removing it from admitted N450 or frozen C750.

## Reproduction and evidence

- `scripts/diagnose_src010128.py`: read-only fixed-source diagnosis; codecs are
  counterfactual only. Detailed output: `runs/n450/src010128-encoding-v1/diagnosis.json`.
- `metadata/evaluations/n450_b1_v2.json`: versioned disposition, exact diagnosis
  fingerprint and frozen native code references. Original v1 is unchanged.
- All 449 previous per-source evidence fingerprints were revalidated and reused;
  their RAW was not replayed. Original profiling driver and evidence index are
  retained alongside this diagnosis.
- Focused checks: 28 passed, covering invalid byte boundaries, exact byte offsets,
  width/terminator accounting, reversible diagnostic reconstruction, surrogate
  rejection, actual frozen native oracle compatibility, existing UTF-8 parsing,
  occurrence fidelity and observation integrity/scope denial. Ruff passed.

Detailed observations and temporary synthetic test outputs remain outside Git.
