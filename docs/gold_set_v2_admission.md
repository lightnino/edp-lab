# GOLD_V2 — Expanded Gold Set Source Registration

## Why GOLD_V2 exists

**Primary reason: preserve the frozen evidence required by the Evaluation Contract V1.** The contract's experimental-integrity principles require stable source identity, immutable RAW hashes, frozen historical cohort membership, and preservation of historical results. In particular, SC2 (No Cohort Replacement), SC3 (Stable Source Identity), SC4 (Cross-Cohort RAW Immutability), and SC6 (Historical Runs and Outputs Remain Available) motivate creating a **new** Gold Set snapshot instead of changing `GOLD_V1`. The contract directly defines nested **scale** cohorts (C300/C750/...), not an obligatory Gold Set V2. Applying the same immutability principles to Gold Set snapshots is a deliberate, compatible design decision; GOLD_V2 is not claimed to be a new requirement explicitly named in the contract.

The expanded reference population comprises **13 logical tables** across **four physical source instances**. The desired number of logical tables is not the rationale for preserving a separate frozen cohort version.

## Preserved historical baseline

- `GOLD_V1` remains **exactly** `SRC000001, SRC000002, SRC000003`.
- Do not change `metadata/cohorts/GOLD_V1.csv`, `docs/gold_set_baseline.md`, or the original three corpus-manifest rows.
- The original `docs/evaluation_contract.md` V1 Git blob is `bb61387a9119c5b80639e6508eed1a1d751bdb6c`.
- GOLD_V1 admitted three independent physical artifacts; it previously had four preliminary logical-table profiles, not four physical source instances.

## Expanded reference snapshot

`GOLD_V2 = GOLD_V1 ∪ {SRC000004}`

| Source instance | Physical artifact | Introduced cohort | SHA-256 |
|---|---|---|---|
| SRC000001 | `data/raw/sec/2013q2_form13f.zip` | GOLD_V1 | `569d56e978f7dee3775e544a1e46019389e22adcf482386fcfaba51ceb6c7e84` |
| SRC000002 | `data/raw/nasdaq/nasdaqlisted.txt` | GOLD_V1 | `1d3656d26cfddd35363ce8022d50cbb5342ae2b1cfebee74f3c3b168b0f0f808` |
| SRC000003 | `data/raw/nasdaq/otherlisted.txt` | GOLD_V1 | `7f099cd61db347f2199251dfe45dc132ffc8c75bd68a91471c30e217e4265d3d` |
| SRC000004 | `data/raw/sec/2010q2_fsds.zip` | GOLD_V2 | `25f416b020fd3e62a67dbf8c6522c9f239e716099b61cf5d05a59a91ffdef1f1` |

- `SRC000004` is one physical SEC Financial Statement archive. Its `sub.txt`, `num.txt`, `tag.txt`, and `pre.txt` members are four **logical tables**, not four separate physical instances.
- The 2013 Q2 SEC 13F archive has seven TSV logical tables; Nasdaq has two standalone text logical tables. Total = **7 + 2 + 4 = 13**.
- Physical/artifact to logical-member lineage and documentation references are recorded in `metadata/gold_set_logical_tables_v2.csv`; this registry is a **scope declaration**, not completed profiling or approved business grain.
- SEC 13F `FORM13F_metadata.json`/`FORM13F_readme.htm` and SEC FSDS `readme.htm` are retained inside their immutable archives as supporting source documentation, not additional business tables.
- For `SRC000004`, the SHA-256 and successful `unzip -t` for all five archive members were provided by the local operator on 2026-10-19 (Singapore local date). Those user-run checks are the provenance of this registration; GitHub Actions cannot independently validate untracked local RAW files.

## Identity, semantics and evaluation boundaries

- `source_instance_id` identifies a **physical delivery/source instance**, not an issuer, security, filing or other enterprise business entity.
- Source files are intentionally excluded from Git; `data/raw/**` is gitignored. This PR must not commit RAW bytes.
- `metadata/corpus_manifest.csv` retains its pinned twelve-column schema, including the stable `introduced_cohort` and `admitted_at_utc` provenance fields. No scheduling fields are required, and no frozen historical manifest record or parser/verifier contract is rewritten.
- `ground_truth_available = FALSE`: this is not an adjudicated semantic truth set.
- Deeper profiling, parser fidelity, business grain validation, fingerprints, canonical mappings, and C300 admission remain **not yet implemented/not yet validated**.
- These four physical instances are not interchangeable with C300's 300 required source instances. No C300 claim or membership is created.

## Verification and limitations

- CI checks roster nesting, unique source IDs, unchanged GOLD_V1 records, matching source hashes and thirteen-table registration **without needing private local RAW bytes**.
- On the original Mac, after checking out this branch (or once merged), run `uv run python -m edp_lab.ingestion.gold_set verify` to recheck the old GOLD_V1 physical byte baseline. Separately run `shasum -a 256 data/raw/sec/2010q2_fsds.zip` and compare against the manifest's SRC000004 SHA-256.
- Day 2 Preflight CLI repair now routes `uv run python -m edp_lab verify-raw` through the canonical source-identity validator, which reads `corpus_manifest.csv` and the logical-table registry; `source_inventory.csv` remains a semantic inventory. The frozen admission records and original GOLD_V2 registration are unchanged.
- Do not run `gold_set init`; the original cohort is already frozen.
- Source registration does **not** authorize source-to-enterprise identity mapping, business key selection, or automatic cleaning. Such decisions require independently supported review and approval.
