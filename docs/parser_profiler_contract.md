# Parser / Profiler Contract

**Contract version:** `parser_profiler_contract_v1`  
**Status:** Proposed for review. Generic definitions are ready to freeze; source-specific parsing profiles require verified local RAW evidence. This is **not** a claim that parsing/profiling of GOLD_V2 is implemented or has passed.

## Purpose and normative dependencies

Source-native parsing and profiling must preserve exactly which source occurrence and field was observed, its lexical representation, and its provenance. This contract operationalizes Evaluation Contract V1 **L4, L5, L6, L7, L8, L9** and experimental integrity **SC2, SC3, SC4, SC6**, without approving any enterprise mappings or inferred business keys.

`GOLD_V2` provides 4 immutable physical source instances and 13 registered logical tables. For archive members the stable logical locator is `(source_instance_id, archive_member)`. Parsing never creates a new physical source instance.

## 1. Boundary of a mechanical parser

- First verify `source_instance_id` and the complete physical RAW SHA-256 against the manifest. Never modify source bytes or replace an admitted source in place.
- Select a **versioned, explicit parsing profile** for each logical member/file. Required configuration: source locator, archive member (if applicable), format, encoding, BOM handling, delimiter, quoting/escaping behavior, header presence/position, line-ending handling, blank-line policy, trailer/footer recognition, whitespace treatment, and declared null tokens. Record the source evidence supporting each choice. No unrecorded autodetection at production parse time.
- Treat every source column initially as lexical/source-native data. Preserve leading zeros, identifier characters, whitespace, empty fields, precision, and repeated source occurrences. Do not infer a canonical type, unit, date meaning or key from the spelling of a column.
- Do not silently skip physical lines or source-record occurrences. Metadata headers/footers, if excluded from *data* row count, must be recognized through a reviewed rule and accounted for separately; a delimiter-based diagnostic line count is not yet a parsed row count.
- Ambiguous encodings, unsupported quoted delimiters/newlines, malformed rows, duplicate headers, inconsistent field counts, and undeclared missing markers require an explicit parse exception or review. They must not be silently dropped/coerced.
- RAW null semantics are source-specific: **absent field**, **empty string**, **declared source-null token**, **whitespace-only**, and **literal zero** are distinguishable. Whether a token is parsed as null is not decided by generic defaults.
- Source-native column names and ordinal positions must be preserved. Any cleaned or typed projection is a separately versioned transformation with original value and lineage intact.

**Physical record locator contract (when parser is implemented):** source instance, member/file, one-based source data-record ordinal, physical line/byte-range where determinable, and raw record evidence reference. A row ordinal must not be presented as a physical line number if quoting can span lines.

## 2. Deterministic profiling metrics

All counts are at the declared `(source_instance_id, archive_member/file, parser_profile_version)` scope.

| Metric | Definition | Zero denominator |
|---|---|---|
| `row_count` | Parsed **data-record occurrences**, excluding separately accounted header/trailer lines under approved rules | 0 |
| `null_count` | Number of occurrences classified null for the field under the **versioned** null policy | 0 |
| `non_null_count` | `row_count - null_count` | 0 |
| `null_pct` | `null_count / row_count`, numerical fraction in [0, 1] | `null` when `row_count=0` |
| `distinct_non_null_count` | Cardinality of exact observed non-null lexical values under the declared representation policy | 0 |
| `distinct_pct` | `distinct_non_null_count / non_null_count`, fraction in [0, 1] | `null` when `non_null_count=0` |
| `duplicate_occurrence_count` | Repeated **observed values/rows**, if measured, *not* automatically duplicate business events | Count only, not deduplication |
| `min/max/sample` | Based on a declared lexical or explicitly typed comparator and deterministic sampling/ordering | `null` with documented applicability |

- Default `count_mode=EXACT` uses a full scan; `APPROXIMATE` results must explicitly record algorithm, parameters, error/precision information, and the reason approximate was used. Approximate results cannot silently replace exact results.
- Report `null_pct` and `distinct_pct` as fractions, not percent points; any UI multiplication by 100 is presentation-only.
- Uniqueness tests produce **observed candidate keys/hypotheses** at a fixed corpus scope, never approved enterprise keys. Record tested column combinations, null policy, number of conflicts and scope; do not select identities automatically.
- Type inference, field meanings, business grain, units and cross-source joins remain **hypotheses or source-documented claims**, not established enterprise semantics.

## 3. Schema fingerprint

A schema fingerprint is a **deterministic hash of a declared parser-visible column signature**, with original column order and spelling, plus the exact parsing-profile digest and fingerprint-algorithm version. The canonical encoding is UTF-8 JSON with sorted keys and compact separators; SHA-256 over that encoded JSON yields a 64-character lowercase hex string.

- `field ordinal + source header spelling` are required.
- Source-declared lexical type may be recorded if evidenced; inferred physical/data types are recorded as separately versioned observations and cannot silently mutate the fingerprint.
- Fingerprints are for change detection, not proof of business-semantic equivalence. A revised parser profile needs its own version/digest and comparison against preserved earlier outputs.
- The current Corpus Manifest's `schema_fingerprint` fields remain blank. Do not populate them before actual parser output exists and is reviewed.

## 4. Reproducibility and evidence

Every future profiling result should record:
- source instance, physical RAW path/hash, archive member and **member hash** where applicable;
- parser contract version, parser-profile ID/version/content SHA-256, profiler implementation version and Git commit;
- runtime/dependency versions (Python, DuckDB when used, lockfile reference), run ID and configuration fingerprint;
- observed row/field counts, metric definitions, null-token policy, count mode, exceptions/unknowns;
- explicit source-record/field locators for checkable examples and deterministic output artifact reference.

Evidence classes (do not collapse them):
- `SOURCE_DOCUMENTATION`: verbatim publisher specification with document/location and edition.
- `OBSERVED_RAW`: exact measured bytes, member, field/record locator and hash.
- `MECHANICAL_DERIVATION`: reproducible computation with algorithm and code version.
- `HYPOTHESIS`: interpretation not yet established by authoritative evidence.
- `HUMAN_APPROVED`: explicitly reviewed decision with approver, scope, decision and evidence.
- `UNKNOWN`: a question/unsupported claim requiring additional evidence.

`HUMAN_APPROVED` is not automatically an independently adjudicated `ground_truth_available=TRUE`. Verified profiles are not full Lossless or Stability passes.

## 5. Source-specific format decisions (PENDING)

Initial **candidate** delimiter families: SEC Form 13F TSV = TAB, SEC FSDS TXT = TAB, Nasdaq directories = PIPE. The previous source profiles report file-creation trailer lines on Nasdaq files. **Actual encoding, quoting, escape, per-member header and source-null tokens have not been audited for all 13 tables.** Do not freeze a production parsing config from these hints alone.

Use `uv run python -m edp_lab.profiling.source_format_probe` on the local machine containing the ignored RAW inputs. The probe verifies full physical RAW hashes, inspects every registered member and reports bounded header/trailer byte excerpts, member hashes, candidate separator counts, newline/BOM evidence and UTF-8 decodability. It is **diagnostic only**: separator counts do not establish parsing fidelity or record counts. Keep probe output in the ignored `reports/` folder; human-review the results before establishing versioned source profiles.

## Review and implementation status

- `metrics_contract.py`: pure count-denominator and schema-fingerprint primitives with synthetic tests; **not** a full profiler.
- `source_format_probe.py`: read-only physical evidence probe; not an approved ingestion/parser implementation.
- No parsed GOLD_V2 tables, `C300`, schema-fingerprint claims, canonical mappings, or full Lossless 1–6/Stability A/B/C results are created in this PR.
- Review gate: approve the generic metric and evidence definitions, inspect actual source-format evidence, then separately freeze source-specific parsing profiles.
