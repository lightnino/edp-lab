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

## Final closeout review (before owner seal)

**Baseline disposition: BLOCKED, NOT_FROZEN.** All eleven mapped Write Task
deliverables exist and contain their declared evidence. Structural Profiling is
COMPLETE (732/732 bindings); Statistical Profiling is PARTIAL (304/732 sets,
3,261/7,746 envelopes, 0.532% of DATA records). Performance is PARTIAL; actual
MEASURED/DERIVED timings, rates and NOT_MEASURED telemetry appear in the existing
`profile_summary_day2.md`. Partial statistical/telemetry outcomes are permissible
under the approved scoped contract, subject to owner acceptance; missing protected
retention is a technical freeze blocker. No full-population statistical PASS.

| Exit requirement | Status | Supporting evidence / remaining requirement |
| --- | --- | --- |
| Eleven Write Tasks | PASS for mapped deliverables | Existing mapping above; closeout write-task verification in supporting annex |
| M1 execution and reconciliation | PASS within lexical scope | 732 gates, 314,164,116 records, 3,577,289,411 fields; original pinned manifests/multiset checks |
| Lossless 1–5 | PASS within verified 732-binding scope | Historical M1 gates and downstream exact comparisons unchanged |
| Lossless 6 | PASS within FIN_001/002 scope | 2/2 and 1/1 exact fixture matches; other economic fields unmodeled |
| Structural Profiling | PASS / COMPLETE | 732 fingerprints (12 lexical hashes), 7,746 positions |
| Statistical Profiling | PARTIAL | 428 missing binding sets/4,485 positions; NULL/key metrics NOT_COMPUTED |
| Performance | PARTIAL | Scope-specific wall/rates and partial billing; no cold end-to-end, total I/O, final dollar cost or active-human timer |
| Regression | PASS for recorded scopes | Accepted historical tests and exact FIN positive/negative replay/comparator; scope audit retained |
| Git delivery | Local commit authorized; no push/merge | Selected closeout files only; remote main 90e067c retained unchanged; actual SHA reported by Git |
| Original Study Notes text acceptance | BLOCKED for independent exact-text comparison | Separate original checklist not located; current FIN and actual-results notes plus recorded eleven-task checklist reconciled |
| Present evidence retrieval | PASS | Existing exports/manifests/FIN archive SHA readbacks; small supporting annex covers otherwise local-only references |
| Historical retention/recovery | BLOCKED | Protected owner/duration/deletion/VACUUM policy and protected recovery proof missing |
| Final baseline seal / Day 2 Exit | BLOCKED | Requires verified retention and explicit owner acceptance before exclusive seal |

### Retention inventory and smallest remediation

| Artifact | Existing location and verified evidence | Protection status |
| --- | --- | --- |
| Original C300 RAW | `/Volumes/workspace/edp_lab/raw/c300-verified-v1/data/raw/`; all 300 parent hashes verified in historical Main physical/checkpoint evidence; 7,632,930,175 unique parent bytes | Managed Volume; retention owner, duration/expiry and deletion/lifecycle safeguards UNVERIFIED |
| Four CLEAN Delta snapshots | Exact version-0 table names above; 100 Main + 20 NUM record files and two binding files; total recorded Delta footprint 9,787,831,179 bytes | Current catalog objects accessible; supported appendOnly feature is not enforcement; no explicit retention durations or VACUUM protections established |
| QUERYABLE definitions | Records/fields catalog definitions checked against exact saved queryable.json SELECT text; FIN archive also preserves SHOW CREATE output | Definitions currently accessible and archived; live views remain mutable |
| Profiles/performance/manifests | Existing combined/Main/NUM/reconciled/statistics Volume locations above; current export and manifest readbacks match original hashes | Accessible; protected retention still UNVERIFIED |
| FIN SQL, fixtures, execution | Existing FIN archive URI/hash above; retrieved again with identical bytes | Accessible; protected retention still UNVERIFIED |
| Supplemental pointers and historical regression | New small supporting annex indexed in O_C300_M1.json; source projection, local-only receipts, catalog observations and exact job terminal evidence | Uploaded/readback verified; same unresolved Volume retention protection |

Smallest proposed remediation is to protect existing locations in place: designate
the retention-policy owner and explicit duration/expiry; restrict baseline writers/
deleters; exclude these tables from destructive VACUUM/optimization schedules and
record sufficient Delta log/deleted-file retention; protect RAW/evidence lifecycle
and deletion; then demonstrate protected readback/recovery against existing hashes,
versions, counts and lineage. Catalog ownership alone is not policy ownership.
Current catalog properties show predictive optimization INHERIT, not an established
freeze exception. No properties, permissions, optimization settings or storage
lifecycle were changed.

This proposal requires no full data copy or reprocessing. Existing footprint is
approximately 17.421 GB (unique RAW plus four Delta table footprints, before logs/
evidence); no incremental duplicate dataset was created. A full-copy fallback would
add approximately that footprint plus logs/evidence and read/write operations;
dollar cost is NOT_MEASURED and such a copy is not authorized. In-place protection
can add log/deleted-file retention storage over time; that increment is not measured.

Before proceeding, the owner must accept the declared scoped PASS/PARTIAL outcomes,
name the retention authority and protected duration, and authorize the concrete
in-place safeguards/recovery check. Supply the original Day 2 checklist or explicitly
accept the recorded checklist as the review authority. Only after technical retention
verification and final owner approval may the existing freeze convention issue a
new exclusive seal. No frozen-baseline artifact is prepared while Step 3 is blocked.

Reproduction: retrieve the indexed FIN archive and supporting annex with
`databricks fs cp dbfs:<uri> <local-path> -p edp-lab`, verify their indexed SHA-256
before extraction, restore archive member paths, then run
`.venv/bin/python scripts/verify_fin_eval_v1.py runs/c300-m1/fin_eval_v1/replay-2`
for the saved SQL/fixture comparison. This is a saved-evidence check, not new SQL.
Original model/rule/runtime bundles, RAW hashes, Delta versions and full-population
validation remain pinned by the unchanged historical manifests. A future SQL replay
must use the retained view definitions/pinned snapshots; a name alone is insufficient.
