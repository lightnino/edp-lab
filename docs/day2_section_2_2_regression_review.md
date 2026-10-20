# Day 2 §2.2 regression review

Scope: preserve required regression tests only. Acceptance requirements are the
user's §2.2 instruction and the existing frozen parsing/source/output contracts.
No separate frozen Study Notes document or §2.2 text was found in the repository;
its location was requested. Final comparison against that document is pending.
This is the only documentary acceptance blocker; C300 admission is not a §2.2 gate.

## Existing coverage inventory and reuse

| Requirement | Existing tests retained | Assessment and addition |
| --- | --- | --- |
| Frozen membership and source references | `tests/corpus_invariants/test_gold_v2_registration.py`, `test_source_identity.py`, `test_gold_set_baseline.py` | Exact GOLD_V1/V2 rosters, manifest snapshot, lineage and rejected membership changes already covered. No duplicate roster assertions added. |
| RAW integrity | `test_source_identity.py`, `test_parser_fidelity.py`, `test_profiling_tools.py`; `tests/lossless/test_raw_inventory.py` | Controlled fixtures already reject changed RAW/member bytes. Reader test asserted empty rows but did not prove parser was never called; strengthened with a forbidden parser sentinel and explicit FAIL/member/read-only assertions. |
| Parser fidelity | `tests/corpus_invariants/test_parser_fidelity.py`, `test_parser_evidence.py`, `test_profiling_tools.py` | Exact leading zeros, signs, precision, dates, blanks, quotes/backslashes, Unicode, duplicate occurrences, byte reconstruction, malformed widths/headers/encoding, footer accounting and multiline synthetic parsing already covered. Reused in place; no duplicate `tests/profiling/test_parser_fidelity.py` created. |
| NULL policy and duplicates | `test_profiling_tools.py`, `test_profiling_conventions.py` | Existing unknown-NULL metrics and exact duplicate totals (2 groups, 5 participating rows, 3 excess), bounded witnesses, explicit synthetic NULL rules and zero denominators retained. Synthetic NULL rules do not authorize source NULL semantics. |
| Replay | `test_profiling_tools.py::test_deterministic_replay_all_functions` | Valid same-provenance full-output equality retained. Missing independent sample ordering and changed-provenance comparison added separately. |
| Schema fingerprint | `test_profiling_tools.py`, `test_profiling_conventions.py` | Distribution separation, order/name/type sensitivity retained. Comparison against the production hash helper alone was a weak canonicalization oracle; added independent exact UTF-8 JSON expectation. |
| Other current tests | CLI, governance Finding contract, SQL smoke | Retained and included in full validation; no later-section functionality added. |

## Added coverage

- `tests/corpus_invariants/test_c300_membership.py`: explicit skipped actual-cohort
  check with admission/parser-registration reason. No fabricated membership or
  claim of C300 validation; admitted GOLD contracts remain covered above.
- `tests/corpus_invariants/test_raw_hashes.py`: parameterized checks of all 13
  frozen table bindings, exact parent/member hashes before parsing, registered
  reader PASS, unresolved NULL semantics, byte-for-byte preservation of RAW,
  members, freeze, CSV registries and parser configuration. RAW absence is an
  explicit local-data skip, never metadata-only proof of bytes. Also checks the
  canonical local four-source validator. Local execution had all RAW available.
- `tests/reproducibility/test_profiling_determinism.py`: all-five-function replay,
  independent result-hash verification, changed-provenance envelope sensitivity
  and equality of every other field. Only provenance/run ID/result hash are
  excluded for that comparison; inputs/configuration/parameters/errors/locators
  and metrics remain compared. No timestamp is currently emitted. Independent
  seed/source/locator SHA-256 sample ranking covers zero, bounded and oversized
  samples; top-value ties, duplicate ordering and source-order witnesses checked.
- `tests/profiling/test_profile_edge_cases.py`: empty and unusual blank/token
  populations retain unknown-NULL NOT_COMPUTED values and reasons; partial scans
  retain exact error line and scanned occurrences without completed row counts.
- `tests/profiling/test_schema_fingerprint.py`: exact canonical JSON bytes and
  whitespace/case/Unicode-normalization/order/addition/removal/type sensitivity.

No production code, registered RAW, frozen metadata/policies/membership or
historical execution evidence changed. No §2.1 defect was identified. No test
required actual C300 admission before this change; the new explicit skipped check
records the unavailable cohort-specific validation.

## Validation and review

Baseline: 155 passed. Final: 188 passed, 1 skipped (actual C300 membership).
Commands use existing local tools without network or dependency synchronization:

```text
.venv/bin/python -m pytest -q   # 188 passed, 1 skipped
.venv/bin/ruff check .         # All checks passed
git diff --check              # no diagnostics
```

Initial Ruff validation found one redundant UTF-8 encode argument in the new
schema test; corrected before final checks. Additional whitespace checking covers
new untracked files, which ordinary `git diff --check` does not inspect.

Status: §2.2 BLOCKED for final frozen-Study-Notes comparison only; all supplied
§2.2 regression requirements implemented and passing. Once the reference is
provided, compare §2.2 only before acceptance. No §2.3–§2.8 requirement is used as
an acceptance gate. C300 creation/admission and parser registration, semantic
NULL resolution, Business Keys, semantic integration and Agent functionality
remain deferred outside this change.

Changed files: this review, the five new test modules listed above, and
`tests/corpus_invariants/test_profiling_tools.py`. Changes are technically ready
for review; final acceptance/commit readiness awaits the documentary comparison.
No commit or push performed.
