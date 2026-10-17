# EDP Lab

Enterprise Data Platform learning lab. **Day 1: repo/environment setup, deterministic source inventory and read-only inspection only.**

## Setup (macOS/Linux)

1. Install `git`, `uv`, and Python 3.12 (uv can install Python): `uv python install 3.12`.
2. `uv sync` (creates `.venv` and `uv.lock`; commit the lockfile).
3. `uv run python -m edp_lab check-env`
4. Put original three source artifacts at the paths below **without modifying the bytes**:
   - `data/raw/sec/2013q2_form13f.zip`
   - `data/raw/nasdaq/nasdaqlisted.txt`
   - `data/raw/nasdaq/otherlisted.txt`
5. `uv run python -m edp_lab verify-raw` — compares SHA-256 to `metadata/source_inventory.csv`.
6. `uv run python -m edp_lab sql sql/raw/00_healthcheck.sql` — runs deterministic SQL using local DuckDB database `data/local/edp_lab.duckdb`.
7. `uv run pytest -q`
8. `uv run ruff check .`

Run tests without raw files: tests use temporary fixtures. `verify-raw` deliberately fails if the actual files have not been placed at declared paths.

## Git boundary

- **Tracked**: Python/SQL code, `metadata/source_inventory.csv` (verified hashes), empty templates, tests, documentation, lockfile, nonsecret configuration.
- **Not tracked**: RAW bytes, staging/vault/marts files, DuckDB database, runs/reports, `.env`, credentials, virtualenv.
- `metadata/source_inventory.csv` includes three SHA-256 hashes computed from user-supplied artifacts; relative paths are **planned project paths**, not the previous uploaded paths.
- Git alone does not prevent modifying a local RAW file; the verifier detects byte changes, and workflow policy forbids overwrites.

## Explicit Day 1 authority boundaries

See `AGENTS.md`. Agents may write boilerplate and deterministic code but **must not** infer canonical mappings, choose enterprise business keys, merge enterprise identities, decide semantic equivalence, normalize identifiers automatically, or silently repair RAW anomalies.

## SQL workflow

Use `.sql` files checked into `sql/<stage>/`; execute them with `uv run python -m edp_lab sql <file.sql>`. The starter intentionally includes only a smoke query. There are **no** Vault, dimensional, or semantic DDLs yet.

## Agents SDK (optional, off by default)

`uv sync --extra agents` installs `openai` + `openai-agents`; `OPENAI_API_KEY` is read from your local environment only. There is no live agent in the starter. Do not put secrets in repo.

## Scope notes

- SEC release (`2013 Q2`) and Nasdaq directory (`2026-10-15` snapshot) are not point-in-time aligned. Do not use 2026 directory membership to assert 2013 listing status.
- Original SEC `13F` archive has multiple TSV members with distinct grains; today only `SUBMISSION` and `INFOTABLE` are in scope for source inspection. No schema or business-key assumptions have been committed.
