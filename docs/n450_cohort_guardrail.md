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
It does not publish an admission or freeze. No production executors are added in
this phase; historical preparers/uploaders/profilers remain excluded.

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
