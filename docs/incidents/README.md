# Incident and engineering-finding register

**One event/finding = one directory = one current disposition.** A hash index, a protected owner recovery packet, and a run closeout are **evidence**, not extra incidents. Update the current status in the original incident document after a corrective PR merges; retain time-stamped historical evidence and distinguish completed operation from outstanding prevention work.

| Date / ID | Canonical record | Current disposition | Distinction |
| --- | --- | --- | --- |
| 2026-10-21 / `EDP-INC-2026-10-21-001` | [Source Universe unauthorized scope expansion](2026-10-21-source-universe/incident.md) | **CLOSED** under owner-approved scope correction, PR #17 / closure review | One incident; [hash index](2026-10-21-source-universe/evidence_index.md) and [retained RAW references](2026-10-21-source-universe/retained_raw_references.md) are supporting artifacts |
| 2026-10-23 / `EDP-INC-2026-10-23-002` | [Repeated step-specific owner grant installation](2026-10-23-standing-authorization/finding.md) | **CLOSED FOR DAY 5 COHORT 0A** after protected standing-broker deployment and Day 5 execution (PR #59 / #64); other workloads require separate authority | **Architecture/autonomy finding**, not an unauthorized-write security event, not PR #63 |
| 2026-10-23 / `DAY5-C2000-SQL-ROSTER-20261023` | [Day 5 P11 SQL / Supervisor incident](2026-10-23-c2000-p11-sql/incident.md) | **Day 5 operation CLOSED** (PR #63 incident report + #64 closeout); **R7 CLOSED** via PR #65; **R4 and R8 OPEN** | Runtime incident; [protected recovery packet](2026-10-23-c2000-p11-sql/recovery_packet.md) preserves the earlier blocked checkpoint |

Cross-references: [Day 5 accepted execution report](../../reports/day5/c2000_live_closeout_20261024.md), [Agent Operating Contract](../workflows/agent_operating_contract_v1.md), [Protected Operating Guide](../operating/agent_operating_guide_v1.md).

**Closure rule:** Do not label the entire protected recovery/monitoring platform reliable because one uncertain SQL operation was recovered. Preserve the independent R4 watchdog/diagnostic and R8 real-response test obligations. Separately, the Vault Day 6 0A installation is not covered by Day 5's Cohort 0A resolution.
