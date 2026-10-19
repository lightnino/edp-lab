# Day 2 §1.4 — Parsing and Profiling Conventions V1

## Authority and status

The authoritative, versioned convention file is
`metadata/profiling_conventions_v1.json`. It covers all thirteen registered
GOLD_V2 logical tables and is frozen as **the V1 contract**, not a completed
Profiler or approved parsed-data baseline.

- **FROZEN NOW:** statistic definitions, exactness classes, default full-scan
  scope, schema-fingerprint algorithm, fail-closed parsing rules, config field
  structure, parser binding IDs, lockfile/version evidence requirements.
- **PROVISIONAL UNTIL LOCAL RAW CHECK:** delimiter, UTF-8 encoding, disabled
  quote/escape processing, header treatment, explicit missing-value tokens,
  footer handling and full-row fidelity for each source-family profile.
- **NOT IMPLEMENTED:** production profiling functions and Agent tool adapters.
  `PROFILE_CONTRACT_V1` is the convention version, **not** an assertion that
  Profiler 0.1.0 has been released.
- No enterprise Business Key, canonical transformation, source-to-source
  identity mapping or data value coercion is authorized by this contract.

## Required run provenance

Every future baseline or profiler output must record:

| Field | Required meaning |
|---|---|
| `profiler_version` | Actual implemented profiler/package version or Git SHA; never just the contract label |
| `parser_version_or_code_revision` | Parser implementation Git commit and the selected parser profile/version |
| `duckdb_version` | Actual runtime `duckdb.__version__`; compare with currently locked 1.5.6 |
| `dependency_versions` | Installed dependency versions and SHA-256 of `uv.lock` at execution |
| `parser_config` | Exact effective resolved profile, not merely a profile ID |
| `profiling_scope` | Full logical table or explicit row/sample subset, including data-vs-metadata record treatment |
| `sampling_method` | FULL_SCAN by default; otherwise exact documented selection |
| `sampling_seed_if_applicable` | Must be present for seeded sampling; NULL for full scan or nonrandom selection |
| `fingerprint_version` | `SCHEMA_SHA256_V1` |
| `canonicalization_version` | `RAW_HEADER_TEXT_V1` |
| `source_instance_id`, `raw_sha256`, `logical_table` | Immutable source identity and exact member |
| `run_id` | Unique reproducible run reference; retain errors, traces, scope and result fingerprints |

Use `uv sync --frozen` to avoid accidentally changing locked dependency
versions while verifying a frozen baseline. Python runtime must match the
project's 3.12 constraint; the exact patch version is captured at run time.

## Conservative source parsing policy

Three **provisional** profiles are bound to the 13 GOLD_V2 logical tables:

- `SEC_13F_TSV_V1`: 7 archive members, TAB-delimited candidate.
- `SEC_FSDS_TSV_V1`: 4 archive members, TAB-delimited candidate.
- `NASDAQ_PIPE_V1`: 2 standalone files, pipe-delimited candidate; trailing
  `File Creation Time:` line must be **accounted for**, not silently dropped.

The initial candidate is UTF-8, header from first source row, no quote/escape
interpretation, ALL_TEXT columns, no guessed date/number coercion, and no
source-specific NULL token substitution. `""`, literal `NULL` and SQL NULL
are distinct. The candidate does **not** assert the real sources lack meaningful
quote/escape or missing-value conventions. Any actual evidence against a
candidate requires review and a versioned config correction **before**
baselines are generated.

The file defines `delimiter`, `has_header`, `quote`, `escape`,
`encoding`, `null_tokens`, `column_names`, `column_types`,
`date_formats`, `timestamp_formats`, `json_format`, `json_max_depth`,
`error_handling`, and `metadata_record_policy`. JSON options are null
because the selected **logical tables** are tabular text, not JSON documents.
If a later source really is JSON, add a reviewed versioned JSON-specific
profile; do not apply an undocumented fallback.

`FAIL_CLOSED` means decoding errors, invalid row widths, duplicate/empty
headers, and unexpected trailing data stop the parser. No auto-renaming,
case folding, trimming, casts, silent row skipping or automatic `DISTINCT`.

### RAW fidelity check before baseline generation

```bash
uv run python -m edp_lab.profiling.conventions
uv run python -m edp_lab.profiling.conventions --check-raw
```

The first command verifies metadata, lockfile compatibility and 13 profile
bindings in CI without RAW files. The second requires the four gitignored
RAW artifacts on the local Mac, verifies their SHA-256 and archive membership,
then scans the selected logical tables using the conservative parser and
checks header/row-width validity and accounted metadata/footer rows.

A successful probe is evidence that **these specified structural checks**
passed on the present RAW bytes. It does **not** establish that Source NULL
semantics, quoting, type/domain meanings, conversion rules or future
Profiler implementation have been fully validated. Review source documentation
and inspect representation-specific edge cases before promoting an effective
parser profile from `PROVISIONAL` to `RAW_VERIFIED`. The profile must then
be frozen before the first official baseline result. Historical versions and
their run outputs are never rewritten to conceal a later corrected assumption.

## Metric semantics

For a declared population of data records (header/footer not counted as
business data, but separately accounted in source inventory):

- `row_count` = number of logical data-record occurrences, preserving duplicates.
- `null_count` = number of actual NULL values as explicitly defined by the
  approved parser, **not** every blank string.
- `non_null_count = row_count - null_count`.
- `null_pct = null_count / row_count`; if `row_count == 0`, report NULL.
- `distinct_non_null_count` = count of distinct non-NULL values.
- `distinct_pct = distinct_non_null_count / non_null_count`; if
  `non_null_count == 0`, report NULL.
- `unique_count` = number of **distinct non-NULL values** occurring **exactly
  once**; `unique_count` is not `distinct_count` and not automatically a
  Business Key proof.
- For an all-NULL nonempty column, `null_pct = 1`,
  `distinct_pct = NULL`, `unique_count = 0`.
- For an empty table, `null_pct = NULL` and `distinct_pct = NULL`.

Every future **reported** metric must carry one of:

- `EXACT_FULL_SCAN`: computed exactly across all eligible logical data rows.
- `EXACT_SAMPLE`: exact inside a clearly specified sample only; include
  selection method, actual sample size and seed if applicable.
- `APPROXIMATE`: include estimator, supported error/uncertainty information
  and scope; never treat this as proof of uniqueness or an FD.
- `NOT_COMPUTED`: include reason; never replace missing computation with 0.

The `reference_count_metrics()` utility is a small exact-value **test
oracle**, not the approved production Profiler. A consumer must not assume
an arbitrary list supplied to that helper represents a full-source scan.

## Schema fingerprint V1

Serialize the ordered pairs `(exact_header_name, declared_logical_type)`
as JSON containing `version: SCHEMA_SHA256_V1` and `columns`.
Use UTF-8, `ensure_ascii=False`, sorted JSON object keys and compact
separators, then SHA-256.

No header stripping, case folding, date conversion, or identifier
normalization is permitted in `RAW_HEADER_TEXT_V1`.

Do **not** include Source Instance ID, cohort, raw bytes/hash, or Agent Version
in the structural fingerprint: those have their own separate provenance.
The initial declared logical type is `TEXT`; later explicitly approved
schema/typing changes require versioned evidence.

## Gate to Day 2 baseline

Do not mark §1.4 fully complete until: local four-RAW integrity checks PASS;
all 13 configured source parsers pass the declared fidelity probes; any
discovered NULL/encoding/quote/footer deviations are reviewed; parser profiles
are approved/versioned; actual dependency and parser implementation versions
can be captured; and the future Profiler emits correctly tagged metrics.
The current V1 file freezes **definitions** but cannot, without user-local
RAW tests, certify effective source parsing.
