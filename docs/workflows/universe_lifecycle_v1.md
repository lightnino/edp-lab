# Universe Lifecycle V1 — Creation (0→1) and Expansion (1→2)

**Status: PROPOSED FOR OWNER REVIEW — specification only.** This document does not approve a universe, mutate existing manifests, select a cohort, authorize processing, or implement an autonomous runner.

**Purpose.** Establish a reusable source-estate governance lifecycle, independent of whether a subsequent cohort follows `INITIAL_MODEL`, `CORPUS_ONLY`, `ADDITIVE` or `CORRECTIVE` processing. A universe lists *eligible candidate source instances*. A cohort selects *approved members* from that universe. These are separate authorities.

**Historical references:** `metadata/source_universes/approved_v1/`, `docs/source_universe_guardrail.md`, `docs/incidents/2026-10-21_source_universe_scope_control.md`, `src/edp_lab/ingestion/universe.py`, `docs/cohort_publication.md`. These are authoritative for existing snapshots; this proposal must not rewrite them.

## 1. One Acquisition-to-Universe workflow; two separate authorities

**Default path:** `Search / Discover → Download (when absent) → Verify local RAW → Upload to Databricks RAW Staging (when absent) → Verify remote RAW → Qualify / Compare → Owner review → Publish approved Universe version`.

This is one simple reusable **operational path** for either new Universe Creation (0→1) or Universe Expansion (1→2). It is **not one undifferentiated permission**:

1. **Acquisition/staging authority:** an independently approved, bounded standing acquisition policy/grant permits search, download and retention, and permits guarded upload **only into an isolated RAW-candidate namespace**. It binds allowed publishers/data classes, source endpoints where applicable, acquisition scope/count/bytes, storage destination, credentials, retries and resource budget. It gives **no approved-universe membership, cohort admission, CLEAN, QUERYABLE or semantic permission**. Human review need not approve each mechanical candidate acquisition if within this standing authority.
2. **Universe membership authority:** after staged RAW and provenance are independently verified, the owner reviews exact candidates and approves **all/some/none** for a new versioned Universe manifest. Selection does not move or re-upload RAW. A rejected/deferred candidate remains retained and unapproved **when lawful and under approved retention policy**.
3. A subsequent **cohort workflow grant** permits selected approved-universe members to be admitted, processed and frozen. Approval of source acquisition or Universe membership alone is insufficient.

| Step | Creation: no approved universe (0→1) | Expansion: approved Uv exists (1→2) | Evidence / exit |
| --- | --- | --- | --- |
| U0. Baseline + bounded acquisition permission | Establish permitted publishers/data types, original inventories if present, discovery limits and isolated RAW staging scope; no universe membership approved yet | Verify approved Uv manifest, holdouts and old source identity; use existing standing acquisition grant or request one for **new** search/download/staging scope | `ACQUISITION_SCOPE_VERIFIED` |
| U1. Search / discover | Agent searches approved online/source catalogs or enumerates pre-existing retained local RAW. Record publisher URI, version/delivery, format, license/retention constraints, candidate acquisition ID, origin and proposed source family | Discover new candidate instances, including retained out-of-universe RAW, while preserving Uv's frozen member list | `CANDIDATES_DISCOVERED` |
| U2. Acquire/download (if needed) | For candidate not already held with verified digest, use authorized downloader; preserve original bytes, exact source URL/metadata, delivery and SHA/size. Do not normalize, silently repair or fabricate an absent artifact | Same; check local inventory and previously acquired data before downloading to avoid duplicate acquisition | `LOCAL_RAW_VERIFIED` / `ALREADY_VERIFIED` |
| U3. Stage Databricks RAW (if needed) | Independently verify local SHA then use guarded upload to the **acquisition-only RAW staging namespace**; read back actual remote bytes/hash, path/object identifier and receipt. Nothing becomes a CLEAN/QUERYABLE source merely by uploading | If remote original is already verified and its receipt/hash matches the exact bytes, **reuse its reference**; otherwise upload once within grant. No copying/moving for Universe promotion | `RAW_STAGING_VERIFIED` / `UPLOAD_DEFERRED_WITH_REASON` |
| U4. Qualify provenance and identity | Inspect source provenance, licensing/access/retention, publisher authenticity evidence where available, family/schema fingerprints, exact delivery/version, duplicates and unknowns. Mark qualify/reject/hold independently from technical upload result | Apply same checks, plus Uv identity+hash and unchanged membership comparison; do not equate same filename, ticker or text with a same physical instance | `QUALIFICATION_RECORDED` |
| U5. Scope and holdouts | Propose eligible development scope and protected holdouts; exclude disallowed or unverified candidates | Preserve old approved holdouts (41 for current v1) unless a separate explicit owner decision changes their status | `SCOPE_AND_HOLDOUTS_RECONCILED` |
| U6. Build candidate review packet | Produce canonical potential universe roster, sorted candidate IDs, SHA, source/remote staging refs, provenance and qualification, proposed excludes/unknowns, complete counts and owner decisions needed | Produce proposed Uv+1 diff: additions vs unchanged members, changed/retired entries if specifically justified, and retained-but-unapproved candidates | `UNIVERSE_PROPOSAL_READY` |
| U7. Human selectively approve/deny/defer | Owner chooses exact approved members; reject/defer candidates without deleting already permitted retained RAW | Owner approves the exact prospective Uv+1 membership/diff. Outside-universe previously uploaded RAW stays outside until specifically approved | `UNIVERSE_OWNER_APPROVED` / `NEEDS_HUMAN_DECISION` |
| U8. Publish immutable Universe version | Exclusively publish approved manifest/digest and separate owner record. Approved members **reference verified staged/original RAW**; no second download/upload | Publish Uv+1 and parent hash; do not rewrite original Uv, holdout decisions, or historical cohorts | `UNIVERSE_VERSION_PUBLISHED` |
| U9. Negative authorization tests | Gate denies unapproved/denied/deferred or holdout sources, changed SHA, wrong remote path, mismatched grant, and untrusted approval; staged RAW alone gives zero processing authority | Additionally deny v1 rewrites, retroactive membership upgrades and changed identity assignments | `UNIVERSE_GATE_VALIDATED` |
| U10. Independent readback + handoff | Read back exact manifest/approval/member counts, stage reference hashes and gate outcome; hand off exact pinned eligible set to a *separate* cohort proposal | Read back unchanged Uv, exact v2 diff, retained rejected sources and new authority; offer approved candidates for later cohort selection | `UNIVERSE_LIFECYCLE_COMPLETE` |

**Skip, do not duplicate:** If exact RAW bytes with valid source identity, local SHA and Databricks readback receipt already exist, reuse the artifact/receipt and skip download/upload. A stored SHA without independent remote byte/readback proof is not equivalent to remote verification. Upload can be deferred for explicit legal, privacy, access, budget or storage reasons; the candidate remains incomplete for processing until required remote verification is later achieved.

**Disposition after selective owner review:**

- `APPROVED_UNIVERSE_MEMBER` — admitted to **Universe membership only**, with original verified RAW reference; later cohort eligibility still separate.
- `DENIED_FOR_UNIVERSE` / `DEFERRED` — not eligible for any new development cohort; permitted staged RAW is retained for audit/future review without new processing authority.
- `ACQUISITION_PROHIBITED` — do not download/upload or retain where licensing, privacy, policy or data-ownership rules prohibit it; this is not the ordinary “denied Universe” case.

The 2026-10-21 source-universe scope incident is the concrete precedent: 800 extra RAW objects were retained in local and Databricks storage while being logically excluded from the approved v1 experiment. **Physical possession and authority remain independent.**

## 2. Input and output contracts

**Candidate input (not authority):** candidate acquisition ID; publisher source URL/catalog and delivery/version; acquisition policy/grant; timestamp, retention/license and provenance; local original artifact path/SHA-256/size; Databricks RAW staging URI/object reference, remote readback SHA and upload receipt (or explicit not-staged reason); format/family; holdout classification; owner qualification/review outcome; link to any already registered physical instance. A source-instance ID allocated during later registration is not invented during acquisition. Filename, basename, CUSIP, ticker or equal text are **not** automatically a physical or enterprise identity.

**Versioned output (after approval):** immutable universe ID/version; exact ordered membership; lineage to inventories; source family and original path/hash; holdout list/policy; qualification outcomes and evidence; version parent (if expanding); approval record anchored outside the untrusted agent; manifest SHA; negative tests and independent readback receipt. Proposals and signed/owner-installed approvals are different artifacts.

**Approval boundaries:**

- Acquisition/staging grant: bounded permission to search/download/retain RAW and write only to isolated Databricks candidate RAW staging, before Universe review; no source eligibility or CLEAN/QUERYABLE grant.
- Universe approval: eligibility to *select* exact source instances in a future development cohort; it does not itself grant RAW upload, cohort admission, model change, Databricks processing write or Git merge.
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
7. Staged RAW must be inaccessible to routine authorized-cohort processing until universe + cohort + workflow checks independently pass; staging-only writes cannot target established CLEAN/QUERYABLE or frozen RAW namespaces.
8. One acquisition grant cannot grant source membership. Owner denial of membership must never silently trigger deletion, data processing or re-upload; storage/retention rights still govern whether the original may be held.
9. Simulated/non-live tests must never be reported as live source acquisition or as a published universe.

## 5. Fit with future orchestration

The Day 5 autonomous C1500→C2000 experiment consumes the **already approved Universe v1**, not a newly invented Universe v2. This document's U0–U10 is a specification for the initial Universe bootstrap and for the *separately owner-governed* future expansion. The executor must consume pinned approvals and verify them; it must not become its own source-estate authorizer.

**No code, admission, new universe, frozen cohort, approval or Databricks operation is performed by this document.**
