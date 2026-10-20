# EDP Lab Agent Rules (Binding)

## May do
- Create/organize repo folders, files, packaging, docs and Git/CI workflows.
- Write deterministic, read-only file inventory, hash checks, column listing, mechanical loaders and tests.
- Run reproducible scripts and report exact output/failures.
- Propose semantic decisions **as questions**, without executing them.

## May NOT do (until explicit human-approved later-phase policy)
- Infer issuer/security/listing canonical mappings or identifiers.
- Choose enterprise business keys or entity merge/split rules.
- Declare two source identifiers semantically equivalent based on names/tickers.
- Design population-level deduplication, transformations, reconciliation tolerances, or sector classifications.
- Mutate, overwrite, auto-correct, or drop RAW rows/files.
- Silently select a 13F amendment as authoritative, or align historical reporting dates without evidence.
- Make network/API calls, including OpenAI API, without direct instruction; do not spend API credits.
- Commit RAW bytes, credentials, `.env`, results or DuckDB local database.

## Review gates
- Before any mapping, identity resolution, canonical merge, business key, or nontrivial data transformation: STOP and request human review with input evidence, alternatives and consequences.
- Every output must preserve reproducible source references. Unknowns are recorded, not guessed.
- Verify source hashes before ingesting; do not process changed inputs silently.

## Current approved scope
- Source Identity and GOLD_V2 registration are approved; see `docs/source_instance_identity.md` and `docs/gold_set_v2_admission.md`.
- Snapshot-scoped lexical parsing is approved only as specified in `docs/parsing_profiling_freeze_v2.md` and DEC-000001–DEC-000005. The profiling functions use that scope; source NULL semantics remain unresolved.
- `docs/ownership_approval_boundaries.md` and Finding Schema v1 are approved governance policy. Mechanical validation never implies semantic approval.
- Deterministic execution within an explicitly approved rule/version/snapshot scope does not need repeated per-record review. New semantic decisions still require the review gates above.
- The five deterministic profiling functions are implemented; see `docs/profiling_tools.md` and `docs/profiling_output_contract.md`. GOLD_V2 execution covers 13 tables, 304,508 occurrences and 149 column profiles, with semantic NULL-dependent metrics and candidate-key eligibility NOT_COMPUTED.
- C300 is not created; C300 execution requires future admission and reviewed parser registration. Semantic integration remains unimplemented. Regression coverage is implemented and accepted; later functionality remains deferred. Historical phase labels in frozen documents describe their original scope.
