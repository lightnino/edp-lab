# Source-instance identity and lineage contract

## Purpose and authority

A `source_instance_id` identifies **one admitted, immutable physical source input/delivery**. It is not a logical table, business row, enterprise entity, issuer, security, filing identifier, or hash digest. This convention implements the experimental-integrity requirements in `docs/evaluation_contract.md`: SC2 (no cohort replacement), SC3 (stable identity), SC4 (RAW immutability), SC6 (preserve historical evidence), and L6 (RAW/hash integrity).

## Source boundaries

| Concept | Stable locator | Example |
|---|---|---|
| Physical source instance | `source_instance_id` | `SRC000004` for `2010q2_fsds.zip` |
| Archive member / logical table | `(source_instance_id, archive_member)` | `(SRC000004, num.txt)` |
| Standalone logical table | `(source_instance_id, logical_table_name)` | `(SRC000002, nasdaqlisted.txt)` |
| Business/source record occurrence | source instance + member/table + source-record locator (defined by its parser) | A source NUM record, **not** a new source instance |

The source boundary is the physical artifact/delivery registered in `metadata/corpus_manifest.csv`. Each archive member in `metadata/gold_set_logical_tables_v2.csv` inherits its archive's Source Instance ID and the parent's SHA-256. Member-level byte hashes may be measured separately for profiling/lineage but do **not** create independent physical deliveries.

`GOLD_V1` has three physical inputs. `GOLD_V2` inherits them and adds `SRC000004`. There are four physical instances and thirteen registered logical tables. The latter count is **not** a source-instance count.

## Identity and admission policy

1. Allocate an unused `SRC######` identifier independently of filename, table names, row contents, and SHA-256. Never renumber or reuse an admitted ID.
2. Record the original physical RAW location under `data/raw/`, exact SHA-256, `source_family`, immutable introduction cohort, admission UTC timestamp, and admission status.
3. Before admission, preserve independent source-delivery evidence (publisher/delivery channel, retrieval or receipt evidence and stable snapshot/edition reference where available). The existing four records have verified local bytes and archive documentation, but not every original external receipt or acquisition timestamp is recoverable: **do not invent missing historical evidence**.
4. The same filename may occur in different deliveries. The same SHA-256 may also occur in two genuinely distinct deliveries. If their hashes match, do **not** merge IDs merely because bytes match; demand independent delivery evidence and review before accepting the extra instance.
5. Two source IDs must not point to the same `raw_path` in the active manifest. Even with equal hashes, distinct verified deliveries need distinguishable immutable storage references. A future storage relocation requires an audited relocation record; never rewrite frozen source identity or historical runs silently.
6. A byte-changed delivery gets a **new Source Instance ID** and a new immutable path; it must not overwrite an existing admitted file or manifest record.
7. Once a cohort is frozen, existing membership, source-to-byte references, recorded evidence and historical outputs remain intact. A newly selected reference population gets a separately named cohort.
8. Do not infer semantic equivalence, approved business keys, canonicals, deduplication, or transformations from these mechanical identity rules.

## Controlled source variants

- `real_or_controlled = REAL`: `variant_type` and `parent_source_id` are empty.
- `real_or_controlled = CONTROLLED`: both `variant_type` and an existing `parent_source_id` are mandatory; a variant must have a separate immutable `raw_path` and Source Instance ID.
- The parent graph must exist and be acyclic. `variant_type` is a description of a known, documented test manipulation, **not** evidence of an independently sourced external feed.
- `ground_truth_available = TRUE` only when independently defined/versioned truth evidence exists, frozen before evaluation. A CSV flag alone is not ground truth.
- Controlled variants may be counted as controlled **source instances** in an explicitly declared evaluation cohort but never as independent real-world source deliveries. Report separate real/controlled counts in scale summaries.

## Verification

```bash
# CI-safe: checks registry invariants without asserting untracked RAW bytes
uv run python -m edp_lab.ingestion.source_identity

# Local: read-only SHA-256 of every admitted RAW and existence of archive members
uv run python -m edp_lab.ingestion.source_identity --check-raw
```

`--check-raw` is expected to fail on GitHub CI because RAW files are deliberately gitignored. Zero physical SHA matches cannot be inferred from a metadata-only PASS.

The validator checks registry schema, unique source IDs and storage paths, SHA format, UTC admission timestamps, real/controlled provenance structure, parent existence/cycles, and archive-member parent lineage. Identical content hashes across distinct IDs produce a `REVIEW_REQUIRED` warning; humans must check independently evidenced deliveries before admitting them.

This is **source-identity validation only**. It does not claim full Lossless 1–6, business-grain proof, parser fidelity, source semantics, or C300 cohort admission.
