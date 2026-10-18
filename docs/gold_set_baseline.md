# Gold Set RAW Baseline

**Cohort:** `GOLD_V1`
**Admitted at (UTC):** `2026-10-18T05:11:35Z`
**Source instances:** `3` immutable physical RAW artifacts
**Inspected logical datasets:** `4` (SEC SUBMISSION, SEC INFOTABLE, and two Nasdaq directories)
**Evaluation contract version:** `V1` (pinned to the committed Git blob below)
**Evaluation contract Git blob SHA:** `bb61387a9119c5b80639e6508eed1a1d751bdb6c`

| Source instance | RAW path | SHA-256 |
|---|---|---|
| `SRC000001` | `data/raw/sec/2013q2_form13f.zip` | `569d56e978f7dee3775e544a1e46019389e22adcf482386fcfaba51ceb6c7e84` |
| `SRC000002` | `data/raw/nasdaq/nasdaqlisted.txt` | `1d3656d26cfddd35363ce8022d50cbb5342ae2b1cfebee74f3c3b168b0f0f808` |
| `SRC000003` | `data/raw/nasdaq/otherlisted.txt` | `7f099cd61db347f2199251dfe45dc132ffc8c75bd68a91471c30e217e4265d3d` |

## Scope and evidence

- Original RAW file bytes were hashed read-only at admission and must remain unchanged.
- Cohort membership is frozen in `metadata/cohorts/GOLD_V1.csv`; existing source IDs are never reassigned.
- The archive is one physical source instance despite containing multiple logical tables.
- `ground_truth_available=FALSE` means there are no independently adjudicated semantic truth labels yet; manual observations are not canonical ground truth.
- Schema fingerprints, business-key decisions, entity equivalence and integrated outputs are not established.
- This baseline proves membership and RAW immutability evidence, NOT the full Lossless 1–6 or Stability A/B/C tests.
- C300 has not been created; no scaled regression comparison exists at this stage.

## Verification

Run `uv run python -m edp_lab.ingestion.gold_set verify` from repository root.
Re-running `verify` must return the same PASS results while preserving all RAW bytes.
