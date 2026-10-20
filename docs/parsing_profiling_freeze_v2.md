# §1.4 Parsing and Profiling Conventions — configuration freeze V2

Human acceptance is complete for D1–D5 as supplied in the final closeout
instruction. DEC-000001 through DEC-000005 in
[the append-only decision log](../metadata/decision_log.csv) record that authority.
The reviewer identity and approval timestamp were not supplied and remain unknown;
recording time is not approval time. Local tests support implementation fidelity,
not the existence of human authority or verified source semantics.

[The versioned freeze record](../metadata/parsing_profiling_freeze_v2.json)
contains the exact effective configuration for all 13 registered GOLD_V2 logical
tables: source IDs, RAW paths and parent SHA-256, uncompressed member SHA-256,
ordered headers, profile bindings, full resolved dialect options and existing
footer expectations. These are copied unchanged from the preserved
[V2 candidate](../metadata/parser_fidelity_v2_candidate.json), whose SHA-256 is
pinned in the freeze. The three effective dialects retain their
`*_V2_CANDIDATE` IDs; renaming is unnecessary for this configuration freeze.
The JSON is a review record, not a new executable loader or runtime activation.
V1 configuration, contract and execution remain immutable. Candidate and evidence
history remain unchanged; their earlier provisional/open review statements are
historical and superseded only for D1–D5 by this closeout.

## Approved boundary

D1 preserves all literal missing-value spellings without claiming source NULL
semantics. D2 preserves quotes and escapes literally, with no automatic unquoting;
new evidence or cases may justify a separately reviewed version. D3 preserves
ALL_TEXT, exact identifiers, padding, signs, precision, case and date spelling.
D4 accepts strict structural/fidelity validation and existing footer accounting
and traceability. Footer metadata is incidental; no further footer engineering
is included. D5 accepts only the two registered Nasdaq snapshots, SRC000002 and
SRC000003, without a universal encoding, dialect or source-format declaration.

This is **snapshot-scoped lexical approval**, not full semantic `RAW_VERIFIED`.
All embedded profiles remain `PROVISIONAL`; no profile is promoted. Successful
strict decoding, exact hash/header/width checks and lexical preservation do not
resolve source intent. No business key, issuer/security/listing equivalence,
deduplication, date alignment, amendment selection or reconciliation is approved.

## Code and runtime provenance

The freeze identifies base Git revision
`71d4ba15a603b9c9d90b3998f7db88ec658fec26` plus SHA-256 of the actual parser,
evidence, conventions and source-identity code and relevant metadata/lockfile.
The new evidence/fidelity modules are uncommitted working-tree additions; the
base SHA alone does not identify their code. Publishing must retain these exact
contents or produce a reviewed new freeze. Future executions must capture their
actual Git revision and dirty-tree/file-hash evidence, never substitute this
base SHA for subsequently committed code.

The local environment is Python 3.12.15 and DuckDB 1.5.6. The pinned lockfile
SHA-256 is `62a95abca6cf980c2f68d97fa34fdcdf4330ab1da49bf01e8bed6b36617a1803`.
Actual installed versions must be captured again for each future run; a lockfile
alone does not prove the runtime environment.

## Future baseline requirements — specification only

The immutable [V1 metric contract](parsing_profiling_contract_v1.md) supplies
formulas, zero-denominator behavior and schema fingerprint algorithms. Row count
counts data occurrences, preserving duplicates; headers and metadata are separately
accounted. `unique_count` counts distinct non-NULL values occurring exactly once,
not distinctness or proof of a business key. Literal empty-string, whitespace-only
and candidate-token occurrence counts are lexical measures, never NULL statistics.
`null_count` and `null_pct` remain `NOT_COMPUTED` with an unresolved-source-semantics
reason. NULL-dependent non-null/distinct/unique metrics must likewise remain
`NOT_COMPUTED` where they require that unresolved interpretation; separately named
literal-text metrics must declare their population and equality rules.

Every future reported metric must carry its own computation mode:

- `EXACT_FULL_SCAN`: exact over all eligible data occurrences.
- `EXACT_SAMPLE`: exact only within a specified selection; record method, actual
  sample size and seed when applicable.
- `APPROXIMATE`: record estimator, scope and supported uncertainty/error information;
  never use it as uniqueness or functional-dependency proof.
- `NOT_COMPUTED`: provide the reason; do not substitute zero.

Full scan is the default. Every future output must retain actual profiler/package
version or Git revision, parser code revision and selected profile/version, exact
resolved parser configuration and freeze reference/hash, Python patch version,
DuckDB runtime version, installed dependency versions and lockfile SHA-256,
source instance/path/RAW and member hashes/logical table, declared population and
metadata accounting, sampling method/size/seed (null if inapplicable),
`SCHEMA_SHA256_V1`, `RAW_HEADER_TEXT_V1`, run ID, errors/traces, result fingerprints
and record/field source locators sufficient for reproducible traceability.
Verify all RAW hashes before reading members and member hashes before parsing;
changed inputs require review, never fallback or silent acceptance.

These requirements are specified for future implementation. Production profiling
functions, baseline generation, runtime integration and semantic NULL interpretation
remain outside this closeout. No profiler release is claimed.

## Evidence and limitations

The [evidence review](parser_evidence_review.md),
[historical proposal](parser_config_v2_proposal.md), and
[candidate validation report](parser_fidelity_validation.md) retain source-document
and literal-record witnesses, strict validation behavior and prior local outcomes.
Nasdaq authoritative serialization documentation is unavailable locally; ASCII-only
snapshots cannot establish all encoding behavior. Quotes may have exporter intent
that remains unverified. The documented non-nullable but empty `pre.plabel` at
SRC000004 / pre.txt line 57071 remains preserved and flagged. Footer date spelling
is preserved without timezone or timestamp conversion. No changed/future snapshot
inherits approval automatically. No further footer investigation, transformations,
network calls or profiling baselines are authorized here.

## Closeout verification

Offline commands used the existing `.venv` directly; no dependency sync occurred.

| Command | Outcome |
| --- | --- |
| `.venv/bin/python -m edp_lab verify-raw` | Exit 0; all 4 RAW instances and archive members PASS; 13 registered tables |
| `.venv/bin/python -m edp_lab.profiling.parser_fidelity` | Exit 0; 13/13 candidate validations PASS; INACTIVE, profiles PROVISIONAL |
| `.venv/bin/python -m edp_lab.profiling.conventions --check-raw` | Exit 0; contract/bindings and 13/13 structural probes PASS |
| `.venv/bin/python -m pytest -q` | Final exit 0; 83 passed in 0.09s |
| `.venv/bin/ruff check .` | Exit 0; All checks passed! |
| `git diff --check` plus untracked-file `git diff --no-index --check` | Exit 0; no whitespace diagnostics |

The first closeout test run had 82 passes and one failure: the preflight test
required a header-only decision log. That obsolete assertion was updated to
validate the stable schema, record widths, unique decision IDs, allowed statuses,
UTC recording suffix and evidence references. The final suite passed. No parser
implementation was changed during closeout. Freeze/candidate equality, all pinned
file hashes, decision-log schema and immutable tracked V1 files were also checked.
