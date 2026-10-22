# Enterprise ERD candidate — Day 4

Every dotted edge is a **proposed or unresolved** relationship. No canonical table, production join, business key or cardinality is approved. Evidence and alternatives: [candidate ERD](../docs/agent_v2_candidate_erd.md) and [entity model](../docs/entity_model.md).

```mermaid
flowchart LR
  MANAGER -. "reporter role / cardinality?" .-> FILING
  FILING -. "source holding occurrences" .-> HOLDING
  FILING -. "reported period role?" .-> REPORTING_PERIOD
  HOLDING -. "security reference?" .-> SECURITY
  SECURITY -. "issuer relation?" .-> ISSUER
  SECURITY -. "listing relation?" .-> LISTING
  IDENTIFIER -. "namespace/time assignment?" .-> MANAGER
  IDENTIFIER -. "namespace/time assignment?" .-> ISSUER
  IDENTIFIER -. "namespace/time assignment?" .-> SECURITY
  IDENTIFIER -. "namespace/time assignment?" .-> LISTING
```
