# EDP Lab Incident — Source Universe Boundary / Unauthorized Scope Expansion

**Incident ID:** EDP-INC-2026-10-21-001
**Observed on:** 2026-10-21 (SGT)
**Status:** CLOSED — explicitly approved by the experiment owner under the seven revised closure gates (§14).
**Closed at:** 2026-10-21T20:03:15+08:00 (UTC+08:00; actual closure recording time).
**Owner approval:** [owner approval comment](https://github.com/lightnino/edp-lab/pull/18#issuecomment-6315368530), by `lightnino` at `2026-10-21T20:00:05+08:00` (GitHub `2026-10-21T12:00:05Z`).
**Classification:** Scope governance / admission authorization control gap
**Decision (experiment owner):** Option 2 — preserve original 3,021 authorized-universe snapshot; exclude the 800 outside-scope instances from the current experiment through logical rollback, without deleting physical RAW.
**Remediation state:** IMPLEMENTED for documented local execution paths; Guardrail [PR #17](https://github.com/lightnino/edp-lab/pull/17) merged as `2988c62ce7e8a92547224e8212ed74f1cec2bc94` at `2026-10-21T11:50:59Z` (19:50:59 UTC+08:00). Existing C750/C1500/C2000 freezes are historical execution evidence, not accepted scope-compliant experiment baselines.
**Retention decision:** RETAIN ALL 800 RAW objects (local and Databricks) for audit, legitimate future source-onboarding proposals and subsequent approved experiments. No deletion workflow planned.
**Day 2:** Separate C300/M1 workstream. Historical reported checkpoint: 21/32 reconciliation groups PASS, 3 running, 8 pending, zero failures, controller PID 72896 alive, optional statistics complete (2026-10-21 16:26 Shanghai/SGT). This is a historical checkpoint, **not** a live-status assertion. Full data validation has separately been reported successful; retained completion evidence records `MAIN_720_COMPLETE_VALIDATED` and `NOT_FROZEN` (§13). O_C300_M1 baseline retention/freeze acceptance is DEFERRED TO DAY 2 and is not an incident closure prerequisite. Do not touch its worktree, jobs, controller or checkpoints.

**Publication:** Original report published in [PR #15](https://github.com/lightnino/edp-lab/pull/15), initial anchor `05854c25dfc7554e5f596b346b489ec304c80a97`; final incident status and evidence summary updated in this document on `main`. Owner closure approval is separately documented at the linked GitHub [approval comment](https://github.com/lightnino/edp-lab/pull/18#issuecomment-6315368530).
**Evidence basis:** Original owner-supplied Codex audit and Day 3–5 summaries, the bounded local governance audit (§13), committed Steps 2–5 evidence, GitHub PR #17 metadata, and the owner-supplied pre-merge execution-isolation audit. Coverage and evidentiary limits are explicit below.

## 1. Intended versus observed scope

The user's stated intended experiment was to sample and scale **within one original RAW source universe of 3,021 inventory entries**, preserving 41 independent Day 13 holdouts. The governance audit (§13) identified the missing mandatory approved-universe gate; no prior explicit owner authorization widening this baseline was identified.

Actual frozen C2000 membership: **2,000 independent physical Source Instances**, consisting of **1,200 from the original 3,021 inventory** and **800 from later acquisitions outside that inventory**:

| Day | Added source outside original 3,021 | Count |
| --- | --- | ---: |
| Day 3 | NOAA GSOD | 50 |
| Day 4 | NOAA GSOD | 250 |
| Day 5 | World Bank WDI | 400 |
| Day 5 | U.S. Treasury annual XML | 100 |
| **Total** | | **800** |

The 800 were reportedly acquired, admitted with distinct IDs and RAW SHA-256/provenance, transferred to Databricks RAW cohort prefixes, and verified by remote readback. They are represented in the canonical admitted corpus manifest, **but not in original whole_lab_inventory_v1/v2**. The reference appendix records each local path, and the local audit found all 800 registered paths present by stat; no common-root arrangement is needed to establish their identities.

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

The following qualification arithmetic describes the **detection checkpoint, before owner qualification**. The inventory identity **3,021** is correct: it includes two SEC bulk candidates even though their *admission qualification* was not established at detection. **Universe membership and admission eligibility are different gates.** Excluding 41 Day 13 holdouts gives an absolute ceiling of **2,980** original-universe non-holdouts. At detection, evidence established **2,978** eligible/previously admitted non-holdouts (including four GOLD) and two not-yet-qualified bulk candidates. The experiment owner has **not selected C2978** as the final cohort size. Both bulk candidates are now owner-qualified (§§11, 16), resolving that qualification exclusion and bringing the non-holdout ceiling to 2,980, but still cannot yield C3000 without an explicitly approved future universe/sampling change. No new cohort has been frozen.

All 41 recorded Day 13 holdouts remain excluded from C2000. The frozen cohorts, admission/receipt hashes and Git commits were reported clean. **Do not equate mechanical admission/hash PASS with scope authorization PASS.**

### Full source-family distribution: authorized v1 versus outside-scope acquisitions

This table preserves **historical qualification at detection**, before the Step 2 owner disposition. Counts are **physical candidate/source instance records**, not source records, ZIP members, logical bindings, or business entities. `Original selected in C2000` is historical execution membership **not** acceptance as the authorized C2000 baseline.

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

Note: the four previously admitted GOLD original entries are outside C2000 but already registered (SEC_FSDS 1; SEC_13F 1; NASDAQ_DIRECTORY 2). Therefore `1,200 + 1,774 + 41 + 2 + 4 = 3,021`. The original non-holdout ceiling is **2,980**, with both SEC_BULK qualification outcomes now resolved by owner attestation; this does not admit or allocate them to a cohort. The extra 800 remain physically legitimate and reproducible, but are **not** approved for the current experiment. The `ECB_SDMX` prospective reserved source family has **zero** original-inventory entries; `ECB_REFERENCE_RATES` has one holdout.

Source-family permission is not instance-level authorization: even Treasury, a pre-existing original family, requires an explicit approved source-instance membership or governed incremental ingestion policy to join a frozen experiment.


## 3. Proximate cause and missing control

- Day 3–5 instructions prioritized additional independently qualified physical Source Instances and greater family diversity beyond SEC/NOAA.
- The instructions failed to require that *candidate membership belong to the authorized Source Universe version*, or to obtain an explicit scope-change authorization before acquiring new source families.
- The admission gates correctly checked provenance, hashes, overlap, holdouts, local/remote byte integrity, and structural coverage, but lacked a **universe-authorization gate**.
- The original whole-lab inventory remained an original-acquisition snapshot while newer accepted sources appeared in the canonical admitted corpus manifest. This split was not presented as a governed universe version change with an explicit authorization decision.
- The failure is a **control-design / instruction / governance gap**; it must not be attributed solely to Codex or to an individual engineer without stronger evidence.

## 4. Potential impact (not all observed)

**Observed:** 800 legitimate but unauthorized-for-this-experiment instances admitted into C2000; related Day 3–5 cohort freezes and RAW uploads exist in local branches and Databricks; original inventory count no longer represented the full known acquired universe. Day 2 main validation was running independently at detection; its later reported validation success does not establish baseline freeze acceptance.

**Potential, requiring verification:** violation of experimental sampling plan; biased / incomparable stability and engineering-effort measures; widening parsing and semantics without prior approval; increased cloud storage / execution cost; unauthorized source/domain/entitlement access; downstream lineage and reconciliation population mismatches; contamination of future holdout evaluation if an explicitly reserved source is processed (no such contamination reported for the 41 holdouts); job code using directory glob/listing that inadvertently consumes all available data; uncontrolled model drift / identity collisions; ability to reproduce frozen experimental observations weakened if membership is derived dynamically.

The incident does **not** prove that downstream CLEAN/QUERYABLE processed the 800 or that production data was exposed. The supplied summaries only establish admission, RAW upload, remote readback and structural profiling for Day 3–5 increments. Investigate actual dependencies before changing storage.

## 5. Decision and remediation — OPTION 2 IMPLEMENTED WITH BOUNDED COVERAGE

### Approved choice — Option 2: return to original authorized 3,021 Source Universe

On 2026-10-21 the experiment owner selected **Option 2, logical rollback first**. The current experiment must draw members only from the original, pinned 3,021-instance universe, subject to admission qualification and preservation of the 41 holdouts. An agent/engineer attempting to insert a real, well-formed, hash-verified but unauthorized instance must receive **OUT_OF_SCOPE / ADMISSION_DENIED**. Do **not** mislabel the original source as corrupt, invalid or rejected on data-quality grounds.

**Decided:**

1. Preserve original v1/v2 inventory and its 3,021 recorded identities/hashes as the **authorized experiment-universe reference**. No silent edits to frozen historic evidence.
2. Mark all 800 later acquisitions as **legitimate RAW, NOT AUTHORIZED FOR CURRENT EXPERIMENT**. They remain eligible *candidates for a later explicitly approved expansion* and must not be cast as invalid source data.
3. Mark current C750/C1500/C2000 frozen membership and processing-readiness evidence as **historical execution artifacts, NOT ACCEPTED under the restored original-universe authorization**. Preserve all Day 3–5 Git commits, freeze records, tests, and receipts; do not merge/promote them as accepted cohort versions. The code may be reused after controlled review.
4. Preserve **all** 800 local and Databricks RAW objects and their SHA-256/provenance/upload receipts. **No physical deletion, no VACUUM, no `DROP VOLUME`, no purging.** Preserve future ability to propose these sources for C4000/C10000/larger authorized experiments. Storage retention remains subject to applicable organizational policies, but no deletion action is requested.
5. Do not automatically classify the 800 as a normal daily 2 GB delta: that was an **analogy illustrating normal, legitimate ongoing source-estate growth**. In a production workflow any real daily increment follows its own approved CDC/source contracts; it cannot silently contaminate the frozen sample.
6. Rebuilding affected post-C300 cohorts is **DEFERRED TO DAY 3**, with separate scoped planning and authorization; it is not an incident closure gate. Use new versioned cohort artifacts, keep old ones intact, rerun all applicable mechanical and semantic gates, and retain a crosswalk showing replaced/excluded members and consequences.
7. Enforce the implemented mandatory **mechanical fail-closed authorized-universe admission gate** (scope ID/version, instance ID, hash, owner/grant where relevant, holdout exclusion, explicit cohort membership), independent of prompt wording. Tests must reject unauthorized but otherwise legitimate inputs and prevent wildcard/prefix scans from expanding a frozen processing run.
8. Keep all 41 Day 13 evaluation holdouts untouched. Future sample-size selection is **DEFERRED TO DAY 3**; theoretical authorized non-holdout maximum is 2,980, both SEC Bulk candidates are now owner-qualified, resolving the historical 2,978 qualification limit without authorizing admission. Do not force C3000 or misstate 3,021 inventory count.

### Rejected alternative for the current experiment — Option 1

Authorizing all 800 now, appending them to a 3,821-member expanded experiment universe and treating existing Day 3–5 cohort freezes as accepted under that new universe **was not selected**. This does **not** prohibit a future, separately authorized universe version with some or all of these sources; it only prohibits retroactive or automatic admission to the **current** experiment.

**Why Option 2:** Source Estate growth is continuous; Experiment Scope changes are explicit, authorized, and versioned. EDP Lab is intended to scale from hundreds to thousands and millions of Source Instances, eventually toward approximately 2 PB of enterprise data. The estate naturally grows, but each experiment requires a pre-approved versioned scope. Silent acquisition to meet a numeric target would alter the original sample design and weaken comparisons between stages. Option 2 preserves scope and reproducibility while retaining legitimate RAW. Option 1 is a valid potential design for a separately approved 3,821-member experiment, but cannot retroactively authorize historical C750/C1500/C2000 evidence. The original non-holdout maximum is 2,980; exact C3000 requires a separately approved scope or target adjustment. This numerical shortfall is **not established as the incident's cause**.

### Implementation and acceptance state

- **Human decision:** COMPLETED — Option 2 chosen; Approved Universe v1 owner authorization recorded in `319281c17d957dc8d442aaa63278df0d5a1596b3`.
- **Physical RAW retention:** VERIFIED for all 800 remote objects at the Step 4 interval; local registered paths present by stat; no deletion or relocation (§13).
- **Admission Guardrail and Agent authorization:** IMPLEMENTED and verified for documented local paths; PR #17 merged at the SHA/time in the header. Historical and remote unguarded paths are EXCLUDED (§13).
- **Rebuilt authorized cohorts:** DEFERRED TO DAY 3; historical cohorts remain unaccepted.
- **Day 2 baseline retention/freeze acceptance:** DEFERRED TO DAY 2, separate from incident closure.
- **Incident closure:** CLOSED. The experiment owner explicitly approved all seven revised gates with their documented scope and limitations (§14).

## 6. Enterprise 2 PB migration analogy and required preventive controls

A real enterprise migration source estate might be ~2 PB, with 2 GB/day of ordinary new business events (the user stated this **as an analogy**, not a measured EDP Lab ingestion workload). Such increments can be legitimate, retained, and later incorporated into a **new approved cohort version**, but must never silently change the fixed prior experiment. The **moving production source estate**, **approved migration scope**, **fixed experiment sample**, and **daily incremental CDC/landing stream** must be distinct populations.

Illustrative contract:

- `source_estate(t)`: continually growing authorized business data.
- `migration_scope_v1`: owner-approved source systems, time ranges, cutoffs and classification boundaries.
- `experiment_cohort_vN`: an explicitly authorized, feasible and frozen set of source-instance IDs + hashes derived from one pinned approved universe version. Its count is a declared experiment parameter, not a quota that overrides the scope boundary.
- `daily_delta(t)`: normal new transactions/market records, handled by a separate change-capture/incremental path with offsets/watermarks, not silently appended to `experiment_C3000_v1`.
- `scope_change_request`: required before adding an out-of-universe source, even if the object passes byte-integrity checks.

Consequences of failing this gate may include inadvertent new data/security domains, uncontrolled cost, semantically invalid joins, new parser/identity assumptions, changes to economic reconciliation populations, experiment leakage/selection bias, broken as-of reproducibility and invalid comparisons of model versions.

**Enterprise control illustration:** The following broader migration contract illustrates the policy; the verified local implementation and its exact boundaries are in §13. It does not claim deployed enterprise entitlement or remote enforcement.

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

## 7. Containment, ownership and remaining restrictions

Option 2 is implemented within the documented local scope. Approved Universe v1 is pinned; the 800 retained objects are excluded from it and accepted C300; deterministic admission/freeze/processing authorization and Agent denials are tested. The exact implementation and restrictions are in §13 and [the Guardrail evidence](../source_universe_guardrail.md).

All 800 local/remote RAW references and historical upload/profiling dependencies are retained, without deletion, relocation or overwrite. Current remote presence/size/SHA-256 verification is 800/800, totaling **79,225,793 bytes**. This is distinct from the approximately 406.6 MB reported for entire Day 3–5 incremental uploads. Global live consumer lineage is not exhaustively established.

Both original SEC Bulk candidates are **QUALIFIED — OWNER_ATTESTED_PROVENANCE**; missing historical publisher receipts and independent digests remain disclosed. Qualification grants no registration, admission or processing authority.

**Decision owner:** Experiment owner; an Agent cannot approve closure or scope expansion.
**Root cause:** Control-design and authorization-boundary failure confirmed by the instruction/policy and implementation audit, not RAW corruption or solely individual/Agent failure.
**Day 13 holdouts:** 41/41 outside accepted C300; original 41 also absent from historical C2000.
**Historical Day 3–5 and unguarded remote execution:** EXCLUDED from approved new execution until integrated, tested and separately human-authorized. No physical disablement or ACL block is claimed.
**Future scope/target choice and cohort rebuild:** DEFERRED TO DAY 3; no new cohort target selected here.
**Day 2 O_C300_M1 retention/freeze acceptance:** DEFERRED TO DAY 2; no final freeze or acceptance inferred.
**Closure disposition:** CLOSED under explicit owner approval in §14. No new experiment execution is authorized by this report.

## 8. Supporting local evidence (original locators; bounded verification in §13)

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
| 2026-10-21 | Corrected count semantics: two SEC bulk entries are **in the 3,021 inventory**, not yet qualified for admission; raw maximum 2,980 non-holdouts, eligible at detection 2,978 | User challenge and original inventory status audit |
| 2026-10-21 | Retention is an affirmative owner decision: preserve all 800 legitimate RAW objects, eligible for consideration in a future authorized universe version; no Databricks cleanup/deletion plan | Experiment owner |
| 2026-10-21 | As last reported, Day 2 C300/M1 reconciliation 21/32 PASS, 3 running, 8 pending, zero failed; no interference permitted | User-provided Codex check |
| 2026-10-21 | Otherwise valid out-of-universe source denied; Agent denial retained for Human Review | PR #17; exact tests in `docs/source_universe_guardrail.md` |
| 2026-10-21 | Synthetic separately approved future host version permits its roster while v1 denies it; no real v2 installed | PR #17; future-version processing-entrypoint test |
| Future Day 3 | Replacement cohorts and Old/New/Combined Lossless/Stability evaluation | DEFERRED TO DAY 3, separate authorization |

**Incident is evidence of a boundary design failure, not evidence the extra RAW data are illegitimate. Retention is intentional: preserving them as real, auditable candidate assets enables legitimate future expansion while keeping the current experiment uncontaminated.**


## 11. SEC_BULK original inventory investigation — qualification complete

`LOCAL_SEC_BULK_COMPANYFACTS` and `LOCAL_SEC_BULK_SUBMISSIONS` remain original-universe members and are individually **QUALIFIED — OWNER_ATTESTED_PROVENANCE**, under the owner's explicit provenance-gap disposition, commit `787b473a78f5bcce814bafd8675ce1a9c5edea65`. The owner directly attested manual download from the official SEC website. This applies only to the two exact existing ZIPs, not independent proof of publisher archive identity. Their original investigation, paths, sizes, hashes, archive observations and missing evidence are preserved in §§13, 15–16. No separate admission defect was established. Qualification neither registers a Source ID nor authorizes cohort admission or processing.

## 12. Remediation execution ledger

This is the single current implementation ledger. Exact operational start/finish times are NOT CAPTURED unless stated; Git times prove commit/merge events, not inferred implementation times. All dates below are 2026-10-21; offset +08:00 is Shanghai/SGT.

| Stage | Final disposition | Actual event time / coverage | Evidence |
| --- | --- | --- | --- |
| Detection and Option 2 decision | COMPLETE | Day precision only; exact times NOT CAPTURED | §§1–5, owner instruction |
| Local governance and receipt reconciliation | COMPLETE | 16:53:31.561694+08:00; investigation completed 16:55:49.956562+08:00 | §13; evidence index and retained-reference appendix |
| Initial incident publication | VERIFIED | Commit 16:59:13+08:00; PR created 16:59:56+08:00; exact push time NOT CAPTURED | `05854c25dfc7554e5f596b346b489ec304c80a97`; PR #15 |
| SEC Bulk qualification | COMPLETE, both OWNER_ATTESTED | Attestation recorded 18:23:20.756079+08:00; commit 18:24:00+08:00 | `787b473a78f5bcce814bafd8675ce1a9c5edea65`; §§15–16 |
| Approved Universe v1 | OWNER APPROVED | Commit 18:37:52+08:00 | `319281c17d957dc8d442aaa63278df0d5a1596b3`; manifest and separate owner record |
| 800 retained RAW verification | VERIFIED with bounded exclusion/lineage coverage | Listing 10:43:24.905060Z–10:43:30.685448Z; readback 10:43:51.785057Z–10:54:15.396438Z; commit 18:56:05+08:00 | `009da4fa053f4d5e3ab182fbe08510808688204c`; Step 4 report and evidence |
| Local Guardrail and Agent boundary | IMPLEMENTED / MERGED | Implementation start/finish NOT CAPTURED; initial implementation commit `0f883e3` 17:23:55+08:00; reviewed final head `6eabe9897aa3a452bce7f279c6f5b4bbf3240d6a` committed 19:42:43+08:00; merge 19:50:59+08:00 | PR #17; merge `2988c62ce7e8a92547224e8212ed74f1cec2bc94`; §13 |
| Regression and negative tests | COMPLETE within offline coverage | Exact run start/finish NOT CAPTURED; recorded 2026-10-21 | 295 PASS, 23 SKIP; targeted 23 PASS, 1 SKIP; exact commands/dispositions in Guardrail evidence |
| Historical/remote execution paths | EXCLUDED from new approved execution | Bounded pre-merge audit; exact audit time NOT CAPTURED | §13; owner-supplied audit, not an independent persisted audit log |
| Replacement cohorts / experimental Lossless and Stability | DEFERRED TO DAY 3 | Outside incident closure scope | Separate approved Day 3 plan required |
| O_C300_M1 baseline retention/freeze acceptance | DEFERRED TO DAY 2 | Reported validation success does not establish final freeze | Step 4 retained completion `MAIN_720_COMPLETE_VALIDATED`, `NOT_FROZEN` |
| Owner closure approval and incident closure | OWNER APPROVED / CLOSED | Approval `2026-10-21T20:00:05+08:00`; closure recorded `2026-10-21T20:03:15+08:00` (UTC+08:00) | [owner approval comment](https://github.com/lightnino/edp-lab/pull/18#issuecomment-6315368530); all seven revised gates and documented limitations explicitly approved; §14 |

Closure is governed by the seven gates in §14. Replacement experiment execution and Day 2 baseline freeze are separate tasks, not incident-remediation prerequisites.

## 13. Independent local governance audit — 2026-10-21

This section preserves the original bounded local audit and records the implemented controls at their integration points. Option 2 is implemented within the documented local scope; the incident is CLOSED under the explicit owner approval recorded in §14. Industry links in §9 were supplied by the owner and were not independently consulted in this offline audit.

### Original local audit boundary and reproducibility

The following describes the original audit task, not the later Step 2–6 executions. Worktree `/Users/lightnino/Projects/edp-lab-incident`, branch `incident/source-universe-scope-control`, began clean at `ddb6e47c52afa08415614dc7f341255255d9c963`, exactly local `main` and its merge base. Remote: `origin https://github.com/lightnino/edp-lab.git`. Historical Day 3/4/5 worktrees at `c223117`, `2eee969`, `b9f5dc7` were read only. No merges/cherry-picks, code changes, RAW scans, downloads, transfers, jobs or Day 2 operational inspection occurred. GitHub publication is the only authorized network operation for this task. Local main ancestry is verified; remote main is checked during publication.

Owner input: `/Users/lightnino/Downloads/2026-10-21_source_universe_scope_control_incident.md`. Original decision dates have day precision only; exact discovery, proposal and owner-decision times are UNKNOWN. The Day 2 21/32 checkpoint remains a supplied historical observation, not independently refreshed.

Evidence documentation:

- [Metadata and receipt hash index](2026-10-21_evidence_index.md).
- [All 800 retained RAW references](2026-10-21_retained_raw_references.md), including per-instance acquisition identity, receipt hash, RAW hash, local path, remote path/status/time and historical processing references.

Count method: compare v1/v2 inventory `(inventory_id, sha256)` sets; crosswalk C2000 manifest members through frozen packet `original_raw_path` plus exact RAW SHA-256 to inventory v2 `final_path` plus SHA-256. This is a mechanical delivery-reference join, not semantic identity inference or a new registration rule. Existing GOLD uses its retained manifest path. Inventory v1/v2 hashes match §8. Both contain 3,021 entries and identical identity/hash sets. Original completion summary records 3,015 new verified publisher deliveries, four unchanged GOLD and two unadmitted bulk candidates; zero admissions/freezes in that acquisition step. Source Instances are physical deliveries, never ZIP members or rows.

The full family table in §2 is independently confirmed without corrections: original 3,021; C2000 2,000 = 1,200 original + 800 later acquisitions; unused original non-holdouts excluding GOLD and unresolved bulk 1,774; four GOLD outside C2000; 41 original holdouts; two bulk candidates. All original holdouts are absent from C2000. “Qualified unused” here means historical acquisition/selection readiness, not newly granted admission or semantic approval. At that historical checkpoint the maximum was 2,980 original non-holdouts and the qualification-limited 2,978 excluded both then-unresolved bulk entries. Both are now owner-qualified (§16). Neither number is an owner-approved new scale target.

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
| Admission qualification | QUALIFIED — OWNER_ATTESTED_PROVENANCE | QUALIFIED — OWNER_ATTESTED_PROVENANCE |
| Missing-evidence disposition | Owner accepted provenance gap for this exact ZIP; publisher receipt/digest unavailable | Owner accepted provenance gap for this exact ZIP; publisher receipt/digest unavailable |

For each, historical provenance says “User-supplied local ZIP; original publisher ZIP identity unverified.” Acquisition UTC, retrieval receipt and publisher archive identity are NULL; publisher URL is a hint only. Sidecars and enclosing directories warrant qualification review but do not prove corruption, completeness of the original SEC delivery, or independent publisher provenance. Historical integrity establishes the retained ZIP's consistency, not original publisher completeness. Missing receipts prevent automatic qualification under existing rules. On available evidence this is normal explicit admission staging, not a substantiated second control failure.

Bounded recovery found no contemporaneous publisher/retrieval evidence (§15). The owner then explicitly qualified both exact ZIPs by first-party attestation (§16). The original evidence gap remains documented; no further recovery is an incident blocker, and no new ID registration or admission occurred.

### 800-object retention and dependencies

The reference appendix identifies exactly 800 IDs. All 800 local registered paths exist by stat. All 800 acquisition receipt files match their frozen packet receipt SHA-256. All 800 retained remote receipts say `REMOTE_READBACK_SHA256_PASS`, with RAW digests matching manifest v6. Sum of those 800 receipt byte sizes is **79,225,793 bytes**; this is receipt-derived historical transfer accounting, not a current RAW measurement or the entire Day 3–5 transfer total.

Observed dependencies: N450 (50 extra NOAA), N750 (250 extra NOAA), N500 (400 WDI + 100 Treasury), their cumulative C750/C1500/C2000 freezes and manifests v4–v6, upload receipts and targeted structural inspection evidence. Structural profiling is downstream processing and must remain preserved. Freeze-time `downstream: NOT_STARTED` describes that checkpoint only. No retained evidence reviewed establishes CLEAN/QUERYABLE execution for these 800. Step 4 subsequently verified current remote presence, sizes and SHA-256 for **800/800**, **79,225,793 bytes**, with zero missing, inaccessible, mismatched or unverified objects. Seven incomplete responses were independently retried; both attempts remain retained. See [Step 4 report](https://github.com/lightnino/edp-lab/blob/009da4fa053f4d5e3ab182fbe08510808688204c/docs/incidents/2026-10-21_800_remote_verification.md), [objects.csv](https://github.com/lightnino/edp-lab/blob/009da4fa053f4d5e3ab182fbe08510808688204c/docs/incidents/evidence/800_remote_verification/objects.csv) and [validation.json](https://github.com/lightnino/edp-lab/blob/009da4fa053f4d5e3ab182fbe08510808688204c/docs/incidents/evidence/800_remote_verification/validation.json), commit `009da4fa053f4d5e3ab182fbe08510808688204c`. Global live consumer lineage remains incompletely established. Inspected C300/M1 physical-input evidence has zero overlap with the 800; all 800 are excluded from Universe v1 and accepted C300, and all 41 holdouts are outside C300. These checks confer no remote processing authority or universal consumer isolation. No physical retention action was necessary or performed; owner retention decision is binding. Missing `original_raw_path` on some earlier packet members is explicitly marked in the appendix; candidate identity, acquisition receipt and registered RAW path remain available. No missing local path or acquisition-receipt hash mismatch was found.

### Exact integration points — implemented local controls and excluded paths

Implementation evidence: [docs/source_universe_guardrail.md](../source_universe_guardrail.md), final reviewed head `6eabe9897aa3a452bce7f279c6f5b4bbf3240d6a`, merged [PR #17](https://github.com/lightnino/edp-lab/pull/17), merge `2988c62ce7e8a92547224e8212ed74f1cec2bc94` at `2026-10-21T11:50:59Z`. GitHub metadata independently verified the merged state, head, merge SHA and timestamp during this report update.

| Integration point | Verified actual implementation / disposition |
| --- | --- |
| `src/edp_lab/ingestion/universe.py`: `UniverseGate.load`, `verify_inventory` | Pins universe bytes, independent owner approval digest/linkage, version, historical sidecar and all referenced evidence hashes; absent/changed authority fails closed. |
| `src/edp_lab/ingestion/c300_admission.py`: `prepare`, `freeze`, `verify_registry` | Checks authorized capacity before selection/acquisition; exact delivery/registered identity, hash/path, qualification, holdouts, exact cohort and owner freeze evidence. Agent-authored permission cannot authorize freeze. No new freeze executed. |
| `metadata/source_universes/historical_cohort_bindings_v1.json` | Hash-bound versioned sidecar separates Universe Authority, Corpus Admission and Frozen Cohort, with universe ID/version/manifest digest. Historical manifests/freezes unchanged. New packets/markers carry universe references and new freezes bind roster/corpus hashes in `universe_binding.json`. |
| `src/edp_lab/profiling/source_reader.py:read_registered`; C300 `occurrences`; shallow `inspect`; checkpoint `validate_c300` | Validate explicit local bindings against universe/cohort identity/hash/path before RAW/parser access; existing RAW/member hashes and parser approval remain independent gates. No directory/prefix discovery can enlarge authorized inputs. |
| `src/edp_lab/tool_adapters/profiling.py`; five profiling functions; Agent interface | Host-fixed authority cannot be supplied/switched by requests. Denials remain BLOCKED / AUTHORIZATION_REQUIRED, approval-required and Human Review; metrics NOT_COMPUTED. No self-approval, cohort/version injection, denial override or acquisition to meet count. |
| Native contract preparation / sealing | Local contract validation does not certify remote execution. Historical remote notebooks and new native submission/processing remain EXCLUDED until guarded and separately authorized. |
| Historical N450/N750/N500 preparers, uploaders and profilers | EXCLUDED from new approved execution, not retrofitted or physically disabled. Exact historical commits, paths and hashes are preserved in the Guardrail document. No executable dispatch for these increments is present on inspected main/PR #17. |

Approved Universe: `EDP_LAB_ORIGINAL_SOURCE_UNIVERSE`, version **1**, **3,021 members**, [manifest](../../metadata/source_universes/approved_v1/manifest.json), SHA-256 `2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c`; [owner authorization](../../metadata/source_universes/approved_v1/owner_authorization.json) independently links that digest. Commit `319281c17d957dc8d442aaa63278df0d5a1596b3` verifies original v1/v2 identities/hashes, both owner-qualified SEC Bulk entries, 41 holdouts, exclusion of the 800 and exact C300 identity/hash/path membership **300/300**. Original frozen artifacts remain unchanged. **Universe Membership Approval does not independently authorize Admission, Freeze or Processing.** No approved manifest/approval record was edited.

Negative/compatibility coverage includes otherwise valid outside-universe data, newly arrived data outside the run roster, reserved holdouts, unapproved same-family instances, hash/qualification failures, missing authority, forged freeze approval and insufficient authorized capacity. Approved local bindings remain permitted within independent parser scope. A synthetic separate future host version demonstrates potential retained-source eligibility without rewriting v1 or creating a real v2. Host code/configuration replacement by an administrator is outside the request-level trust boundary.

Final offline results: **295 PASSED, 23 SKIPPED**, zero unexplained failures; targeted final correction **23 PASSED, 1 SKIPPED**. Ruff and whitespace PASS; GitHub [CI run 39593988618](https://github.com/lightnino/edp-lab/actions/runs/39593988618) independently verified completed/success for the final reviewed head. Exact commands and **each of the original 29 failure dispositions** are in the Guardrail document: **28 PASS; one environmental GOLD RAW SKIP**, with its independent missing-authority negative test now PASS (BLOCKED / AUTHORIZATION_REQUIRED). The real GOLD RAW files were absent from the test worktree; that accepted limitation leaves positive real-RAW fidelity unverified. It is not evidence of an incorrect 3,021 universe, corruption of the 800 or a production Guardrail failure. SKIP is not PASS. Tests were not rerun for this documentation-only change.

### Pre-merge execution-isolation audit — bounded evidence

The exact evidentiary basis for the following discovery counts is the **owner-supplied pre-merge audit summary in the Step 6B instruction**, corroborated for historical path exclusions by the committed Guardrail document. No separate reproducible local audit-output artifact was identified in this report's tracked evidence; these counts are not represented as independently captured logs. No new Databricks audit was started and no remote notebook was modified.

- GitHub main and PR #17: no executable N450/N750/N500 dispatch; old preparers/uploaders/profilers remain in separate historical branches/worktrees.
- Configured Databricks workspace: **0 accessible Jobs, 0 active runs, 0 pipelines, 23 retained terminal SUBMIT_RUN records**; no N450/N750/N500 workload identified in inspected run history.
- Retained trees: **3 notebooks** under `/Shared/edp-lab-native-v1`, **24** under `/Shared/edp-lab-c300-m1`; **27 sources** inspected read-only. They are not protected by the new remote runtime Guardrail, and manually executable historical paths remain technically callable.

This is bounded discovery, not universal proof of absent external execution paths. Historical Day 3–5 and unguarded remote paths are **EXCLUDED** from approved new experiment execution pending integration, testing and separate human authorization. They were not physically disabled or ACL-blocked, and live Databricks Guardrail execution was not verified. Successful RAW integrity checks do not prove global consumer isolation.

### Remaining experiment work

Replacement rosters, target adjustment, historical-to-replacement crosswalks, real new-cohort Lossless/Stability runs and operational measurements are **DEFERRED TO DAY 3**. O_C300_M1 baseline retention/freeze acceptance is **DEFERRED TO DAY 2**. These are outside the revised incident closure gates. The experiment owner explicitly approved incident closure with the documented coverage limits under §14. The single execution ledger is §12.

Retained structural completion summaries were also inspected: N450 records zero Databricks processing jobs and deferred final M1 fit; N750/N500 explicitly record `CLEAN_QUERYABLE: NOT_RUN`, `Stability: NOT_RUN`, and zero Databricks processing jobs. These are historical checkpoint claims, not current live dependency certification.

## 14. Closure criteria and owner review

**Decision date:** 2026-10-21 (UTC+08:00; exact original decision time NOT CAPTURED). Authority: explicit experiment-owner revised pre-Day-3 closure instruction and latest Step 6B in-place editing instruction.

**Current incident status: CLOSED — explicit experiment-owner approval recorded.** Owner `lightnino` approved EDP-INC-2026-10-21-001 under all seven revised closure gates at `2026-10-21T20:00:05+08:00` in the [owner approval comment](https://github.com/lightnino/edp-lab/pull/18#issuecomment-6315368530). Actual closure recorded at `2026-10-21T20:03:15+08:00` (UTC+08:00). The approval expressly accepts the documented local enforcement scope, accepted test limitations and exclusion of historical unguarded remote paths. Rebuilding N450/C750 and new experiment runs are deferred to Day 3; Day 2 baseline retention/freeze acceptance remains separate. Historical C750/C1500/C2000 are not approved baselines. Retain all 800 legitimate local/remote RAW and reproducible references unless a separate future retention decision changes that requirement.

### Seven closure gates — final evidence assessment

| Gate | Final disposition after owner review | Exact supporting evidence / commit | Coverage boundary |
| --- | --- | --- | --- |
| 1. Approved Universe v1 | EVIDENCE COMPLETE — OWNER APPROVED | `metadata/source_universes/approved_v1/{manifest.json,owner_authorization.json,verification.json,approval_verification_v1.json}`; manifest digest `2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c`; commit `319281c17d957dc8d442aaa63278df0d5a1596b3` | Exact 3,021; 41 reserved; 800 excluded; C300 300/300; membership grants no admission/freeze/processing authority. |
| 2. SEC Bulk owner qualification | EVIDENCE COMPLETE — BOTH QUALIFIED | §§11, 13, 15–16; commit `787b473a78f5bcce814bafd8675ce1a9c5edea65` | Exact two retained ZIPs only; first-party manual official-SEC-download attestation; historical publisher receipts/digests unavailable; no registration/admission. |
| 3. 800 retained RAW integrity and exclusion | EVIDENCE COMPLETE — VERIFIED WITH BOUNDED EXCLUSION | Step 4 report; `evidence/800_remote_verification/{objects.csv,validation.json,exclusions.json,dependencies.json,known_c300_consumers.json}`; commit `009da4fa053f4d5e3ab182fbe08510808688204c` | Presence/size/SHA 800/800; 79,225,793 bytes; zero unverified; both retry attempts retained; excluded from universe/C300, zero inspected M1 overlap; global live consumer lineage not exhaustive. |
| 4. Deterministic admission/freeze/processing authorization | EVIDENCE COMPLETE — IMPLEMENTED LOCAL SCOPE | §13; `docs/source_universe_guardrail.md`; PR #17 merged `2988c62ce7e8a92547224e8212ed74f1cec2bc94` | Exact identity/hash/path, qualification/holdouts, roster/capacity, owner authority and fail-closed checks; explicit local bindings; remote/historical paths excluded, not certified guarded. |
| 5. Agent authorization boundary | EVIDENCE COMPLETE — TESTED WITHIN HOST TRUST BOUNDARY | Guardrail Agent outcomes and authorization tests; PR #17, final head `6eabe9897aa3a452bce7f279c6f5b4bbf3240d6a` | No self-approval/version/cohort injection, denial override or acquisition for quota; reviewed host installation is trusted; no autonomous authority granted. |
| 6. Tests and historical path restrictions | EVIDENCE COMPLETE — ACCEPTED TEST LIMITATIONS DISCLOSED | Guardrail exact commands, 29 individual dispositions, final correction; PR #17 and GitHub CI; §13 pre-merge audit basis | 295 PASS/23 SKIP; targeted 23 PASS/1 SKIP; original 28 PASS/1 environmental GOLD RAW SKIP; independent missing-authority PASS; historical/remote paths EXCLUDED pending separate integration/tests/approval. No live remote Guardrail verification. |
| 7. Merged Guardrail, ledger and explicit owner closure | COMPLETE — OWNER APPROVED / CLOSED | PR #17 merged at `2026-10-21T11:50:59Z`, merge `2988c62ce7e8a92547224e8212ed74f1cec2bc94`; consolidated ledger §12; [owner approval comment](https://github.com/lightnino/edp-lab/pull/18#issuecomment-6315368530) | Explicit owner approval at `2026-10-21T20:00:05+08:00` covers all seven revised gates and documented limitations; closure recorded `2026-10-21T20:03:15+08:00` (UTC+08:00). |

### Final incident closure update

Update current status **in place**. Do not append superseding statuses or preserve obsolete current-state ledgers; Git retains earlier versions. Preserve genuine historical events, timestamps and evidence. This replaces the earlier append-only instruction.

The experiment owner explicitly approved closure of this incident under the seven revised closure gates in the [owner approval comment](https://github.com/lightnino/edp-lab/pull/18#issuecomment-6315368530). The existing header, current status and final ledger have been updated in place to **CLOSED**, with separate actual approval and closure recording timestamps above. The final report is maintained directly on `main`; the owner approval remains linked above. No Day 3 admission, freeze, upload, profiling or processing is authorized by closure review.

## 15. Step 2 SEC Bulk qualification recovery evidence

Recorded at **2026-10-21T18:14:10.642456+08:00** (UTC+08:00; actual recording time, not original retrieval time). Worktree `/Users/lightnino/Projects/edp-lab-incident`, branch `incident/closure-evidence`, starting commit `d216390`. Scope: only `LOCAL_SEC_BULK_COMPANYFACTS` and `LOCAL_SEC_BULK_SUBMISSIONS`. Original observations and timestamps below describe the bounded investigation; current qualification reflects the subsequent owner disposition.

**Outcome: investigation COMPLETE within the bounded search; final qualification for each candidate is QUALIFIED — OWNER_ATTESTED_PROVENANCE (§16).** No authentic contemporaneous publisher/retrieval evidence was recovered in the searched records. This is a bounded negative finding, not proof that no receipt exists elsewhere. Admission is not authorized or executed.

| Required determination | LOCAL_SEC_BULK_COMPANYFACTS | LOCAL_SEC_BULK_SUBMISSIONS |
| --- | --- | --- |
| Approved universe membership | CONFIRMED: original v1 and v2 inventories each contain 3,021 entries and this exact candidate/hash | CONFIRMED: original v1 and v2 inventories each contain 3,021 entries and this exact candidate/hash |
| Physical RAW integrity | Historical SHA-256 and full archive CRC PASS; 1,418,648,998 bytes; 40,924 members including 20,462 macOS sidecars | Historical SHA-256 and full archive CRC PASS; 1,974,869,371 bytes; 1,988,886 members including 994,443 macOS sidecars |
| Retained SHA-256 | `23e23cc8293fa22abda2f7d0568ee5534e149b51a77cd40171c3d834278cc902` | `5c75f9d996d5eea8a0e05689e28079d069a80e1632cf87ba24021da7e48d465b` |
| Current physical check | Stat matches historical size/inode `170344231`/mtime_ns `1792486764931827650`; current content hash/CRC NOT RERUN | Stat matches historical size/inode `170344669`/mtime_ns `1792487319033321638`; current content hash/CRC NOT RERUN |
| Publisher provenance | OWNER_ATTESTED official SEC manual download; independent archive identity/edition unknown | OWNER_ATTESTED official SEC manual download; independent archive identity/edition unknown |
| Retrieval receipt | MISSING in searched evidence; original receipt/acquisition UTC NULL; current `xattr -l` succeeds with empty output | MISSING in searched evidence; original receipt/acquisition UTC NULL; current `xattr -l` succeeds with empty output |
| Admission qualification | **QUALIFIED — OWNER_ATTESTED_PROVENANCE** | **QUALIFIED — OWNER_ATTESTED_PROVENANCE** |
| Historical gap / final disposition | No recovered original receipt; explicitly dispositioned by owner attestation | No recovered original receipt; explicitly dispositioned by owner attestation |
| Owner qualification authority | RECORDED in §16; actual admission remains separately gated | RECORDED in §16; actual admission remains separately gated |

RAW paths remain those in §13. No full ZIP scan was repeated: existing integrity evidence is unchanged and another CRC/hash pass cannot recover missing provenance. A matching stat is not a current byte-integrity proof. Before any future ingest/admission, verify the exact retained RAW hashes under the applicable contract.

### Evidence recovered and contract assessment

The original local availability observation is `2026-10-20T09:12:00.756956+00:00`. Its provenance objects explicitly record NULL acquisition UTC, original retrieval receipt and publisher archive identity, and empty historical extended attributes. Local move records establish same-volume relocation from Downloads, with preserved inode and hash; they are local custody evidence, not SEC retrieval receipts. `reuse-checks.json` records zero network requests for these candidates. The completion summary explicitly records 3,021 entries, 3,015 new verified publisher deliveries, four unchanged GOLD and **two existing unadmitted bulk candidates**, zero new admissions and zero freezes at that checkpoint. The v2 `publisher=SEC` label supplies no missing receipt: both inventories retain blank publisher URL and Source Instance ID.

The organization report records that `Downloads/EDP` disappeared externally, an initial empty submissions ZIP was invalid, and the extracted submissions inventory was interrupted (`FileNotFoundError CIK0002142938.json`). These historical observations remain preserved. They do not invalidate the subsequently verified retained submissions ZIP, establish delivery equivalence, or supply an original publisher identity. Directory inventories and macOS sidecars cannot establish publisher completeness or archive authenticity.

Contract applied: `docs/source_instance_identity.md` identity/admission rules 2–4 and `docs/corpus_admission_policy.md` require independent delivery provenance and receipt/retrieval evidence, with explicit present-day disposition of historical gaps; `docs/c300_acquisition_tooling.md` records approval of that minimum policy. `docs/whole_lab_sources.md` explicitly keeps locally intact bulk packages with unknown publisher identity unadmitted. Policy approval and universe membership do not constitute per-delivery admission authority. Recovered evidence alone did not satisfy the complete delivery-evidence contract; the subsequent explicit owner disposition supplies the authorized qualification outcome (§16). No separate upload failure, lost authenticated receipt, or code defect is established.

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

### Final qualification disposition after recovery

The bounded investigation identified a historical provenance gap, not RAW corruption or a newly established admission defect. The owner subsequently qualified both exact ZIPs by explicit first-party attestation (§16). Both remain in the original 3,021-member universe; neither qualification allocates IDs or executes admission. The historical 2,978 qualification limitation is resolved; the absolute non-holdout maximum remains 2,980. No inventory, cohort or RAW was changed by qualification.

## 16. SEC Bulk owner attestation and qualification disposition

**Attestation date: 2026-10-21. Recorded at 2026-10-21T18:23:20.756079+08:00 (UTC+08:00).** Authority: the experiment owner's explicit instruction in this conversation. The original message timestamp and a separate signed attestation artifact are unavailable; the recording time is not represented as the original message or acquisition time.

The owner's statement is preserved verbatim here:

> Record the experiment owner's explicit first-party SEC Bulk provenance attestation above in the existing incident/closure-evidence branch.

The owner expressly directed:

> Set Admission Qualification for BOTH sources to QUALIFIED — OWNER_ATTESTED_PROVENANCE, under the admission policy's explicit human disposition of missing evidence.

This records first-party owner-attested provenance and explicit human disposition under `docs/corpus_admission_policy.md` and `docs/source_instance_identity.md`; it does not represent independently verified SEC download logs. The owner directly attested: “User-supplied Local ZIP — Downloaded Manually by Owner Directly from the Official SEC Website.” This is also pinned in the Approved Universe v1 qualification evidence; no acquisition date or SEC archive edition is inferred. The attestation is linked only to the two existing physical ZIP references below and does not establish a general waiver for other sources.

| Existing inventory ID | Existing RAW path | Recorded SHA-256 | Final Admission Qualification |
| --- | --- | --- | --- |
| `LOCAL_SEC_BULK_COMPANYFACTS` | `/Users/lightnino/Projects/edp-lab/data/raw/sec/bulk/companyfacts.zip` | `23e23cc8293fa22abda2f7d0568ee5534e149b51a77cd40171c3d834278cc902` | **QUALIFIED — OWNER_ATTESTED_PROVENANCE** |
| `LOCAL_SEC_BULK_SUBMISSIONS` | `/Users/lightnino/Projects/edp-lab/data/raw/sec/bulk/submissions.zip` | `5c75f9d996d5eea8a0e05689e28079d069a80e1632cf87ba24021da7e48d465b` | **QUALIFIED — OWNER_ATTESTED_PROVENANCE** |

For **each** ZIP, original download receipts and independent publisher digests remain **UNAVAILABLE**. Original acquisition UTC and independently authenticated publisher archive/snapshot identity remain unknown. Owner attestation supplies the expressly authorized human provenance disposition; it does not recover or replace those missing historical artifacts. Historical local SHA/archive integrity remains verified as documented in §§13 and 15; no new full RAW hash/CRC verification is claimed. Current hash verification remains required before any future ingestion under the existing contract.

**SEC Bulk Qualification Recovery: COMPLETE.** This owner disposition applies to these two exact candidates only. Original investigation findings, missing-evidence observations and historical timestamps are preserved; current qualification fields are reconciled in place. Both remain members of the original **3,021 Approved Universe**; qualification changes neither universe membership nor frozen cohort membership. The earlier 2,978 ceiling excluded these two unresolved candidates; this disposition resolves that qualification exclusion, without selecting a scale target or creating admitted instances.

No Source Instance IDs were allocated, RAW modified, inventory/registry changed, or source admitted into a cohort. Qualification is separate from actual admission and parser/processing approval. Incident closure is now explicitly owner-approved under all seven revised gates (§14). Qualification evidence is retained in commit `787b473a78f5bcce814bafd8675ce1a9c5edea65` on `incident/closure-evidence`. The documentation publication was authorized by Step 6B; the separate explicit owner incident closure approval is recorded in §14.
