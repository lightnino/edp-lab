# Documentation ownership and navigation

**Purpose:** Discover the **one owning, versioned source** of prospective requirements. Do not treat historical project notes, incident evidence, proposals or example commands as automatically current/binding rules. The root-level `AGENTS.md` is the stable entry point for autonomous agents.

| Content | Authoritative home | Change/approval rule |
| --- | --- | --- |
| Lifecycle ownership, sequence, branch selection, acceptance stage | [Workflows](workflows/README.md) | Amend the owning reviewed Workflow; preserve published historical versions |
| Cross-lifecycle authority, recovery classifications and escalation | [Agent Operating Contract V1](workflows/agent_operating_contract_v1.md) | Reviewed Contract change **plus** protected policy/runtime implementation where necessary |
| General safe operation, observability and recovery procedure | [Operating Guide V1](operating/agent_operating_guide_v1.md) | Reviewed Guide change; descriptive text alone cannot grant authority |
| Generalized broker, DAG and Databricks adapter implementation guidance | [Operating](operating/README.md) | Versioned technical implementation documentation; verify *deployed* code/identity separately |
| Domain source identity, parsing, model, consumer semantics and typed-tool interfaces | [Contracts registry](contracts/README.md) | Preserve byte-for-byte approved/pinned contracts; new semantic scope needs reviewed successor |
| Actual events, failures, postmortems and tracked corrections | [Incident register](incidents/README.md) | Update the **same** event's current status and tracked actions; do not add status-only incident duplicates |
| Runs, Day-specific evaluations, closeouts and measured outcomes | [Reports](../reports/) and `metadata/evaluations/` | Historical evidence is not an execution instruction or prospective policy |
| Signed source authorizations, freezes, immutable artifacts and versioned results | `metadata/authorizations/`, `metadata/freezes/`, and signed protected receipts | Review exact pinned bytes and real installed trust; never relocate/alter signed evidence as housekeeping |
| Candidate ERD, Agent V1/V2 assessments, experiments and preregistered test findings | [Experiments](experiments/README.md) and their pinned legacy evidence | Research evidence only until separately approved and promoted into a domain contract |

## Document lifecycle

- **Proposed** = design for review; not approved and not installed.
- **Approved contract/specification** = a specific, versioned scope; its cited evidence and SHA/path pin must remain consistent.
- **Implemented** = code exists; not proof a protected service is installed/healthy or an external write completed.
- **Deployed / live accepted** = independently observed authority, remote effects, exact receipts and required validation.
- **Superseded** = no longer a live rule; preserve links and prior versions in Git/immutable evidence without circulating a second canonical entry point.
- **Incident resolved** = the documented operation/root cause is disposed with evidence; separately tracked preventative items may stay OPEN. Update the original record *in place*, link the corrective PR, keep historical chronology intact.

**Relocation safety:** Never move or edit an approved SHA-pinned semantic contract, a file referenced by an installed standing policy, or signed freeze/authorization metadata merely to improve folder layout. Migrate via a reviewed versioned successor with updated consumers and negative tests. In particular the byte- and path-pinned [Vault Load Contract V1](vault_load_contract_v1.md) remains at its original canonical path, even though the [contracts registry](contracts/README.md) lists it. A directory index is not an alternative rule copy.

**Legacy root-level Markdown:** Some source-specific and historical `docs/day*`, `docs/c*`, `docs/n*`, `docs/gold*`, and parser experiment records predate this taxonomy. They are **not** a current lifecycle or standing authority merely by living in `docs/`. Their actual source/pins and inbound references must be audited before moving them. New prospective general rules must not be added at the docs root; create the appropriate owner directory and register them here.
