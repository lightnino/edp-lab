# Day 7 — C3000 incremental execution binding (proposed)

**Scope:** Day-specific invocation of the existing [Universe U0–U10](workflows/universe_lifecycle_v1.md), [Cohort/Model 0A, P0–P14](workflows/cohort_model_lifecycle_v1.md), [Validation/Stability/Freeze](workflows/validation_freeze_lifecycle_v1.md), [Operating Contract](workflows/agent_operating_contract_v1.md) and [Guide](operating/agent_operating_guide_v1.md). **Not a new lifecycle, policy authority, executable, deployment receipt or live C3000 completion.**

**Objective:** Expand the authorized source estate, freeze `C3000 = C2000 ∪ N1000`, process **only N1000 plus proven affected dependencies**, run A/B2/C + Lossless, assess Agent V5 and freeze the actual C3000 result. Preserve and reuse accepted old CLEAN/QUERYABLE/RAW, model contracts and validated evidence. A historical C2000 freeze is immutable; a pending Day 6 Vault integration is an independent downstream input only if genuinely completed and verified.

## Owner's Day 7 membership decision

The owner explicitly approves **all 800 retained, independently identified and remotely hash-verified source instances from the 2026-10-21 source-universe incident** for prospective membership in an expanded Universe. This is a **new** Universe-v2 membership decision: no historical manifest/freeze or past incident is rewritten, and no RAW reupload follows merely from membership approval. The intended population is original approved v1 (`3,021`) plus the exact retained `800` (`3,821`), with the same protected `41` holdouts. Previously frozen source-preserving outputs remain frozen.

Evidence anchors to verify before publication:
- `metadata/source_universes/approved_v1/manifest.json` (SHA-256 `2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c`) and its separate owner authorization.
- Original incident `docs/incidents/2026-10-21-source-universe/incident.md`; its 800-reference ledger SHA-256 `13cdaf7a7be3f9c2a966b84769b459ea3eaa186e26f8f70257fbe999ffeadeae` recorded in the v1 manifest. The original 800 reference list is an **external/local provenance artifact**, not the blank placeholder path in this Git tree; do not reconstruct a fictitious list from aggregate counts.
- Each approved source must independently resolve unique physical identity, original RAW digest and bytes, actual retained Databricks locator, verified remote readback and existing acquisition/reference evidence. Record exact 800/800 matches, no overlaps with original 3,021 or holdouts, unchanged original v1; publish an immutable v2 membership manifest and verified handoff only when all exact members are grounded. The user's membership approval is **not** proof that publication or 800/800 current readback has happened.

**Known baseline discrepancy to reconcile mechanically, without reprocessing:** The 2026-10-21 incident records frozen C2000 as original-v1 `1,200` plus outside-v1 `800`; the owner's current verbal description treats C2000 as entirely within original `3,021`. Compare the exact accepted `metadata/freezes/C2000_v1/freeze.json` membership against original-v1 and incident-800 IDs/hashes. Do not silently choose either story or change C2000. Regardless of source mix, if disjointness is verified, `3,821 − 41 − 2,000 = 1,780` available; select 1,000 only from the **actual** 1,780 IDs.

## End-to-end orchestration map (one autonomous run, existing stage ownership)

| Day 7 intent | Existing canonical stage and exact responsibility | Evidence/output |
| --- | --- | --- |
| 0. Historical baseline | Cohort P0; fixed C2000 live freeze, M1/M2/contracts, source/hash/QUERYABLE, prior tests and conditional completed Vault baseline | `C2000_BASELINE_VERIFIED` |
| 1. Universe v2 delta | Universe EXPAND U0–U10; reuse candidate inventory and RAW; this owner's prospective membership approval is U7 input; publish only exact verified delta via U8–U10; no mandatory acquisition | `UNIVERSE_SCOPE_RESOLVED`, manifest/readback |
| 2. N1000 selection | P1 exact eligible disjoint candidates and RAW handoff; P5 automatic policy decision; P6 freeze the roster `C3000=C2000∪N1000` | `C3000_COHORT_PASS` |
| 3. Model fit/evolution | P2 profiling, P3 B1 router; conditional P4 exact contracts and minimal impact plan (PARSER_EXCEPTION, ADDITIVE, CORRECTIVE, UNRESOLVED as needed) | `MODEL_EVOLUTION_APPROVED_OR_UNCHANGED` |
| 4. Incremental Delta | P7 conditional smoke; P8 true native Spark/Delta N1000-only CLEAN + candidate QUERYABLE with historical pinned UNION ALL; if necessary approved, dependency-scoped replay, not blind history replacement | `INCREMENTAL_LOAD_VALIDATED` |
| 5. Lossless / Stability | P9 calls shared Lossless 1–6 registry; P10 calls A(old C2000)/B2(new N1000)/C(combined C3000) with C1/C2/C3 and source/economic applicability; regression never inferred from A+B2 alone | `STABILITY_A_B2_C_EVALUATED` |
| 6. Agent V5 evidence | P11 conditional failure diagnosis/recovery and P12 operating trace; Day 7 benchmark report measures autonomy/impact targeting from **actual observations**, not a new universal mandatory processing stage | `AGENT_V5_EVALUATED` / `NOT_TRIGGERED` where appropriate |
| 7. Live exit | P12 metric evidence → P13 independently verified Databricks live C3000 result freeze → P14 Git checks/PR/merge/readback | `DAY7_COMPLETE` / accurately scoped PARTIAL |
| 8. Workflow improvement | **After exit only**, audit real incidents and propose amendments to their **owning existing spec/contract/guide**. No new lifecycle or duplicate acceptance clauses. | `WORKFLOW_REVIEWED` |

## Runner/executor reuse contract — minimal integration, not another stack

Use `src/edp_lab/operating/runner.py` and existing DAG/broker/Databricks adapter, with **one Day 7 parameter binding**, not a copied P0–P14 engine. The binding supplies:
- Immutable `approved_universe_v2_sha256`, `c2000_input_freeze_sha256`, exact `n1000_roster_sha256`, `c3000_roster_sha256`, source-level RAW handoff identity/path/sha/bytes/receipt, holdout exclusion and branch-specific M1/M2/rules/negative-control pins.
- `previous_result` UC table/version and source identities from accepted C2000; outputs to new exclusive C3000/N1000 targets, with no old result replacement and no Cohort RAW writes.
- Policy-bound operation/resource/retry/time limits and durable per-operation checkpoints; resume by completed stage/partition and independently reconcile remote writes before retry. Materialize N1000 CLEAN exactly once per source/operation or reconcile existing outcomes; historical C2000 is referenced, not copied.
- P3/P4 emits exact model-classification and minimal dependency impact manifest. In addition to cohort/family source IDs it describes temporal fields (event/valid/ingest), old/new rule versions, affected vs unaffected partitions, action `NO_REPLAY | QUERY_ONLY | FROZEN_CLEAN_PROJECTION | TARGETED_CLEAN | TARGETED_RAW`, expected deltas, prior live pins, test registry and human semantic decision when required.
- P8 executes native Delta append/versioned views by default. Allow `MERGE` only for explicitly supported stable merge key, history/effective-time semantics and duplicate-safe idempotency; it is **not** automatically required for every new immutable source. P9/P10 independent controls and the P13 protected verifier determine accepted results.
- Agent V5 report uses the existing P2/P3/P4/P11/P12 trace: drift/collision/late-arrival cases actually observed, diagnosis accuracy against verified evidence, scope precision, tests/replay executed, unnecessary old recomputation, intervention/human minutes, remote write recovery and unresolved causes. Mark `NOT_OBSERVED` when no real model-evolution incident occurred; do not fake a benchmark.
- Do not assume the docs alone install protected RAW handoff/adapters; the open Acquisition-only RAW-writer/handoff integration issue must be checked against the **actual** deployed runner. Reuse independently verified Databricks RAW and skip duplicate uploads.

## One-time Day 7 protected deployment / acceptance prep

Prepare **one install action**, rather than repeated Owner approvals: use existing personal Databricks workspace and supported persistent noninteractive credentials for the actual background actor, verify workspace/UC effective rights, rebind the standing policy to **published Universe v2** (not v1), allowed `N1000` increment/C3000 outputs and pinned contracts, install minimal changed runner/executor only if necessary, and prove one full protected Job + readback path before executing the real increment. Where macOS root is actually required, present one exact Owner terminal command; do not infer that text approvals bypass the OS password. Do **not** reuse Day 6's four-family Vault service as a general C3000 Cohort executor without verified operation/target permissions.

After installation, the Agent runs the mapped existing stages continuously, diagnosing and resuming within already installed authority. No further ordinary technical or per-Job Owner decisions; only genuinely **new** business meaning/model correction, changing held-out Universe membership, unsupported access/budget, unresolved external effects or required Git merge review cause exception. The owner can pre-approve one explicitly scoped final PR merge after actual acceptance if desired.

## Stage exit / no-false-completion conditions

`DAY7_COMPLETE` requires published v2 and verified 800 identity/source handoff, exact verified N1000/C3000 disjoint freeze, native live N1000 CLEAN/combined QUERYABLE, applicable actual A/B2/C and Lossless results, true controlled replay or truthful NOT_REQUIRED, reproducible Agent V5 diagnostics evidence, verified P13 Delta freeze, P14 merged remote SHA and closeout. An unmaterialized intent, test-only PASS, incomplete source list or pending Day 6 Vault baseline must never be presented as a successful live C3000/Vault result.
