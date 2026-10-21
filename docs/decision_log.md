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

## C300 M1 execution

DEC-000006 records explicit user authority for lexical M1 and gated QUERYABLE
publication. See [authority](day2_c300_m1_authority.md). Supplemental NUM quote
boundary rules remain proposed in [triage](c300_num_exception_triage_v1.md).

DEC-000007 is a PROPOSED supplemental NUM quote-boundary rule supported by bounded
witness evidence. It is not an approval; all twelve affected bindings remain
BLOCKED pending an actual human decision and subsequent strict validation.

DEC-000008 records the user’s explicit approval of DEC-000007; see [supplemental authority](c300_num_recovery_authority_v1.md). Original proposal history remains intact.

DEC-000009 records explicit user approval of FIN_EVAL_V1 as a scoped read-only
evaluation overlay; see `metadata/evaluations/fin_eval_v1.json`. M1 and the
historical lexical Lossless results remain unchanged. Final freeze is withheld.

The final closeout instruction now authorizes a selected local Day 2 commit. This
supersedes only earlier no-commit instructions; final freeze still requires verified
retention and explicit owner approval. No new semantic decision is recorded.

## SRC010128 source-specific encoding approval (Day 3 / N450)

DEC-000010 records the owner's explicit selection of Option B over
Option A (quarantine). The [source-specific encoding decision](src010128_encoding_exception.md)
contains the full A/B alternatives, advantages/costs, decision criteria,
why B was chosen, supporting byte/name evidence, explicit limits, and the
conditions that send the record back to quarantine. This is a reversible,
source-and-field-specific ISO-8859-1 interpretation for the single reported
`0xC3` byte in `SRC010128` Company Name, not a global encoding rule.

**APPROVED is interpretation authority, not implementation success.**
Preserve the initial HUMAN_UNRESOLVED finding and immutable RAW.
The 450/450 FITS_EXISTING_MODEL outcome is conditional on actual bounded
validation; it is not a strict UTF-8 PASS. No source-universe or cohort
admission, M1 change, blanket file encoding, entity/CIK equivalence, or
reprocessing of 449 unchanged sources is implied.
