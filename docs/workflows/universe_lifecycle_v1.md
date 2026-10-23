# Universe Lifecycle V1 — Creation (0→1) and Expansion (1→2)

**Status: PROPOSED FOR OWNER REVIEW — specification only.** This document does not approve a universe, mutate existing manifests, select a cohort, authorize processing, or implement an autonomous runner.

**Purpose.** Establish a reusable source-estate governance lifecycle, independent of whether a subsequent cohort follows `INITIAL_MODEL`, `CORPUS_ONLY`, `ADDITIVE` or `CORRECTIVE` processing. A universe lists *eligible candidate source instances*. A cohort selects *approved members* from that universe. These are separate authorities.

**Historical references:** `metadata/source_universes/approved_v1/`, `docs/source_universe_guardrail.md`, `docs/incidents/2026-10-21_source_universe_scope_control.md`, `src/edp_lab/ingestion/universe.py`, `docs/cohort_publication.md`. These are authoritative for existing snapshots; this proposal must not rewrite them.

## 1. Reusable process (two modes)

| Step | Creation: no approved universe (0→1) | Expansion: approved Uv already exists (1→2) | Required evidence / exit |
| --- | --- | --- | --- |
| U0. Identify authority baseline | Locate original inventories, acquisition evidence, raw artifacts and exclusions; **no universe authority yet** | Verify current approved universe ID/version, exact manifest bytes/SHA, owner record, protected holdouts and governing policies | `UNIVERSE_BASELINE_VERIFIED` or `NO_PRIOR_UNIVERSE` |
| U1. Discover candidate instances | Inventory every retained RAW artifact: exact path, physical identity, SHA, size, provenance, format/family, version/date and original-vs-controlled nature | Inventory only new/proposed changed instances; retain previous member list and track candidate provenance separately | `CANDIDATES_INVENTORIED` |
| U2. Qualify | Independently check original evidence, source family, instance identity, reproducible hashes and missing/uncertain provenance; quarantine unresolved | Apply same checks to additions; compare with old universe by **physical identity**, source/version and hash; no silent cross-version identity reassignment | `QUALIFICATION_RECORDED` |
| U3. Holdout and scope | Define intended development scope and protected transfer/holdout population before sampling | Retain unchanged holdout protection unless a separate explicit owner decision revises it; reject inclusion of any reserved source | `SCOPE_AND_HOLDOUTS_RECONCILED` |
| U4. Proposal + difference | Build canonical candidate manifest and sorted digest; record exclusions, exceptions, assumptions, source evidence, and population counts | Publish a *proposed* Uv+1 diff: additions, unchanged members, changed facts, removed/retired members (if any), source-by-source rationale | `UNIVERSE_PROPOSAL_READY` |
| U5. Owner semantic/governance decision | Owner chooses eligible scope and provenance exceptions, accepts/denies candidate universe version | Owner explicitly approves the new membership/diff and any changed holdout policy; old approval never implicitly extends to new sources | `UNIVERSE_OWNER_APPROVED` / `NEEDS_HUMAN_DECISION` |
| U6. Versioned publication | Exclusively publish approved Uv manifest, digest and distinct owner approval; never derive approval from a proposed JSON flag | Exclusively publish Uv+1, preserving Uv and previous authorization byte-for-byte, with parent version/hash | `UNIVERSE_VERSION_PUBLISHED` |
| U7. Enforcement + negatives | Verify actual gate rejects absent identities, mismatched hashes, forged approval, unqualified entries and reserved holdouts | Additionally reject unapproved Uv+1 changes, old-source modifications, unintended removals and historical retroactive scope | `UNIVERSE_GATE_VALIDATED` |
| U8. Independent readback | Read back manifest, approval signatures/pins, exact membership/counts, holdout separation and evidence references | Read back both old and new versions and reproducible diff; demonstrate previous cohort memberships unchanged | `UNIVERSE_FROZEN_AND_VERIFIED` |
| U9. Exit and handoff | Make Uv available to cohort planning; **no admission or processing authority granted** | Make Uv+1 available for *future* cohort planning; preserve historical runs under their original authority | `UNIVERSE_LIFECYCLE_COMPLETE` |

Both modes share one contract; only the existence of a prior approved universe and the old/new diff requirements differ. The number of new source families is unrestricted by workflow design; it is determined by approved evidence and scope.

## 2. Input and output contracts

**Candidate input (not authority):** candidate instance ID; publisher/delivery ID; acquisition timestamp and provenance; original artifact path and SHA-256; size and format; family; source snapshot/version; holdout classification; review/evidence status; link to any already registered instance. Filename, basename, CUSIP, ticker or equal text are **not** automatically a physical or enterprise identity.

**Versioned output (after approval):** immutable universe ID/version; exact ordered membership; lineage to inventories; source family and original path/hash; holdout list/policy; qualification outcomes and evidence; version parent (if expanding); approval record anchored outside the untrusted agent; manifest SHA; negative tests and independent readback receipt. Proposals and signed/owner-installed approvals are different artifacts.

**Approval boundaries:**

- Universe approval: eligibility to *select* exact source instances in a future development cohort; no RAW upload, admission, model change, Databricks write or Git merge.
- Cohort approval: selection/admission of a disjoint finite subset under that universe; no implicit new parser/business model.
- Bounded workflow grant: exact subsequent operations, source hashes, contract versions, output namespaces, runtime/retry budgets, and protected write authority.
- New publisher, identity equivalence, holdout release, newly inferred economic interpretation or out-of-universe acquisition is a fresh governance decision, not self-granted by the agent.

## 3. Existing Universe v1 and future v2 guardrails

The existing owner-approved `EDP_LAB_ORIGINAL_SOURCE_UNIVERSE` v1 has **3,021** members and **41 protected Day 13 holdouts**. Therefore the upper bound inside v1 without consuming holdouts is **2,980** physical instances, before any other cohort restrictions. A 3,000-member development cohort cannot be obtained solely from those approved non-holdout v1 members.

The previously acquired **800 outside-original-universe RAW objects** are retained, not erased, and may be researched as v2 candidates, but were *not* authorized into v1 by their physical retention or old processing evidence. New v2 approval is prospective; it cannot retroactively legalize historical out-of-universe cohort selection. The two original SEC Bulk candidates have owner-attested provenance qualification in current v1 evidence; universe qualification alone does not admit them to a cohort.

No unreviewed universe v2 is created by this specification. Day 7 Universe Expansion remains **agent-assisted investigation + owner approval**, not an autonomous scope-widening operation. Once scope is approved, the separate Cohort/Model Workflow can automate processing.

## 4. Hard negative tests / non-negotiable behavior

1. Wrong/changed RAW SHA, missing or ambiguous physical identity, source/manifest mismatch → refuse enrollment, retain evidence.
2. Any holdout or unapproved source → fail the universe gate before admission, even if physical RAW exists in Databricks.
3. Agent-edited approval text, untrusted “approved” marker, or unsigned altered manifest → no authority.
4. Universe membership ≠ successful source qualification ≠ cohort admission ≠ RAW availability ≠ processed/verified QUERYABLE.
5. An expanded universe must not modify historical manifests/cohorts, delete earlier evidence, or silently redefine source identities.
6. Unresolved provenance/identity → `UNRESOLVED` with exact question/evidence; unaffected candidate evaluation may continue.
7. Simulated/non-live tests must never be reported as live source acquisition or as a published universe.

## 5. Fit with future orchestration

The Day 5 autonomous C1500→C2000 experiment consumes the **already approved Universe v1**, not a newly invented Universe v2. This document's U0–U9 is a specification for the initial Universe bootstrap and for the *separately owner-governed* future expansion. The executor must consume pinned approvals and verify them; it must not become its own source-estate authorizer.

**No code, admission, new universe, frozen cohort, approval or Databricks operation is performed by this document.**
