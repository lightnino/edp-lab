# EDP Lab Agent Rules — Day 1 (Binding)

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
