# N750 Step 8 execution evidence

Status: **completed for the approved N750 processing scope**, with Lossless 6 economic reconciliation **NOT_IMPLEMENTED** because no Treasury relationship, grain, or units have been approved. No Step 9 work or main merge was performed. Historical C750 M1/M2 outputs and frozen N750/C1500 admission files were not repointed or changed.

## Authority and source resolution

The installed `metadata/authorizations/n750_processing_v1.json` SHA-256 is `5ae18d7d2ee770cbefb3f6ad0a6b05eac87282d8e88b2c9f6422dff7c9b7b120`. The trusted `n750_step8_authorization.py` host SHA-256 is `82c78933b4ace7a0b2b8e9009e3c9ee3f6395c92cb05e3cffa2d33c60d633bad`. Independent hash checks matched both the proposal pin `0c0571e45de48ea96ebac0c6d6a28a2cf6c6ee5086558da23087014d07f05b36` and every pinned input. The authorization preflight accepted exactly 750 frozen bindings, with remote resolution confined to the exact 300-source complement of the 450 historical receipts.

The three prior RAW prefix inventories matched their retained completion receipts. The 300 missing SEC originals were sealed against the frozen SHA before upload into the new, separate `dbfs:/Volumes/workspace/edp_lab/raw/n750-step8-raw-v1-5ae18d7d2ee7` prefix. Existing objects were not overwritten. All 750 remote objects were independently downloaded and SHA-256 checked against the frozen bindings: **450 reused, 300 uploaded, 750 verified, 0 mismatches**. Verified remote bytes totaled **269,323,425**; uploaded bytes totaled **108,168,785**. The remote resolution and readback elapsed **675.667 seconds**. The immutable run receipt is [raw/completion.json](../runs/n750/step8-v1/raw/completion.json), SHA-256 `c58a1a36d99b71d79948ea5a41b82069df40d78d8797611411516de52255ac86`.

## CLEAN, M1, M2 and QUERYABLE

After remote readback, the deterministic CLEAN builder processed hash-equivalent original RAW bytes locally and sealed each source again before and after parsing. SEC retained every physical line, source framing, byte offset/length, exact original text and five lexical fields for DATA rows. The Treasury adapter retained every property QName, attributes, XML byte span, entry and property ordinal, lexical text and source hash. It checked each extracted property against the parsed XML tree and exact RAW span. M2 used only the approved Treasury property allowlists and `EXACT_DECIMAL_38_4_V1`; structural absence became an explicit `MISSING` evaluation, separate from present M1 occurrences. No numeric unit conversion, deduplication or source identity merge was performed.

Coverage: **750/750 sources COMPLETE** (745 SEC, five Treasury); **3,047,639 SEC DATA records**, **15,238,195 SEC lexical fields**, **21,616 Treasury property occurrences**, and **12,948 M2 evaluations**. M2 outcomes were **12,793 VALID** and **155 MISSING**, with zero other observed outcomes. The local CLEAN build plus full persisted Parquet readback took **45.890 seconds**. The independent reader reconstructed every SEC source byte from persisted locators, rechecked every XML property span against RAW, and checked each M2 projection/outcome. The [CLEAN completion](../runs/n750/step8-v1/clean/completion.json) SHA-256 is `a95af935e8b1bdc043e2e458a01a582130642746a4cb1b8579b922bec6560fbb`. Its `started_at_utc` field was recorded at completion by this script; use the measured `wall_seconds` for elapsed time.

This production population did not exercise real BLANK, NULL_UNRESOLVED, INVALID, SCALE_EXCEEDED or OVERFLOW numeric outcomes. The approved converter's earlier bounded synthetic checks cover those policies; this run's outcome claim is limited to the two outcomes observed here.

The four Parquet artifacts were uploaded into a separate versioned CLEAN stage and independently downloaded for SHA readback. Four new Databricks Delta tables were created and validated at **version 0**:

| Relation | Delta ID | Rows |
| --- | --- | ---: |
| `workspace.edp_lab.clean_n750_m1_sec_records_step8_v1` | `a02e488f-7be4-4b40-9b64-0585e6f6e962` | 3,052,854 including seven framing lines per source |
| `workspace.edp_lab.clean_n750_m1_treasury_properties_step8_v1` | `c818b141-23b8-4bf2-b4a5-8c2ae44a59df` | 21,616 |
| `workspace.edp_lab.clean_n750_m2_treasury_rates_step8_v1` | `abba3c2a-f7ae-43cf-ab4c-e87b933f306c` | 12,948 |
| `workspace.edp_lab.clean_n750_source_coverage_step8_v1` | `b5960f3d-c7db-43dd-9b67-be7e53a9be8c` | 750 |

For each table, independent SQL `EXCEPT ALL` comparisons between the staged Parquet and Delta version 0 returned **zero rows in both directions**. SQL checks matched full and per-source row counts, all 750 source identities and RAW hashes, M2-to-M1 lexical lineage, 12,793 present/155 missing evaluations, and exact Decimal values for every `VALID` row. The four version-pinned views `q_n750_m1_sec_records_step8_v1`, `q_n750_m1_treasury_properties_step8_v1`, `q_n750_m2_treasury_rates_step8_v1`, and `q_n750_source_coverage_step8_v1` were created in `workspace.edp_lab` and independently counted. [Delta readback](../runs/n750/step8-v1/publication/delta-readback.json) SHA-256: `a99f2ca46886c439ecbdffff24b5cb14223ea7dff741331d4ec0d974c2e4bd96`. [QUERYABLE receipt](../runs/n750/step8-v1/publication/queryable.json) SHA-256: `32f0cdb08fe6fbebc28e763783a832f73268c40254876c2debfd6b001cd3e6d8`.

The recorded SQL request/result intervals were 55.145 seconds for table creation, 91.842 seconds for Delta validation, 27.862 seconds for views and their counts, and 43.465 seconds for final coverage/lineage checks. These are elapsed local request/result intervals, not Databricks task runtime or DBU consumption. The Statement API did not expose DBUs or executor CPU. The Databricks SQL warehouse ID was `589e80595c7c8cb8`. Processing used a local lexical builder followed by Databricks Delta publication; this run does not claim that parsing executed on Databricks compute.

Execution used Python 3.12.15 and PyArrow 19.0.1. SHA-256 code references: `resolve_n750_step8_raw.py` `6cbeba5be67dd8487dbcdd49b53f544fb55a302bc18c7d9434b6c25ad0735b23`; `build_n750_step8_clean.py` `27595e36743a4553c3d601af166f838a0e5f56a7cabc8343b069e52d9b7d1835`; `publish_n750_step8.py` `8426951390f9af31d1e102ffc533771365368f20bf06dd7393c7d47143096836`; `validate_n750_step8.py` `a4e4cff6155a86e516c7345c8841660a603058fde5cfc76d11f0faafc23ed78f`; parser `n750_step8.py` `96201d86013ea1c89c34ca7220d8fdb37b2bfe1a8437456f7ef191c39a5483de`; approved converter `typed_numeric_v1.py` `ae06d39409c2542273f269356a5905553b08621546de2bda6c972b22bc50d507`.

The executed versions of the five new code files are retained under ignored `runs/n750/step8-v1/executed-code/` at those exact hashes. Subsequent import-order and explicit-subprocess-check style edits changed the working copies without rerunning RAW or CLEAN. The installed authorization host remains byte-identical to the trusted owner pin; a narrow Ruff per-file import-order exception in `pyproject.toml` preserves that SHA. Focused Step 8/M2/stability/FIN tests: **84 passed**. Full local pytest: **490 passed, 77 skipped**; repository Ruff: **PASS**. The skipped tests require host-local retained runtime inputs absent from this worktree. The ignored machine-readable Step 8 validation SHA-256 is `551821cd120f86dc2278c67cdec693e3db07da53b26d0809ce4bb3afc1d7201d`; the CLEAN staging receipt SHA-256 is `b8be581e691f821f9b15ac1bc3d38d112718196e5e2d33a0461e5265a1663d31`.

## Lossless 1–6 disposition

| Test | Status | Actual basis |
| --- | --- | --- |
| 1 — record accountability | PASS | Full per-source DATA/property counts; all 750 source outcomes COMPLETE; M2 present and missing evaluations counted separately. |
| 2 — field accountability | PASS | All 15,238,195 SEC DATA fields and 21,616 present Treasury properties retained. |
| 3 — value fidelity | PASS | Exact SEC byte reconstruction, Treasury RAW span readback, Decimal outcome/value checks, and bidirectional full Delta multiset comparison. |
| 4 — RAW/hash immutability | PASS | Frozen hashes matched 750 downloaded remote objects and sealed local originals; no existing RAW overwrite. |
| 5 — lineage and reconstructability | PASS | Per-source identity/hash/count joins, exact byte locators and M2-to-M1 present-property lineage checked. |
| 6 — numeric/economic reconciliation | NOT_IMPLEMENTED | No approved Treasury relationship, grain and units. SEC Daily Master is a filing index and supplies no modeled financial measure. No economic PASS is claimed. |

The full machine-readable [validation](../runs/n750/step8-v1/validation.json) records these dispositions and output IDs. The source of truth for individual remote SHA checks, SQL requests/responses and persisted output hashes remains in the ignored `runs/n750/step8-v1/` directory. No RAW bytes, run results or local database are tracked for Git publication.

Before the Step 9 handoff, a fresh read-only check confirmed all four live Delta IDs, latest versions (all 0), version-0 row counts, four pinned view definitions and view counts. The ignored `runs/n750/step8-v1/live-verify-v1.json` evidence SHA-256 is `7cbefeb505f0dd98bfee911d47a234522c8d5158b86f4104c0f6867094d80e7f`; the verifier source SHA-256 is `98861f9d047f82d060062576ce89b6999dec9b29329100d98f31788e868a92fc`.
