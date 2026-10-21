# Day 2 C300 + M1 readiness proposal V1

Status: APPROVED lexical execution scope for the original 720 PASS bindings,
subject to per-binding Lossless gating and the constraints in DEC-000006.
The earlier review requested revisions; the subsequent user execution instruction
provided authority. These are distinct events. See
[authority](day2_c300_m1_authority.md) and [actual baseline status](../reports/C300_baseline.md).
No full C300 Lossless PASS or durable freeze is asserted by this contract.
Frozen historical contracts, original approval packets and run snapshots remain
unchanged. Older copies of this proposal are pinned in their runtime bundles.

## Scope, sequence and authority

Required order: frozen C300 RAW verification/parsing → lexical CLEAN M1 → actual
Lossless 1–6 → exception triage/remediation and retained per-binding Lossless Gate
→ QUERYABLE for PASS bindings → downstream correctness/end-to-end checks →
regression/performance and original Write Tasks → verified historical freeze.
Diagnostic SQL is allowed before the gate. Optional statistics reuse the parsing
spool or completed CLEAN without a new full RAW benchmark scan; statistical
failures never invalidate independently valid CLEAN output.

C300 is the first formal M1 baseline. GOLD_V2 A–D and Stability A/B/C remain
deferred; compatible existing GOLD/C300 evidence is reused without rerunning
unchanged checkpoint checks. No enterprise identities, business keys, entity
integration, source NULL interpretation or source-specific business logic is
approved. Existing parser authority remains exactly the original 720 bindings.

Authority: [AGENTS.md](../AGENTS.md), DEC-000006, the subsequent user execution-order
and exception-triage instructions, and the [Evaluation Contract](evaluation_contract.md).
Derived Databricks CLEAN writes and gated views for those 720 are authorized;
new consequential parser rules for the twelve NUM exceptions are not automatically
approved. Their [triage proposal](c300_num_exception_triage_v1.md) awaits review.

## Readiness evidence inspected

| Evidence | Authoritative reference / observed boundary |
| --- | --- |
| Physical admission | `metadata/cohorts/C300.csv`; `metadata/corpus_manifest_v3.csv`; `metadata/freezes/C300_v1/{freeze,authorization,references}.json`; original `runs/c300/frozen-v1/` |
| Exact parser authority | `metadata/section_2_6_checkpoint_v2.json`; `runs/section-2-6/review-v1/approval-packet.json`; `runs/c300-post-approval-v1/{authorization,activation,checkpoint}.json` |
| Discovery and binding rules | Registry path/hash in approval packet; `src/edp_lab/parsers/c300_v1.py` and `c300_reader_v1.py`; [Agent V0](source_observation_agent_v0.md) |
| Post-approval execution | `runs/c300-post-approval-v1/{summary,metrics,evaluation}.json`; [execution boundary](source_observation_post_approval.md) |
| Existing statistics | `profiling/source_reader.py`, `tools.py`, `conventions.py`, `run_gold.py`; [output contract](profiling_output_contract.md); [completion references](preflight_exit_checklist.md) |
| Existing orchestration | `agents/analyst_v0.py`, `c300_shallow_v0.py`, `post_approval_v1.py`; `tool_adapters/profiling.py`; no replacement Agent framework needed |
| Native Spark/Delta execution | `metadata/native_nasdaq_checkpoint_v1.json`; `runs/databricks-native-v1/{checkpoint,native-results,environment}.json`; `notebooks/bronze_nasdaq_listed.py`; [native execution](native_databricks_execution.md) |

Historical Phase 1 checks (reported here unchanged; not rerun for this revision): the canonical roster and v3 manifest match
freeze hashes; all five path/hash pairs in the V2 post-approval reference match;
the native checkpoint hash matches its reference. The manifest-to-roster join has
300 local files present, totaling 7,632,930,175 bytes by filesystem stat. This is
presence/size evidence, **not a fresh RAW hash verification**. No RAW parsing,
full RAW rehash, remote lookup or network/API call was performed in this review.
The 76 post-approval checkpoint artifact hashes and 38 native checkpoint artifact
hashes also matched (114 entries, zero mismatches); native results report TESTED.
Proposal relative links and whitespace checks passed.
The existing post-approval evidence already records all 300 RAW hashes checked;
execution must verify them again against the bytes it actually consumes.

Pinned roster SHA-256:
`f052599a7cfac3b566a236965e2ab163934d4541e7b09e03da98be728c1541e4`.
Pinned v3 manifest SHA-256:
`27ce93f363ebeb234737659e9a411927aed3dd3a674bc8a21b780e05dfdc4bdf`.
Parser approval packet SHA-256:
`3873e9d07e4bcc2f357f940d05cf4fc5dc1262358b641d1debba2ef117910e05`.

C300 has 60 FSDS archives, 42 13F archives and 198 Daily Master deliveries,
SRC000005–SRC000304. All are REAL; there are no controlled ground-truth variants.
732 logical bindings comprise 240 FSDS, 294 13F and 198 Daily Master bindings.
Approved execution covers 228 FSDS + 294 13F + 198 Daily Master = 720 bindings
across all 300 instances. Twelve instances also contain a blocked NUM member.
The v3 manifest's other four GOLD rows do not enter the C300 execution population.

Prior shallow execution used VERIFIED_EVIDENCE_REUSE: zero newly parsed records,
zero new member scans, `full_c300_profiling: false`. Its 6.44-second host execution
and 0.10-second Agent timing are not C300 parsing/profiling benchmark results.
The native NASDAQ success proves one bounded standalone source can preserve exact
bytes/locators in Delta, with multiset comparison and byte reconstruction. It does
not prove C300 archive support, executor memory capacity or C300 throughput.

## Approved M1 representation

Model identifier `M1_LEXICAL_V1`; rule identifier `C300_LITERAL_IDENTITY_V1`.
These describe source representation only. Below are exact logical Spark types;
all columns are required except those explicitly marked nullable. Array elements
and struct members are required. Runtime validation enforces this even where CTAS
or Delta readers relax schema nullability. No DDL is executed by this document.

Two run-scoped Delta tables under `workspace.edp_lab`, with immutable names
`clean_c300_m1_records_<run_suffix>` and `clean_c300_m1_bindings_<run_suffix>`.
Suffix is a host-validated identifier, recorded in the run manifest. Do not use an
unversioned current table, MERGE, overwrite, or CREATE OR REPLACE publication.

`clean_c300_m1_records_<run_suffix>`:

```text
run_id                 STRING
model_version          STRING              # M1_LEXICAL_V1
rule_version           STRING              # C300_LITERAL_IDENTITY_V1
source_instance_id     STRING              # existing physical source identity
binding_sha256         STRING              # canonical fingerprint of approved binding
source_line            BIGINT              # 1-based physical member line
byte_offset            BIGINT              # 0-based uncompressed member byte start
byte_length            BIGINT              # includes exact terminator
record_kind            STRING              # DATA | HEADER | METADATA
fields                 ARRAY<STRUCT<
  field_ordinal: INT,                       # 1-based position
  original_name: STRING,
  lexical_value: STRING,
  disposition: STRING                      # DIRECT_MAP
>>
admission_outcome      STRING              # ACCEPTED for completed DATA; nullable
outcome_reason         STRING              # nullable for non-DATA framing records
```

`fields=[]` for HEADER/METADATA; their exact byte intervals remain addressable
in immutable RAW without treating preamble components as data attributes. For DATA, names come from
ordered exact bound headers; every position has one field. `lexical_value` is
strictly decoded exact text, never SQL NULL. Empty string remains empty string.
The nullable admission columns distinguish framing records from data occurrences;
DATA has `ACCEPTED` / `IDENTITY_LEXICAL_PRESERVATION`. No source rejection rule is
introduced. A failed binding publishes no ACCEPTED records.

`clean_c300_m1_bindings_<run_suffix>` (exactly 732 rows):

```text
run_id                 STRING
model_version          STRING
rule_version           STRING
source_instance_id     STRING
source_family          STRING
raw_path               STRING              # unchanged registered path
volume_path            STRING              # verified physical copy; nullable if absent
raw_sha256             STRING
archive_member         STRING              # exact registry spelling
member_sha256          STRING
logical_table_name     STRING
binding_sha256         STRING
parser_profile_id      STRING
parser_version         STRING
parser_code_sha256     STRING
reader_code_sha256     STRING
registry_sha256        STRING
approval_packet_sha256 STRING
cohort_sha256          STRING
manifest_sha256        STRING
ordered_header         ARRAY<STRING>
expected_member_bytes  BIGINT
processing_status      STRING              # COMPLETE | FAILED | BLOCKED
reason_code            STRING
error_evidence_ref     STRING              # nullable on success
records_total          BIGINT              # nullable unless completed
records_data           BIGINT              # nullable unless completed
fields_data            BIGINT              # nullable unless completed
observed_member_sha256 STRING              # nullable if not scanned
```

Technical locator `(run_id, binding_sha256, source_line)` is unique by construction,
not an enterprise business key. Fields add `field_ordinal`. The binding relation
joins one-to-many to records, providing original RAW/member/profile references
for every occurrence and value. These relations are run outputs, not replacement
source registries. Original record BINARY payloads are not copied into Delta:
verified immutable RAW remains the byte authority. Resolve each record through
its binding's RAW hash and physical reference, exact archive member and member
hash, then read its uncompressed byte interval. This includes exact delimiters,
terminators and framing. Reconstruction requires retrievable immutable RAW;
lexical fields alone are not claimed to reproduce all bytes. Any later BINARY
column requires a demonstrated fidelity invariant and a reviewed contract change. Model/rule specifications, actual code hashes, lock/dependency
versions, Spark/Python versions, configuration and table Delta versions are pinned
in `profile_run_manifest.json` and the eventual output seal.

Binding failures retain typed errors and partial counters separately in run evidence.
They must not invent record counts or per-record outcomes for unparsed members.
All known diagnostic occurrences keep their original witnesses. Binding-level
QUARANTINED coverage is not falsely presented as complete L1 occurrence accounting.

## Allowed mechanical transformations and execution design

Approved operations within the original 720-binding scope: strict UTF-8 decode; the already approved literal delimiter
split; separate exact terminators for decoding while retaining their RAW byte references;
classify registered framing; package ordered strings and locator metadata; compute
hashes, counts and structural fingerprints; expose identity SQL projections.
No trim, case fold, quote interpretation, escape decoding, type inference, numeric
or date cast, NULL mapping, repair, deduplication, joins across sources or field
renaming. No semantic selection of amendments or reporting dates.

Within the recorded execution authority, use the existing CLI profile `edp-lab`, catalog `workspace`,
schema `edp_lab`, Volume `/Volumes/workspace/edp_lab/raw`. Upload only missing
unchanged RAW copies to a new immutable C300 path after local hash verification;
record physical-copy references rather than rewrite registered paths. Recheck
remote hashes before consumption. Never replace the native NASDAQ table or files.
Remote presence and available disk/memory are unverified today.

Use one reusable Python/Spark job, not a new Agent. The initial implementation
uses one bounded driver-side parser at a time, reusing executor/driver-local
scratch by parent archive; Spark materializes Delta and performs native multiset
and QUERYABLE checks. Parsing concurrency is one, not a distributed parsing
throughput claim. The host builds the hash-pinned work list from the canonical
roster and exact activation. The existing reader requires a verified local scratch
copy at the registered relative path with pinned metadata/code; this is a physical
access adapter, not a new parser. Preserve `occurrences` activation and pre/post
parent/member hash gates. Scratch stays separate from immutable admitted RAW.
Do not load entire archives with driver `binaryFile.collect()` as in the small demo.
Any later distributed adapter must demonstrate executor filesystem/package support.

Mandatory CLEAN execution streams each approved member through the existing
reader and packages every framing/data record with exact lexical fields and RAW
locators. Preserve source/locator fields and `null_tokens=None`. Mandatory checks
are source/parser integrity, record and field accounting, ordered schema
fingerprint, original lexical values, multiplicity, lineage, processing status
and errors. Compute the fingerprint using the existing convention from bound
schema metadata without requiring an in-memory population. Stage output in a
new run directory; a binding is COMPLETE only after terminal integrity gates,
mandatory correctness validation and record/binding publication succeed. Spark
retries/speculative attempts use unique staging paths; publish one successful
attempt per binding and preserve failed attempts. QUERYABLE exposes only validated,
sealed COMPLETE bindings; partial attempts never appear as completed data.

The reader's pre/post parent/member integrity reads are mandatory verification
I/O, not redundant profiling scans. Statistical profiling is a separate optional
stage, reusing existing functions where feasible. A bounded spool may share the
parse stream; do not require a full in-memory SourceTable for CLEAN completion.
Statistical attempts consume that spool or a separately recorded read of completed
CLEAN with the required source metadata; disclose extra I/O and any repeated passes.

Existing statistical profilers use in-memory Counters/sets and are not distributed.
Enforce measured worker memory/disk budgets and isolate statistical attempts from
CLEAN workers/publication. Collect actual computation scope, elapsed time and peak
memory per metric/function. On a resource limit, affected metrics are NOT_COMPUTED
with RESOURCE_LIMIT evidence; retain only independently completed valid metrics.
An optional profiler exception or OOM does not invalidate correctly completed
CLEAN materialization. An OOM interrupting mandatory CLEAN work leaves that attempt
incomplete and requires a separate recorded retry; it cannot be marked COMPLETE
from partial output. No sampling or replacement statistical implementation is
silently substituted. A larger-memory statistical retry is a separate attempt;
a profiler rewrite requires a later explicit scope decision.

Publish the two Delta tables exclusively after staging validation. Delta does not
provide a transaction across these two tables: write a final run completion marker
only after table versions, counts and hashes are verified. A failed publication
remains an incomplete run, never repaired in place. Consumer queries are created only after a retained, versioned per-binding
Lossless Gate, against pinned table versions and explicit PASS membership. Record all intermediate failures.

## Minimal QUERYABLE contract

Create three run-specific views only after the retained CLEAN Lossless Gate: `q_c300_m1_records_<suffix>`
(select DATA records only from COMPLETE bindings whose Lossless Gate is PASS),
`q_c300_m1_fields_<suffix>` (explode fields only for gate-PASS records with ordinal, text and full joined
source/member/record lineage), and `q_c300_m1_coverage_<suffix>` (all 732 binding
outcomes including twelve blocked). Require the exact run ID and join cardinality
checks. Header/metadata locators remain queryable in CLEAN and resolve to exact RAW bytes.
No pivot into business entities, aggregation of economic measures, DISTINCT,
implicit ordering, or latest-amendment selection. Consumers order explicitly by
source/member/source_line/field_ordinal. Query SQL and its hash are frozen with
Delta input versions; views alone are not immutable snapshots.

## Twelve blocked bindings

SRC000052–SRC000054 and SRC000056–SRC000064 / `num.txt` retain historical validation
FAILED and current execution BLOCKED. Preserve all twelve binding rows, parent and
member hashes, exact original errors and diagnostic witnesses. Do not invoke their
parsers, create repaired data, emit fabricated empty profiles, or report zero rows.
Supporting archive members/readme remain hash-inventoried RAW; unresolved encoding
is retained and no supporting HTML is turned into a data table.

This keeps 300/300 physical-instance coverage and 732/732 binding accounting,
with at most 720/732 completed lexical materializations. It does not establish
full C300 occurrence accountability: the blocked members' logical populations are
unknown under the approved parser. A scoped baseline with exclusions can be frozen
as historical evidence; a full-corpus Lossless PASS cannot be claimed.

## Lossless 1–6 implementation plan

The implementation is `edp_lab.materialization.c300_m1`,
`lossless_gate` and `notebooks/clean_c300_m1.py`; actual coverage/status is in the
baseline report and run artifacts. Store one result per family and binding, with status, scope, equation, expected/observed values and evidence refs;
rollups preserve failures/unresolved results rather than averaging them into PASS.

| Test | Actual planned check and acceptance boundary |
| --- | --- |
| 1 — records / multiplicity | Compare parser-emitted locator multiset against persisted DATA outcomes using bidirectional `exceptAll`; every completed source occurrence has exactly one ACCEPTED outcome and one target. Unique locators, duplicate values retained, count identities per binding. Twelve blocked members remain BLOCKED/HUMAN_UNRESOLVED for full occurrence accounting; no count-only PASS. |
| 2 — fields | Enumerate every header position on every accepted record; expected count is data occurrences × bound header width. Compare exact ordinal/name/value/disposition multiset; require exactly one DIRECT_MAP per accepted field and no extra target. Check framing byte accounting separately. Treat all source fields as in scope without guessing meaningfulness. |
| 3 — values / structure | Resolve persisted byte intervals against verified immutable RAW and compare persisted ordered strings against an independent approved split of those bytes; test lengths, source lines, offsets, terminators, leading zeros, blanks and literal tokens without semantic conversions. Compare actual duplicate multiplicities. Reconstruct each completed member from RAW-referenced intervals in byte_offset order including framing; require no overlaps/gaps, exact total length and expected member hash. No persisted BINARY column is required. |
| 4 — RAW hashes | Verify all 300 local upload inputs and all consumed Volume copies against frozen manifest before processing; member hashes before iterator output, terminal hashes after iteration. Include blocked parents in physical immutability coverage. Byte/hash mismatch fails affected scope, never rebinds input. |
| 5 — lineage / reproducibility | Anti-join both directions at record and field grain; require one bound parent/member and target per accepted occurrence/field. Resolve original byte intervals and verify member reconstruction; archive itself remains retrievable, no ZIP recompression claim. Pin input, code, dependency, model/rule and Delta versions. Bounded deterministic replay of one completed binding from each of the three families compares complete outputs excluding run IDs/timestamps; reuse unchanged GOLD reference. Report replay coverage of 3 bindings, not a full C300 replay. Deterministic sorted row hashes include multiplicity and chunk boundaries; retain canonicalization specification. |
| 6 — numeric/economic controls | Proposed M1 disposition for every field is PRESERVED_NOT_MODELED as an integrated economic measure, even though its lexical string is DIRECT_MAP. Produce a per-header control inventory with source refs, raw unit/meaning/grain/grouping dimensions/time basis UNRESOLVED, reconciliation eligibility limited to the lexical-only boundary, numeric promotion none, conversion/rule version none, tolerance none, equation and observed economic result NOT_APPLICABLE, exception status and lexical fidelity reference. No sums or inferred units. DEC-000006 authorizes this lexical-only applicability boundary: report NOT_APPLICABLE with inventory, never economic reconciliation PASS. New economic modeling requires separate review. |

The field disposition in Test 2 concerns string preservation; the separate Test 6
measure disposition explicitly withholds economic modeling. Human review may instead
require applicable economic equations, in which case model/authority work is needed
and freeze as a passing baseline stays blocked. Value fidelity does not prove source
business meanings. Cross-cutting L5 reproducibility records actual replay limits.

## First real C300 workload benchmark

Use all 720 approved bindings as the attempted population, plus explicit outcomes
for all twelve blocked. Record profiling COMPLETE/FAILED separately from M1
materialization COMPLETE/FAILED so one cannot mask the other's failure.
For each statistical attempt, build a bounded SourceTable only where feasible
and reuse unchanged `profile_table`,
`profile_column` on every column (top_limit=10, sample_size=5, sample_seed=0),
`find_duplicates` on all fields (group_limit=20, witness_limit=3),
`schema_fingerprint`, and `candidate_key_scan` with all singleton candidates and
pairs in the first three ordered fields (max_width=2, max_combinations=256).
These are full-population statistics only when the entire declared binding
population was consumed successfully; displayed witnesses are bounded. Record
attempted/completed bindings, rows, columns and candidate combinations per metric,
actual parameters, computation mode and exclusions. Resource-limited metrics are
NOT_COMPUTED, never PASS. Any explicitly chosen sample must report its population,
selection method, size and sampled scope and cannot stand in for a full-population
statistic. Mandatory schema fingerprints are independent of these optional metrics.
NULL-dependent metrics and candidate eligibility stay NOT_COMPUTED. Sample values
are EXACT_SAMPLE only and do not establish population uniqueness. Preserve original
PROFILING_OUTPUT_V1 envelopes; exports are projections with references to them.

Capture host and per-worker elapsed time, parent/member hash time and bytes,
parse time and bytes, each profiler's elapsed time, materialization and Delta commit
time, validation/query time, total wall time, peak process RSS, executor memory,
scratch/disk high water, Spark task retries, CPU/executor time, spill, shuffle and
Delta output bytes/files where exposed. Missing telemetry is UNAVAILABLE with a
reason. Report job/compute configuration, concurrency, cold/warm conditions and
actual CLI/job IDs. Never infer cost/DBUs if unavailable. Shared stages overlap:
do not sum worker times and label them end-to-end wall time.

Report compressed-input bytes/sec separately from uncompressed parsed bytes/sec,
records/sec and fields/sec, with explicit stage wall-time denominators. Record
physical, binding, occurrence and field coverage; per-stage failures; approved
completion ratio /720 and all-binding ratio /732; human authority decisions,
per-record interventions and intervention minutes when measured. No timing or
throughput numbers are fabricated today; there is no prior full C300 benchmark.
No speed target is invented for a first baseline. A partial run yields measured
partial coverage, not an all-C300 performance claim. Benchmark manifest records
whether profiling shared parsing, memory-budget failures and all extra I/O.

## Original Day 2 Write Task mapping

The user supplied the authoritative eleven-artifact Day 2 §7 checklist in the
execution-order instruction. All eleven remain required; see the baseline report
for actual locations, coverage, gaps and verified equivalents. The mapping below
retains the execution design and additional reused components. No duplicate active
metadata store is introduced.

| Requested artifact/task | Existing authority / equivalent | Missing output and planned disposition |
| --- | --- | --- |
| `source_inventory.csv` | `metadata/source_inventory.csv` (semantic inventory); C300 physical roster is the v3 manifest | Reuse; do not duplicate C300 identities into this inventory or treat it as the admission manifest. |
| `decision_log.csv` | `metadata/decision_log.csv`, DEC-000001–000005; `docs/decision_log.md`; freeze and parser authorization references | Append actual new model/evaluation decisions after review with actual time/status/authority; do not manufacture retrospective approvals. This proposal is the review evidence. |
| `schema_fingerprints.parquet` | Existing GOLD schema_fingerprint JSON and C300 ordered-header/binding evidence | Missing C300 mandatory structural export; derive per-binding SCHEMA_SHA256_V1 / RAW_HEADER_TEXT_V1 from existing function, retain binding hashes separately; blocked rows unavailable. |
| `corpus_manifest.csv` / v3 | Historical `metadata/corpus_manifest.csv`; active C300 authority `metadata/corpus_manifest_v3.csv` | Reuse v3 with exact hash; no active-registry switch or copy under a misleading new name. |
| `cohorts/C300.csv` | `metadata/cohorts/C300.csv` plus original freeze | Complete/reused unchanged; no regeneration. |
| `table_profiles.parquet` | GOLD JSON outputs in `runs/profiling/`; C300 shallow output is not equivalent | Missing; project unchanged full profiling envelopes to run-local Parquet, 732 binding-status coverage, completed metrics only where computed. Preserve duplicate/key outputs in referenced JSON. |
| `column_profiles.parquet` | GOLD column-profile JSON; `profiling_output_contract.md` | Missing C300; derive run-local per-column metrics with computation mode/reason and envelope reference. Do not synthesize blocked-table column populations. |
| `profile_run_manifest.json` | GOLD execution index and Agent/native checkpoints are earlier scoped equivalents | Missing C300 M1 combined manifest; pins canonical inputs, binding statuses, metric parameters, versions, stage metrics, telemetry gaps and all result hashes/Delta versions. |
| `docs/profiling_notes.md` | `docs/profiling_tools.md`, `profiling_output_contract.md`, freeze V2 and this proposal | Git-track at this exact path; future concise index to those authorities plus actual C300 memory/performance limitations; no copied policy/contract. |
| `reports/profile_summary_day2.md` | `docs/preflight_exit_checklist.md` and GOLD execution report cover prior GOLD only | Git-track at this exact path; future report of measured C300 workload, coverage, failure reasons, NULL limitations and linked manifest. |
| `reports/C300_baseline.md` | `docs/c300_admission.md`, frozen references; no M1 baseline yet | Git-track at this exact path; future report of O_C300_M1 artifacts, six test statuses, exclusions, replay coverage, decisions and actual freeze status. |
| Five tools / Agent V0 | Existing profiling functions, typed adapters, deterministic Agent and checkpoints | Reuse implementation and GOLD regression references; host adds C300 SourceTable bridge and execution packaging only. |
| Native execution / RAW → CLEAN → QUERYABLE | Successful NASDAQ bounded notebook/checkpoint | Reuse integrity/Delta evidence pattern; C300 job, tables and views remain unimplemented. |
| Lossless 1–6 / O_C300_M1 | Existing Evaluation Contract is specification only | Implement after approval; preserve failures, exact scope and immutable seal. |
| GOLD_V2 A–D; Stability A/B/C | Existing GOLD is regression reference | Explicitly deferred; neither prerequisite nor claimed complete today. |

The original Day 2 §7 Write Tasks remain execution requirements. Before
execution closeout, reconcile every original metadata artifact against the user
supplied exact checklist: produce it, or record a verified authoritative equivalent with exact
path/URI, version, hash, scope, schema/content coverage and verification evidence.
A related older GOLD artifact or a future plan is not a verified C300 equivalent.
The supplied eleven-item checklist resolves the earlier missing-text question;
unproduced/unverified artifacts must still be reported incomplete.

Git-track `docs/profiling_notes.md`, `reports/profile_summary_day2.md`,
`reports/C300_baseline.md`, updates to the existing decision log, the M1 contract
(at this path, pinned by hash), and a compact durable baseline manifest/summary at
`metadata/baselines/O_C300_M1.json`. These are future execution deliverables;
actual completion is recorded in the baseline report and compact status summary. The compact manifest is an evidence
index, not a second registry: reference canonical metadata and durable output
locations rather than copy source inventories. Log only actual decisions with
true status and authority; requested revisions are not approvals.

Large profiling exports, detailed results and operational artifacts may remain
outside Git under a new gitignored `runs/c300-m1/<run_id>/` bundle, with durable
copies referenced by the tracked summary. Required tracked documentation cannot
be replaced by same-named files inside that bundle. Do not commit RAW, large result
payloads, credentials or databases. Canonical metadata CSVs remain the sole registry
authority; Delta bindings/profile exports are explicitly scoped run evidence.

## Freeze plan and human review

Only after actual execution/evaluation write a new exclusive O_C300_M1 seal last.
It identifies the cohort hash, manifest hash, exact approval/registry membership,
model/rule specification hash, code/runtime/configuration, both Delta table versions,
view SQL hashes, profiles, benchmark, per-family Lossless results, block/error
inventory and file content hashes. Operational timestamps live outside deterministic
content fingerprints. Require a retrievable historical CLEAN Delta snapshot of both tables or an
equivalent durable preservation with demonstrated schema, values, multiplicity
and lineage recovery. A local gitignored runs/ directory, view, table name or
Delta version number alone is not a durable freeze. Preserve required Delta log
and data files, or a verified equivalent export, at recorded durable locations;
record snapshot/export versions, content hashes, scope and retrieval procedure.
Record retention owner, configured duration/expiry, deletion/VACUUM protections,
RAW-reference retention, and evidence of an actual retrieval/read-back validation
with observed hashes/counts. Unverified retention blocks the freeze. No storage
backend or retention period is silently selected by this proposal.
The tracked compact manifest links these retention facts, model/code/input hashes,
all 732 binding outcomes, actual evaluation results, output versions and durable
large-artifact references. Retention and retrieval evidence must exist before sealing.
Mandatory CLEAN or Lossless 1–5 incompleteness gets no successful completion seal.
Optional statistical NOT_COMPUTED outcomes alone do not block an otherwise valid
scoped CLEAN baseline; the seal and reports must preserve those outcomes. A frozen scoped result may honestly
retain BLOCKED/NOT_APPLICABLE outcomes; it must never be labeled full Lossless PASS.
No Stability acceptance is implied by historical preservation.

Actual blockers/risks are recorded in the baseline report: remaining processing
coverage, optional statistical resource/computation gaps, NUM supplemental parser
approval/recovery and verified durable historical retention. Three-family smoke
success establishes its actual bounded coverage, not large-member capacity or
full-corpus performance. Source NULL semantics remain unresolved without blocking
literal lexical preservation.

## Consequential review and execution boundaries

The two-table schema, three gated views, bounded expansion toward the 720 eligible
bindings, optional profiling and lexical-only Lossless 6 boundary are already
authorized by DEC-000006. No repeated routine approval is needed.

The new consequential question is the exact supplemental quote-boundary rule in
the NUM triage proposal. Preserve its PENDING status until a real human decision
arrives. If approved, validate and reprocess only the affected immutable bindings
under new versioned rules and rerun their actual Lossless checks; if unresolved,
retain exact BLOCKED/QUARANTINED evidence and continue unaffected bindings.

Retention is an evidence requirement before freezing, not permission to fabricate
a successful seal. Record actual owner, location, duration/protection and retrieval
evidence, or report NOT FROZEN. The eleven supplied Write Tasks require actual
artifacts or exact verified equivalents; no blanket waiver is implied. No RAW,
GOLD, frozen C300 or prior run may be overwritten. No commit, push, PR or merge.

## Subsequent execution authority and corrected order

The user subsequently approved the execution scope; see
[recorded authority](day2_c300_m1_authority.md), DEC-000006. The earlier requested
revision status above remains historical proposal context. Execution order is RAW
verification/parsing → CLEAN → actual Lossless 1–6 → exception triage/remediation
and retained per-binding Lossless Gate → QUERYABLE → downstream and end-to-end
validation → regression/performance and Write Tasks → verified durable freeze.
Internal diagnostic SQL may precede the gate; consumer records/fields views must
include only gate-PASS bindings. Each binding is gated independently; failures do
not prevent unrelated verified publication. All 732 binding outcomes remain in
coverage. The twelve NUM exceptions are under active triage, not permanent
exclusion. Any supplemental parser rule requires separate explicit human approval.

## Supplemental NUM approval

The user explicitly approved DEC-000007 after the proposal above. Append-only
DEC-000008 records that authority; see `c300_num_recovery_authority_v1.md`.
Exactly twelve frozen NUM bindings may undergo strict full-member validation and
conditional recovery with C300_FSDS_NUM_QUOTE_BOUNDARY_V1. Every failure remains
accounted for; only independent actual CLEAN Lossless PASS permits publication.
Original RAW, binding membership, failed evidence and completed outputs are unchanged.
No further routine parser approval is pending within this exact rule and scope.
