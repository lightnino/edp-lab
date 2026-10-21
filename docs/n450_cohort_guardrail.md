# N450/C750 host authorization boundary

Phase A only, on `day3-authorized-n450-v1`. The four owner-specified
fingerprints were verified exactly before implementation. The original proposal,
Universe v1, historical C300, RAW, freezes and M1 remain unchanged.

`edp_lab.ingestion.n450_authorization.validate_packet` checks host-pinned roster,
qualification, C750 union and historical remote evidence bytes. It verifies the
original universe/inventory and historical sidecar using the existing gate,
450 unique identities/paths/hashes, holdout and historical exclusions, exact
unchanged C300 plus N450 union, and 450 unique exact remote evidence bindings.
`verify_local_bytes` additionally rehashes all 450 explicit local files and sizes.
Observed result: VALIDATED_NOT_AUTHORIZED, 450 N450 / 750 C750.

`authorize` is the common preflight boundary for admission, freeze, upload,
processing and remote_processing. No execution owner pin is installed. The fixed
owner-record location cannot grant authority without an independently reviewed host
pin. A request cannot supply a pin. A future installed grant must bind exact packet,
universe, action, cohort and complete ordered inputs; admission/freeze preflight
also checks current local bytes, with historical C300 hashes checked for freeze.
The admission/freeze publication integration is described below; historical
preparers/uploaders/profilers remain excluded.

The existing generic N450/C750 processing entrypoint now routes through this gate,
after universe eligibility checks. The excluded remote native notebook now raises
before imports, contract loading, Spark or RAW access. This is a deliberate remote
execution block, not certification of a deployed Databricks gate. Transfer and
processing stay denied even with a synthetic host grant until reviewed storage
protection, remote immediate hash verification and independent parser/M1 adapters
are installed. C750 processing is also explicitly unavailable. This avoids inferring
those outstanding contracts from the implementation request.

Trust boundary: reviewed host code/configuration. An actor able to replace host
pins/code is outside this boundary. Tests install synthetic pins only; no test grant
or approval record is installed in production. A positive synthetic admission
preflight mocks the local rehash (separately executed against all actual N450 files);
it does not prove real admission publication or remote behavior.

The original `remote-live.json` remains byte-for-byte SHA-256
`8b46ce38d970be771ad56bbfd1a86d8eb60438852f3e9b5fe98fa57ac10f844b`.
Its 450/450 remote hash results are historical observations, not a fresh availability
or immutability claim. No files were uploaded, copied or remotely checked here.

Validation (existing Python/pytest environment, offline):

- `PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python -m pytest -q tests/authorization`
  — 45 passed, 4 skipped (existing future integration checks).
- `verify_local_bytes(Path.cwd())` — all 450 expected local hashes/sizes verified.
- `ruff check .` and `git diff --check` — PASS.

The first focused run exposed changed denial ordering for the retained outside-universe
negative test. Universe eligibility was restored ahead of the cohort grant check;
the complete authorization suite then passed. No test was weakened.

Owner review remains required before actual admission, freeze, upload or processing.
An exact-scope execution grant, storage protection decision and separately approved
parser/processing scope are still absent. Phase B is not complete or enabled.
Phase C waits for frozen O_C300_M1; no A/B/C result, FIN replay, O_C750_M1 freeze
or M2 is claimed. This change makes no source semantic decisions.

## Admission and cohort-freeze integration (readiness only)

`python -m edp_lab.ingestion.n450_admission admit|freeze --bindings <json>
--output <destination>` supplies the two metadata publication entrypoints. Both
call the existing host-pinned authorization gate before writes. The owner record
now uses separate `scopes.admission` (N450) and `scopes.freeze` (C750), so approving
one action cannot silently grant the other. The owner pin remains `None`.

Admission publishes only to `metadata/admissions/N450_v1/`: original v3 bytes,
additive `corpus_manifest_v4.csv`, `N450.csv`, exact physical-to-registration
`bindings.json`, and a last-written `admission.json` completion marker. New
registration IDs are supplied in the reviewed owner record, validated as unused
and unique, and never inferred from names/tickers/hashes. Original physical paths
remain exact; no RAW is copied or relocated. The existing active registry and
historical Universe sidecar are not rewritten or activated for new readers.

Freeze publishes only to `metadata/freezes/C750_v1/`. It requires the completed
admission to match every recomputed byte and approved file digest, revalidates
N450 and historical C300 RAW hashes through authorization, and publishes the
admission snapshot plus original C300 roster, exact C750 roster/bindings and a
last-written `freeze.json` marker. This is a **cohort** freeze, never O_C750_M1.
The fixed independent owner record remains the authority; its host pin is external
to the published file-digest set, avoiding a circular approval-record hash.

Destinations must be exact, fresh and free of symlink ancestors. All scope,
identity, RAW-integrity, registration, historical preservation and output-byte
approval checks precede directory creation. Existing or interrupted destinations
cannot be overwritten. An I/O failure may leave an incomplete directory without
the final completion marker; that directory is blocked, never treated as success.
New publication does not broaden parser, remote, GOLD or C300 processing grants.

### Required Step 2 owner approval (after Day 2 Exit Check)

Supply an independent `OWNER_APPROVED` record at
`metadata/authorizations/n450_execution_v1.json`, followed by review/installation
of its exact SHA-256 in `OWNER_GRANT_SHA256`. No Agent-created record can activate
execution. The record must bind:

- The exact Universe ID/version/manifest digest already validated by the gate.
- All four `PINS` values (roster, qualification, C750 proposal, remote evidence).
- Separate exact scopes: `admission` / `N450` and `freeze` / `C750`, each with the
  complete ordered `bindings` expected by `authorize`. Admission uses the 450
  physical identities, original paths and hashes; freeze uses the exact 750-member
  proposal. No other action is implied.
- `registrations`: the ordered 450 entries, each with `source_identity` and a
  reviewed, unused `source_instance_id`; and an explicit UTC `admitted_at_utc`.
- `destination` and `files_sha256` for every file in each publication bundle.
  `admission_files` and `freeze_files` are read-only metadata planners for review;
  they do not establish authority or publish anything.

Owner authorization must explicitly permit registration using the proposal's
exact retained physical paths and the chosen storage protection / immutable
historical snapshot mechanism. That storage decision remains outstanding; this
code's hash checks alone are not an immutability claim. Day 2 completion and Exit
Check remain prerequisites by owner instruction. Upload/copy, parsing, M1 jobs,
remote reuse and Stability require their own later grants and integration.

Focused verification covers real entrypoint denials and temporary synthetic
positive admission/freeze publication. Positive tests use the real packet and
Universe gate, but mock RAW rehash routines as explicit sentinels; they do not
claim real C300 RAW, storage protection or remote execution coverage. Synthetic
host pins and temporary publication outputs are never installed in the worktree.

Readiness-only validation on 2026-10-21:

- `pytest -q tests/authorization/test_n450_authorization.py`: 39 passed in 84.39s.
- After tightening negative assertions to require exact denial reasons and adding
  historical RAW failure / registration collision checks:
  `pytest -q tests/authorization/test_n450_authorization.py -k 'publication_denials or historical_raw_failure or registration_collision'`:
  24 passed, 17 deselected in 46.38s. All 41 distinct tests in the updated file
  have passed across these focused runs; no broad suite or unchanged RAW scan run.
- Ruff on the two implementation modules and focused test: PASS.
- `git diff --check`: PASS.

No actual worktree admission/freeze was invoked. Universe v1, historical C300,
RAW, existing freezes and the remote verification packet remain unchanged.
