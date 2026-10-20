# EDP Lab

Enterprise Data Platform learning lab. Source Identity, GOLD_V2 registration, snapshot-scoped Parsing/Profiling Freeze V2 and Governance Policy are approved. The five deterministic profiling functions are implemented and verified on GOLD_V2. See [profiling completion evidence](docs/preflight_exit_checklist.md).

## Setup (macOS/Linux)

1. Install `git`, `uv`, and Python 3.12 (uv can install Python): `uv python install 3.12`.
2. `uv sync` (creates `.venv` and `uv.lock`; commit the lockfile).
3. `uv run python -m edp_lab check-env`
4. Put the four admitted source artifacts at the paths below **without modifying the bytes**:
   - `data/raw/sec/2013q2_form13f.zip`
   - `data/raw/nasdaq/nasdaqlisted.txt`
   - `data/raw/nasdaq/otherlisted.txt`
   - `data/raw/sec/2010q2_fsds.zip`
5. `uv run python -m edp_lab verify-raw` — verifies all admitted physical RAW SHA-256 values and archive members against `metadata/corpus_manifest.csv` and `metadata/gold_set_logical_tables_v2.csv`. This is equivalent to `uv run python -m edp_lab.ingestion.source_identity --check-raw`; the old `--inventory` CLI argument has been retired.
6. `uv run python -m edp_lab sql sql/raw/00_healthcheck.sql` — runs deterministic SQL using local DuckDB database `data/local/edp_lab.duckdb`.
7. `uv run pytest -q`
8. `uv run ruff check .`

Run tests without raw files: tests use temporary fixtures. `verify-raw` deliberately fails if the actual files have not been placed at declared paths.

## Parsing and profiling status

The immutable [V1 definitions](docs/parsing_profiling_contract_v1.md) and
[V2 snapshot-scoped freeze](docs/parsing_profiling_freeze_v2.md) apply to all
13 registered GOLD_V2 logical tables. DEC-000001–DEC-000005 record the approved
lexical scope. Source NULL semantics remain unresolved; profiles retain their
PROVISIONAL labels. The V2 freeze is a review record, not runtime activation.
The implemented [profiling tools](docs/profiling_tools.md) share the frozen parser
configuration and verify source hashes before parsing. GOLD_V2 execution covers
13 tables, 304,508 data occurrences and 149 column profiles, with no hash or parse
failures. Outputs are deterministic, versioned JSON with source provenance.
Semantic NULL-dependent metrics and candidate-key eligibility remain NOT_COMPUTED.
Mechanical results grant no semantic approval; see the
[output contract](docs/profiling_output_contract.md).

Offline checks use the installed environment:

```bash
.venv/bin/python -m edp_lab.profiling.conventions
.venv/bin/python -m edp_lab.profiling.conventions --check-raw
```

The second command requires the four local gitignored RAW artifacts.

## Git boundary

- **Tracked**: Python/SQL code, the canonical `metadata/corpus_manifest.csv` (admitted RAW hashes), semantic `metadata/source_inventory.csv`, `metadata/decision_log.csv`, cohort registries, tests, documentation, lockfile, nonsecret configuration.
- **Not tracked**: RAW bytes, staging/vault/marts files, DuckDB database, runs/reports, `.env`, credentials, virtualenv.
- `metadata/source_inventory.csv` holds provisional source-level semantic observations; it is **not** a SHA-256 inventory. The canonical twelve-column `metadata/corpus_manifest.csv` contains source identities, local RAW paths, and recorded SHA-256 values. `docs/decision_log.md` documents the append-only decision log and links frozen historical engineering evidence.
- Git alone does not prevent modifying a local RAW file; the verifier detects byte changes, and workflow policy forbids overwrites.

## Authority boundaries

See `AGENTS.md`. Agents may write boilerplate and deterministic code but **must not** infer canonical mappings, choose enterprise business keys, merge enterprise identities, decide semantic equivalence, normalize identifiers automatically, or silently repair RAW anomalies.

## SQL workflow

Use `.sql` files checked into `sql/<stage>/`; execute them with `uv run python -m edp_lab sql <file.sql>`. The starter intentionally includes only a smoke query. There are **no** Vault, dimensional, or semantic DDLs yet.

## Agents SDK (optional, off by default)

`uv sync --extra agents` installs `openai` + `openai-agents`; `OPENAI_API_KEY` is read from your local environment only. There is no live agent in the starter. Do not put secrets in repo.

## Scope notes

- SEC release (`2013 Q2`) and Nasdaq directory (`2026-10-15` snapshot) are not point-in-time aligned. Do not use 2026 directory membership to assert 2013 listing status.
- `GOLD_V2` registers 4 physical source instances and 13 logical tables (seven SEC 13F, two Nasdaq, four SEC FSDS). Deep profiling has executed on all 13 within the frozen lexical scope. No enterprise business-key or mapping decisions have been committed.
- C300 execution remains subject to future source admission and reviewed parser registration. The current registered reader accepts only frozen GOLD_V2 bindings; their approval does not transfer to future sources. Regression coverage is implemented and accepted; see the [regression review](docs/day2_section_2_2_regression_review.md). C300 population and later functionality remain deferred.
