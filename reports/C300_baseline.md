# C300 M1 actual baseline status

**732/732 execution scopes validated; protected retention UNVERIFIED; NOT FROZEN.**
No final Day 2 freeze/completion seal or merge is issued. Frozen RAW admission and
all prior evidence remain unchanged. See `metadata/baselines/O_C300_M1.json`.

All 720 main bindings and the separately approved 12 NUM bindings are COMPLETE.
The combined views contain **314,164,116 DATA occurrences and
3,577,289,411 fields**, with all 732 binding outcomes. Source schemas,
literal values, duplicates, locators and lineage are preserved; no enterprise
mapping, business key, semantic NULL interpretation or economic conversion is added.

| Lossless test | Actual binding outcomes |
| --- | --- |
| 1 | `{'PASS': 732}` |
| 2 | `{'PASS': 732}` |
| 3 | `{'PASS': 732}` |
| 4 | `{'PASS': 732}` |
| 5 | `{'PASS': 732}` |
| 6 | `{'NOT_APPLICABLE': 732}` |

Tests 1–5 pass for all 732 bindings: source occurrence/field accountability,
independent RAW interval/member reconstruction, unchanged RAW parent hashes,
persisted exact multisets, locators and reproducibility/provenance. Test 6 is
NOT_APPLICABLE only under the approved lexical M1 boundary, with all 7,746 header
positions inventoried as PRESERVED_NOT_MODELED. Economic reconciliation is not PASS.

QUERYABLE exact record/field/coverage comparisons passed in disjoint, retained
checkpoints against four pinned source Delta snapshots. All bidirectional multiset
differences are empty; expected and observed counts match. Gate fingerprint:
`cb9639969f2f1de1ebdedeb10aa548fa7c1ce7d356a1cc5508be4e0a0e82d6fb`. Views were created only after source CLEAN gates.
Reconciliation uses disjoint UNION ALL, retaining each source operational run_id;
no NUM reprocessing or new CLEAN copy was performed. Table versions:
`{'workspace.edp_lab.clean_c300_m1_bindings_main_recovery_20261021_v4_full': 0, 'workspace.edp_lab.clean_c300_m1_bindings_num_recovery_20261021_v1_recovery': 0, 'workspace.edp_lab.clean_c300_m1_records_main_recovery_20261021_v4_full': 0, 'workspace.edp_lab.clean_c300_m1_records_num_recovery_20261021_v1_recovery': 0}`. SQL/hashes: `/Volumes/workspace/edp_lab/raw/c300-m1/reconciled_recovery_20261021_v2/full/queryable.json`.

An independent warehouse check retrieved 120 fields from one original
failure witness in each of the twelve NUM bindings and reconstructed exact captured
RAW bytes/hashes, with zero failures. This bounded witness check supplements the
full-population comparisons; it does not replace them. Replay scope remains the
original three complete smoke bindings, one per family, plus the previously
recorded first 1,024 physical occurrences per recovered NUM binding.

## Recovery and preserved work

Original main run 427800138450251 timed out at its existing eight-hour limit with
348/720 bindings staged. NUM run 653857229258835 remains unchanged and validated.
Recovery verified/reused 429 COMPLETE checkpoints: original348, 80 completed by the
first working bounded recovery, and one earlier Daily Master smoke outside the348.
Only 291 missing/incomplete bindings were parsed by the final recovery. All three
original smoke bindings were excluded from new parsing. Incomplete interrupted
work and two setup failures remain in the cost/time ledger; no known successfully
completed binding was restarted. See [performance](profile_summary_day2.md) and
[Performance Finding](day2_performance_finding.md) for the complete history.

## Original eleven Day 2 artifacts

Canonical metadata remains the registry. Run-specific equivalents below are
content-verified scoped evidence; they do not create a competing registry.

| Requested artifact | Authority / verified equivalent | Coverage |
| --- | --- | --- |
| `metadata/source_inventory.csv` | `metadata/source_inventory.csv; metadata/corpus_manifest_v3.csv; metadata/cohorts/C300.csv; runs/c300-m1/lexical_20261020_v2/source_inventory_projection.csv` | Canonical identities/projection reused; C300 semantic meanings UNRESOLVED |
| `metadata/decision_log.csv` | `metadata/decision_log.csv` | DEC-000006 and approved supplemental rule DEC-000008 preserved; recovery authority in versioned contracts |
| `metadata/schema_fingerprints.parquet` | `/Volumes/workspace/edp_lab/raw/c300-m1/reconciled_recovery_20261021_v2/full/schema_fingerprints.parquet` | 732 verified CLEAN headers; exact frozen ordered text names/types |
| `metadata/corpus_manifest.csv and v3` | `metadata/corpus_manifest.csv; metadata/corpus_manifest_v3.csv` | Canonical historical/additive manifests unchanged |
| `metadata/cohorts/C300.csv` | `metadata/cohorts/C300.csv` | Frozen 300 physical instances unchanged |
| `metadata/table_profiles.parquet` | `/Volumes/workspace/edp_lab/raw/c300-m1/stats_recovery_20261021_v2/full/table_profiles.parquet` | 732 outcomes; 304 complete full-binding tool-envelope sets; resource/NULL-dependent limits explicit |
| `metadata/column_profiles.parquet` | `/Volumes/workspace/edp_lab/raw/c300-m1/stats_recovery_20261021_v2/full/column_profiles.parquet` | 7746 positions; 3261 full-population column envelopes; other metrics NOT_COMPUTED |
| `metadata/profile_run_manifest.json` | `/Volumes/workspace/edp_lab/raw/c300-m1/day2_completed_recovery_20261021_v1/profile_run_manifest.json` | Combined actual code/runtime/inputs/outputs, 732 outcomes, statistics parameters, benchmark, SQL and retention limits |
| `docs/profiling_notes.md` | `docs/profiling_notes.md` | Scope and recovery/metric limitations |
| `reports/profile_summary_day2.md` | `reports/profile_summary_day2.md` | Original timeout, measured recovery, cost evidence and scaling implications |
| `reports/C300_baseline.md` | `reports/C300_baseline.md` | Actual six-test applicability, 732 results, provenance and retention blocker |

Combined acceptance/benchmark/manifest: `/Volumes/workspace/edp_lab/raw/c300-m1/day2_completed_recovery_20261021_v1`. Local reproducible
counterparts: `runs/c300-m1/day2_completed_recovery_20261021_v1/`. Separate main, NUM, reconciliation and
statistics manifests pin actual code, model/rule, dependencies, runtime, inputs,
Delta versions, SQL, outcomes and telemetry limitations. The tracked summary is an
evidence index, not a successful freeze seal. Large results/RAW remain outside Git.

## Remaining gate

Historical protected retention is UNVERIFIED: owner, protected duration/expiry,
deletion/lifecycle/VACUUM guarantees and RAW-reference retention require verified
policy evidence. Content read-back and a managed Volume/table version do not supply
that guarantee. No final freeze seal, global Day 2 PASS, Stability A/B/C, commit,
push or merge is declared. Source NULL semantics and candidate-key eligibility
remain NOT_COMPUTED as required; optional resource-limited metrics are explicit.

## FIN_EVAL_V1 closeout overlay — 2026-10-21

**Lossless 1–5: unchanged PASS for 732/732 bindings in the verified lexical scope.
Lossless 6: SCOPED_PASS for FIN_001/FIN_002, three filing/date contexts only.**
The earlier NOT_APPLICABLE inventory above remains the historical M1 execution
result. FIN_EVAL_V1 is attached evaluation metadata, not a replacement model or a
retroactive change to CLEAN. Other economic fields remain PRESERVED_NOT_MODELED /
NOT_APPLICABLE. This is normative L3 reconciliation, distinct from normative L6
RAW immutability. No global financial correctness or Stability acceptance is implied.

| Replay | Actual amounts / exact differences (USD) | Result |
| --- | --- | --- |
| FIN_001, 20221231 | Assets 384159000; liabilities 290982000; equity 93177000; total 384159000; both differences 0 | PASS |
| FIN_001, 20230630 | Assets 343482000; liabilities 251761000; equity 91721000; total 343482000; both differences 0 | PASS |
| FIN_002, 20230630 | Assets/total 30929500000; liabilities 15558800000; equity including NCI 15370700000; parent equity 14138000000; correct difference 0; wrong difference/implied NCI 1232700000 | PASS |

All returned numerical values match the supplied independent expected fixture with
Decimal equality and zero tolerance. FIN_001 requires four unique valid facts per
date; FIN_002 confirms five. The NCI difference is implied, not independently
verified against a separately disclosed NCI fact. Positive and negative controls
were executed on actual QUERYABLE results. One additional local regression passes:
offsetting wrong amounts and a suppressed negative-control difference are rejected.
Accepted earlier regression is reused: 188 passed/1 skipped in
`docs/day2_section_2_2_regression_review.md`; 58 passed in
`runs/c300-m1/reconciled_20261021_v2/implementation-validation.json`.
These historical counts describe their recorded code scopes, not a fresh full-suite run.

Contract, exact supplied SQL/fixture and study notes:
`metadata/evaluations/fin_eval_v1.json`, `sql/reconciliation/fin_eval_v1/`.
Full requests/responses, statement IDs, 13 source-line witnesses and hashes:
`runs/c300-m1/fin_eval_v1/replay-2/verification.json` and sibling files.
FIN_001 statement `01f1cd5b-63b5-15bf-8ec4-e4dbf8e5d462`;
FIN_002 statement `01f1cd5b-6d50-1df0-98bc-50ce45dfac44`.
The supplied FIN_002 projects differences only; a companion read of the same CTE
verified all fixture amounts. A failed lineage metadata query is preserved;
the corrected fields-view query returned 13 exact RAW/member-hash witnesses.
Records and fields definitions contain the exact historical saved SELECT SQL;
records definition also matches before/after replay. All four source Delta tables
still report version 0. No table/view write, RAW parse or full ingestion was run.

### Original tasks and actual coverage

| Requirement | Disposition / remaining scope |
| --- | --- |
| Structural profiling | COMPLETE: 300 physical inputs, 732 bindings, 7746 column positions; exact schema/lineage and outcomes retained |
| Statistical profiling | PARTIAL: 304/732 complete full-binding envelope sets, 3261/7746 column envelopes; 1,670,599 DATA records (0.532%); 257 member-budget and 171 time-budget outcomes NOT_COMPUTED. Semantic NULL/key eligibility remains NOT_COMPUTED. No population claims for missing metrics |
| Performance | PARTIAL measurement coverage: timeout/recovery, measured stage rates, bytes, outcomes and partial billing recorded in existing summary/finding. Executor memory/CPU, spill/shuffle, final monetary cost and active human minutes remain unavailable; no new ingestion benchmark required |
| Regression | Existing accepted scoped evidence reused; actual FIN positive/negative replay PASS, exact-value comparator regression PASS |
| Eleven Write Tasks | 11/11 authoritative equivalents mapped above; original hash readbacks retained in required-artifact-verification-v1.json and retrieval-validation-v1.json. No duplicate profile registry |
| Decisions | Record actual FIN approval only; no invented ten decisions or source interpretation |
| Original notes comparison | FIN bundle sections 6A–F/7 and original requirements transcribed in readiness document reconciled. Separate original Day 2 Study Notes text not located; exact independent line-by-line comparison remains UNVERIFIED pending its path |

### Owner review packet and remaining freeze requirements

**O_C300_M1 remains NOT_FROZEN; retention BLOCKED/UNVERIFIED.** Current SQL
readability and previous full hash/multiset verification support present scoped
reproducibility, not indefinite recoverability. SHOW TBLPROPERTIES exposed no
explicit deleted-file/log retention durations, append-only enforcement or VACUUM
protection. A supported appendOnly feature is not enforced protection. Prior
catalog inspection reported inherited predictive optimization ENABLE. No retention
property, optimization setting, lifecycle or access control was changed.

Before an actual freeze, supply/verify the designated retention-policy owner,
protected duration/expiry and deletion/lifecycle/VACUUM controls covering the exact
four Delta version-0 logs/data, referenced RAW/member sources, checkpoints and
operational/FIN evidence. Demonstrate recovery/readback from that protected copy
or documented equivalent using the existing hashes, schemas, counts and lineage;
no new full ingestion is needed. Preserve the two view definitions, model/parser/
runtime digests and all existing run references. Resolve the original-notes text
verification gap, retain the FIN evidence with verified retrieval, then obtain
owner acceptance of PARTIAL profiling/performance and scoped Lossless 6 before
writing an exclusive final baseline seal. The current closeout instruction authorizes a local Git commit of selected Day 2
artifacts; unrelated Day 2 implementation changes remain intact and uncommitted. No final freeze is issued.

FIN evidence retention checkpoint: the new bundle was uploaded to
`/Volumes/workspace/edp_lab/raw/c300-m1/fin_eval_v1_replay_20261021/fin-eval-v1-evidence.zip`
and retrieved byte-for-byte (247454 bytes, SHA-256
`9d0fc256970bf3815a9020bf628c960ee7f601ac6fd03596121ed211b758916d`).
The evidence-retention/readback step above is therefore complete for present
accessibility; protected duration and deletion policy remain unverified. See
`runs/c300-m1/fin_eval_v1/evidence-readback.json`.

Regression scope audit: core lexical M1, NUM recovery and gate implementation
hashes still match the accepted 58-test record. Its earlier reconciliation notebook
and report-generator hashes differ from the existing current Day 2 files; the
historical result does not certify those current revisions. Current actual SQL
validation is recorded separately. See
`runs/c300-m1/fin_eval_v1/regression-scope-audit.json`. The frozen cohort, canonical
source manifests, approval binding registry and source inventory hashes match
existing baseline references. The decision log receives only DEC-000009; historical
snapshot hashes remain historical, with the current digest indexed separately.

## Final owner-approved closeout

**O_C300_M1: FROZEN**, within the historical lexical and FIN evaluation scopes.
The owner's latest instruction authorizes the final seal after minimum retention
verification and accepts the Statistical Profiling, Performance and Free Edition
durability limitations. Earlier NOT_FROZEN/UNVERIFIED passages above describe
historical review checkpoints, superseded by this closeout. The owner-supplied
Day 2 §10 is authoritative; no alternative historical checklist is required.

| Exit evidence mapping | Disposition | Evidence / scope |
| --- | --- | --- |
| C300 admission and source identity | PASS | 300 frozen sources; unchanged cohort/v3 hashes |
| M1 CLEAN and QUERYABLE execution | PASS | 732 bindings; 314164116 DATA records; 3577289411 fields; pinned versions 0 |
| Lossless 1–5 | PASS | 732 scoped PASS each; historical gate and downstream multiset evidence |
| Lossless 6 | SCOPED_PASS | FIN_001 2/2 and FIN_002 1/1 exact fixture; other economic fields unmodeled |
| Structural and statistical profiling | PARTIAL_ACCEPTED | Structural COMPLETE; statistical 304/732 sets,3261/7746 envelopes,0.532% DATA records |
| Performance | PARTIAL_ACCEPTED | Measured/derived results in profile_summary_day2.md; missing telemetry retained |
| Regression | PASS_FOR_RECORDED_SCOPES | Historical accepted scopes reused; FIN positive/negative comparator; no certification of changed historical generator revisions |
| Write Tasks | PASS | 11/11 mapped authoritative artifacts verified |
| Retention, reproduction and owner-approved seal | PASS_WITH_ACCEPTED_LIMITATIONS | 90-day safeguards and readback PASS; owner accepts Free Edition workspace-loss risk; independent backup waived |

Day 2 Exit is COMPLETE within these owner-accepted scopes, subject to safe Git
integration and passing CI. This does not claim full statistical or performance
measurement coverage, global economic reconciliation, or disaster recovery.

All four historical CLEAN tables have verified `delta.logRetentionDuration =
interval 90 days`, `delta.deletedFileRetentionDuration = interval 90 days`, and
`delta.appendOnly = true`. Effective predictive optimization is disabled. Version 0
history is unchanged; version 1 is retention metadata only. Four bounded version-0
reads succeeded. Existing population-wide reconciliation is reused, and FIN_001
2/2 and FIN_002 1/1 match the exact fixture after protection. No full reprocessing
or recovery was performed. RAW verification found 300/300 matching parent hashes
(7,632,930,175 bytes). All 11 mapped Write Tasks retain their authoritative evidence.

Final protection SQL requests/results, before/after history, property/catalog
readbacks, FIN witnesses and RAW verification are retained at
`/Volumes/workspace/edp_lab/raw/c300-m1/final_freeze_20261022_v1/final-retention-evidence-v1.zip`
(140,792 bytes; SHA-256 `a541a990643b907334fd24b4fb8fb9d687be99ea1c522d57caf0ad91c23ed75d`),
with byte-identical readback. Original evidence URI/hash indices remain in
`metadata/baselines/O_C300_M1.json`. Seal, authorization and references are in
`metadata/freezes/O_C300_M1_v1/`.

Retention owner: baseline owner under the explicit current conversation approval.
Review/extend protection before 2027-01-18 UTC; avoid destructive VACUUM, DROP,
overwrite and baseline writer changes. These safeguards are not WORM. Privileged
owners can override them; RAW, SQL views and evidence remain mutable. Workspace
loss remains an accepted risk. Full independent recovery is NOT_VERIFIED and is
explicitly waived as a freeze prerequisite. The incomplete checkpoint backup is
excluded from recovery claims. Downloads stopped; no files were deleted.

Reproduction: retrieve indexed archives using `databricks fs cp dbfs:<uri>
<local-path> -p edp-lab`; verify SHA-256 before extraction. Restore archive member
paths and run `scripts/verify_fin_eval_v1.py` against saved replay-2 for the exact
SQL/fixture comparison. SQL replay requires the saved view definitions and pinned
version-0 snapshots. Historical runtime/code/input hashes and population checks
remain in the original manifests; mutable object names alone are insufficient.
