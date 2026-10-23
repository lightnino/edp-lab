# EDP Lab Agent Rules (Binding)

## May do
- Create/organize repo folders, files, packaging, docs and Git/CI workflows.
- Write deterministic, read-only file inventory, hash checks, column listing, mechanical loaders and tests.
- Run reproducible scripts and report exact output/failures.
- Propose semantic decisions **as questions**, without executing them.

## May NOT do (until explicit human-approved later-phase policy)
- Infer issuer/security/listing canonical mappings or identifiers.
- Choose enterprise business keys or entity merge/split rules.
- Declare two source identifiers semantically equivalent based on names/tickers.
- Design population-level deduplication, transformations, reconciliation tolerances, or sector classifications.
- Mutate, overwrite, auto-correct, or drop RAW rows/files.
- Silently select a 13F amendment as authoritative, or align historical reporting dates without evidence.
- Make network/API calls, including OpenAI API, without direct instruction; do not spend API credits.
- Commit RAW bytes, credentials, `.env`, results or DuckDB local database.

## Review gates
- Before any mapping, identity resolution, canonical merge, business key, or nontrivial data transformation: STOP and request human review with input evidence, alternatives and consequences.
- Every output must preserve reproducible source references. Unknowns are recorded, not guessed.
- Verify source hashes before ingesting; do not process changed inputs silently.

## Current approved scope
- Source Identity and GOLD_V2 registration are approved; see `docs/source_instance_identity.md` and `docs/gold_set_v2_admission.md`.
- Snapshot-scoped lexical parsing is approved only as specified in `docs/parsing_profiling_freeze_v2.md` and DEC-000001–DEC-000005. The profiling functions use that scope; source NULL semantics remain unresolved.
- `docs/ownership_approval_boundaries.md` and Finding Schema v1 are approved governance policy. Mechanical validation never implies semantic approval.
- Deterministic execution within an explicitly approved rule/version/snapshot scope does not need repeated per-record review. New semantic decisions still require the review gates above.
- The five deterministic profiling functions are implemented; see `docs/profiling_tools.md` and `docs/profiling_output_contract.md`. GOLD_V2 execution covers 13 tables, 304,508 occurrences and 149 column profiles, with semantic NULL-dependent metrics and candidate-key eligibility NOT_COMPUTED.
- C300 was admitted and frozen under explicit user authorization on 2026-10-20; the exact approved roster and additive manifest are persisted in `metadata/cohorts/C300.csv` and `metadata/corpus_manifest_v3.csv`, with original freeze/authorization records and evidence references in `metadata/freezes/C300_v1/`. Operational evidence remains in `runs/c300/frozen-v1/`. See `docs/c300_admission.md`. C300 parser registration and execution remain unapproved; physical admission does not extend GOLD parser scope. Semantic integration remains unimplemented. Historical phase labels in frozen documents describe their original scope.

## EDP Lab Mission and Engineering Priorities

### Mission
Demonstrate the feasibility of a domain-agnostic, Databricks-based enterprise data platform maintaining RAW -> CLEAN -> QUERYABLE with measurable LOSSLESS and STABILITY properties. Evaluate whether standardized contracts, automation, metadata and agents could enable a small engineering team (~10 people rather than ~200) to operate it. This staffing proposition is an experimental hypothesis, not an established guarantee.

### Engineering priorities (binding)
1. Prioritize reusable platform mechanisms over exhaustive source-specific interpretation.
2. Demonstrate correctness of system invariants, not perfect understanding of every source record.
3. Preserve RAW immutability, provenance, lineage, reproducibility and explicit failure accounting.
4. FAILED, BLOCKED and UNRESOLVED are acceptable recorded outcomes. Silent data loss, distortion and false PASS claims are not.
5. Use representative experiments and bounded evaluations when sufficient for the current requirement; state actual coverage.
6. Do not repeatedly scan or retest unchanged evidence unless a relevant change invalidates the previous result.
7. Investigate individual anomalies only as necessary to demonstrate detection and isolation mechanisms.
8. Measure automation coverage, human intervention, processing time, failure rate and resource usage.
9. Request human judgment only when an actual authority decision is required; preserve existing approval boundaries.
10. Follow the Study Notes sequentially. Do not introduce downstream requirements into earlier sections or expand scope without a concrete dependency.
11. Keep Git branch, commit and PR names independent of Study Notes section numbers.
12. Prefer the simplest implementation satisfying current acceptance criteria.

These priorities do not rewrite frozen historical contracts or weaken existing safety and integrity rules.

## Future-day operating contract

For each new day, read the approved scope and last frozen result, verify the baseline and input hashes, then select all applicable versioned Lossless, Stability and FIN controls. Preserve newly approved controls in `metadata/operating/validation_registry_v1.json` or a reviewed successor. Treat `PRESERVED_NOT_MODELED` as an independent economic-research question, never as a corrupt-record count or authority to change source values. Structural absence and missing business approval are not data defects without evidence.

Future autonomous external operations require a bounded signed grant verified against owner-controlled trust material outside the writable worktree, operation-boundary enforcement, durable state, bounded retries and output locking. One grant may cover multiple authorized steps and resumptions. Historical SHA-pin authorization remains valid for historical reproduction only. The agent cannot approve its own grant by editing a repository file. Proposed economic rules stay proposals until human approval.

Accepted final results require actual version-pinned Databricks Result Freeze verification and live readback evidence. A Git marker alone is insufficient; the later executed Day 4 V2 Databricks freeze is recorded separately from its historical Git-only marker. Use branch, tests, review, PR, CI and merge gates for writes; continue through routine authorized steps, record interventions and recovery, and pause only for real integrity or semantic authority decisions. See `docs/agent_operating_contract.md`.

### Scoped C300 parser approval
The user approved mechanical, read-only lexical parsing and shallow inspection of exactly the 720 PASS bindings in approval packet SHA-256 `3873e9d07e4bcc2f357f940d05cf4fc5dc1262358b641d1debba2ef117910e05`. This explicit subsequent authority supersedes only the earlier statement that C300 parser execution is unapproved for these bindings. The other 12 FSDS `num.txt` bindings remain FAILED/BLOCKED with their evidence intact. No semantic NULL interpretation, business key, canonical mapping or modification to RAW, GOLD or frozen C300 is approved. Preserve the original packet membership and historical checkpoints; see `metadata/section_2_6_checkpoint_v2.json` for the post-approval evidence reference.

## Day 4 subsequent owner authorization (2026-10-23 SGT)

- The original Day 4 Step 13 CANDIDATE and Exit V1 PARTIAL assessments remain historical evidence. The requesting owner subsequently authorized an explicit **bounded source-preserving O_C1500_M2 result freeze by human override**, recorded in `metadata/freezes/O_C1500_M2_v1/`, and a **Day 4 COMPLETE_BY_HUMAN_OVERRIDE_WITH_EXCEPTIONS** closeout in `metadata/evaluations/day4_exit_v2.json`.
- Standing **10× C3.4 phase budget** is approved **only for future comparably measured N750-like workloads**, until explicit supersession; see `metadata/authorizations/day4_c3_4_budget_approval_v1.json`. No automatic new workload applicability or retrospective technical C3.4 PASS.
- The 50 source/QName Treasury L3 dispositions and B2.1/C1 source-preserving PASS were separately approved in PR #48. The 155 structural MISSING outcomes are not corrupt records. Treasury L6-B remains NOT_IMPLEMENTED; no canonical economic or entity semantics are approved.
- This Git freeze marker records a human decision and pinned version-0 references; it does not assert that new Databricks readback, physical write protection, independent archive, or WORM immutability was performed. Those controls must be separately verified before any stronger retention claim.
