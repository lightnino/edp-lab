# EDP Lab

**Independent, experimental Enterprise Data Platform preflight lab** built with public financial-data sources and Databricks. It explores whether agent-assisted workflows can take data through **RAW → CLEAN → QUERYABLE** while keeping provenance, correctness evidence, source authority, and historical compatibility explicit.

This is a research/prototype repository, **not a production platform**, an institutional data model, or a benchmark proving throughput for an enterprise team. It is designed around public-source experiments; publication of the complete repository and its history still requires separate privacy and secret review.

## What it tests

| Capability | Experiment |
| --- | --- |
| **Source universe / acquisition** | Discover physical sources, inventory and fingerprint them, admit approved additions, record holdouts, preserve immutable RAW identity, and verify provenance. |
| **Additive evolution** | Extend a frozen source/model baseline without silently modifying previously accepted results; use pinned snapshots and regression/stability checks. |
| **Transformation validation** | Test RAW → CLEAN → QUERYABLE with bounded lossless recovery, schema/lexical fidelity, source traceability, and independently reviewable freeze evidence. |
| **Modelling** | Evaluate source-specific 3NF/normalized and Data Vault Hub/Link/Satellite approaches without claiming that mechanical key candidates establish business equivalence. |
| **Controlled agents** | Separate routine technical execution from semantic decisions and scope expansion, with limited authority, audit trails, and fail-closed recovery when remote outcomes are uncertain. |

## Progress and current limits

**Snapshot: 26 October 2026.** These are separate milestones; inventory, processed results, prototypes and pending work should not be conflated.

- **Source universe:** 3,821 physical source members in the published inventory, including 41 held out; the approved 2,000-source baseline is preserved. The count is *inventory membership*, not 3,821 fully processed sources. See [Day 7 closeout / PR #80](https://github.com/lightnino/edp-lab/pull/80).
- **Incremental processing:** Day 5 concluded with a signed, independently checked live Databricks result freeze for the 2,000-source composition. The recorded combined result covers 321,188,377 source occurrences; it retained previous results while adding the final 500 sources. See [Day 5 closeout](reports/day5/c2000_live_closeout_20261024.md).
- **Live runner / autonomy:** Day 7 Universe publication and protected Runner deployment were independently verified and PR #80 merged. **Autonomous C3000 execution was not authorized or completed**; selected-source handoff/admission remains a separate gate.
- **Vault exploration:** Approved source-scoped modelling decisions and an eight-table, 127-row *bounded historical prototype* demonstrate parts of the Hub/Link/Satellite design. **Full Vault integration is still unfinished**; the live V3 path has an unresolved lexical-consistency failure and no V9 final freeze. See [Vault prototype](reports/day6_vault_prototype_evidence.md), [Contract V1](docs/vault_load_contract_v1.md), and [PR #75](https://github.com/lightnino/edp-lab/pull/75).
- **Business semantics:** Enterprise-wide canonical positions, exposures, metrics, entitlements for consumption and measurable downstream business outcomes have **not** been implemented or validated.

## What the experiments surfaced

1. **Exact source identity matters.** File/member case, archive-member naming, lexical ordering and occurrence-level lineage can break integration even after local tests pass.
2. **Write authority and semantic authority differ.** An agent may be authorized to perform bounded technical work without being authorized to broaden the approved universe or decide canonical business equivalence.
3. **Recovery must match the failure.** Platform permissions, source-contract mismatches, semantic decisions and uncertain writes need different handling. Additional safeguards can themselves create operational overhead.

For root-cause detail and unresolved corrections, see the [incident register](docs/incidents/README.md). An incident report is evidence of an observed problem, not proof of damage or a general platform failure.

## Project navigation

- [Agent rules and routing](AGENTS.md) · [Document ownership registry](docs/README.md)
- [Lifecycle specifications](docs/workflows/README.md) · [Canonical contracts](docs/contracts/README.md)
- [Historical freezes and approvals](metadata/freezes/) · [Incident register](docs/incidents/README.md)
- [Day 5 accepted closeout](reports/day5/c2000_live_closeout_20261024.md) · [Day 7 deployed milestone](https://github.com/lightnino/edp-lab/pull/80) · [Day 6 outstanding integration](https://github.com/lightnino/edp-lab/pull/75)

**Evidence policy:** Acceptance requires the relevant exact source manifests, version pins, signed live receipts and scope-specific reviews. Local CI alone is not a remote deployment or business-semantic acceptance result.

## Local starter setup (macOS/Linux)

This is the original lightweight profiling/RAW verification setup, **not** a one-command recreation of all later protected Databricks runs. For authoritative lifecycle procedures and acceptance records, follow the linked specs and frozen receipts.

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

## Historical parsing and profiling baseline

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

## Starter SQL workflow

Use `.sql` files checked into `sql/<stage>/`; execute them with `uv run python -m edp_lab sql <file.sql>`. The starter SQL path contains a smoke query; later model/Vault experiments and Databricks operations have separate contracts, source code, evidence, and acceptance gates. Do not infer that the starter reproduces them.

## Agents SDK (optional, off by default)

`uv sync --extra agents` installs `openai` + `openai-agents`; `OPENAI_API_KEY` is read from your local environment only. The starter does not provision a live agent; later agent-controlled execution is implemented separately. Do not put secrets in repo.

## Scope notes

- SEC release (`2013 Q2`) and Nasdaq directory (`2026-10-15` snapshot) are not point-in-time aligned. Do not use 2026 directory membership to assert 2013 listing status.
- `GOLD_V2` registers 4 physical source instances and 13 logical tables (seven SEC 13F, two Nasdaq, four SEC FSDS). Deep profiling has executed on all 13 within the frozen lexical scope. No enterprise business-key or mapping decisions have been committed.
- C300 execution remains subject to future source admission and reviewed parser registration. The current registered reader accepts only frozen GOLD_V2 bindings; their approval does not transfer to future sources. Regression coverage is implemented and accepted; see the [regression review](docs/day2_section_2_2_regression_review.md). This paragraph describes the historical Day 2 starter contract, not the current program status; consult the later frozen evidence and PRs above.
