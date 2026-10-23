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

### Shared operations and mode selection

**Shared operation chain:** `Discover → Acquire → Verify → Qualify → Owner Review → Publish → Validate`.

- `U0` establishes authority and prerequisites before this chain; `U1–U10` below specify its **full operational granularity** (including separate local/remote RAW verification, proposal, negative tests and final readback).
- **Choose exactly one execution mode at run start:** `CREATE` if no approved Universe exists; `EXPAND` if an approved Universe exists. The two columns below are **alternative implementations of the same stage contract, not two parallel jobs**. They may take different actions, have different comparison scope and skip already-verified mechanical transfers. An `EXPAND` invocation must never implicitly recreate the old Universe.
- Each stage has one required outcome/evidence boundary. Mode selection changes *what is examined and approved*, not the safety requirements. No `U0–U10` stage, source acquisition/remote verification action, or selective-approval disposition is removed.

| Dimension | CREATE — initial Universe (0→1) | EXPAND — existing Universe to new version (1→2) |
| --- | --- | --- |
| Existing Universe | None; may have retained RAW/inventories, but no approved membership | Required: verify exact approved Uv manifest, owner approval, hash and holdouts before discovery |
| Candidate scope | Initial proposed source population | Only new/proposed changed source instances; unchanged Uv membership inherited by reference |
| Acquisition and staging | Search/download/Databricks RAW staging as needed within the acquisition grant | Acquire only missing/new bytes as needed; independently reuse already-verified staged/original RAW, **never re-upload solely because membership changes** |
| Qualification and review | Qualify entire proposed population; owner selectively approves each eligible member or defined subset | Qualify proposed changes, compare Uv+1 against pinned Uv and review delta + impact; owner selectively approves/denies/defers |
| Preservation | Establish first immutable approved membership, RAW references, holdouts and controls | Preserve all historical Uv bytes/approval/cohorts; changes are a prospective new version, never retroactive reassignment |
| Output | First approved Universe version (e.g., U1) and independent readback | New approved version Uv+1 linked to pinned Uv with versioned exact diff and independent readback |

### Stage-by-stage execution — shared stage IDs, mode-specific rules

| Step | Creation: no approved universe (0→1) | Expansion: approved Uv exists (1→2) | Evidence / exit |
| --- | --- | --- | --- |
| U0. Baseline + bounded acquisition permission | Establish permitted publishers/data types, original inventories if present, discovery limits and isolated RAW staging scope; no universe membership approved yet | Verify approved Uv manifest, holdouts and old source identity; use existing standing acquisition grant or request one for **new** search/download/staging scope | `ACQUISITION_SCOPE_VERIFIED` |
| U1. Search / discover | Agent searches approved online/source catalogs or enumerates pre-existing retained local RAW. Record publisher URI, version/delivery, format, license/retention constraints, candidate acquisition ID, origin and proposed source family | Discover new candidate instances, including retained out-of-universe RAW, while preserving Uv's frozen member list | `CANDIDATES_DISCOVERED` |
| U2. Acquire/download (if needed) | For candidate not already held with verified digest, use authorized downloader; preserve original bytes, exact source URL/metadata, delivery and SHA/size. Do not normalize, silently repair or fabricate an absent artifact | Same; check local inventory and previously acquired data before downloading to avoid duplicate acquisition | `LOCAL_RAW_VERIFIED` / `ALREADY_VERIFIED` |
| U3. Stage Databricks RAW (if needed) | Independently verify local SHA then use guarded upload to the **acquisition-only RAW staging namespace**; read back actual remote bytes/hash, path/object identifier and receipt. Nothing becomes a CLEAN/QUERYABLE source merely by uploading | If remote original is already verified and its receipt/hash matches the exact bytes, **reuse its reference**; otherwise upload once within grant. No copying/moving for Universe promotion | `RAW_STAGING_VERIFIED` / `UPLOAD_DEFERRED_WITH_REASON` |
| U4. Qualify provenance and identity | Inspect source provenance, licensing/access/retention, publisher authenticity evidence where available, family/schema fingerprints, exact delivery/version, duplicates and unknowns. Mark qualify/reject/hold independently from technical upload result | Apply same checks, plus Uv identity+hash and unchanged membership comparison; do not equate same filename, ticker or text with a same physical instance | `QUALIFICATION_RECORDED` |
| U5. Scope and holdouts | Propose eligible development scope and protected holdouts; exclude disallowed or unverified candidates | Preserve all holdouts in the pinned prior approved Universe unless a separate explicit owner decision changes their status | `SCOPE_AND_HOLDOUTS_RECONCILED` |
| U6. Build candidate review packet | Produce canonical potential universe roster, sorted candidate IDs, SHA, source/remote staging refs, provenance and qualification, proposed excludes/unknowns, complete counts and owner decisions needed | Produce proposed Uv+1 diff: additions vs unchanged members, changed/retired entries if specifically justified, and retained-but-unapproved candidates | `UNIVERSE_PROPOSAL_READY` |
| U7. Human selectively approve/deny/defer | Owner chooses exact approved members; reject/defer candidates without deleting already permitted retained RAW | Owner approves the exact prospective Uv+1 membership/diff. Outside-universe previously uploaded RAW stays outside until specifically approved | `UNIVERSE_OWNER_APPROVED` / `NEEDS_HUMAN_DECISION` |
| U8. Publish immutable Universe version | Exclusively publish approved manifest/digest and separate owner record. Approved members **reference verified staged/original RAW**; no second download/upload | Publish Uv+1 and parent hash; do not rewrite original Uv, holdout decisions, or historical cohorts | `UNIVERSE_VERSION_PUBLISHED` |
| U9. Negative authorization tests | Gate denies unapproved/denied/deferred or holdout sources, changed SHA, wrong remote path, mismatched grant, and untrusted approval; staged RAW alone gives zero processing authority | Additionally deny prior-version rewrites, retroactive membership upgrades and changed identity assignments | `UNIVERSE_GATE_VALIDATED` |
| U10. Independent readback + handoff | Read back exact manifest/approval/member counts, stage reference hashes and gate outcome; hand off exact pinned eligible set to a *separate* cohort proposal | Read back unchanged Uv, exact Uv+1 diff, retained rejected/deferred sources and new authority; offer approved candidates for later cohort selection | `UNIVERSE_LIFECYCLE_COMPLETE` |

**Skip, do not duplicate:** If exact RAW bytes with valid source identity, local SHA and Databricks readback receipt already exist, reuse the artifact/receipt and skip download/upload. A stored SHA without independent remote byte/readback proof is not equivalent to remote verification. Upload can be deferred for explicit legal, privacy, access, budget or storage reasons; the candidate remains incomplete for processing until required remote verification is later achieved.

**Disposition after selective owner review:**

- `APPROVED_UNIVERSE_MEMBER` — admitted to **Universe membership only**, with original verified RAW reference; later cohort eligibility still separate.
- `DENIED_FOR_UNIVERSE` / `DEFERRED` — not eligible for any new development cohort; permitted staged RAW is retained for audit/future review without new processing authority.
- `ACQUISITION_PROHIBITED` — do not download/upload or retain where licensing, privacy, policy or data-ownership rules prohibit it; this is not the ordinary “denied Universe” case.

**Physical possession and authority remain independent.** Historical examples and their actual counts belong in the approved manifests and incident evidence, not in the reusable step contract.

## 2. Input and output contracts

**Candidate input (not authority):** candidate acquisition ID; publisher source URL/catalog and delivery/version; acquisition policy/grant; timestamp, retention/license and provenance; local original artifact path/SHA-256/size; Databricks RAW staging URI/object reference, remote readback SHA and upload receipt (or explicit not-staged reason); format/family; holdout classification; owner qualification/review outcome; link to any already registered physical instance. A source-instance ID allocated during later registration is not invented during acquisition. Filename, basename, CUSIP, ticker or equal text are **not** automatically a physical or enterprise identity.

**Versioned output (after approval):** immutable universe ID/version; exact ordered membership; lineage to inventories; source family and original path/hash; holdout list/policy; qualification outcomes and evidence; version parent (if expanding); approval record anchored outside the untrusted agent; manifest SHA; negative tests and independent readback receipt. Proposals and signed/owner-installed approvals are different artifacts.

**Approval boundaries:**

- Acquisition/staging grant: bounded permission to search/download/retain RAW and write only to isolated Databricks candidate RAW staging, before Universe review; no source eligibility or CLEAN/QUERYABLE grant.
- Universe approval: eligibility to *select* exact source instances in a future development cohort; it does not itself grant RAW upload, cohort admission, model change, Databricks processing write or Git merge.
- Cohort approval: selection/admission of a disjoint finite subset under that universe; no implicit new parser/business model.
- Bounded workflow grant: exact subsequent operations, source hashes, contract versions, output namespaces, runtime/retry budgets, and protected write authority.
- New publisher, identity equivalence, holdout release, newly inferred economic interpretation or out-of-universe acquisition is a fresh governance decision, not self-granted by the agent.

## 3. Hard negative tests / non-negotiable behavior

1. Wrong/changed RAW SHA, missing or ambiguous physical identity, source/manifest mismatch → refuse enrollment, retain evidence.
2. Any holdout or unapproved source → fail the universe gate before admission, even if physical RAW exists in Databricks.
3. Agent-edited approval text, untrusted “approved” marker, or unsigned altered manifest → no authority.
4. Universe membership ≠ successful source qualification ≠ cohort admission ≠ RAW availability ≠ processed/verified QUERYABLE.
5. An expanded universe must not modify historical manifests/cohorts, delete earlier evidence, or silently redefine source identities.
6. Unresolved provenance/identity → `UNRESOLVED` with exact question/evidence; unaffected candidate evaluation may continue.
7. Staged RAW must be inaccessible to routine authorized-cohort processing until universe + cohort + workflow checks independently pass; staging-only writes cannot target established CLEAN/QUERYABLE or frozen RAW namespaces.
8. One acquisition grant cannot grant source membership. Owner denial of membership must never silently trigger deletion, data processing or re-upload; storage/retention rights still govern whether the original may be held.
9. Simulated/non-live tests must never be reported as live source acquisition or as a published universe.

## 4. Interface with the Cohort/Model Lifecycle

**Output:** a versioned, owner-approved and independently verified Universe manifest, with exact source membership, physical RAW identity/hash/provenance, staged-original byte references (where allowed), holdout policy, approval evidence and the comparison-to-parent manifest for `EXPAND`.

**Handoff:** the Cohort/Model Lifecycle consumes that approved Universe and independently selects/adopts a bounded development cohort. A source that was searched, downloaded or uploaded to candidate Databricks RAW staging is **not** eligible for cohort admission until its exact identity is approved in the Universe and subsequently admitted under a separate cohort/workflow authorization.

- The acquisition agent may autonomously discover, download, upload, verify and qualify candidates **within its existing bounded acquisition authority**. Those activities do not alter Universe membership.
- The owner alone (or their designated independent authority) approves `CREATE` membership or an `EXPAND` delta, plus source-estate/holdout policy exceptions. The agent may prepare the decision packet but **cannot authorize itself**.
- Neither `CREATE` nor `EXPAND` triggers CLEAN/QUERYABLE materialization, a new model, cohort/result freeze or Git merge. Those are downstream separately authorized operations.
- Retained but denied/deferred RAW is not erased merely because Universe membership was refused, subject to legal/licensing/retention rules; it remains inaccessible to ordinary admitted-cohort processing.
- The downstream executor verifies the exact signed/owner-pinned Universe version, RAW identity/hashes and separate cohort/workflow grant. It **reuses verified RAW receipts**, without a second acquisition or upload simply for Universe admission.

**Historical evidence (non-normative):** see [approved Universe v1](../../metadata/source_universes/approved_v1/README.md) and the [source-universe boundary incident](../incidents/2026-10-21_source_universe_scope_control.md) for actual prior member/holdout/out-of-scope counts. The current historical source estate is an *example*, not an embedded limit in this future reusable workflow.

**No code, admission, new universe, frozen cohort, approval or Databricks operation is performed by this specification.**
