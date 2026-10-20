# Profiling output contract V1 — implemented §2.1 outputs

Status: implemented by `edp_lab.profiling.tools` as `PROFILING_OUTPUT_V1`.
This document describes the current §2.1 outputs and reuses, without amending, the
immutable [V1 metric contract](parsing_profiling_contract_v1.md),
[V2 freeze](parsing_profiling_freeze_v2.md) and
`metadata/profiling_conventions_v1.json`. See [usage](profiling_tools.md) and
[completion evidence](preflight_exit_checklist.md). §2.2–§2.4 are outside this scope.

Every output identifies its output-contract version and function; it must
retain the existing required run provenance: run ID, actual profiler/package/code
revision and dirty-tree/file hashes as needed, parser revision and selected profile,
resolved config and freeze reference/hash, Python patch version, DuckDB runtime,
installed dependencies and lockfile SHA-256. Inputs identify source ID, RAW path/hash,
archive member or standalone table and member hash, ordered fields and source
record/field locators. Verify RAW then member hashes before parsing. Hash mismatch
or structural failure stops affected output; preserve errors and traces.

Declare full-table or selection population, duplicate-preserving data occurrences,
separate header/metadata accounting, sampling method, actual sample size and seed
(null when inapplicable), schema fingerprint `SCHEMA_SHA256_V1` with
`RAW_HEADER_TEXT_V1`, and result fingerprints. Preserve deterministic result payloads
separately from operational timestamps for reproducible comparison. Retain failures;
never publish a failed/partial scan as a completed full scan.

Each metric carries its own value, computation mode, scope and reason when
NOT_COMPUTED. Modes are EXACT_FULL_SCAN (default), EXACT_SAMPLE (specified selection
only), APPROXIMATE (estimator and supported uncertainty), NOT_COMPUTED (no fabricated
zero). Approximation/sample results cannot prove full-population uniqueness or FDs.

Use exactly the V1 count formulas: row_count counts data occurrences including
repeats; non_null_count = row_count - null_count; null_pct = null_count / row_count;
distinct_pct = distinct_non_null_count / non_null_count. Zero denominators yield
null. unique_count counts distinct non-NULL values occurring exactly once.
Under the effective V2 scope, semantic NULL and NULL-dependent metrics remain
NOT_COMPUTED with an unresolved-source-semantics reason. This also applies to
non_null_count, distinct_non_null_count, distinct_pct and unique_count when they
depend on that interpretation. Lexical empty/whitespace/token counts must have
separate names, explicit equality/population and never masquerade as NULL metrics.
No trim, coercion, date interpretation, deduplication or inferred key is authorized.

All functions accept the same materialized `SourceTable`; they do not reopen
RAW. The shared envelope contains `output_version`, `function`, `source`, `config`,
`provenance`, `parameters`, `run_id`, `parse_status`, `errors`, `population`,
`rows_scanned` and `result_sha256`. Registered inputs carry exact frozen source,
member and parser references. Provenance includes `EDP_PROFILING_V1`, actual Git
revision/status, Python source-content hashes, runtime dependency versions and
lock hash. Hashes use canonical JSON; execution timestamps are absent from the
deterministic payload. Replay requires identical inputs, parameters and provenance.

| Function | Signature after `table` | Successful output |
| --- | --- | --- |
| `profile_table` | No further arguments | Occurrence `row_count`, `column_count`, ordered TEXT columns and whole-row literal `duplicate_summary` |
| `profile_column` | `column, *, top_limit=10, sample_size=5, sample_seed=0` | Semantic `statistics`, separate `literal_statistics`, exact TEXT ordering and `sample_selection` |
| `find_duplicates` | `columns=None, *, group_limit=20, witness_limit=3` | Tested columns, exact tuple equality, duplicate groups, rows in groups, excess rows and bounded source witnesses |
| `candidate_key_scan` | `*, composites=(), search_columns=None, max_width=1, max_combinations=256` | Singleton, supplied composite and bounded combination candidates; literal uniqueness/minimality, NULL eligibility and unapproved Business Key status |
| `schema_fingerprint` | No further arguments | `fingerprint_version`, `canonicalization_version` and structural `schema_sha256` |

Literal column measures include empty/whitespace counts, distinct/singleton text
counts, text min/max and bounded top frequencies. Top values sort by descending
frequency then exact text. Samples select occurrences by lowest SHA-256 of
seed/source/locator, with occurrence-index tie breaking; each value retains its
column and record locator. Selection reports method, seed, actual size and
population size, with EXACT_SAMPLE mode. Other literal counts use full scans.

Duplicate totals remain exact even when displayed groups or witnesses are bounded;
no rows are removed or classified as errors. Candidate minimality checks every
nonempty proper subset using literal equality. An empty population establishes no
eligible key. Under frozen unknown NULL semantics, `non_null_eligible` and
`candidate_eligible` remain NOT_COMPUTED. Mechanical uniqueness grants no semantic
key approval. The schema fingerprint uses ordered exact name/TEXT pairs and
excludes source identity, distributions and operational provenance.

On integrity or parsing failure, the envelope retains FAIL and errors, scanned
occurrence accounting remains observable, and dependent completed-table metrics
remain NOT_COMPUTED. Invalid columns/search parameters raise ValueError. The
implementation materializes one table in memory; no larger-corpus performance
claim is made.

Future C300 mechanical execution requires source admission and reviewed parser
registration. The current registered reader accepts only the frozen GOLD_V2
bindings; synthetic fixture parsing does not authorize future RAW snapshots.
C300 population, Agent adapters and later-section implementation are outside this
§2.1 contract. No frozen policy or semantic decision is changed here.
