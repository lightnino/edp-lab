# Shared operating implementations and procedures

Only cross-lifecycle or reusable execution mechanisms belong in this folder. No Day-specific run result, incident record or owner recovery evidence belongs here.

| Canonical document | Scope / authority |
| --- | --- |
| [Agent Operating Guide V1](agent_operating_guide_v1.md) | Shared routine execution, liveness observation, diagnosis, protected recovery; **procedural, not an authorization** |
| [Standing Policy V1](standing_policy_v1.md) | 0A/P5 broker/grant mechanics; actual installed signed policy and protected service override illustrative instructions |
| [Databricks Adapter Integration V1](databricks_adapter_integration_v1.md) | General guarded Jobs/SQL adapter interface and readback safety; earlier milestone claims are historical |
| [Cohort DAG Pilot Implementation V1](cohort_dag_pilot_implementation_v1.md) | General DAG compilation/stage evidence boundaries; not automatically full current runtime coverage |

**Authority owner:** [Agent Operating Contract V1](../workflows/agent_operating_contract_v1.md). Lifecycle ordering and independent acceptance are owned by [Workflow Specifications](../workflows/README.md).

Historical execution data, including the accepted C2000 [Day 5 closeout](../../reports/day5/c2000_live_closeout_20261024.md), is stored outside this directory. The Day 5 P11 incident/recovery packet lives in the [Incident Register](../incidents/README.md). No document here can install credentials or a signature on behalf of the owner.
