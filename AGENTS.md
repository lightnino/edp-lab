# EDP Lab — Agent Entry Point (Binding Routing Rules)

This file is a **stable entry point for autonomous agents**, not an incident diary, cohort status report, deployment approval or substitute for an installed policy. See the [Documentation Ownership Registry](docs/README.md) for canonical folder roles, incident disposition, contracts and historical-evidence classification. Read it first; follow the authoritative documents for the operation at hand. Never use the existence of a document as proof of live authorization.

## 1. Route each task to its owning specification

| Question / operation | Normative source | Responsibility |
| --- | --- | --- |
| Discover/acquire sources, RAW candidate staging, source eligibility, Universe approval/handoff | [Universe Lifecycle](docs/workflows/universe_lifecycle_v1.md) | Acquisition owns RAW writes; Universe owns membership/version decisions; neither alone authorizes cohort processing |
| Select a cohort, choose INITIAL_MODEL / CORPUS_ONLY / ADDITIVE / CORRECTIVE, run RAW-read → CLEAN → QUERYABLE, diagnose P11 | [Cohort & Model Lifecycle](docs/workflows/cohort_model_lifecycle_v1.md) | Processing stages/branching/checkpoint and strict RAW-read-only boundary |
| Lossless, Stability, economic meaning controls, resource limits, accepted result freeze and Git exit | [Validation, Stability, Budget & Freeze Specification](docs/workflows/validation_freeze_lifecycle_v1.md) | Exact applicable oracles, independent PASS/BLOCKED criteria and evidence |
| Shared execution authority, separation of duties, 0A/P5 enforcement, uncertain writes, liveness and recovery classification | [Agent Operating Contract V1](docs/workflows/agent_operating_contract_v1.md) | **Canonical cross-lifecycle rules**, including [Recovery Decision Matrix](docs/workflows/agent_operating_contract_v1.md#recovery-decision-matrix) |
| How to start, observe, diagnose, safely reconcile, escalate and resume | [Agent Operating Guide V1](docs/operating/agent_operating_guide_v1.md) | Generic protected recovery runbook; **does not grant authority** |
| Task-specific source identity, parsing, modeling, Vault/consumer semantics | [Canonical Domain/Tool Contracts Registry](docs/contracts/README.md), including approved [Vault Load Contract V1](docs/vault_load_contract_v1.md) | Narrower, SHA-/path-pinned scope and acceptance evidence; no unapproved semantic assumptions and no implicit execution approval |

When a new independent workflow is introduced, create or update its **own** reviewed specification and link it in this routing table. Put reusable cross-lifecycle requirements in the Operating Contract, operator steps in the Guide, and enforcement in protected runtime/tests. Do **not** append historical narratives or new scope-specific runbooks to this entry point.

**Document status matters.** A PROPOSED specification is not binding authority merely because it is linked here. Verify each document's actual review/approval state and all required installed-policy gates. If documents disagree about an operation, pause and request explicit owner clarification rather than choosing the more permissive rule.

## 2. Authority and safety invariants

- Operate only within the **currently owner-installed**, independently enforced standing policy, signed grant/receipt and exact approved source/model/rule/registry scope. An editable worktree, this AGENTS file, an unsigned manifest or green local tests cannot grant permissions.
- Agents may implement deterministic, reversible, scoped code, local tests and read-only analysis **within authorized task scope**. Do not make external writes, network/API calls or spend paid resources beyond explicitly permitted standing policy/task instructions. Protect credentials, keys and root-only ledgers in separately controlled environments.
- Acquisition alone may stage RAW using its specific protected identity; Cohort/Model can only verify/consume RAW. Preserve original bytes, immutable identity, hashes, provenance, lineage, previous frozen results and approved holdouts. Never silently deduplicate, overwrite, or restage originals.
- Do not infer enterprise business identity, canonical keys, issuer equivalence, missing-value meaning, mapping, tolerance, semantic reconciliation, or which amendment supersedes another without appropriate evidence and explicit semantic authority. Preserve unresolved interpretations and source-native data; mechanical correctness is not business approval.
- Independently verify remote effects and signed receipts before declaring an external operation or final freeze complete. Do not resubmit an uncertain non-idempotent write; follow the [Recovery Decision Matrix](docs/workflows/agent_operating_contract_v1.md#recovery-decision-matrix) and bound the resume to the original checkpoint.
- **Checkpoint status and Supervisor liveness are different facts.** Check trusted process/service heartbeat, latest verified progress and the applicable stall threshold before saying a run is active. A stale VALIDATING state cannot justify "still running." Missing monitoring is an operational gap to report, never permission to assume success or resubmit SQL.
- Retain human gates for consequential new semantics, Universe/policy scope changes, true integrity/budget exceptions outside installed limits and explicit PR review/merge. No agent can sign its own expansion.
- Never commit RAW source bytes, secret material, private ledgers, local databases or unapproved result dumps. Record evidence by stable references and hashes.

## 3. Standard agent lifecycle

1. **Discover the owner of the task.** Choose the owning Lifecycle/specification and its applicable version, domain contract and acceptance tests; do not combine independent lifecycles unless authorized.
2. **Establish reality.** Inspect latest verified `main`, current signed approval/policy/grant and actual protected-runtime availability, source/remote evidence, previously accepted freeze and current checkpoint. Do **not** substitute historical narrative or planned work for current observed state.
3. **Bind and execute.** Stay within approved identities, operations, budget and time bounds. Prefer reusable mechanisms, targeted tests, existing artifacts and unchanged snapshots over bespoke rework or repeated whole-corpus scans.
4. **Monitor and recover.** Track service liveness **and** progress; distinguish long legitimate work, hard stalls, nontransient failures and uncertain remote effects. Use the Contract decision matrix and protected Guide. Auto-repair only when the installed independent authority permits it; otherwise provide a single evidence-complete decision packet.
5. **Independently verify.** Run applicable registered controls and negative tests, verify remote readback and exact immutable output IDs/receipts. State PASS, FAIL, BLOCKED and UNRESOLVED precisely; never convert a local simulation, proposal or signed plan into a live PASS.
6. **Deliver with approval gates.** For Git writes, use a scoped branch, tests/lint, CI and reviewed PR; await explicit required human merge approval and verify final `main` SHA. Report durable outcomes, scope limitations, retries, failed states and measured human/compute costs; leave unknown figures null.

## 4. Where historical and current state belongs

- **Past approvals, source-specific exceptions, runs, incidents and exact freeze evidence:** the relevant `metadata/authorizations/`, `metadata/freezes/`, `metadata/evaluations/`, `reports/` and domain-specific records, with original hashes/refs.
- **Current runnable authority:** the actual protected installed policy, grants, revocations, trust material and readback receipts, independently verified. Repository descriptions do not supersede these.
- **Reusable rule changes:** reviewed owning Workflow or Operating Contract, with negative tests/enforcement as applicable.
- **Operational how-to changes:** shared Operating Guide; runtime changes require separate code/tests/deployment. No new historical status sections in `AGENTS.md`.

**EDP Lab engineering objective:** test a reusable Databricks RAW → CLEAN → QUERYABLE platform preserving Lossless and Stability invariants with measurable automation, throughput, cost, human intervention and correctness. The small-team operating model is a hypothesis to measure, not a license to relax evidence or safety gates. Prefer minimal general mechanisms over repeated source-specific bespoke patches.
