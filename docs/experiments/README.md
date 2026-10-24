# Experimental agent evaluations — not operating authority

These are preregistered questions, candidate schemas and point-in-time evaluation evidence, not live canonical business keys, approved source joins or operational rules.

| Artifact | Existing stable file | Meaning |
| --- | --- | --- |
| Agent V2 candidate ERD | [Candidate ERD](../agent_v2_candidate_erd.md) | **PROPOSED/UNRESOLVED** entity/key/relation hypotheses; cannot authorize production joins |
| Agent V2 ground truth | [Ground Truth V1](../agent_v2_ground_truth.md) | Fixed scoped development labels, not independent enterprise golden truth |
| Agent V2 evaluation | [Evaluation V1](../agent_v2_evaluation.md) | Limited historical benchmark, not proof of autonomous agent production semantics |
| Day 4 Agent V2 quality regression | [Quality regression](../day4_step10_agent_v2_quality_regression.md) | Historical measurement with pinned evidence, not generalized API or model rules |

Supporting immutable inputs/labels/evaluations remain in `metadata/evaluations/agent_v2/`. The tools behind [Profiling Tool Contract V1](../contracts/tools/profiling_tool_contract_v1.md) remain implemented and independently useful; do **not** call that interface obsolete just because a candidate Agent V2 experiment is historical.

The existing file paths are retained for now because the byte-pinned [Vault Load Contract V1](../vault_load_contract_v1.md) explicitly links to Agent V2 candidate/evaluation records. Moving them without a reviewed V1-contract successor would break those approved references. Do not create redundant canonical copies or pointer stubs.
