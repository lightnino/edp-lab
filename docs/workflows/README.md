# Workflow specifications — authoritative navigation

This directory owns **lifecycle behavior and acceptance-stage sequencing**. The [shared Operating Contract](agent_operating_contract_v1.md) owns execution authority, recovery classification, service observability and escalation; the [shared Operating Guide](../operating/agent_operating_guide_v1.md) owns generic procedures. A published Markdown file is **not** an owner-installed signing policy or proof of live Databricks execution.

| Workflow / contract | Owner of | Recorded document status |
| --- | --- | --- |
| [Universe Lifecycle V1](universe_lifecycle_v1.md) | Acquisition, verified RAW handoff, Universe CREATE/EXPAND, U7 owner approval | **Proposed for owner review** as marked in its specification. Existing approved Universe membership is independently governed by signed manifests. |
| [Cohort + Model Lifecycle V1](cohort_model_lifecycle_v1.md) | P0–P14, model route, RAW-read-only processing, conditional P11 | **Binding Day 5 standing-authorization specification**; not itself deployed credentials |
| [Validation/Stability/Freeze V1](validation_freeze_lifecycle_v1.md) | Exact Lossless, Stability, budget, P13 live result freeze and P14 evidence criteria | **Proposed for owner review**, as marked in its specification; prior scoped approved controls remain binding on their own terms |
| [Agent Operating Contract V1](agent_operating_contract_v1.md) | Cross-lifecycle authority, liveness and the five-class recovery decision matrix | **Owner reviewed and merged in PR #65**; runtime implementation/deployment is separately evidenced |

**Canonical delegation:** Lifecycle owns *what/when*; Operating Contract owns *who may act*; [Operating Guide](../operating/agent_operating_guide_v1.md) explains *how*; protected runtime enforces; Validation owns independently checked PASS/BLOCKED; domain contracts specify source/business semantics.

**Conflict rule:** a proposed extension cannot silently override installed standing policy, frozen historical approval, protected write boundary or source-specific signed scope. Seek an explicit, versioned owner decision on the conflicting authority. Historical PR descriptions, early milestone labels and Day-specific examples are evidence, not updated runtime specifications.

See [Documentation Registry](../README.md), [Incident Register](../incidents/README.md), and [Domain/Tool Contract Registry](../contracts/README.md).
