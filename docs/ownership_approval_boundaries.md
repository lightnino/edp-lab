# Ownership and approval boundaries

Status: APPROVED governance policy. Explicit Human Review approval was confirmed
in the project conversation on 2026-10-20 for the five Finding states, Human/Agent
ownership boundaries, P0–P3 materiality, stopping rules, and Finding Schema v1.
The reviewer's formal identity and precise approval timestamp were not supplied.
This approval does not authorize any particular business rule, source interpretation,
semantic mapping, data transformation, or new source admission.

Authority remains with [AGENTS.md](../AGENTS.md), the
[evaluation contract](evaluation_contract.md), [source identity contract](source_instance_identity.md),
and frozen [V1](parsing_profiling_contract_v1.md) and
[V2](parsing_profiling_freeze_v2.md) parsing/profiling contracts. Nothing here
changes RAW, cohorts, source identities, historical decisions or those contracts.

## Findings and independent vocabularies

A Finding is an evidence-backed claim or question within a declared scope.

| Finding State | Meaning |
| --- | --- |
| OBSERVED | Evidence recorded; claim not yet checked |
| PROPOSED | Interpretation or action posed for review, with alternatives and consequences |
| VALIDATED | The claim passed its stated validation method within its stated scope only |
| REJECTED | Evidence refutes the claim within the stated scope; retain rationale |
| UNRESOLVED | Evidence or authority is insufficient; record the question, missing evidence and next review trigger |

These are not a compulsory linear workflow. Preserve earlier evidence and state
history in versioned artifacts; renewed evidence may reopen a claim. Validation
must describe population, columns/locators, input hashes, method, code/config/run
references and limitations as applicable. A sample validates only the sample.
REJECTED requires contrary validation evidence with its scope and method, just
as VALIDATED requires supporting validation evidence. Without sufficient contrary
evidence, leave the finding PROPOSED or UNRESOLVED.

| Independent dimension | Existing vocabulary / authority |
| --- | --- |
| Decision Log Status | PROPOSED, APPROVED, REJECTED, UNRESOLVED, SUPERSEDED; [Decision Log](decision_log.md) |
| Source Admission Status | ADMITTED in the existing corpus manifest; unchanged source-identity/admission contracts govern admission |
| Record Admission Outcomes | ACCEPTED, REJECTED, QUARANTINED; evaluation L1 |
| Statistic Computation Modes | EXACT_FULL_SCAN, EXACT_SAMPLE, APPROXIMATE, NOT_COMPUTED; frozen parsing/profiling contract |

No vocabulary is renamed or extended by the Finding states. Parser profile
PROVISIONAL/RAW_VERIFIED, onboarding outcomes and evaluation test statuses also
remain unchanged. Shared words such as REJECTED do not imply a cross-dimension
transition. VALIDATED is never a synonym for APPROVED, ADMITTED or ACCEPTED.
NOT_COMPUTED is a metric mode, not a Finding state; a finding explaining why a
metric is unavailable may remain UNRESOLVED.

## Ownership and authority

The agent or mechanical executor owns reproducible observation, evidence,
limitations and faithful execution. The authorized human reviewer owns semantic
interpretation and consequential approval. No new person or role assignment is
inferred; reviewer identity/authority must be supplied at review.

| Subject | Executor may establish | Human approval boundary |
| --- | --- | --- |
| Mechanical observations | Hashes, headers, widths, occurrence counts, literal equality and scoped check results | No per-observation approval; changed inputs or rules require review |
| Grain | Source-record locators and measured cardinalities | Meaning of a business observation and integration grain |
| Candidate keys | Uniqueness/NULL/FD measurements under declared equality and population | Candidate interpretation, Business Key selection and scope; uniqueness alone is insufficient |
| Dates and units | Preserve spelling; report documented declarations and lexical patterns | Date role, alignment, timezone, units, scale and conversion interpretation |
| Duplicate explanations | Equal-looking occurrences and their multiplicity | Whether occurrences represent one event; deduplication/merge rules |
| Source equivalence | Byte equality and delivery evidence | Semantic equivalence; equal hashes/names/tickers do not establish it |
| Canonical mappings | Inventory source fields and references | Entity resolution, canonical identifiers, merge/split and mapping rules |
| Transformations | Reproduce an already approved exact rule within scope | Any new/nontrivial transformation, reconciliation tolerance or semantic change |
| Record exclusion | Account for all occurrences; execute an approved invalidity rule | New exclusion/rejection rules; uncertain records remain withheld, never silently dropped |

Semantic proposals are questions with input evidence, alternatives and
consequences; do not infer actual keys or mappings to populate proposals.
Every SEMANTIC finding in PROPOSED state requiring HUMAN_REVIEW must include
explicit alternatives and consequences sufficient for a human decision. Ordinary
MECHANICAL findings do not require these fields.
An executor may VALIDATE faithful execution of a human-approved semantic rule;
that does not independently validate its real-world meaning.

Deterministic execution needs no fresh approval per record or mechanical
finding when an existing approval explicitly covers the rule version, exact
source snapshots/population, configuration, purpose, permitted outputs and
limitations. Verify hashes before ingesting, and member hashes before parsing.
Record the applicable authority and actual execution provenance. An existing
Decision Log reference is evidence to inspect, never an executable permission
token. Check status, scope, actual human authorization and supersession before
execution. Historical approvals outside the log remain valid references; do not
fabricate retrospective entries. DEC-000001–DEC-000005 authorize only the frozen
lexical scope described in V2; future snapshots do not inherit it.

Use only the existing append-only [decision log](../metadata/decision_log.csv)
for consequential decisions. Append actual proposals/unresolved decisions or
authorized approvals when they occur, per its contract. Do not log every
mechanical observation. Do not invent approvers or approval timestamps, revise
historical rows, or treat a test pass, Finding, commit or schema validation as
approval. The policy approval is recorded at the top of this document; it grants no approval to individual findings.

## Materiality and stopping rules

Materiality describes impact, not authority. Low materiality never bypasses a
semantic approval gate. Classify by evidence and affected scope; if impact is
unknown, record uncertainty and hold dependent work until bounded.

| Level | Impact and required stop |
| --- | --- |
| P0 | RAW/hash/cohort/history integrity breach or lost accountability: immediately stop affected ingestion and dependent outputs; preserve evidence, notify human reviewer; no fallback |
| P1 | Identity, grain, units/dates, exclusion, material semantics or unexplained regression can affect correctness: stop dependent integration/promotion pending human review |
| P2 | Bounded quality or interpretation question without established critical impact: preserve evidence, mark unresolved, hold dependent interpretation; independent approved mechanical work may continue |
| P3 | Incidental metadata/documentation with preservation and accounting satisfied and no demonstrated semantic dependency: record limits and stop investigation; no promotion blocker solely for unanswered incidental meaning |

Stop at any unapproved mapping, key, equivalence, merge, nontrivial
transformation or exclusion regardless of priority. Present evidence, alternatives,
consequences and affected scope for review. Structural parser failures stop the
affected parse under FAIL_CLOSED, even for apparently incidental content.

For footers, preserve exact bytes/locators, separately account metadata versus
data occurrences and retain the scoped rule/provenance. Once these controls pass,
do not investigate timestamp meaning, timezone or exporter intent indefinitely.
Existing frozen footer handling stands. Reopen only for a concrete new mismatch,
failed accounting, new source/version or demonstrated downstream semantic need;
this requires scoped review rather than automatic engineering. An incidental
meaning question can remain UNRESOLVED/P3 without blocking independent work.

## Minimal machine-readable contract

[finding_schema_v1.json](../metadata/finding_schema_v1.json) is an offline JSON
Schema Draft 2020-12 contract, version 1.0.0. It defines findings, not an approval
store or workflow engine. Required fields include stable finding ID, claim,
owner, source references, evidence references, type, state, validation scope and
method, materiality and approval requirement. Optional decision_ref points to an
existing DEC identifier; resolving its authority is a separate review obligation.
Governance-only findings may have an empty source_refs array but still need
versioned documentary evidence. Data findings require at least one immutable
source reference: physical instance/path/hash and precise member/table/record/field
locator as applicable. Evidence references carry a version or content hash and
locator; references must resolve to retained artifacts before validation is accepted.

MECHANICAL findings may specify approval_requirement NONE; SEMANTIC findings
always specify HUMAN_REVIEW, including when VALIDATED. UNRESOLVED requires a
reason and next review trigger, not a guessed answer or deadline-driven approval.
VALIDATED and REJECTED require validation.evidence_refs; for REJECTED these
identify the contrary evidence assessed by validation.scope and validation.method.
SEMANTIC/PROPOSED/HUMAN_REVIEW requires alternatives (at least two nonblank
options) and consequences (a nonblank explanation of the consequences of each
option). Human review assesses their sufficiency; schema validity checks only
their structure. No APPROVED Finding state or embedded
decision status exists. Unknown fields are rejected to prevent accidental approval
flags. Schema validity cannot prove evidence truth, link resolution, human authority
or permission to run; the targeted tests check structure and guards only.

Breaking changes need a separately reviewed schema version; retain prior records
and interpretation. No finding registry, runtime transition engine or approval
database is introduced. The governance policy and Finding Schema v1 have been
accepted through explicit Human Review; this does not approve any individual
Finding or grant a new runtime authority. Existing unresolved source NULL,
exporter intent and date/unit semantics remain unchanged and unapproved.
