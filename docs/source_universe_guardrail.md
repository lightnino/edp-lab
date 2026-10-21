# Authorized source universe guardrail

Incident **EDP-INC-2026-10-21-001**. Branch `fix/source-universe-admission-gate`.
Completion of implementation `0f883e3` using owner-approved artifact commit `319281c`.
Step 5 authorizes this implementation, offline validation, commit, and conditional PR;
it does not authorize new cohort admission, acquisition, uploads, or processing.

## Authority and preserved evidence

The active host path is exactly `metadata/source_universes/approved_v1/manifest.json`.
SHA-256: `2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c`.
The loader pins these bytes and the independent `owner_authorization.json` digest
`3307ff5c234e20b48a7a2ced6de7c54d504eb475de8ae90d4509cfd49002823d`.
The owner record explicitly approves this manifest digest. Agent verification files
are reproducibility evidence, never approval authority. No owner record was edited.

Verified: exactly 3,021 unique members; 41 reserved development holdouts; both
`LOCAL_SEC_BULK_COMPANYFACTS` and `LOCAL_SEC_BULK_SUBMISSIONS` are included with
**QUALIFIED — OWNER_ATTESTED_PROVENANCE**. The pinned manifest records Step 2
qualification commit `787b473a78f5bcce814bafd8675ce1a9c5edea65`, section 16.
Missing publisher receipts/digests remain recorded; no new provenance barrier or
independent verification claim is introduced.

The manifest and prior pinned `verification.json` retain exclusion evidence for all
800 additional legitimate RAW instances. No repeated 800-file scan was performed.
No RAW bytes were modified, moved, deleted, acquired, or committed. Frozen C300,
`corpus_manifest_v6.csv`, and frozen C750/C1500/C2000 records are unchanged. The
historical C300 roster, corpus v3, owner authorization, freeze marker, and exact
original packet hashes are rechecked through the sidecar evidence pins.

## Three separate contracts and implemented paths

1. **Approved Universe** specifies eligible physical instances. It cannot grant an
   experiment roster or parser scope.
2. **Corpus Manifest** records actual admissions. It cannot expand universe authority.
3. **Frozen Cohort** names the exact admitted instances for a run. Its owner approval
   and parser approval remain independent requirements.

`metadata/source_universes/historical_cohort_bindings_v1.json` is a versioned,
hash-bound sidecar, with its digest pinned in `ingestion/universe.py`. It references
`universe_id`, `universe_version`, and `universe_manifest_sha256`. Its GOLD/C300
registered aliases are copied mechanically from the frozen corpus/rosters and the
original owner-approved C300 packet; delivery ID, registered ID, exact path and hash
are compared. All input locators/digests are retained. This records existing grants;
it creates no new authority. Historical CSV and freeze schemas remain unchanged.

- `UniverseGate.load`: exact universe pin, owner-record pin and digest linkage,
  sidecar pin/version and all sidecar evidence hashes. `verify_inventory` checks the
  pinned original inventory before admission/processing. Missing/changed evidence
  fails closed. Validation uses explicit exceptions and remains active under Python
  optimization.
- C300 `prepare`: inventory and authorized capacity before review/selection; each
  selected delivery must belong to the pinned C300 cohort before reservation/output.
  Existing mechanical qualification, provenance, hash and overlap checks remain.
- C300 `freeze`: capacity, exact reviewed packet authorization and pinned historical
  owner-authorization bytes, delivery/registered membership, complete input roster,
  RAW hashes and duplicate paths/IDs before publication. An Agent-authored approval
  file cannot authorize a new freeze. A future freeze needs reviewed host evidence.
  No new freeze was run in this task.
- New review packets and freeze markers carry the three universe fields. New freeze
  output also includes `universe_binding.json`, binding the corpus and roster hashes;
  the freeze file inventory includes that sidecar. No historical packet is rewritten.
- `verify_registry`: original rows preserved; exact registered instance/hash/path,
  approved cohort, duplicates/overlap and optional RAW integrity checks. Historical
  GOLD_V1 introductions remain covered by their approved GOLD_V2 roster.
- GOLD `read_registered`, C300 `occurrences`, shallow `inspect`, and checkpoint
  `validate_c300`: existing scope checks precede parser/RAW access. Registered aliases
  come only from sealed historical evidence. Parser activation is still independent.
- Profiling adapter: host-fixed gate and cohort checked independently of principal
  grants. Requests cannot supply authority or switch versions/cohorts. Ordinary
  malformed requests remain FAILED; authority injection is BLOCKED for Human Review.
- All five profiling functions now propagate an authorization-blocked table with
  BLOCKED status, separate authorization evidence, and NOT_COMPUTED metrics. They
  neither treat legitimate out-of-scope RAW as corruption nor compute empty-population
  success metrics. This fixes a broader regression exposed during completion.
- Native contract preparation retains its existing local gate. The remote native
  notebook remains unguarded and excluded from new execution (see below).

`ScopeDenied.outcome` reports `OUT_OF_SCOPE / AUTHORIZATION_REQUIRED`, DENY,
approval-required, reason, evidence and Human Review. Capacity validation checks
`requested_count <= eligible_authorized_count` for the selected explicit roster;
insufficiency reports `INSUFFICIENT_AUTHORIZED_SOURCES` and Human Review before
selection/acquisition. There is no automatic source acquisition or monitoring service.

## Runtime isolation and Agent outcomes

Runtime consumers select explicit bindings, not directory prefixes. Every binding is
checked against identity, expected hash, exact path, universe and cohort before RAW
inspection. Existing readers then verify actual RAW/member hashes before parsing.
The real reader fixture lists both approved and unauthorized files and reads only
the explicitly pinned table. The inspection test passes an authorized binding plus an unexpected physical input
and proves the entire scope is rejected before parser activation; a GOLD instance
in a C300 run and a reserved holdout are also denied. A directory containing retained
RAW therefore cannot enlarge the selected roster. Local checks do not certify a
remote directory/prefix consumer: those paths remain excluded.

Observed Agent-interface results: self-approval, alternative universe/version and
cohort injection -> BLOCKED; unauthorized source -> OUT_OF_SCOPE; forged freeze
approval at actual `freeze` -> OUT_OF_SCOPE; insufficient capacity at actual `prepare`
-> BLOCK before plan/acquisition access. The adapter's denial trace preserves
approval-required and Human Review, and subsequent valid requests remain unchanged.
No onboarding/acquisition tool is granted execution authority. Historical acquisition
scripts are excluded, including attempts to meet a numeric target by expansion.

The trust boundary is a reviewed host installation. Requests cannot change pins;
an administrator or actor allowed to replace host code/configuration is outside this
boundary. Synthetic test constructors/pin monkeypatches grant no production authority.
A future owner-approved version and independently approved roster can authorize
previously retained RAW: an actual processing-entrypoint test demonstrates this using
a separate synthetic host pin, while v1 and old cohort bytes stay unchanged. No real
Universe v2 is approved or installed.

## Day 3 execution boundary — binding restriction

**No unguarded historical Day 3–5 path is approved for the upcoming experiment.**
These paths were inspected READ-ONLY at the following commits. They lack the new
pinned universe/cohort gate; they are not represented as protected, merged, enabled,
or eligible for execution. Before future use they require integration and tests at
selection/admission/freeze, transfer, and each physical-input read. The historical
N500 code's self-generated permission text cannot establish authority.

| Historical path | SHA-256 | Upcoming execution |
| --- | --- | --- |
| `c223117:scripts/prepare_n450.py` | `b1f5e27e87ca9c552d2749ed19390b2a502287c50e53c8a3e43e11437f2a72f5` | EXCLUDED until guarded |
| `c223117:scripts/upload_n450.py` | `9d66666444825c54d43c54340f5f46442b0eba0ef2ab3552c802840db871fd95` | EXCLUDED until guarded |
| `c223117:scripts/profile_n450_targeted.py` | `b970d129429e92f784d8b6119b54c21b6d4d0d94171d1a7b1502fb03cbcd9219` | EXCLUDED until guarded |
| `2eee969:scripts/prepare_n750.py` | `0f78e2647d0141c7dba3007debf9cdba49b7fd00d97e2b8ed0345833d7a8b09f` | EXCLUDED until guarded |
| `2eee969:scripts/upload_n750.py` | `4762e76010292196856a40252a1c7620a8491232b8bb9ee906dc8a6fb1d230eb` | EXCLUDED until guarded |
| `2eee969:scripts/profile_n750_targeted.py` | `dd4338e0f334da3530ca7ee9cf9cee1a328c0adc6652fd882300df5b72c4e1b2` | EXCLUDED until guarded |
| `b9f5dc7:scripts/prepare_n500.py` | `aa921b7f6134ce93fa84bd44b33c02dbc3fe0e1f773d36e546b6f45ffd3743a4` | EXCLUDED until guarded |
| `b9f5dc7:scripts/upload_n500.py` | `e6710affe855a79766b9b21d17797532cb854add962a8985f08158e75b4edf23` | EXCLUDED until guarded |
| `b9f5dc7:scripts/profile_n500_targeted.py` | `089c3726ed20a33b7ba398f0e5f4ca282fb683357c12e5800e5c07964727f87c` | EXCLUDED until guarded |

N750/N500 upload adapters delegate to the historical N450 uploader, so exclusion
includes that shared path. The preparers' acquisition/qualification and conditional
freezes, including N500 `qualify`, `admit`, `historical_gate`, and `freeze`, are all
excluded. Targeted profilers are excluded even where their selection is bounded.
No new N450/N750/N500 entrypoint is present on this baseline. Future rebuilt paths
need integration before approval; this Step 5 PR does not approve them.

`notebooks/bronze_nasdaq_listed.py`, historical remote notebook paths, and new native
job submission/processing remain **EXCLUDED / UNVERIFIED** until a deployable pinned
roster/universe check is enforced before remote RAW reads. Native sealing and
post-approval replay evaluate historical evidence; they do not authorize new work.
No C300/M1 Databricks processing, C300 full replay, Day 3 Stability A/B/C, new admission,
upload, or remote job was executed. No historical unauthorized cohort was merged.

## Exact validation commands and coverage

All commands run in this worktree on 2026-10-21. Interpreter/tool installation is the
existing read-only `/Users/lightnino/Projects/edp-lab/.venv/bin/`.

```sh
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python -m pytest -q tests/authorization tests/parsers/test_c300_v1.py tests/profiling tests/governance tests/lossless
# 114 passed, 4 skipped
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python -m pytest -q tests/authorization tests/agents tests/tool_adapters tests/corpus_invariants/test_c300_admission.py tests/governance
# 123 passed, 6 skipped
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python -m pytest -q -rs --tb=short
# 294 passed, 23 skipped; no failures
/Users/lightnino/Projects/edp-lab/.venv/bin/ruff check .
# All checks passed
git diff --check
# PASS
```

The original broad run was reproduced exactly: **85 passed, 29 failed, 5 skipped**.
All 29 original dispositions are below: 28 now PASS and one environmental SKIP.
There are no unexplained failures. This is an offline suite result with explicit
skips, not full live/RAW regression coverage.

Full-suite skips: four pending integrations (future admission/freezes; historical
transfer/profiling; remote processing; future Agent onboarding/release evaluation),
one post-approval evidence dependency, one actual C300 membership evidence dependency,
14 RAW-hash cases missing local RAW, two actual C300 parser evidence dependencies,
and one registered GOLD adapter case missing local RAW. The actual authority-context
checks additionally declare external pinned inventory/packet prerequisites, and skip
when those are absent on another machine; tampered present evidence still fails.

Positive owner-context tests use actual installed artifacts and frozen registry
entrypoints without reading RAW. Synthetic tests exercise real `prepare`,
`processing`, reader and adapter entrypoints with test-only sealed bytes/pins.
The reader fidelity fixture mocks frozen-config loading and source registry integrity,
but exercises the real universe load, RAW/member hashes and parser. Its result does
not certify a real GOLD snapshot. The runtime scope test mocks parser activation
with a sentinel to prove denial precedes it; it does not mock authorization. A
positive C300 inspection-boundary test reaches the independent parser approval gate
without parsing RAW. Future-version tests monkeypatch the trusted test deployment
pin only; no request interface can do this. No live Databricks behavior is verified.

Additional full-suite findings fixed: reader integrity fixture missing authorization
context, and direct profiling of a blocked reader result attempting metrics before
schema availability. Three pre-existing Ruff findings in the universe proposal
script were corrected mechanically (import order and regular-expression flag names);
the generator was not executed and approved artifacts were not regenerated.

## Disposition of every original failure

| Exact original test node | Classification | Resolution | Final |
| --- | --- | --- | --- |
| `tests/agents/test_analyst_v0.py::test_agent_independent_expectations_replay_and_provenance` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/agents/test_analyst_v0.py::test_malformed_source_is_not_completed_population` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/agents/test_analyst_v0.py::test_agent_does_not_write_files_or_open_network` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/tool_adapters/test_profiling.py::test_independent_calls_reuse_exact_existing_outputs_and_replay[profile_table-parameters0]` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/tool_adapters/test_profiling.py::test_independent_calls_reuse_exact_existing_outputs_and_replay[profile_column-parameters1]` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/tool_adapters/test_profiling.py::test_independent_calls_reuse_exact_existing_outputs_and_replay[find_duplicates-parameters2]` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/tool_adapters/test_profiling.py::test_independent_calls_reuse_exact_existing_outputs_and_replay[candidate_key_scan-parameters3]` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/tool_adapters/test_profiling.py::test_independent_calls_reuse_exact_existing_outputs_and_replay[schema_fingerprint-parameters4]` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/tool_adapters/test_profiling.py::test_malformed_requests_are_structured_failures[change0]` | Genuine implementation regression | Fixed blanket exception classification: ordinary invalid requests return FAILED; authority-field injection remains BLOCKED. | PASS |
| `tests/tool_adapters/test_profiling.py::test_malformed_requests_are_structured_failures[change1]` | Genuine implementation regression | Fixed blanket exception classification: ordinary invalid requests return FAILED; authority-field injection remains BLOCKED. | PASS |
| `tests/tool_adapters/test_profiling.py::test_malformed_requests_are_structured_failures[change2]` | Genuine implementation regression | Fixed blanket exception classification: ordinary invalid requests return FAILED; authority-field injection remains BLOCKED. | PASS |
| `tests/tool_adapters/test_profiling.py::test_malformed_requests_are_structured_failures[change3]` | Genuine implementation regression | Fixed blanket exception classification: ordinary invalid requests return FAILED; authority-field injection remains BLOCKED. | PASS |
| `tests/tool_adapters/test_profiling.py::test_malformed_requests_are_structured_failures[change4]` | Genuine implementation regression | Fixed blanket exception classification: ordinary invalid requests return FAILED; authority-field injection remains BLOCKED. | PASS |
| `tests/tool_adapters/test_profiling.py::test_malformed_requests_are_structured_failures[change5]` | Genuine implementation regression | Fixed blanket exception classification: ordinary invalid requests return FAILED; authority-field injection remains BLOCKED. | PASS |
| `tests/tool_adapters/test_profiling.py::test_malformed_requests_are_structured_failures[change6]` | Genuine implementation regression | Fixed blanket exception classification: ordinary invalid requests return FAILED; authority-field injection remains BLOCKED. | PASS |
| `tests/tool_adapters/test_profiling.py::test_malformed_requests_are_structured_failures[change7]` | Genuine implementation regression | Fixed blanket exception classification: ordinary invalid requests return FAILED; authority-field injection remains BLOCKED. | PASS |
| `tests/tool_adapters/test_profiling.py::test_malformed_requests_are_structured_failures[change8]` | Genuine implementation regression | Fixed blanket exception classification: ordinary invalid requests return FAILED; authority-field injection remains BLOCKED. | PASS |
| `tests/tool_adapters/test_profiling.py::test_resource_limits_do_not_run_profiler[scope0]` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/tool_adapters/test_profiling.py::test_resource_limits_do_not_run_profiler[scope1]` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/tool_adapters/test_profiling.py::test_failed_scans_preserve_evidence_without_completed_metrics[a,b\n1,x\ninvalid\n-PARTIAL-1]` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/tool_adapters/test_profiling.py::test_failed_scans_preserve_evidence_without_completed_metrics[wrong\n-FAILED-0]` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/tool_adapters/test_profiling.py::test_unresolved_semantics_are_partial_and_evidence_is_retained` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/tool_adapters/test_profiling.py::test_invalid_column_and_search_limits` | Genuine implementation regression | Fixed blanket exception classification: ordinary invalid requests return FAILED; authority-field injection remains BLOCKED. | PASS |
| `tests/tool_adapters/test_profiling.py::test_registered_gold_binding_and_integrity_failure` | Missing authorization context, then environmental dependency | Host gate installed; positive authorization passes, but original GOLD RAW is absent. Explicit environmental skip; no fidelity or real-RAW PASS claim. | SKIP |
| `tests/tool_adapters/test_profiling.py::test_host_bindings_are_isolated_from_input_and_response_mutation` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/corpus_invariants/test_c300_admission.py::test_historical_registry_supported` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/corpus_invariants/test_c300_admission.py::test_registry_rejects_historical_rewrite` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/corpus_invariants/test_c300_admission.py::test_no_freeze_without_scoped_authority` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |
| `tests/corpus_invariants/test_c300_admission.py::test_expansion_protects_complete_frozen_rows` | Missing authorization fixture/context | Explicit synthetic host fixture for in-memory profiling, or exact installed owner/frozen evidence for registry checks. Original assertions retained. | PASS |

## Release assessment and remaining restrictions

Step 5 is ready for Step 6 human closure review: deterministic local enforcement,
authority linkage, explained regressions, and the pre-Day-3 exclusion boundary are
implemented. This is not incident closure, merge approval, or authorization to begin
Day 3 processing. Release is limited to the reviewed local guardrail and existing
GOLD/C300 scope. Live Databricks behavior and absent real-RAW coverage remain
UNVERIFIED; historical Day 3–5 and remote processing paths remain excluded until
guarded and separately approved. These restrictions cannot be cleared by an Agent.
