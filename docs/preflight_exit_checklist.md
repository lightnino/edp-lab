# §2.1 completion evidence and preflight scope

Status: §2.1 implementation complete, with documentation reconciled for review.
This record covers the five deterministic profiling functions only. Full Day 2
completion, the broader preflight checklist and §2.2–§2.4 are separate reviews;
their implementation is not a prerequisite for §2.1 completion.

| §2.1 requirement | Status | Evidence / boundary |
| --- | --- | --- |
| Five independently callable functions | PASS | `profile_table`, `profile_column`, `find_duplicates`, `candidate_key_scan`, `schema_fingerprint` in `src/edp_lab/profiling/tools.py`; [usage](profiling_tools.md) |
| Shared reader and configuration | PASS | `source_reader.py` uses the frozen GOLD_V2 configuration and reviewed lexical parser |
| Integrity before parsing | PASS | RAW and member hashes verified before parsing; frozen artifacts and existing evidence preserved |
| Deterministic machine-readable outputs | PASS | [Output contract](profiling_output_contract.md): versions, run/result hashes, actual code/environment provenance, source references and computation modes |
| Frozen NULL policy | PASS | Semantic NULL-dependent metrics and candidate eligibility remain NOT_COMPUTED with reasons; literal measures are separately named |
| GOLD_V2 execution | PASS | 13 tables, 304,508 data occurrences, 149 column profiles; no hash or parse failures |
| Offline validation | PASS | 155 tests; Ruff and whitespace checks pass |

Existing execution evidence is retained unchanged under gitignored
`runs/profiling/`:

- [Execution report](../runs/profiling/execution-report-54b3bbde96ee91a6ed488269efe46ecea4d51c1fad6b0e2b82c726eb76873987.md)
- [Machine-readable evidence index](../runs/profiling/execution-summary-54b3bbde96ee91a6ed488269efe46ecea4d51c1fad6b0e2b82c726eb76873987.json), including per-table output-file SHA-256

Every column was profiled. Each table also ran whole-row literal duplicate checks,
all singleton key candidates plus bounded pairs within its first three columns,
and the frozen structural fingerprint. This is not an exhaustive composite-key
search or approval of a Business Key. Unknown source NULL semantics are preserved
as NOT_COMPUTED, not treated as missing implementation.

The five functions operate on the shared `SourceTable` representation. GOLD_V2
supplies the verified deep-profiling execution. Future C300 mechanical execution
requires admitted immutable sources and reviewed parser registration; the current
registered reader is limited to frozen GOLD_V2 bindings. No C300 cohort or future
parser scope is created here. The [proposed admission policy](corpus_admission_policy.md)
retains its Human Review status; approval of that proposal and C300 execution are
outside this §2.1 completion review.

The earlier preflight review recorded that the original broader study-plan
checklist was unavailable locally. That limitation remains for any future exact
review of that checklist; it does not block the narrowly scoped §2.1 completion
confirmed by the current instruction. The [historical engineering evidence index](decision_log.md#frozen-engineering-evidence-index)
continues to link existing approvals without invented retrospective records.
Frozen policy documents retain their historical status statements unchanged.

Remaining §2.1 blockers: none identified. No §2.2, §2.3 or §2.4 implementation,
semantic approval, API call, commit or push is part of this reconciliation.
