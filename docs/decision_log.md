# Decision Log Contract (Day 2 Preflight §1.1)

`metadata/decision_log.csv` is the append-only index of consequential decisions made
during EDP source onboarding, data-model evolution, and agent review. It is **not** a
source inventory, a source-instance identity registry, or a replacement for evidence
in `docs/evaluation_contract.md`.

## Columns

- `decision_id`: Stable unique identifier, e.g. `DEC-000001`; never reuse.
- `recorded_at_utc`: Actual recorded UTC timestamp in ISO-8601 format (ending in `Z`).
- `decision_scope`: Affected source, cohort, mapping, model, tool, or governance scope.
- `decision_type`: Category such as `SOURCE_ADMISSION`, `IDENTITY`, `GRAIN`,
  `MAPPING`, `MODEL_CHANGE`, `EVALUATION` or `POLICY`.
- `status`: `PROPOSED`, `APPROVED`, `REJECTED`, `UNRESOLVED` or `SUPERSEDED`.
- `question`: Exact issue or ambiguity being decided.
- `decision`: Proposed or accepted outcome; may be empty if unresolved.
- `rationale`: Why the outcome is justified, or why it is still uncertain.
- `evidence_refs`: References to versioned source documentation, tests, decisions,
  review notes, commits or tool-run artifacts. Separate multiple refs with `;`.
- `source_instance_ids`: Applicable `SRC######` IDs (separated with `;`), if any.
- `model_version`: Applicable model version, if any.
- `approved_by`: Actual authorized reviewer identity/reference, only when a decision
  was approved. Leave empty for proposals, unresolved items, and unknown approvals.

## Rules

- The CSV was initially header-only. It now contains DEC-000001–DEC-000005
  for the approved parsing freeze; no historical approval, timestamp or rationale
  may be reconstructed from a guess.
- Record real decisions **when they occur**, with their supporting evidence.
  An Agent's proposal must not be silently recorded as an approved business decision.
- Keep entries append-only. Corrections/supersessions are new records that reference
  the earlier decision; do not erase accepted historical evidence.
- `status=APPROVED` requires actual authorization; a successful parser/test or
  an accepted Git commit alone does not establish business-semantic approval.
- Follow the frozen evaluation contract and approval boundaries in `AGENTS.md`.
  This log cannot authorize modifying GOLD_V1/GOLD_V2 membership, rewriting RAW
  bytes, or changing the twelve-column corpus-manifest schema.
- Frozen historical decisions already documented in `docs/gold_set_baseline.md`,
  `docs/gold_set_v2_admission.md`, and `docs/source_instance_identity.md`
  remain valid references; do not fabricate retrospective log entries.

## Use

At each consequential new identity, mapping, grain, reconciliation, model, or
governance decision, append a row referencing the actual evidence and approval state.
The log is designed to support later Agent run review, replay, and audit.

## Frozen engineering evidence index

This index links existing decisions; it adds no retrospective CSV approval rows.
Source Identity and GOLD_V2 are accepted as approved by the current task instruction.
Their historical approver identities and approval instants are not reconstructed.

| Scope / existing decision | Retained evidence |
| --- | --- |
| Physical-delivery identity; member lineage; distinct controlled variants; stable IDs and immutable paths | [Source Identity](source_instance_identity.md); `metadata/corpus_manifest.csv`; `metadata/gold_set_logical_tables_v2.csv`; `tests/corpus_invariants/test_source_identity.py` |
| Preserve GOLD_V1; expand via a separate GOLD_V2 with four physical instances / 13 tables | [GOLD_V2 admission](gold_set_v2_admission.md); [original baseline](gold_set_baseline.md); `metadata/cohorts/GOLD_V1.csv`; `metadata/cohorts/GOLD_V2.csv`; `tests/corpus_invariants/test_gold_v2_registration.py` |
| D1–D5 snapshot lexical scope | DEC-000001–DEC-000005 in `metadata/decision_log.csv`; [V2 freeze](parsing_profiling_freeze_v2.md); exact code/config/member hashes in `metadata/parsing_profiling_freeze_v2.json` |
| Finding states, ownership and stopping rules | [approved governance policy](ownership_approval_boundaries.md); `metadata/finding_schema_v1.json`; `tests/governance/test_finding_contract.py` |

Tests demonstrate their declared mechanical invariants, not human approval.
Whether this documentary index satisfies the frozen study plan's exact Decision
Log evidence requirement remains pending access to that text. If it explicitly
requires new records, Human Review must decide whether linked historical evidence
suffices or authorize present-day records with actual recording time and known
approval provenance. Do not backdate them.
