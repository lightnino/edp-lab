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
**Day 2 / C300:** The accepted C300 population remained separate from the historical Day 3–5 scope expansion; original source identity/path/hash compatibility is 300/300. Day 2 processing and baseline operations are not part of this incident remediation.

**Publication:** Original report published in [PR #15](https://github.com/lightnino/edp-lab/pull/15), initial anchor `05854c25dfc7554e5f596b346b489ec304c80a97`; final incident status and evidence summary updated in this document on `main`. Owner closure approval is separately documented at the linked GitHub [approval comment](https://github.com/lightnino/edp-lab/pull/18#issuecomment-6315368530).
**Evidence basis:** Original read-only investigation, owner decisions, immutable inventory/cohort evidence, approved Universe v1, Step 2/4 verification, merged Guardrail PR #17 and bounded execution audit (§§8, 11–13).

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

## 5. Decision and remediation — Option 2 implemented

### Option 2: restore the original authorized universe

On 2026-10-21, the experiment owner chose **Option 2 (logical rollback)**: preserve the original **3,021-member, owner-approved Universe v1**, its 41 holdouts and unchanged historical artifacts. The 800 later-acquired sources are legitimate, hash-verified RAW assets but **outside the current experiment**. Retain them locally and in Databricks; **no deletion, VACUUM, relocation or retrospective admission**. Historical C750/C1500/C2000 freezes remain evidence, **not approved baselines**.

**Why Option 2:** **Source Estate growth is continuous; Experiment Scope changes are explicit, authorized, and versioned.** EDP Lab may grow toward millions of Source Instances and ~2 PB of enterprise data, but silent source acquisition to meet a target changes the experimental population and makes results across stages incomparable. A frozen experiment needs an independently approved universe, a qualified admitted set, and a specific authorized cohort. An otherwise valid source outside that scope must be denied as **OUT_OF_SCOPE / AUTHORIZATION_REQUIRED**, not misclassified as corrupt.

### Option 1 not selected

Option 1 would expand the current universe to **3,821** by retroactively including the 800. A *separately owner-approved future version* may legitimately include some or all of them, but cannot retroactively validate these historical cohorts. The original non-holdout ceiling is **2,980**; exact C3000 would require a separate scope or target decision. That numerical limit is **not an established cause** of this incident.

### Implemented disposition

- **Universe:** Original inventory and **300/300 C300 identity/path/hash** compatibility verified; Universe v1 pinned to owner approval and SHA-256. Both SEC Bulk entries qualified under their specific owner attestations (§11); qualification itself grants no admission.
- **RAW:** All **800/800** retained remote objects passed current presence, size and SHA-256 readback; the 800 remain excluded from Universe v1 and accepted C300.
- **Guardrail:** Deterministic local admission, freeze, processing and Agent authorization boundaries implemented and merged in [PR #17](https://github.com/lightnino/edp-lab/pull/17); historical unguarded Day 3–5 and remote execution paths are **excluded**, not technically disabled (§13).
- **Decision and closure:** **APPROVED / CLOSED** by the experiment owner (§14). No new experiment run is authorized by closure.

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

## 7. Containment and boundaries

The incident is **CLOSED**. C300 belongs to the original approved universe and remained separate from the historical Day 3–5 expansion. The retained 800 RAW objects and their audit evidence were not deleted or reclassified as bad data. Historical C750/C1500/C2000 are not accepted baselines.

The implemented Guardrail protects the specified **local** entrypoints. Historical scripts and Databricks notebooks are **excluded from new authorized runs**, but are not physically disabled or proven universally inaccessible; full remote-consumer lineage and live remote Guardrail execution were **not verified** (§13). Any later use requires separate guarded integration and owner authorization.

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

## 10. Decision and authorization record

| Event | Resolution | Evidence |
| --- | --- | --- |
| Detection, 2026-10-21 | C2000 reconciled to 1,200 original + 800 outside sources; original 41 holdouts preserved | §§1–3; original source-family breakdown |
| Owner decision | **Option 2:** preserve the original 3,021 Universe v1, retain but exclude the 800, and reject retroactive approval of historical cohort freezes | §5 |
| Owner authorization and remediation | SEC Bulk separately qualified; original Universe v1 approved; remote 800/800 verified; local Guardrail merged | §§11–13; [PR #17](https://github.com/lightnino/edp-lab/pull/17) |
| Owner closure | **APPROVED** | [Owner comment](https://github.com/lightnino/edp-lab/pull/18#issuecomment-6315368530) |

## 11. SEC Bulk — investigation and final qualification

Two existing SEC Bulk ZIPs were always among the **3,021 original physical sources**. At detection they lacked contemporaneous retrieval/publisher evidence and had not been admitted. The bounded evidence recovery found no original publisher receipt or independently authenticated archive digest. The owner subsequently attested that these exact ZIPs had been **downloaded manually from the official SEC website** and expressly resolved that provenance gap under the admission policy.

| Source in original inventory | Retained local RAW | Recorded bytes | Recorded SHA-256 | Historical archive integrity | Final qualification |
| --- | --- | ---: | --- | --- | --- |
| `LOCAL_SEC_BULK_COMPANYFACTS` | `data/raw/sec/bulk/companyfacts.zip` | 1,418,648,998 | `23e23cc8293fa22abda2f7d0568ee5534e149b51a77cd40171c3d834278cc902` | CRC PASS; 40,924 entries (20,462 macOS sidecars) | **QUALIFIED — OWNER_ATTESTED_PROVENANCE** |
| `LOCAL_SEC_BULK_SUBMISSIONS` | `data/raw/sec/bulk/submissions.zip` | 1,974,869,371 | `5c75f9d996d5eea8a0e05689e28079d069a80e1632cf87ba24021da7e48d465b` | CRC PASS; 1,988,886 entries (994,443 macOS sidecars) | **QUALIFIED — OWNER_ATTESTED_PROVENANCE** |

**Evidence boundary:** Original publisher receipts, acquisition UTC and independently verified SEC ZIP edition/digest remain unavailable; preserved file sizes/inode/mtime match historical observations, but no new full current-content hash or CRC was run. Owner attestation is not independent publisher verification. No new Source Instance IDs, admissions, freezes or processing were created. This is qualification of **these two retained snapshots only**, not a blanket provenance waiver.

Detailed original recovery observations, source records and evidence hashes remain in [Step 2 commit `787b473`](https://github.com/lightnino/edp-lab/commit/787b473a78f5bcce814bafd8675ce1a9c5edea65) and the original Git history. **Current final disposition: QUALIFIED for both; no separate SEC Bulk control failure was established.** Source qualification changes no universe membership and does not authorize admission.

## 12. Remediation execution ledger

This ledger records **only incident remediation and closure**. Times are on 2026-10-21; a Git commit time is evidence of that commit, not an inferred implementation start time.

| Completed incident step | Final status | Primary evidence |
| --- | --- | --- |
| Detection and Option 2 decision | **COMPLETE** | §§1–5; owner decision |
| SEC Bulk provenance investigation and owner qualification | **QUALIFIED** (both) | §11; [commit `787b473`](https://github.com/lightnino/edp-lab/commit/787b473a78f5bcce814bafd8675ce1a9c5edea65); owner attestation recorded 18:23:20+08:00 |
| Approved Universe v1 | **APPROVED**, 3,021 members, 41 holdouts | [commit `319281c`](https://github.com/lightnino/edp-lab/commit/319281c17d957dc8d442aaa63278df0d5a1596b3); pinned manifest/owner record |
| 800 retained RAW remote integrity/exclusion | **VERIFIED**, 800/800 | [Step 4 commit `009da4f`](https://github.com/lightnino/edp-lab/commit/009da4fa053f4d5e3ab182fbe08510808688204c); readback 10:43:51–10:54:15Z |
| Local Guardrail, Agent denial and regression tests | **IMPLEMENTED / PASS within tested scope** | [PR #17](https://github.com/lightnino/edp-lab/pull/17), merged `2988c62ce7e8a92547224e8212ed74f1cec2bc94` at 19:50:59+08:00; §13 |
| Incident closure | **APPROVED / CLOSED** | [Owner approval](https://github.com/lightnino/edp-lab/pull/18#issuecomment-6315368530) at 20:00:05+08:00; closure recorded 20:03:15+08:00 |

## 13. Verified Guardrail and execution boundaries

### Scope and evidence

Approved universe: `EDP_LAB_ORIGINAL_SOURCE_UNIVERSE` v1, **3,021** exact physical identities; pinned [manifest](../../../metadata/source_universes/approved_v1/manifest.json), SHA-256 `2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c`, with separate [owner approval](../../../metadata/source_universes/approved_v1/owner_authorization.json). Original inventory v1/v2 and **C300 300/300** identity/path/hash compatibility verified; 41 holdouts remain reserved. This is universe authorization, not automatic source admission or processing approval.

The original reconciliation compared inventory identities/SHA-256 with frozen C2000 manifests and acquisition receipts; the complete **family breakdown is preserved in §2**, with [evidence index](evidence_index.md) and [800-reference appendix](retained_raw_references.md).

Step 4 independently verified **800/800 current remote RAW objects** for presence, size and SHA-256, totaling **79,225,793 bytes**, with no mismatches; seven incomplete responses were retried and both attempts retained. The 800 are excluded from Universe v1 and accepted C300; examined C300/M1 physical inputs had zero overlap. Historical Day 3–5 uploads and structural profiling are preserved; global live consumer lineage is **not exhaustively verified**. Evidence: [Step 4 report](https://github.com/lightnino/edp-lab/blob/009da4fa053f4d5e3ab182fbe08510808688204c/docs/incidents/2026-10-21_800_remote_verification.md), [800-object readbacks](https://github.com/lightnino/edp-lab/blob/009da4fa053f4d5e3ab182fbe08510808688204c/docs/incidents/evidence/800_remote_verification/objects.csv) and [validation](https://github.com/lightnino/edp-lab/blob/009da4fa053f4d5e3ab182fbe08510808688204c/docs/incidents/evidence/800_remote_verification/validation.json).

### Implemented deterministic controls (local scope only)

[Guardrail PR #17](https://github.com/lightnino/edp-lab/pull/17), merge `2988c62ce7e8a92547224e8212ed74f1cec2bc94`; detailed code/test evidence in [source_universe_guardrail.md](../../source_universe_guardrail.md).

| Integration | Verified control |
| --- | --- |
| `ingestion/universe.py`; owner manifest and pinned cohort sidecar | Validate exact owner approval, universe version/digest, source identity/hash/path, 41 holdouts and cohort binding; fail closed on missing/changed evidence. |
| `c300_admission.py`: `prepare`, `freeze`, `verify_registry` | Check authorized roster and capacity before selection/freeze; invalid or Agent-injected approval denied. |
| `profiling/source_reader.py`; C300 reader, inspection and checkpoint; native local preparation | Check explicit eligible binding before protected local RAW/processing; parsing/RAW hash rules remain additional independent checks. |
| `tool_adapters/profiling.py` and Agent boundary | Requests cannot self-approve, change version/roster or bypass `BLOCKED / AUTHORIZATION_REQUIRED`; Human Review required. |

**Tests:** 295 PASS / 23 SKIP full offline suite; final targeted correction 23 PASS / 1 SKIP; Ruff, whitespace and GitHub CI **PASS**. The original 29 failures were dispositioned as **28 PASS + 1 environmental GOLD RAW SKIP**; independent missing-authority negative test PASS. The missing GOLD files prevent a real-RAW fidelity PASS and do **not** indicate corrupt 800 data or an invalid 3,021 inventory. See Guardrail evidence for exact 29-case mapping and other skip prerequisites.

### Unguarded historical and remote execution — excluded

- **GitHub/main:** No N450/N750/N500 execution dispatch in the inspected main or merged PR. Historical preparers, uploaders and profilers remain in separate branches/worktrees; they are **not approved for execution**.
- **Bounded Databricks discovery:** 0 accessible Jobs, 0 active runs, 0 pipelines; 23 historical terminal `SUBMIT_RUN` records. Retained remote notebook trees held 3 native and 24 C300/M1 notebooks; 27 notebook sources inspected. None were shown to enforce the new remote pinned-universe Guardrail.
- **Boundary:** Historical worktrees/notebooks remain potentially manually callable. They were **not** ACL-blocked, physically disabled or proven universally inaccessible. These results are from the owner's bounded pre-merge audit summary, **not** an independently persisted full workspace audit. Future execution requires guarded integration, testing and separate authorization. No live Databricks Guardrail coverage is claimed.

## 14. Closure approval

**Status: CLOSED. Owner approval: APPROVED** ([GitHub approval](https://github.com/lightnino/edp-lab/pull/18#issuecomment-6315368530)). Approved 2026-10-21T20:00:05+08:00; closure recorded **2026-10-21T20:03:15+08:00**. Approval accepts the stated local enforcement scope, test skips and excluded unguarded historical/remote paths; it grants **no new execution authority**.

| Closure criterion | Result and evidence |
| --- | --- |
| 1. Original Universe v1 | **APPROVED** — 3,021 members, 41 holdouts, 800 excluded, C300 300/300; §13, commit `319281c` |
| 2. SEC Bulk qualification | **QUALIFIED** — both exact ZIPs by owner attestation; §11, commit `787b473` |
| 3. 800 preservation and exclusion | **VERIFIED** — 800/800 remote presence/size/SHA, approved-universe and C300 exclusion; §13, commit `009da4f` |
| 4. Deterministic authorization | **PASS (local scope)** — pinned admission/freeze/processing checks; PR #17 |
| 5. Agent authority boundary | **PASS (local scope)** — no self-approval or denial override; PR #17 |
| 6. Regression and historical paths | **ACCEPTED** — 295 PASS/23 SKIP, 29 original failures dispositioned, historical/remote execution excluded; §13 |
| 7. Merge and owner signoff | **APPROVED / CLOSED** — PR #17 merged; owner approval linked above |

