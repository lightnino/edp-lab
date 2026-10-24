# EDP Lab Incident-Level Finding — Repeated Owner-Grant Installation Blocks Bounded Autonomy

**Tracking ID:** EDP-INC-2026-10-23-002  
**Recorded:** 2026-10-23 (SGT; exact time not independently recorded)  
**State (updated 2026-10-24):** CLOSED FOR THE BOUNDED DAY 5 COHORT 0A USE CASE; general deployment coverage remains policy-/workflow-specific  
**Priority:** P1 for the EDP Lab Operational Scalability experiment  
**Classification:** authorization workflow / human-intervention overhead (**architecture finding**, not an unauthorized-execution or security breach)  
**Owner decision:** Record the problem during Day 4; complete the existing Step 8 trusted approval without changing active authorization enforcement; make the durable fix a Day 5 milestone.  
**Scope:** EDP Lab Agent A (bounded platform operations), separate from Agent V1–V3 semantic capability versions.

**Resolution evidence:** [Standing authorization PR #59](https://github.com/lightnino/edp-lab/pull/59) merged with protected broker/auto-grant support; the owner-installed protected Day 5 run was executed to [C2000 513/513, signed P13 and merged P14](https://github.com/lightnino/edp-lab/pull/64). This closes repeated step-specific code/SHA-pin installation for the approved Day 5 mechanical cohort run. It does **not** grant all future cohorts, arbitrary Acquisition RAW mutation, Day 6 Vault deployment or semantic/policy expansion. An owner-signed *uncertain-write integrity disposition* in [the separate P11 incident](../2026-10-23-c2000-p11-sql/incident.md) was required and is not a regression to repeated routine infrastructure signoffs. This report's original Day 4 observations and unmet-at-the-time release wording remain as dated history, not current state. No measured across-cohort autonomy benchmark is claimed.

## 1. Intended control versus observed workflow

The intended policy is already in [ownership and approval boundaries](../../ownership_approval_boundaries.md): an approved, pinned rule/source/configuration scope permits deterministic execution without repeated per-record human approvals; new consequential semantic or source-scope decisions need human review. The [authorized source universe incident](../2026-10-21-source-universe/incident.md) showed why independent source-scope enforcement is non-negotiable.

In implementation, Day 3 N450 processing used separately installed, host-pinned processing grants; Day 4 N750 admission/C1500 freeze used an admission-only owner grant; Day 4 Step 8 then encountered an additional processing gate. The *boundaries are valid*, but re-preparing a bespoke proposal, canonicalizing approval JSON, manually installing a new approved record, and changing a cohort/step-specific Python SHA pin adds an additional human-directed deployment step for each newly scoped workflow.

**This is not evidence that the gates should be removed or that an admission approval should silently imply processing authority.** The gap is that one human-approved bounded workflow cannot currently authorize its already-declared mechanical substeps via a reusable, independently enforced policy without repeated step-specific code/pin installation.

## 2. Evidence / chronology

| Stage | Observed evidence | Implication |
| --- | --- | --- |
| Day 2 C300 | [Frozen C300 approval](../../../metadata/freezes/O_C300_M1_v1/authorization.json) scoped the historical M1 closeout. | A prior C300 approval does not grant N750 processing. |
| Day 3 N450/C750 | [Actual execution report](../../n450_c750_execution_evidence.md) records separately pinned processing/publication authority and later approved runtime correction. | Processing required real owner authority; technical retry and scope control were both explicit. |
| Day 4 Step 1 | [N750 admission/freeze evidence](../../history/day4-c1500/n750_c1500_execution_evidence.md) and [installed N750 admission grant](../../../metadata/authorizations/n750_admission_v1.json) pin exactly 750 new sources and the C1500 membership freeze. | Admission/freeze authority is **not** processing authorization. |
| Day 4 Step 8 preflight | [C1500 freeze](../../../metadata/freezes/C1500_v1/freeze.json) states `processing_authorization: NOT_GRANTED`, `output_freeze: NOT_RESULT_FREEZE`. [Execution evidence](../../history/day4-c1500/n750_c1500_execution_evidence.md) reports 450 remotely VERIFIED and 300 UNVERIFIED. | The executor correctly failed closed at **0/750 processed**; no CLEAN/M1/M2/QUERYABLE outputs were created in that blocked attempt. |
| Step 8 follow-up | Local-only owner proposal at `runs/day4/n750-step8-worktree/proposals/n750-step8-v1/owner-record.proposed.json` was reported with proposed SHA-256 `0c0571e45de48ea96ebac0c6d6a28a2cf6c6ee5086558da23087014d07f05b36`; reported expected approved SHA-256 `5ae18d7d2ee770cbefb3f6ad0a6b05eac87282d8e88b2c9f6422dff7c9b7b120`. | Owner review and separate trusted installation required. These local-only artifacts and reported digests have **not** been independently verified in this GitHub record. Their appearance here is **not** approval or evidence of installation. |

The remote 300 are **UNVERIFIED**, not proven missing, corrupt, or out of universe. An authorized RAW upload or processing must still satisfy exact source identity and independent remote SHA checks.

## 3. Root cause / risks

- **Observed design friction:** hardcoded, cohort/step-specific trusted owner SHA pins and repeated manual installation, despite reusable high-level operation scopes being conceptually possible.
- **Security requirement retained:** a request or Agent-generated approval record can never activate its own grant; authenticated owner approval and independent trust validation remain necessary.
- **Operating-model risk:** agent requires human procedural steering for mechanically repeatable scope-contained phases; approval minutes/interruptions and blocked execution may grow with cohort count. There is no evidence yet of a measured personnel cost or a 2 PB scaling curve.
- **Incorrect shortcut to reject:** broad permanent allow-all, default processing inherited from admission, request-provided trusted pins, retroactive approvals, and silent relaxation of per-object SHA verification.

## 4. Immediate Day 4 disposition

1. Keep the existing separate, fail-closed Step 8 grant and trusted installation procedure; owner completes it outside Agent execution if approved.
2. Do **not** edit installed Step 1 admission authority, historical grants, source universe, frozen C1500 metadata, M1/M2 outputs or Agent V2 ground truth.
3. Resume processing only after approval is installed and each exact RAW object independently verified. Record `N750_PROCESSING_PARTIAL` until actual validated coverage reaches 750/750.
4. Do not represent this documentation commit as a processing grant, policy migration, source admission, or incident closure.

## 5. Day 5 required remediation

Day 5 must implement the minimum **policy-enforced, bounded authorization envelope**, reusing the existing UniverseGate/owner-approval/typed tool enforcement as far as practical:

- Human approves a **specific** immutable source/cohort/version scope, authorized operation set, permitted outputs/environment/principal and expiry or revocation policy **once per bounded workflow** (not once per internal processing phase).
- Trusted policy store/anchor is independent of Agent code and requests. New approved scopes or consequential business/model decisions still require fresh owner approval. Agent cannot approve itself.
- Agent may execute/retry/resume already-approved mechanical operations without another trusted Python SHA-pin edit. Enforce at the host/tool/Databricks permission boundary, not merely in a prompt.
- Every action logs decision (allow/deny), source/config/contract fingerprints, workflow ID, tool/result versions, checkpoint and human intervention; preserve old pinned grants as historical evidence.
- Provide positive, negative and revocation/scope-expansion tests, backward compatibility, and a minimal N500 pilot with independently validated results.

**Day 5 release gate:** `BOUNDED_AUTHORIZATION_POLICY_VALIDATED` before claiming Runtime Agent A L2 autonomy. If not implemented or independently tested, report `AUTONOMY_PILOT_BLOCKED` or `LEGACY_GRANT_ONLY`; do not relabel manual Codex execution as autonomous Runtime Agent operation.

## 6. Original Day 4 resolution criteria (subsequently met for the bounded Day 5 cohort case)

- One explicit trusted owner approval covers an N500-sized **bounded, versioned workflow**, not undefined future cohorts or model changes.
- Agent can run/resume at least two approved mechanical phases without a second manual code-pin installation.
- Out-of-scope source, unapproved model version, unauthorized write, revoked/expired authority, and forged approval all fail closed at the enforcement layer; remote hash mismatches block individual source processing.
- Reproducible audit trail separates approvals, mechanical execution, human decisions, rejected attempts and actual human minutes.
- Existing Day 2–4 grants and frozen data are unchanged; no implied historic authorization or success.

**Current disposition (2026-10-24):** BOUNDED_DAY5_COHORT_REMEDIATION_VERIFIED; tracking closed for repeated per-step owner grant/code-pin installation in that run. Protected 0A still requires per-workflow installed authority and independently signed exact scope. Do not generalize this result to other execution identities or the separately pending Day 6 Vault installation.
