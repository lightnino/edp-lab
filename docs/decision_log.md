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

- The CSV starts **header-only**. This is intentional: no historical approval,
  timestamp, or rationale is reconstructed from a guess.
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
