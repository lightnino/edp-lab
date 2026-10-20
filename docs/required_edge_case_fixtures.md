# Required edge-case fixtures

Scope: the eleven scenarios listed in the task instruction, checked against the
existing frozen V1 metrics, V2 parsing freeze, source identity and profiling output
contracts. The standalone Study Notes text is not stored in this repository;
this inventory uses the supplied scenario list without inventing extra requirements.
All test references below are in `tests/`.

| Scenario | Reused or added coverage |
| --- | --- |
| Leading-zero IDs | Existing `corpus_invariants/test_parser_fidelity.py::test_exact_text_and_duplicate_occurrences_survive`; added `corpus_invariants/test_profiling_tools.py::test_leading_zero_ids_remain_distinct_text` compares `001` with `1` without coercion. |
| Quoted CSV delimiters | Reused `corpus_invariants/test_profiling_tools.py::test_explicit_quoted_delimiter_and_multiline_locator`, including physical-line spans and rejection with quoting disabled. |
| Malformed records | Reused `corpus_invariants/test_parser_fidelity.py::test_bad_records_fail_closed`, `corpus_invariants/test_profiling_tools.py::test_fail_closed` and `profiling/test_profile_edge_cases.py::test_partial_scan_retains_failure_line_and_occurrences`. |
| Empty tables | Reused `corpus_invariants/test_profiling_tools.py::test_empty_all_null_and_blank` and `profiling/test_profile_edge_cases.py::test_empty_and_blank_populations_keep_unknown_null_metrics`. |
| All-NULL columns | Reused `corpus_invariants/test_profiling_tools.py::test_empty_all_null_and_blank` with an explicit synthetic token rule; registered source NULL semantics remain unresolved. |
| Duplicate frequencies | Reused `corpus_invariants/test_profiling_tools.py::test_occurrences_duplicates_and_witnesses` and `test_column_metrics_and_ordering`: two groups, five participating occurrences, three excess rows, exact frequencies and singleton counts. |
| Composite NULL keys | Added `corpus_invariants/test_profiling_tools.py::test_composite_null_key_eligibility`: token in either component, literal uniqueness/minimality, explicit synthetic NULL disqualification and unknown-NULL NOT_COMPUTED behavior. No Business Key approval. |
| Repeated source identity | Reused `corpus_invariants/test_source_identity.py::test_bad_new_identity_rejected` (duplicate ID/path) and `test_identical_hash_with_distinct_delivery_paths_requires_review`. |
| Reordered columns | Reused `corpus_invariants/test_profiling_tools.py::test_schema_order_and_distribution_separation` and ordered-header rejection in `corpus_invariants/test_parser_fidelity.py::test_bad_records_fail_closed`. |
| Nested JSON fields | Added `corpus_invariants/test_profiling_tools.py::test_nested_json_field_is_preserved_as_literal_text`: nested objects, array, repeated nested field names, zero-prefixed strings and JSON null survive CSV decoding as exact text with a source locator. Added `profiling/test_schema_fingerprint.py::test_nested_json_field_addition_changes_metadata_fingerprint`: hand-declared nested structure type metadata gains a field and changes the V1 fingerprint, verified against independent exact canonical bytes. No flattening or JSON interpretation. |
| Distinct event IDs | Added `corpus_invariants/test_profiling_tools.py::test_distinct_event_ids_with_equal_payloads_preserve_both_occurrences`: equal payloads with distinct IDs remain separate full rows; projected equality is observation only, with both source locators retained. |

Fixtures are synthetic and remain in existing test code; no new source is admitted.
Registered RAW, frozen metadata, policies, historical evidence and production code
are unchanged. JSON-document ingestion remains unsupported pending a reviewed
profile. Nested-field structural change is tested on explicitly declared synthetic
metadata through the existing V1 exact type-text hashing behavior. The opaque
fixture descriptors introduce no type grammar or automatic schema discovery;
registered GOLD_V2 columns remain TEXT and their fingerprints are unchanged.
No new fingerprint algorithm or version is needed.

Validation on base `dd5beb8593a648df724585267adaeaca9209cda6`, matching freshly
fetched `origin/main`:

- `.venv/bin/python -m pytest -q`: 196 passed, 1 skipped (C300 not admitted).
- `.venv/bin/ruff check .`: all checks passed.
- `git diff --check` and an untracked-document whitespace check: no diagnostics.

No implementation defect was exposed. C300 admission and semantic NULL resolution
remain deferred under the existing contracts. No commit or push was performed.
