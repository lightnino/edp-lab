# EDP Lab

Enterprise Data Platform learning lab. Day 1 source registration is frozen; Day 2 deterministic profiling and agent tooling remain in development.

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

## Day 2 Preflight §1.4 — Parsing and profiling conventions

The V1 **definitions and provisional GOLD_V2 parser bindings** are committed in
`metadata/profiling_conventions_v1.json`, documented at
`docs/parsing_profiling_contract_v1.md`. Before generating an official
profiling baseline, inspect the configuration and run:

```bash
uv run python -m edp_lab.profiling.conventions
uv run python -m edp_lab.profiling.conventions --check-raw
```

The second command needs the four local gitignored RAW artifacts. A parser
probe PASS checks byte identity, UTF-8 decoding, record widths, headers and
footer accountability; it does **not** automatically approve provisional
NULL/quote/date semantics. The production profiler is still unimplemented.

## Git boundary

- **Tracked**: Python/SQL code, the canonical `metadata/corpus_manifest.csv` (admitted RAW hashes), semantic `metadata/source_inventory.csv`, `metadata/decision_log.csv`, cohort registries, tests, documentation, lockfile, nonsecret configuration.
- **Not tracked**: RAW bytes, staging/vault/marts files, DuckDB database, runs/reports, `.env`, credentials, virtualenv.
- `metadata/source_inventory.csv` holds provisional source-level semantic observations; it is **not** a SHA-256 inventory. The canonical twelve-column `metadata/corpus_manifest.csv` contains source identities, local RAW paths, and recorded SHA-256 values. `docs/decision_log.md` documents the empty, append-only decision log.
- Git alone does not prevent modifying a local RAW file; the verifier detects byte changes, and workflow policy forbids overwrites.

## Explicit Day 1 authority boundaries

See `AGENTS.md`. Agents may write boilerplate and deterministic code but **must not** infer canonical mappings, choose enterprise business keys, merge enterprise identities, decide semantic equivalence, normalize identifiers automatically, or silently repair RAW anomalies.

## SQL workflow

Use `.sql` files checked into `sql/<stage>/`; execute them with `uv run python -m edp_lab sql <file.sql>`. The starter intentionally includes only a smoke query. There are **no** Vault, dimensional, or semantic DDLs yet.

## Agents SDK (optional, off by default)

`uv sync --extra agents` installs `openai` + `openai-agents`; `OPENAI_API_KEY` is read from your local environment only. There is no live agent in the starter. Do not put secrets in repo.

## Scope notes

- SEC release (`2013 Q2`) and Nasdaq directory (`2026-10-15` snapshot) are not point-in-time aligned. Do not use 2026 directory membership to assert 2013 listing status.
- `GOLD_V2` registers 4 physical source instances and 13 logical tables (seven SEC 13F, two Nasdaq, four SEC FSDS). Four logical tables have preliminary profiles; deep profiling for all 13 is not yet complete. No enterprise business-key or mapping decisions have been committed.
