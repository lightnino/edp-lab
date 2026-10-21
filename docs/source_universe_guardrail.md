# Authorized source universe guardrail

Implementation for EDP-INC-2026-10-21-001 / PR #15, based on main
`ddb6e47c52afa08415614dc7f341255255d9c963`. Branch:
`fix/source-universe-admission-gate`. This is a fail-closed implementation,
not an operationally approved experiment baseline or incident closure.

## Authority dependency — BLOCKED

This worktree has no original whole-lab 3,021-entry inventory and no approved
machine-readable universe authority artifact. No substitute universe was generated.
`metadata/source_universe_authority.json` and its trusted deployment SHA-256 pin
`APPROVED_AUTHORITY_SHA256` are deliberately absent/unset. Installing evidence and
changing that pin requires human review; a tool request cannot do it.

The proposed V1 authority schema is executable in `ingestion/universe.py`.
It pins the exact universe version, approval reference, original inventory reference
and SHA-256, declared member count, per-delivery identity, RAW hash, path and
holdout flag, plus explicit run/cohort identity rosters. The entire document's digest
pins all these fields, including the roster. `bindings` explicitly crosswalks an
inventory delivery to registered Source Instance IDs and paths under the same RAW
hash. No names, tickers or family-based inference is performed. Production evidence
must account for all 3,021 entries, all 41 holdouts and exact approved registration
crosswalks before activation. Fixtures are synthetic and grant no real authority.

This is a trusted-host boundary, not protection against an administrator modifying
Python code or configuration. Agents receive request interfaces, never authority
constructors, filesystem-write grants or deployment privileges. Future versions
need independently reviewed bytes and a new trusted pin. Existing versions and
cohort documents are never edited by this code. Holdout evaluation is unsupported
and denies until a separately reviewed evaluation mechanism exists.

## Enforcement implemented

- C300 `prepare`: inventory authority before selection and delivery identity/hash/path
  before ID reservation and output. Existing qualification checks remain required.
- C300 `freeze`: authority before reading an approval packet; all delivery and
  registered identities checked before publication. Packet authorization remains
  independently required. An Agent-authored packet cannot supply a universe pin.
- `verify_registry`: authority and registered membership before integrity validation.
- GOLD `read_registered`: authority before frozen configuration/RAW access, then
  exact `GOLD_V2` membership before materialization. Scope denial has a separate
  `authorization_outcome`, BLOCKED parse status, no parser errors and zero rows.
- C300 `occurrences`, shallow `inspect`, and checkpoint `validate_c300`: exact C300
  run membership before parser activation or RAW inspection. Engineering-only parser
  validation primitives retain their existing purpose; they do not grant processing
  or experiment admission authority.
- Profiling adapter: host-owned immutable authority bytes and fixed cohort checked
  before profiling, independently of principal grants. Missing authority blocks.
  Agent trace preserves denial, approval-required status and Human Review route.
  Requests cannot supply approvals, scope versions or cohort changes.
- Native contract preparation: inventory authority before output creation and pinned
  GOLD binding before RAW access. No remote job was submitted or modified.

The core denial exception carries `OUT_OF_SCOPE / AUTHORIZATION_REQUIRED`, reason,
evidence references, DENY, approval-required and Human Review. RAW retention and
acquisition routines are not changed. These denials make no claim of RAW corruption.
A frozen run uses the host's explicit identity roster; discovery cannot expand it.
Existing RAW hash validation and independent parser approvals remain in force.

## Read-only historical comparison and pending integration

Incident verified integration findings were read from the separate incident
worktree, commit `b45ec60`, §13 of
`docs/incidents/2026-10-21_source_universe_scope_control.md`.
Day 3 `c223117`, Day 4 `2eee969`, Day 5 `b9f5dc7` were inspected read only.
Their N450/N750/N500 preparation validates counts, history, provenance and holdouts,
but does not pin an approved universe. Day 5 freeze constructs conditional cohort
permission text itself; that cannot establish universe authority.

PENDING: reuse this gate in rebuilt N450 selection, N750 selection, N500
`qualify/admit/historical_gate/freeze`; upload_n450/upload_n500 and N750 upload;
all three targeted profilers; rebuilt membership tests. None exists on this main
baseline, and no historical code/data/freeze was merged. Remote notebook execution
still needs a deployable trusted authority/roster check before RAW reads. Existing
native sealing verifies historical receipts; it does not certify new scope compliance.
Post-approval evidence replay is historical evidence evaluation, not onboarding
approval. Future Agent onboarding, acquisition/quota proposals and release evaluation
need integration tests against the actual rebuilt entrypoints. They are not certified.

## Executed validation

Commands used `PYTHONPATH=src` and the existing read-only interpreter/tool installation
at `/Users/lightnino/Projects/edp-lab/.venv/bin/`.

- `python -m pytest -q tests/authorization tests/parsers/test_c300_v1.py tests/profiling tests/governance tests/lossless`:
  **104 PASS, 4 SKIPPED**, zero failures. The four skips are explicitly
  BLOCKED/PENDING integrations: rebuilt admission/freezes, historical transfer/
  profiling, remote processing and future Agent release evaluation.
- Authorization coverage includes positive synthetic evidence; outside universe;
  new Treasury; holdout; new daily data outside a frozen run; missing authority;
  manifest pin/version/inventory mismatch; explicit registration crosswalk;
  Agent self-approval/version/cohort injection; Agent denial trace; future version
  eligibility without changing the original authority. Real local admission/freeze/
  registry/reader entrypoints are tested for missing-authority enforcement.
- Broader regression command:
  `python -m pytest -q tests/authorization tests/agents tests/tool_adapters tests/corpus_invariants/test_c300_admission.py tests/governance`:
  **85 PASS, 29 FAIL, 5 SKIPPED**. This is not a green regression release.
  Failures: three Analyst tests, 22 adapter tests, four C300 admission tests.
  Existing fixtures lack host universe authority and expect successful execution,
  older malformed-request FAILED statuses, or prior packet/registry errors instead
  of the new fail-closed authority denial. Fixture migration remains pending;
  actual original-inventory positive admission cannot be certified without evidence.
- Ruff and `git diff --check` are run before commit. No RAW scan, network call,
  ingestion, upload, job execution, cohort rebuild or admission was performed.

## C300 operational effect

The active Day 2 worktree/jobs and all frozen C300 bytes remain untouched. This branch
blocks new C300 admission and processing because the required universe evidence is
missing. Its historical parser approval is not revoked or expanded, but does not
substitute for universe authority. This branch must not be promoted as an operational
replacement until the missing authority and regression fixture migration are reviewed.
The 800 legitimate external RAW objects remain retained and unauthorized for the
current experiment. Retention verification and historical cohort remediation are
outside this implementation's measured coverage.
