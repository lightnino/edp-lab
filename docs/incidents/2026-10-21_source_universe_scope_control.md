# EDP Lab Incident — Source Universe Boundary / Unauthorized Scope Expansion

**Incident ID:** EDP-INC-2026-10-21-001
**Observed on:** 2026-10-21 (SGT)
**Status:** OPEN — Option 2 selected; remediation not yet executed
**Classification:** Scope governance / admission authorization control gap
**Decision (experiment owner):** Option 2 — preserve original 3,021 authorized-universe snapshot; exclude the 800 outside-scope instances from the current experiment through logical rollback, without deleting physical RAW.
**Remediation state:** SELECTED / NOT IMPLEMENTED. Existing C750/C1500/C2000 freezes are historical execution evidence, not accepted scope-compliant experiment baselines.
**Retention decision:** RETAIN ALL 800 RAW objects (local and Databricks) for audit, legitimate future source-onboarding proposals and subsequent approved experiments. No deletion workflow planned.
**Day 2:** C300/M1 remains independently active. Last independently reported checkpoint: 21/32 reconciliation groups PASS, 3 running, 8 pending, zero failures, controller PID 72896 alive, optional statistics complete (2026-10-21 16:26 Shanghai/SGT). This is a historical checkpoint, **not** a live-status assertion. Final full-scope acceptance and historical retention verification remain pending. Do not touch its worktree, jobs, controller or checkpoints.

**Required GitHub location:** `docs/incidents/2026-10-21_source_universe_scope_control.md`. Publish through a **new dedicated documentation branch/worktree based on `main`**, commit and push the branch and open a documentation-only PR for review; do **not** merge Day 3–5 branches or alter the active Day 2 worktree. Until a GitHub URL / commit is reported, repository publication is **NOT VERIFIED**.
**Evidence basis:** User-supplied Codex audit and Day 3–5 execution summaries. Not independently verified against the user's local Mac or Databricks account.

## 1. Intended versus observed scope

The user's stated intended experiment was to sample and scale **within one original RAW source universe of 3,021 inventory entries**, preserving 41 independent Day 13 holdouts. Whether the historical written admission policy formally prohibited subsequent external acquisitions remains to be verified; no prior explicit user approval of widening this baseline has been identified in the present evidence.

Actual frozen C2000 membership: **2,000 independent physical Source Instances**, consisting of **1,200 from the original 3,021 inventory** and **800 from later acquisitions outside that inventory**:

| Day | Added source outside original 3,021 | Count |
| --- | --- | ---: |
| Day 3 | NOAA GSOD | 50 |
| Day 4 | NOAA GSOD | 250 |
| Day 5 | World Bank WDI | 400 |
| Day 5 | U.S. Treasury annual XML | 100 |
| **Total** | | **800** |

The 800 were reportedly acquired, admitted with distinct IDs and RAW SHA-256/provenance, transferred to Databricks RAW cohort prefixes, and verified by remote readback. They are represented in the canonical admitted corpus manifest, **but not in original whole_lab_inventory_v1/v2**. Their exact common local RAW-root arrangement has not yet been separately verified.

This is **not evidence of fabricated data or failed transfer integrity**. It is a distinct failure to gate cohort selection against an authorized universe and a missing or unapproved source-universe version transition.

## 2. Detection

Discovered during parallel operation: Day 2 **C300/M1 RAW → CLEAN → QUERYABLE** reconciliation was still running while separate Day 3/4/5 worktrees advanced cohort membership **C300 → C750 → C1500 → C2000**, uploading/profiling the increments. While assessing the planned Day 7 extension to **C3000**, the experiment owner asked if the **41 Day 13 holdouts** (CFTC, NYC Taxi, ECB) would be consumed or contaminated. Naive arithmetic for the closed original universe showed `3021 - 41 = 2980 < 3000`. An agent then claimed there were **1,774** eligible unused candidates and no N1000 shortfall. Read-only reconciliation exposed the missing assumption: C2000 already included **800 out-of-original-universe acquisitions**, so only 1,200 of its 2,000 members consumed original inventory. That discrepancy triggered the incident. A read-only inventory reconciliation found:

| Population | Count |
| --- | ---: |
| Original v1/v2 inventory | 3,021 |
| Original entries appearing in frozen C2000 | 1,200 |
| C2000 admitted from outside original inventory | 800 |
| Original entries not in C2000 | 1,821 |
| Of those, four existing GOLD admissions | 4 |
| Original unadmitted entries | 1,817 |
| Reserved Day 13 holdouts, unused | 41 |
| SEC_BULK candidates not yet qualified | 2 |
| Qualified unused non-holdout original candidates | 1,774 |
| N1000 shortfall if external acquisitions may be used | None — 774 candidate surplus before any other selection constraints |

The inventory identity **3,021** is correct: it includes two SEC bulk candidates even though their *admission qualification* is not established. **Universe membership and admission eligibility are different gates.** Excluding 41 Day 13 holdouts gives an absolute ceiling of **2,980** original-universe non-holdouts. Current evidence establishes **2,978** eligible/previously admitted non-holdouts (including four GOLD) and two not-yet-qualified bulk candidates. The experiment owner has **not selected C2978** as the final cohort size. Qualifying both bulk candidates could bring eligibility to 2,980, but still cannot yield C3000 without an explicitly approved future universe/sampling change. No new cohort has been frozen.

All 41 recorded Day 13 holdouts remain excluded from C2000. The frozen cohorts, admission/receipt hashes and Git commits were reported clean. **Do not equate mechanical admission/hash PASS with scope authorization PASS.**

### Full source-family distribution: authorized v1 versus outside-scope acquisitions

Counts are **physical candidate/source instance records**, not source records, ZIP members, logical bindings, or business entities. `Original selected in C2000` is historical execution membership **not** acceptance as the authorized C2000 baseline.

| Source family | Original approved universe | Original selected in existing C2000 | Extra out-of-universe admitted in existing C2000 | Original unused holdout | Original unused qualified non-holdout | Unresolved original qualification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SEC_EDGAR_DAILY_MASTER | 2,866 | 1,093 | 0 | 0 | 1,773 | 0 |
| SEC_FSDS | 61 | 60 | 0 | 0 | 0 | 0 (1 previously admitted GOLD) |
| SEC_13F | 43 | 42 | 0 | 0 | 0 | 0 (1 previously admitted GOLD) |
| SEC_BULK | 2 | 0 | 0 | 0 | 0 | **2** |
| NASDAQ_DIRECTORY | 2 | 0 | 0 | 0 | 0 | 0 (2 previously admitted GOLD) |
| NASDAQ_TRADED_DIRECTORY | 1 | 0 | 0 | 0 | 1 | 0 |
| TREASURY_ANNUAL_XML | 5 | 5 | **100** | 0 | 0 | 0 |
| CFTC_COT | 28 | 0 | 0 | **28** | 0 | 0 |
| NYC_TLC_TRIPS | 12 | 0 | 0 | **12** | 0 | 0 |
| ECB_REFERENCE_RATES | 1 | 0 | 0 | **1** | 0 | 0 |
| NOAA_GSOD | 0 | 0 | **300** | 0 | 0 | 0 |
| WORLD_BANK_WDI | 0 | 0 | **400** | 0 | 0 | 0 |
| **Total** | **3,021** | **1,200** | **800** | **41** | **1,774** | **2** |

Note: the four previously admitted GOLD original entries are outside C2000 but already registered (SEC_FSDS 1; SEC_13F 1; NASDAQ_DIRECTORY 2). Therefore `1,200 + 1,774 + 41 + 2 + 4 = 3,021`. The original non-holdout ceiling is **2,980**, subject to eligibility of the two SEC_BULK candidates. The extra 800 remain physically legitimate and reproducible, but are **not** approved for the current experiment. The `ECB_SDMX` prospective reserved source family has **zero** original-inventory entries; `ECB_REFERENCE_RATES` has one holdout.

Source-family permission is not instance-level authorization: even Treasury, a pre-existing original family, requires an explicit approved source-instance membership or governed incremental ingestion policy to join a frozen experiment.


## 3. Proximate cause and missing control

- Day 3–5 instructions prioritized additional independently qualified physical Source Instances and greater family diversity beyond SEC/NOAA.
- The instructions failed to require that *candidate membership belong to the authorized Source Universe version*, or to obtain an explicit scope-change authorization before acquiring new source families.
- The admission gates correctly checked provenance, hashes, overlap, holdouts, local/remote byte integrity, and structural coverage, but lacked a **universe-authorization gate**.
- The original whole-lab inventory remained an original-acquisition snapshot while newer accepted sources appeared in the canonical admitted corpus manifest. This split was not presented as a governed universe version change with an explicit authorization decision.
- The failure is a **control-design / instruction / governance gap**; it must not be attributed solely to Codex or to an individual engineer without stronger evidence.

## 4. Potential impact (not all observed)

**Observed:** 800 legitimate but unauthorized-for-this-experiment instances admitted into C2000; related Day 3–5 cohort freezes and RAW uploads exist in local branches and Databricks; original inventory count no longer represented the full known acquired universe. Day 2 main validation was running independently and must not be interrupted.

**Potential, requiring verification:** violation of experimental sampling plan; biased / incomparable stability and engineering-effort measures; widening parsing and semantics without prior approval; increased cloud storage / execution cost; unauthorized source/domain/entitlement access; downstream lineage and reconciliation population mismatches; contamination of future holdout evaluation if an explicitly reserved source is processed (no such contamination reported for the 41 holdouts); job code using directory glob/listing that inadvertently consumes all available data; uncontrolled model drift / identity collisions; ability to reproduce frozen experimental observations weakened if membership is derived dynamically.

The incident does **not** prove that downstream CLEAN/QUERYABLE processed the 800 or that production data was exposed. The supplied summaries only establish admission, RAW upload, remote readback and structural profiling for Day 3–5 increments. Investigate actual dependencies before changing storage.

## 5. Decision and remediation — OPTION 2 SELECTED, NOT YET EXECUTED

### Approved choice — Option 2: return to original authorized 3,021 Source Universe

On 2026-10-21 the experiment owner selected **Option 2, logical rollback first**. The current experiment must draw members only from the original, pinned 3,021-instance universe, subject to admission qualification and preservation of the 41 holdouts. An agent/engineer attempting to insert a real, well-formed, hash-verified but unauthorized instance must receive **OUT_OF_SCOPE / ADMISSION_DENIED**. Do **not** mislabel the original source as corrupt, invalid or rejected on data-quality grounds.

**Decided:**

1. Preserve original v1/v2 inventory and its 3,021 recorded identities/hashes as the **authorized experiment-universe reference**. No silent edits to frozen historic evidence.
2. Mark all 800 later acquisitions as **legitimate RAW, NOT AUTHORIZED FOR CURRENT EXPERIMENT**. They remain eligible *candidates for a later explicitly approved expansion* and must not be cast as invalid source data.
3. Mark current C750/C1500/C2000 frozen membership and processing-readiness evidence as **historical execution artifacts, NOT ACCEPTED under the restored original-universe authorization**. Preserve all Day 3–5 Git commits, freeze records, tests, and receipts; do not merge/promote them as accepted cohort versions. The code may be reused after controlled review.
4. Preserve **all** 800 local and Databricks RAW objects and their SHA-256/provenance/upload receipts. **No physical deletion, no VACUUM, no `DROP VOLUME`, no purging.** Preserve future ability to propose these sources for C4000/C10000/larger authorized experiments. Storage retention remains subject to applicable organizational policies, but no deletion action is requested.
5. Do not automatically classify the 800 as a normal daily 2 GB delta: that was an **analogy illustrating normal, legitimate ongoing source-estate growth**. In a production workflow any real daily increment follows its own approved CDC/source contracts; it cannot silently contaminate the frozen sample.
6. Rebuild affected post-C300 cohort versions from approved original-universe members after C300/M1 baseline acceptance and appropriate scoped planning. Use new versioned cohort artifacts, keep old ones intact, rerun all applicable mechanical and semantic gates, and retain a crosswalk showing replaced/excluded members and consequences.
7. Implement a mandatory **mechanical fail-closed authorized-universe admission gate** (scope ID/version, instance ID, hash, owner/grant where relevant, holdout exclusion, explicit cohort membership), independent of prompt wording. Tests must reject unauthorized but otherwise legitimate inputs and prevent wildcard/prefix scans from expanding a frozen processing run.
8. Keep all 41 Day 13 evaluation holdouts untouched. Final Day 7 sample size remains **pending independent design decision**; theoretical authorized non-holdout maximum is 2,980, currently evidenced eligible is 2,978 pending the two SEC bulk candidates. Do not force C3000 or misstate 3,021 inventory count.

### Rejected alternative for the current experiment — Option 1

Authorizing all 800 now, appending them to a 3,821-member expanded experiment universe and treating existing Day 3–5 cohort freezes as accepted under that new universe **was not selected**. This does **not** prohibit a future, separately authorized universe version with some or all of these sources; it only prohibits retroactive or automatic admission to the **current** experiment.

### Implementation and acceptance state

- **Human decision:** COMPLETED — Option 2 chosen.
- **Physical RAW retention:** DECIDED — retain, do not delete.
- **Incident documentation:** recorded in this file; Git commit/merge status to be recorded separately when performed.
- **Mechanical admission gate and Agent escalation workflow:** NOT IMPLEMENTED / NOT VERIFIED. Must be implemented before any further authorized cohort extension; then exercised as part of Agent V1–V6 evolution and the Day 12 release evaluation, not solely written as a prompt.
- **Rebuilt authorized cohorts:** NOT STARTED.
- **Day 2 C300/M1 acceptance:** PENDING as of last report.
- **Incident closure:** OPEN until authorized cohort baselines, guardrail tests, and source/object accounting have been validated.

## 6. Enterprise 2 PB migration analogy and required preventive controls

A real enterprise migration source estate might be ~2 PB, with 2 GB/day of ordinary new business events (the user stated this **as an analogy**, not a measured EDP Lab ingestion workload). Such increments can be legitimate, retained, and later incorporated into a **new approved cohort version**, but must never silently change the fixed prior experiment. The **moving production source estate**, **approved migration scope**, **fixed experiment sample**, and **daily incremental CDC/landing stream** must be distinct populations.

Illustrative contract:

- `source_estate(t)`: continually growing authorized business data.
- `migration_scope_v1`: owner-approved source systems, time ranges, cutoffs and classification boundaries.
- `experiment_cohort_vN`: an explicitly authorized, feasible and frozen set of source-instance IDs + hashes derived from one pinned approved universe version. Its count is a declared experiment parameter, not a quota that overrides the scope boundary.
- `daily_delta(t)`: normal new transactions/market records, handled by a separate change-capture/incremental path with offsets/watermarks, not silently appended to `experiment_C3000_v1`.
- `scope_change_request`: required before adding an out-of-universe source, even if the object passes byte-integrity checks.

Consequences of failing this gate may include inadvertent new data/security domains, uncontrolled cost, semantically invalid joins, new parser/identity assumptions, changes to economic reconciliation populations, experiment leakage/selection bias, broken as-of reproducibility and invalid comparisons of model versions.

**Required future mechanical gate (concept):**

```
FOR EACH candidate_source_instance:
  ASSERT candidate is registered in approved_universe_version
  ASSERT candidate source/period/domain is in approved migration_scope
  ASSERT candidate is not in reserved_holdout_population
  ASSERT candidate has required provenance, legal/data access and storage policy
  ASSERT candidate identity + RAW hash are valid and not overlapping as forbidden
  ELSE BLOCK ADMISSION/TRANSFER/PROCESSING AND EMIT REVIEWABLE EVIDENCE

FOR EACH run:
  ASSERT explicitly pinned cohort_id + manifest_hash + model_version + code_version
  ASSERT no implicit glob/directory scan can extend frozen membership
  ASSERT every processed source ID belongs to approved input roster
```

Reconciliation should distinguish `(authorized, selected, transferred, successfully processed, blocked/quarantined)` and should fail closed when an unexpected source appears; new arrivals should enter only separately versioned incremental cohorts or formally approved source-estate change flows.

## 7. Containment, ownership and unresolved questions

**Planned containment and implementation (Option 2 selected; actions below not yet executed unless stated):**
1. Preserve the incident evidence and existing freeze/transfer receipts. Do not interfere with the running Day 2 C300/M1 reconciliation.
2. Stop unauthorized cohort expansion. Source acquisition and RAW retention may continue under separately authorized source-estate workflows, but Day 7 selection cannot consume data outside the pinned original universe. No new Day 7 experiment membership until the mechanical gate and revised sampling plan are reviewed.
3. Read-only dependency inventory: check which source-set version each ingestion/processing command accepts and whether any dynamic directory listing can expand a frozen cohort; enumerate the 800 Databricks RAW objects, remote prefixes, sizes and any downstream consumers. Inventory and retain objects, **not a deletion candidate list**. The combined ~406.6 MB reported for Day 3–5 entire incremental-cohort uploads is **not** a measured byte size of the 800 only; compute the exact 800 subset if needed.
4. Implement a fail-closed authorized-universe membership gate in the actual deterministic admission/cohort freeze paths and, where relevant, processing manifest validation. Add regression tests that deliberately present (a) valid-hash, out-of-universe source; (b) legitimate new daily data not in frozen cohort; (c) original-inventory Day 13 holdout; and (d) same source family but unapproved new instance. All must be denied for this frozen experiment, with explicit machine-readable escalation and without labeling RAW invalid. The Agent must propose a separately authorized universe version rather than override this gate. Integrate it into Agent evolution / evaluation.
5. Investigate the two original-inventory SEC_BULK candidates (Companyfacts/Submissions): existence of authentic RAW bytes, hash, acquisition receipts, publisher provenance, qualification status, archive/member structure, admission blockers and intentional deferral reason. Original universe membership is already confirmed; do not alter `3,021` or grant PASS by membership alone. If evidence is complete, propose an ordinary controlled admission under the approved universe; otherwise preserve BLOCKED/UNRESOLVED and exact reason. A distinct incident exists only if a separate control failure is substantiated.
6. Execute the selected Option 2 in a separate scoped change after Day 2 acceptance, with authorized replacement cohort versions, explicit exclusions and full regression; record evidence and any changed study results. Until then, keep prior Day 3–5 freezes/commits as historical evidence, not approved baselines.

**Decision owner:** User / designated experiment owner (not automatically the agent).
**Current decision:** OPTION 2 SELECTED by experiment owner; implementation pending.
**Root cause confirmation:** Observed instruction-level missing scope gate; repository-level policy/implementation audit still pending.
**800 physical RAW relocation/deletion:** The owner explicitly decided **RETAIN / NO PHYSICAL DELETION**, including Databricks. They are legitimate candidate assets for a future separately approved universe expansion; do not reclassify as automatically admitted daily increments, delete, relocate, or overwrite. Retention does not grant current-cohort approval.
**Day 13 holdouts:** preserved by the reported audit.
**Main Git branch / Day 2 jobs:** no changes requested by this incident report.

## 8. Supporting local evidence (paths provided by Codex; not opened here)

- `runs/whole_lab/candidates-v1/completion-summary.json`
- `runs/whole_lab/candidates-v1/whole_lab_inventory_v1.csv` (SHA-256: `99f09213dc17d845a4ea6e97dfd6b99fabf7e4a7f5cb618253f7040fa706ca6c`)
- `runs/whole_lab/layout-v2/whole_lab_inventory_v2.csv` (SHA-256: `1dcf16137a3a3cd0be3c4f025d9e6274e2a9bba34163e121004a97b1961bc45a`)
- `runs/whole_lab/layout-v2/path-mapping.json`
- `metadata/cohorts/C2000.csv`; `metadata/corpus_manifest_v6.csv`; `metadata/freezes/N500_v1/freeze.json`
- `runs/n500/frozen-v1/review.json`; `runs/n500/frozen-v1/historical-gate.json`
- Day 3 upload/profiling commit `c223117058c955ce6d9858eba9a35e190bf04da6`
- Day 4 upload/profiling commit `2eee969`
- Day 5 freeze commit `c2ed689d388e6a04da705b8f17151120969ce22b`
- Day 5 upload/profiling commit `b9f5dc7efd2197c6e4aa39e14aae8c38c326ecce`
- Databricks N500 RAW prefix: `dbfs:/Volumes/workspace/edp_lab/raw/n500-raw-v1-2bde6cf62012`

## 9. Relevant industry guidance

- AWS Prescriptive Guidance, *Wave planning — Managing change*: https://docs.aws.amazon.com/prescriptive-guidance/latest/application-portfolio-assessment-guide/wave-planning.html (single source of truth for migration wave scope; formally identify, analyze and communicate scope changes).
- Microsoft Cloud Adoption Framework, *Execute migration to cloud*: https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/migrate/execute-migration (change freeze, automated gates, validation, fallback).
- Databricks, *Unity Catalog best practices*: https://docs.databricks.com/aws/en/data-governance/unity-catalog/best-practices/ (govern external RAW locations, controlled grants and isolation).
- Databricks, *Auto Loader production*: https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/production (new-arrival tracking and incremental checkpoints, distinct from fixed experimental membership).
- Databricks, *Expectation recommendations and advanced patterns*: https://docs.databricks.com/gcp/en/ldp/expectation-patterns (quarantine separate from accepted processing).

## 10. Decision log and follow-up guardrail acceptance

| When | Decision / observation | Evidence or owner |
| --- | --- | --- |
| 2026-10-21 | Inventory reconciliation exposed 800 source instances outside original 3,021 after concurrent C300 processing and Day 3–5 admissions/uploads | User-supplied read-only Codex audit |
| 2026-10-21 | Selected Option 2: restore original 3,021 experiment universe, reject unauthorized cohort-admission attempts, preserve all historical evidence and all 800 RAW objects | Experiment owner |
| 2026-10-21 | Corrected count semantics: two SEC bulk entries are **in the 3,021 inventory**, not yet qualified for admission; raw maximum 2,980 non-holdouts, eligible presently 2,978 | User challenge and original inventory status audit |
| 2026-10-21 | Retention is an affirmative owner decision: preserve all 800 legitimate RAW objects, eligible for consideration in a future authorized universe version; no Databricks cleanup/deletion plan | Experiment owner |
| 2026-10-21 | As last reported, Day 2 C300/M1 reconciliation 21/32 PASS, 3 running, 8 pending, zero failed; no interference permitted | User-provided Codex check |
| Future | Verify guardrail using an **otherwise valid** out-of-universe source and ensure the agent requests authorization rather than silently widening scope | Pending deterministic negative test |
| Future | Verify approved future cohort growth may incorporate previously retained 800 without rewriting original inventory or old frozen cohort | Pending versioned-scope test |
| Future | Freeze replacement cohorts and run Old/New/Combined Lossless/Stability gates | Pending controlled remediation |

**Incident is evidence of a boundary design failure, not evidence the extra RAW data are illegitimate. Retention is intentional: preserving them as real, auditable candidate assets enables legitimate future expansion while keeping the current experiment uncontaminated.**


## 11. SEC_BULK original inventory investigation — open, not automatically a second incident

The two entries `LOCAL_SEC_BULK_COMPANYFACTS` and `LOCAL_SEC_BULK_SUBMISSIONS` **are already members of the original 3,021 authorized candidate universe**. Their current recorded statuses do not prove independent qualified-delivery admission. Membership in an approved candidate universe is necessary, **not sufficient**, for physical-source admission. Before deeming this a separate problem, inspect the original completion report and acquisition/status evidence to distinguish an intentional reserved/unready candidate from a lost upload/receipt or actual code defect. Verify bytes, hash, path, provenance, physical-vs-logical-unit grain, and relevant admission rules. Keep the two within the 3,021 universe even if admission is `BLOCKED` or `UNRESOLVED`; do not silently promote or remove them. Record exact determination, evidence paths, any remediation and effect on 2,978/2,980 eligible ceiling. No inference of qualification is authorized by this incident record.

## 12. Remediation execution ledger — update with concrete proofs; do not claim completion prematurely

| Stage | State as of incident decision | Actual start (SGT) | Actual finish (SGT) | Evidence (commit, tests, PR, run) |
| --- | --- | --- | --- | --- |
| Discovery and read-only reconciliation | **COMPLETE** — 2026-10-21 | 2026-10-21 | 2026-10-21 | Original inventory v1/v2, C2000 freeze, Codex audit; full paths §8 |
| Decision: Option 2 + retain 800 RAW | **DECIDED** — 2026-10-21 | 2026-10-21 | 2026-10-21 | Owner instruction recorded in this incident |
| Incident documentation committed/published on GitHub | **PENDING VERIFICATION** | TBD | TBD | Add commit SHA, branch, GitHub PR URL |
| Local/remote 800-object disposition and dependency inventory | **NOT STARTED** | TBD | TBD | Add read-only inventory paths, counts and hashes |
| SEC_BULK candidate-status investigation | **NOT STARTED** | TBD | TBD | Add exact qualifying evidence and explicit result for both |
| Deterministic universe/cohort gate + negative tests | **NOT STARTED** | TBD | TBD | Add code paths, test cases, actual PASS/FAIL |
| Agent unauthorized-source escalation test | **NOT STARTED** | TBD | TBD | Add Agent version, tool calls, actual blocked attempt and approval trace |
| Authorized replacement cohort design/selection | **NOT STARTED; WAIT FOR DAY 2** | TBD | TBD | Add owner-approved plan and membership hash |
| Authorized cohort processing / Lossless / Stability | **NOT STARTED** | TBD | TBD | Add model version, OLD/NEW/COMBINED results |
| Incident accepted/closed | **OPEN** | TBD | TBD | Closure conditions below |

**Closure conditions:** all 800 out-of-universe members excluded from any *currently approved experiment* cohort; original 3,021 source-universe snapshot and 41 holdouts unchanged; full retained RAW accounting (local + Databricks), no deletions; exact status of both SEC_BULK entries understood and recorded; fail-closed mechanical membership and frozen-run validation tests demonstrably pass; Agent cannot self-authorize scope expansion; authorized replacement cohorts and regressions accepted; reviewable GitHub incident/implementation evidence and dated closure approval. A decision alone is not incident resolution.

**Preferred implementation sequencing:** (A) document and publish incident on separate documentation-only branch now, while Day 2 runs; (B) independently audit SEC_BULK and the 800 disposition, read-only; (C) implement the deterministic scope gate and Agent-control tests in an authorized code-change branch without changing active Day 2; (D) after Day 2 baseline acceptance, freeze new compliant expansion cohorts and verify real runs; (E) record measured outcomes, close only upon acceptance. The 800 may enter a **future** approved universe version; not this one.

## 13. Independent local governance audit — 2026-10-21

This section supersedes the earlier “not opened here” qualification and NOT STARTED audit rows only for the checks explicitly recorded below. The supplied owner report above is retained in full. Solution 2 remains selected; implementation remains PENDING and incident OPEN. Industry links in §9 were supplied by the owner and were not independently consulted in this offline audit.

### Audit boundary and reproducibility

Worktree `/Users/lightnino/Projects/edp-lab-incident`, branch `incident/source-universe-scope-control`, began clean at `ddb6e47c52afa08415614dc7f341255255d9c963`, exactly local `main` and its merge base. Remote: `origin https://github.com/lightnino/edp-lab.git`. Historical Day 3/4/5 worktrees at `c223117`, `2eee969`, `b9f5dc7` were read only. No merges/cherry-picks, code changes, RAW scans, downloads, transfers, jobs or Day 2 operational inspection occurred. GitHub publication is the only authorized network operation for this task. Local main ancestry is verified; remote main is checked during publication.

Owner input: `/Users/lightnino/Downloads/2026-10-21_source_universe_scope_control_incident.md`. Original decision dates have day precision only; exact discovery, proposal and owner-decision times are UNKNOWN. The Day 2 21/32 checkpoint remains a supplied historical observation, not independently refreshed.

Evidence documentation:

- [Metadata and receipt hash index](2026-10-21_evidence_index.md).
- [All 800 retained RAW references](2026-10-21_retained_raw_references.md), including per-instance acquisition identity, receipt hash, RAW hash, local path, remote path/status/time and historical processing references.

Count method: compare v1/v2 inventory `(inventory_id, sha256)` sets; crosswalk C2000 manifest members through frozen packet `original_raw_path` plus exact RAW SHA-256 to inventory v2 `final_path` plus SHA-256. This is a mechanical delivery-reference join, not semantic identity inference or a new registration rule. Existing GOLD uses its retained manifest path. Inventory v1/v2 hashes match §8. Both contain 3,021 entries and identical identity/hash sets. Original completion summary records 3,015 new verified publisher deliveries, four unchanged GOLD and two unadmitted bulk candidates; zero admissions/freezes in that acquisition step. Source Instances are physical deliveries, never ZIP members or rows.

The full family table in §2 is independently confirmed without corrections: original 3,021; C2000 2,000 = 1,200 original + 800 later acquisitions; unused original non-holdouts excluding GOLD and unresolved bulk 1,774; four GOLD outside C2000; 41 original holdouts; two bulk candidates. All original holdouts are absent from C2000. “Qualified unused” here means historical acquisition/selection readiness, not newly granted admission or semantic approval. Maximum 2,980 original non-holdouts; the report's 2,978 excludes both unresolved bulk entries. Neither number is an owner-approved new scale target.

### SEC Bulk findings — separate determinations

Evidence for both: `/Users/lightnino/Projects/edp-lab/runs/local_inventory/availability.json`, observed `2026-10-20T09:12:00.756956+00:00`; inventory v1/v2; completion summary `existing_bulk_candidates_unadmitted: 2`; admission evidence requirements in `docs/corpus_admission_policy.md`. These are deliberately staged candidates with no registered Source ID, not failed qualified deliveries. No evidence establishes a permanent intention to exclude them. No unsupported-ZIP admission rule or separate admission defect was established. Parser approval remains a separate later gate.

| Field | LOCAL_SEC_BULK_COMPANYFACTS | LOCAL_SEC_BULK_SUBMISSIONS |
| --- | --- | --- |
| Original membership | CONFIRMED | CONFIRMED |
| Physical RAW integrity | VERIFIED in retained historical SHA/archive evidence; current bytes UNVERIFIED (no rescan) | VERIFIED in retained historical SHA/archive evidence; current bytes UNVERIFIED (no rescan) |
| Current accessibility | Readable file; size/inode/mtime match historical record by stat | Readable file; size/inode/mtime match historical record by stat |
| Local path | `/Users/lightnino/Projects/edp-lab/data/raw/sec/bulk/companyfacts.zip` | `/Users/lightnino/Projects/edp-lab/data/raw/sec/bulk/submissions.zip` |
| Recorded bytes | 1,418,648,998 | 1,974,869,371 |
| Recorded SHA-256 | `23e23cc8293fa22abda2f7d0568ee5534e149b51a77cd40171c3d834278cc902` | `5c75f9d996d5eea8a0e05689e28079d069a80e1632cf87ba24021da7e48d465b` |
| Historical archive integrity | PASS; 40,924 members; 20,462 macOS sidecars | PASS; 1,988,886 members; 994,443 macOS sidecars |
| Admission eligibility | UNRESOLVED | UNRESOLVED |
| Exact blocker | `UNRESOLVED_ORIGINAL_DELIVERY_EVIDENCE` | `UNRESOLVED_ORIGINAL_DELIVERY_EVIDENCE` |

For each, historical provenance says “User-supplied local ZIP; original publisher ZIP identity unverified.” Acquisition UTC, retrieval receipt and publisher archive identity are NULL; publisher URL is a hint only. Sidecars and enclosing directories warrant qualification review but do not prove corruption, completeness of the original SEC delivery, or independent publisher provenance. Historical integrity establishes the retained ZIP's consistency, not original publisher completeness. Missing receipts prevent automatic qualification under existing rules. On available evidence this is normal explicit admission staging, not a substantiated second control failure.

Bounded recovery proposal for later approval, independently for each candidate: (1) owner supplies original retrieval receipt/download history or contemporaneous publisher digest and snapshot identity; (2) verify that evidence and rehash exactly the one retained ZIP read only, validate its archive without repacking; (3) compare recorded digest and publisher delivery identity, record sidecars and unknowns; (4) owner explicitly dispositions provenance gaps under the existing admission policy; (5) only after approval propose ordinary admission with unchanged original universe membership and immutable RAW. If no authentic historical evidence exists, retain UNRESOLVED; a fresh publisher download cannot retroactively prove this original snapshot and would need separate scope authorization. No recovery, ID registration or admission was executed.

### 800-object retention and dependencies

The reference appendix identifies exactly 800 IDs. All 800 local registered paths exist by stat. All 800 acquisition receipt files match their frozen packet receipt SHA-256. All 800 retained remote receipts say `REMOTE_READBACK_SHA256_PASS`, with RAW digests matching manifest v6. Sum of those 800 receipt byte sizes is **79,225,793 bytes**; this is receipt-derived historical transfer accounting, not a current RAW measurement or the entire Day 3–5 transfer total.

Observed dependencies: N450 (50 extra NOAA), N750 (250 extra NOAA), N500 (400 WDI + 100 Treasury), their cumulative C750/C1500/C2000 freezes and manifests v4–v6, upload receipts and targeted structural inspection evidence. Structural profiling is downstream processing and must remain preserved. Freeze-time `downstream: NOT_STARTED` describes that checkpoint only. No retained evidence reviewed establishes CLEAN/QUERYABLE execution for these 800. Live remote existence, current remote hashes and complete Databricks consumer lineage remain UNVERIFIED because no remote query/job/RAW scan was authorized. No physical retention action was necessary or performed; owner retention decision is binding. Missing `original_raw_path` on some earlier packet members is explicitly marked in the appendix; candidate identity, acquisition receipt and registered RAW path remain available. No missing local path or acquisition-receipt hash mismatch was found.

### Exact integration points — design only, NOT IMPLEMENTED

The current controls validate identity, hashes, historical preservation, grants and holdout exclusions but do not implement a pinned owner-authorized universe membership gate. Historic freezes contain cohort-growth authorization text, but do not establish an explicitly approved universe expansion. This supports a control-design gap; it does not establish individual intent.

| Integration point | Required future change |
| --- | --- |
| `src/edp_lab/ingestion/c300_admission.py`: `prepare`, `freeze`, `verify_registry` | Require pinned universe version/hash, authorized candidate identity/hash membership and explicit owner authorization. Validate before allocating IDs/writing admission artifacts; repeat at freeze. Keep original inventory IDs distinct from assigned Source Instance IDs with an evidenced crosswalk. |
| Historical Day 3 `scripts/prepare_n450.py:main`; Day 4 `scripts/prepare_n750.py:main`; Day 5 `scripts/prepare_n500.py:qualify`, `admit`, `freeze`, `historical_gate` | Block unauthorized candidates before acquisition/selection and at final freeze. Existing count targets, family validity and provenance cannot authorize expansion. Review reusable code in a separate branch; do not merge historic baselines. |
| Day 5 `scripts/upload_n450.py:main(cohort=...)`, reused by `upload_n500.py`; N750 uploader | Require authorized pinned roster and digest before transfer; remote listings are integrity observations, never candidate discovery. No current transfer authorized. |
| `scripts/profile_n450_targeted.py`, `profile_n750_targeted.py`, `profile_n500_targeted.py:main` in their historical worktrees | Check frozen universe/cohort relationship and each member identity/hash before reading RAW. Existing packet/hash checks alone are insufficient. |
| `src/edp_lab/profiling/source_reader.py:read_registered`; `src/edp_lab/agents/checkpoint_v0.py:validate_c300`; `src/edp_lab/agents/c300_shallow_v0.py:inspect` | Enforce run-specific authorized cohort, holdout authority and member hashes before materialization; preserve parser approval gates independently. |
| `scripts/prepare_native_nasdaq.py:main`, `scripts/seal_native_nasdaq.py`, contract described in `docs/native_databricks_execution.md` | Future contracts pin universe/cohort version and roster digest; execution validates all inputs against that explicit roster. Do not change existing Day 2 execution or its controllers. |
| `src/edp_lab/tool_adapters/profiling.py:Authorization`, `ExecutionScope`, `ProfilingAdapters.invoke` | Host supplies immutable universe/cohort authority; grant checks cannot substitute for experiment scope. Denial emits `OUT_OF_SCOPE / AUTHORIZATION_REQUIRED`, `approval_required=True`; agent cannot supply its own grant/version or bypass denial. |
| `src/edp_lab/agents/analyst_v0.py:plan`, `observe`; `post_approval_v1.py:load_evidence`, `evaluate`; `docs/agent_tool_contract.md` and Agent authority contract | Preserve deterministic denial in report/trace, route a versioned scope-change proposal to Human Review. No acquisition merely to meet count, frozen edits, implicit version switch or self-approval. |
| `tests/corpus_invariants/test_c300_admission.py`; historical N450/N750/N500 membership tests; `tests/agents/test_analyst_v0.py`, `test_post_approval_v1.py`; tool-adapter tests | Add executable cases below at admission/freeze, manifest loading, agent onboarding and final release/regression boundaries. Existing test results do not cover the missing control. |

Required authority populations: Enterprise Source Estate may grow under its own approvals; Approved Source Universe is owner-authorized and versioned; Qualified Source Instances satisfy admission evidence rules; Frozen Experiment Cohort is an immutable selected subset of both; Reserved Holdouts require separate evaluation authority; Out-of-scope legitimate RAW remains retained without current cohort eligibility. Fail closed on absent/mismatched scope/version/hash. Runs use exact frozen member rosters; directory discovery cannot add inputs. A source family allowlist cannot authorize new instances. Future scope changes create new versions and approval evidence without rewriting historical universes/cohorts.

Mandatory future executable acceptance cases, **all PENDING / NOT RUN**:

1. Correct SHA-256/provenance but outside pinned universe → DENY with authorization-required evidence.
2. Legitimate newly arrived business data outside frozen run roster → DENY for that run.
3. Reserved Day 13 holdout before authorized evaluation → DENY.
4. New unapproved Treasury instance despite allowed family → DENY.
5. Original-universe member with correct identity, approved cohort selection and normal qualification → ALLOW; qualification/hash failures still block.
6. A retained 800 member under a future explicitly human-approved universe/cohort → ALLOW only there; original version still DENY and historical digests unchanged.
7. Agent attempts self-expansion, acquisition to meet quota, cohort edit, version switch or denial override → deterministic block and Human Review proposal; approved change requires authenticated owner evidence, not agent assertion.

These are mandatory acceptance criteria for future Agent onboarding, Day 7 resumption and Day 11–12 Agent/release evaluation. No mechanical guardrail, regression or Agent authorization test was implemented or executed in this documentation task.

### Solution 2 dependencies and remaining work

PENDING: owner-approved versioned universe authority artifact and scope-change schema referencing the unchanged 3,021 snapshot; deterministic gate and integration tests on a separate implementation branch; Agent authority routing/evaluation; explicit SEC Bulk provenance disposition; completed Day 2 C300/M1 acceptance; owner decision on revised target (neither C2978, C2980 nor C3000 selected here); new authorized replacement rosters/freezes and historical-to-replacement crosswalk; run-level hash/membership validation; bounded authorized processing with Lossless/Stability accounting and measured operational outcomes; retained remote/dependency verification under separate read-only authorization; final owner review and dated closure approval. Preserve all historical commits, freezes, 41 holdouts and 800 RAW objects. No reconstruction has started.

### Actual execution ledger supplement

Earlier §12 audit states are superseded below; implementation states remain PENDING. Timestamp precision is preserved; unknown historical times are not reconstructed.

| Step | Actual timestamp (UTC+08:00) | Evidence / outcome |
| --- | --- | --- |
| Incident detected; root-cause investigation; solutions proposed | 2026-10-21; exact times UNKNOWN | Owner-supplied report §§1–5; historical chronology retained |
| Solution 2 selected | 2026-10-21; exact time UNKNOWN | Owner instruction; logical rollback and retain all 800 DECIDED |
| Local investigation started | Start timestamp not captured | This task; SEC Bulk and 800 receipt audit read only |
| Count and 800 receipt reconciliation completed | 2026-10-21T16:53:31.561694+08:00 | §13 and reference appendix; 800 retained receipt hash/readback matches; current remote integrity UNVERIFIED |
| SEC Bulk investigation completed; freeze/hash audit completed | 2026-10-21T16:55:49.956562+08:00 | §13, evidence index; provenance UNRESOLVED for both, historical physical integrity VERIFIED; three increment freeze file sets/canonical rosters/manifests match |
| Incident documentation committed | 2026-10-21T16:59:13+08:00 | `05854c25dfc7554e5f596b346b489ec304c80a97`; required commit message; documentation only; whitespace/credential checks clean |
| GitHub branch published / PR opened | PR created 2026-10-21T16:59:56+08:00; branch push completed before PR creation (exact push timestamp not captured) | [Branch](https://github.com/lightnino/edp-lab/tree/incident/source-universe-scope-control); [PR #15](https://github.com/lightnino/edp-lab/pull/15), OPEN against main; publication VERIFIED, not merged |
| Admission gate implementation started/completed | PENDING | No implementation performed |
| Guardrail regression tests executed | PENDING | NOT RUN |
| Agent authorization tests executed | PENDING | NOT RUN |
| Authorized cohort reconstruction started/completed | PENDING | Await dependencies and owner scale decision |
| Lossless and Stability checks | PENDING | No reruns |
| Incident closure approved | PENDING | OPEN; closure criteria §12 apply |

Retained structural completion summaries were also inspected: N450 records zero Databricks processing jobs and deferred final M1 fit; N750/N500 explicitly record `CLEAN_QUERYABLE: NOT_RUN`, `Stability: NOT_RUN`, and zero Databricks processing jobs. These are historical checkpoint claims, not current live dependency certification.

Publication verification: GitHub PR metadata confirms `main` base, incident branch head, OPEN state and exactly the three documentation files above. Remote main was independently checked at `ddb6e47c52afa08415614dc7f341255255d9c963` before publication. The publication ledger is recorded in a subsequent documentation-only commit; the initial report commit is the immutable anchor above.

## 14. Superseding Decision — Pre-Day-3 Closure

**Decision date:** 2026-10-21 (UTC+08:00; exact owner-decision time not supplied).

**Authority:** Explicit experiment-owner instruction to amend closure criteria for EDP-INC-2026-10-21-001.

**Current incident status:** **OPEN — revised closure gates below are not yet verified.**

This decision supersedes the earlier closure conditions, implementation sequencing and remediation dependencies only where they conflict with this section. All discovery evidence, root cause, original decisions, historical observations and implementation logs above remain intact. In particular, the historical `NOT_IMPLEMENTED` / `NOT IMPLEMENTED`, PENDING and NOT STARTED entries describe their recorded checkpoints; this amendment does not assert that implementation has occurred.

The owner has decided:

- Incident remediation must be completed and closure approved **before the new Day 3 experiment**.
- Rebuilding N450/C750 belongs to Day 3, **not incident remediation**. Replacement cohort construction and experimental processing/acceptance previously listed as incident-closure dependencies are deferred to Day 3; they are not prerequisites to incident closure under this decision.
- Previously frozen unauthorized C750/C1500/C2000 remain historical evidence, **not approved baselines**. Preserve their membership, hashes, commits, receipts and execution records without retroactive authorization.
- Retain all **800 legitimate outside-scope RAW instances permanently**, including local and remote RAW and their reproducible references, unless a separate future retention decision changes that requirement. Retention grants no current experiment-processing authority.
- The incident remains **OPEN** until all seven revised closure gates are verified and explicit owner closure approval is recorded.

### Revised closure gates

All seven gates are required. Documentary intent, historical receipts or a mechanical PASS alone do not establish current authorization or closure.

1. **Approved Universe v1:** Preserve the original **3,021-member Approved Universe v1**, with per-member IDs and hashes, pinned universe version and snapshot digest, and explicit owner authorization tied to that exact version and membership. Retain the original inventory evidence in §8 and the 41 reserved holdouts; do not silently change membership or versions.
2. **SEC Bulk qualification:** Both `LOCAL_SEC_BULK_COMPANYFACTS` and `LOCAL_SEC_BULK_SUBMISSIONS` retain universe membership and have **individually documented admission qualification outcomes**, supporting evidence and exact blockers or disposition. Membership is distinct from qualification; do not infer PASS. Any BLOCKED/UNRESOLVED outcome must remain explicit and supported by evidence.
3. **800-instance preservation and exclusion:** Retain all **800 legitimate outside-scope RAW references**, reconciled to the reference appendix, with **current remote preservation evidence** and proof that they are excluded from current authorized experiment processing. Record verification time, exact coverage, paths, hashes/results and any unknowns. Historical remote readback receipts alone do not prove current remote preservation or processing exclusion.
4. **Deterministic authorization:** Enforce deterministic admission, freeze and processing authorization against the pinned owner-authorized universe and exact frozen cohort membership, including identity/hash validation and holdout restrictions. Missing, mismatched or denied authority must fail closed; directory/prefix discovery cannot expand authorized processing.
5. **Agent authority boundary:** Demonstrate that the Agent cannot self-approve, change universe versions or bypass authorization denial. A proposed scope/version change requires separate explicit owner authorization; an Agent assertion cannot supply that authority.
6. **Compatibility and negative tests:** Validate guardrail compatibility tests and negative tests with actual commands, coverage and results. Explain and resolve or explicitly disposition **all previously observed 29 broad-suite failures**, with a traceable outcome for each; do not claim a clean broad suite while failures remain undispositioned. Historical Day 3 entrypoints cannot be promoted or executed as authorized entrypoints without the guardrail. Record evidence covering those entrypoints and attempted bypasses. The count of 29 is owner-supplied prior test context, not a test result independently reproduced by this documentation amendment.
7. **Merged implementation and owner closure:** Merge the guardrail code PR, complete the incident implementation ledger with verified evidence for the gates above, and record **explicit owner closure approval** and closure timestamp. Publishing or merging this documentation amendment alone does not satisfy this gate or close the incident.

### Required final incident closure update

When implementation is complete, **append a superseding verified implementation status** linked to the historical observations above. Do not rewrite historical `NOT_IMPLEMENTED` entries or backfill unknown historical times as if observed. The final update must include:

- Actual implementation paths and the controls enforced at each relevant admission, freeze, processing and Agent integration point.
- Commit SHAs and merged PR URLs for the guardrail and relevant incident implementation changes.
- Actual test commands and results, including compatibility and negative tests, historical Day 3 entrypoint coverage and the resolution or explicit disposition of each of the 29 broad-suite failures.
- RAW verification results for all 800 retained references, including current remote preservation evidence and proof of exclusion from current authorized experiment processing, with reproducible evidence paths, verification timestamps and coverage.
- Separate SEC Bulk qualification outcomes and evidence for both original universe entries.
- Actual implementation start and finish timestamps with timezone; preserve UNKNOWN where a timestamp was not captured.
- Unresolved limitations and their impact on each closure gate, including any explicit dispositions; do not silently convert unknowns into PASS.
- Final explicit owner approval, its reproducible approval reference and the incident closure timestamp with timezone.

**Scope of this amendment:** Documentation only. No code implementation, RAW modification, Day 2 change, SEC Bulk qualification, new cohort or experiment is performed or authorized by this update. All implementation and verification claims remain to be evidenced under the revised gates.


## 15. Execution ledger supplement — Step 2 SEC Bulk qualification recovery

Recorded at **2026-10-21T18:14:10.642456+08:00** (UTC+08:00; actual recording time, not original retrieval time). Worktree `/Users/lightnino/Projects/edp-lab-incident`, branch `incident/closure-evidence`, starting commit `d216390`. Scope: only `LOCAL_SEC_BULK_COMPANYFACTS` and `LOCAL_SEC_BULK_SUBMISSIONS`. Earlier investigation and ledger checkpoints remain unchanged.

**Outcome: investigation COMPLETE within the bounded search; admission qualification UNRESOLVED for each candidate.** No authentic contemporaneous publisher/retrieval evidence was recovered in the searched records. This is a bounded negative finding, not proof that no receipt exists elsewhere. Admission is not authorized or executed.

| Required determination | LOCAL_SEC_BULK_COMPANYFACTS | LOCAL_SEC_BULK_SUBMISSIONS |
| --- | --- | --- |
| Approved universe membership | CONFIRMED: original v1 and v2 inventories each contain 3,021 entries and this exact candidate/hash | CONFIRMED: original v1 and v2 inventories each contain 3,021 entries and this exact candidate/hash |
| Physical RAW integrity | Historical SHA-256 and full archive CRC PASS; 1,418,648,998 bytes; 40,924 members including 20,462 macOS sidecars | Historical SHA-256 and full archive CRC PASS; 1,974,869,371 bytes; 1,988,886 members including 994,443 macOS sidecars |
| Retained SHA-256 | `23e23cc8293fa22abda2f7d0568ee5534e149b51a77cd40171c3d834278cc902` | `5c75f9d996d5eea8a0e05689e28079d069a80e1632cf87ba24021da7e48d465b` |
| Current physical check | Stat matches historical size/inode `170344231`/mtime_ns `1792486764931827650`; current content hash/CRC NOT RERUN | Stat matches historical size/inode `170344669`/mtime_ns `1792487319033321638`; current content hash/CRC NOT RERUN |
| Publisher provenance | UNVERIFIED: user-supplied local ZIP; publisher archive identity and edition NULL; SEC URL is a hint | UNVERIFIED: user-supplied local ZIP; publisher archive identity and edition NULL; SEC URL is a hint |
| Retrieval receipt | MISSING in searched evidence; original receipt/acquisition UTC NULL; current `xattr -l` succeeds with empty output | MISSING in searched evidence; original receipt/acquisition UTC NULL; current `xattr -l` succeeds with empty output |
| Admission qualification | **UNRESOLVED** | **UNRESOLVED** |
| Exact blocker | `UNRESOLVED_ORIGINAL_DELIVERY_EVIDENCE`: no authenticated original delivery/publisher link or retrieval receipt | `UNRESOLVED_ORIGINAL_DELIVERY_EVIDENCE`: no authenticated original delivery/publisher link or retrieval receipt |
| Owner authority needed | Explicit provenance-gap disposition/exception required to admit on present evidence; otherwise retain UNRESOLVED pending authentic evidence | Explicit provenance-gap disposition/exception required to admit on present evidence; otherwise retain UNRESOLVED pending authentic evidence |

RAW paths remain those in §13. No full ZIP scan was repeated: existing integrity evidence is unchanged and another CRC/hash pass cannot recover missing provenance. A matching stat is not a current byte-integrity proof. Before any future ingest/admission, verify the exact retained RAW hashes under the applicable contract.

### Evidence recovered and contract assessment

The original local availability observation is `2026-10-20T09:12:00.756956+00:00`. Its provenance objects explicitly record NULL acquisition UTC, original retrieval receipt and publisher archive identity, and empty historical extended attributes. Local move records establish same-volume relocation from Downloads, with preserved inode and hash; they are local custody evidence, not SEC retrieval receipts. `reuse-checks.json` records zero network requests for these candidates. The completion summary explicitly records 3,021 entries, 3,015 new verified publisher deliveries, four unchanged GOLD and **two existing unadmitted bulk candidates**, zero new admissions and zero freezes at that checkpoint. The v2 `publisher=SEC` label supplies no missing receipt: both inventories retain blank publisher URL and Source Instance ID.

The organization report records that `Downloads/EDP` disappeared externally, an initial empty submissions ZIP was invalid, and the extracted submissions inventory was interrupted (`FileNotFoundError CIK0002142938.json`). These historical observations remain preserved. They do not invalidate the subsequently verified retained submissions ZIP, establish delivery equivalence, or supply an original publisher identity. Directory inventories and macOS sidecars cannot establish publisher completeness or archive authenticity.

Contract applied: `docs/source_instance_identity.md` identity/admission rules 2–4 and `docs/corpus_admission_policy.md` require independent delivery provenance and receipt/retrieval evidence, with explicit present-day disposition of historical gaps; `docs/c300_acquisition_tooling.md` records approval of that minimum policy. `docs/whole_lab_sources.md` explicitly keeps locally intact bulk packages with unknown publisher identity unadmitted. Policy approval and universe membership do not constitute per-delivery admission authority. Neither candidate satisfies the complete existing evidence contract on recovered evidence. No separate upload failure, lost authenticated receipt, or code defect is established.

### Bounded search and reproducible evidence locators

Searched local `runs/local_inventory`, `runs/whole_lab`, and metadata/scripts, then filename/content matches across the original worktree's `runs`/metadata/scripts (excluding large per-file JSONL inventories, log files and bytecode in that final search). Inspected original availability, initial/current archive observations, relocation records, organization/interruption/reuse records, completion summary, inventory v1/v2 and the historical review-packet evidence references. No bulk retrieval receipt appeared among matching acquisition/delivery metadata. Downloads top-level names matching companyfacts/submissions/sec/receipt yielded none; no private browser database or unrelated personal history was searched. Both current ZIP extended-attribute listings were empty. No network calls or fresh downloads occurred.

Local Git history search used `git log --all -G 'companyfacts|submissions.zip|LOCAL_SEC_BULK' -- .` and acquisition/inventory/provenance/receipt commit-subject searches. The literal-name search returned only incident commits `05854c25dfc7554e5f596b346b489ec304c80a97` and `7becc7c9e7390e0995b86d4a19fb08622f1aa542`; inspection of acquisition commit `1aaf56c02f7fd5b0e3304ec06893334c8c922aed` and preliminary manifest commit `62fc3c13646c0730ef49b4221003a6d39b7761de` recovered no original bulk receipt. Git history coverage is locally available refs only; no fetch or remote search. Operational evidence is intentionally untracked. No historical receipt/timestamp was reconstructed.

Content hashes measured for small evidence files in this recovery (absolute paths under `/Users/lightnino/Projects/edp-lab/`):

| Evidence path relative to that root | SHA-256 |
| --- | --- |
| `runs/local_inventory/availability.json` | `74773ac1841c5f2d1a21be6c3a2cb1cc09cca78a15a8750865867d7d837e46ca` |
| `runs/local_inventory/files-before.json` | `a68d0ebda9acf3dbc7fa306f1cb367b40243bdc2b93b1b9a016171421dab69e6` |
| `runs/local_inventory/bulk-files-current.json` | `6edb340dbdd56209cb201d726e6da9b50a07885b44aa16ba61507d3925510c26` |
| `runs/local_inventory/move-companyfacts-zip.json` | `5997f6969400d8484313f3ac6b44078b6a3e221f154662c293aa150d2fd48859` |
| `runs/local_inventory/move-submissions-zip.json` | `c7cd765aa181668ff0ffae3a6612f640a519aa03f81b09ab0546684669bb43d7` |
| `runs/local_inventory/inventory-interruption.json` | `ce64afd81f61b1da230dfbf1cf73aeb3405d03ccd0a1fb6dee7c9c0197b8d568` |
| `runs/local_inventory/organization-report.md` | `84189f41211c3f115d50c0be2963cb0c8a1352c63df09ab727ebc0686dcca173` |
| `runs/local_inventory/reuse-checks.json` | `0a7db1d07a5726965607661735caa36d2340c1824add93f4e1b12a3608c15d99` |
| `runs/whole_lab/candidates-v1/completion-summary.json` | `43106d9625ae744966eef22afc06b5859f44655d9026e4f6b270cda4137000c8` |
| `runs/whole_lab/candidates-v1/whole_lab_inventory_v1.csv` | `99f09213dc17d845a4ea6e97dfd6b99fabf7e4a7f5cb618253f7040fa706ca6c` |
| `runs/whole_lab/layout-v2/whole_lab_inventory_v2.csv` | `1dcf16137a3a3cd0be3c4f025d9e6274e2a9bba34163e121004a97b1961bc45a` |
| `runs/whole_lab/candidates-v1/review-inventory-549769752030eec1461560156f78a67ae52453a23d4a6277025d2e679db8444c.json` | `549769752030eec1461560156f78a67ae52453a23d4a6277025d2e679db8444c` |
| `runs/whole_lab/candidates-v1/review-inventory-06a21f4efd01debe36eaffda8c79e3bac9e8a99643638c45672299ac30bdcd69.json` | `06a21f4efd01debe36eaffda8c79e3bac9e8a99643638c45672299ac30bdcd69` |

### Owner decision required before any exception-based admission

Pending question for the experiment owner: retain both candidates as UNRESOLVED while seeking authentic original publisher/retrieval evidence, or explicitly authorize a separately recorded provenance exception for either exact candidate/hash? Retention preserves the current evidence standard and delays qualification; an exception would accept the specified missing delivery evidence and must identify each candidate/hash, accepted unknowns and authority. No exception is inferred here, and even an exception would not allocate IDs or execute admission in this task. Fresh downloads cannot prove the original delivery.

Both candidates remain in the original authorized 3,021-member universe. No inventory, manifest, cohort, Source Instance ID, RAW bytes or historical evidence was changed. The conditional 2,978/2,980 ceiling is unchanged; neither candidate adds a qualified instance. Step 2's individual findings are recorded, while owner disposition and incident closure remain pending. No push or merge performed.


## 16. Execution ledger supplement — SEC Bulk owner attestation and qualification disposition

**Attestation date: 2026-10-21. Recorded at 2026-10-21T18:23:20.756079+08:00 (UTC+08:00).** Authority: the experiment owner's explicit instruction in this conversation. The original message timestamp and a separate signed attestation artifact are unavailable; the recording time is not represented as the original message or acquisition time.

The owner's statement is preserved verbatim here:

> Record the experiment owner's explicit first-party SEC Bulk provenance attestation above in the existing incident/closure-evidence branch.

The owner expressly directed:

> Set Admission Qualification for BOTH sources to QUALIFIED — OWNER_ATTESTED_PROVENANCE, under the admission policy's explicit human disposition of missing evidence.

This records first-party owner-attested provenance and explicit human disposition under `docs/corpus_admission_policy.md` and `docs/source_instance_identity.md`; it does not represent independently verified SEC download logs. No additional acquisition narrative, date, SEC archive edition or download method is inferred. The attestation is linked only to the two existing physical ZIP references below and does not establish a general waiver for other sources.

| Existing inventory ID | Existing RAW path | Recorded SHA-256 | Final Admission Qualification |
| --- | --- | --- | --- |
| `LOCAL_SEC_BULK_COMPANYFACTS` | `/Users/lightnino/Projects/edp-lab/data/raw/sec/bulk/companyfacts.zip` | `23e23cc8293fa22abda2f7d0568ee5534e149b51a77cd40171c3d834278cc902` | **QUALIFIED — OWNER_ATTESTED_PROVENANCE** |
| `LOCAL_SEC_BULK_SUBMISSIONS` | `/Users/lightnino/Projects/edp-lab/data/raw/sec/bulk/submissions.zip` | `5c75f9d996d5eea8a0e05689e28079d069a80e1632cf87ba24021da7e48d465b` | **QUALIFIED — OWNER_ATTESTED_PROVENANCE** |

For **each** ZIP, original download receipts and independent publisher digests remain **UNAVAILABLE**. Original acquisition UTC and independently authenticated publisher archive/snapshot identity remain unknown. Owner attestation supplies the expressly authorized human provenance disposition; it does not recover or replace those missing historical artifacts. Historical local SHA/archive integrity remains verified as documented in §§13 and 15; no new full RAW hash/CRC verification is claimed. Current hash verification remains required before any future ingestion under the existing contract.

**SEC Bulk Qualification Recovery: COMPLETE.** This dated owner disposition supersedes the UNRESOLVED qualification outcomes and pending owner-decision status in §§13 and 15 for these two exact candidates only. All earlier investigation findings, missing-evidence observations and historical checkpoints are preserved unchanged. Both remain members of the original **3,021 Approved Universe**; qualification changes neither universe membership nor frozen cohort membership. The earlier 2,978 ceiling excluded these two unresolved candidates; this disposition resolves that qualification exclusion, without selecting a scale target or creating admitted instances.

No Source Instance IDs were allocated, RAW modified, inventory/registry changed, or source admitted into a cohort. Qualification is separate from actual admission and parser/processing approval. Incident closure remains subject to its other gates and explicit owner approval. This ledger update is committed on `incident/closure-evidence`; no push or merge is authorized or performed.
