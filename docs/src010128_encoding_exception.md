# SRC010128 — owner-approved source-specific encoding interpretation

**Decision:** APPROVED — Option B (Human-approved, narrowly scoped, reversible source-encoding exception).  
**Implementation status:** NOT IMPLEMENTED / NOT VALIDATED by this decision record.  
**Owner approval:** Explicit user selection of Option B in the project conversation, 2026-10-22 (Asia/Singapore). Approval's precise clock time and formal reviewer identity were not supplied; do not invent either.  
**Decision Log:** DEC-000010, `metadata/decision_log.csv`.  
**Scope limitation:** This is a human interpretation decision, **not** evidence of successful N450 recovery, B1 eligibility, source-universe admission, a new model version, or strict UTF-8 parsing.

## Diagnosis — preserve original evidence

Owner-supplied terminal/RAW diagnosis (must be independently rechecked by the implementing executor against the pinned original bytes):

- Source instance: `SRC010128`
- RAW SHA-256: `5869c2d2e76ec56302291d7812add9d8cc1a0b9788478050344e40d14927e71d`
- Physical line: `6215`
- Field: `Company Name`
- Original exceptional byte: `0xC3` (reported absolute offset `516344`; verify offset indexing and byte-to-field alignment before implementation)
- Reported original value, using an ASCII/escaped-byte notation: `EXPLORA INVESTIMENTOS GEST\xC3O DE RECURSOS LTDA`
- Expected approved field interpretation: `EXPLORA INVESTIMENTOS GESTÃO DE RECURSOS LTDA`

The field-local ISO-8859-1 (Latin-1) interpretation decodes the reported single byte `0xC3` as `Ã`, producing `GESTÃO`. This is **not** a blanket assertion that the entire SEC file is Latin-1; it is **not** an independent verification of the row's CIK.

### Independent name corroboration (separate from byte evidence)

1. Brazilian CVM, *Ata da Reunião do Colegiado Nº 06 de 09.02.2010*: states “Explora Investimentos Gestão de Recursos Ltda.” in proceeding RJ2010/0230. https://conteudo.cvm.gov.br/decisoes/2010/20100209_R2.html
2. ANBIMA, *Relatório Anual 2011*, page 40: lists “Explora Investimentos Gestão de Recursos Ltda.” https://www.anbima.com.br/relatorioanual/2011/files/assets/basic-html/page40.html

These two historical documents corroborate the Portuguese company-name spelling. They **do not** independently establish the source file's overall encoding, the exact physical line, byte offset, row hash, or CIK. The owner-provided byte facts above require actual RAW/source validation. Do not infer canonical entity linkage from textual name matching.

## Human decision — Option A vs Option B (owner review)

**Question:** The reported SEC source snapshot `SRC010128` has a non-UTF-8 byte in the Company Name field at physical line 6215. Should that record remain excluded from normally validated CLEAN output pending investigation, or should we approve a tightly bounded alternative interpretation of the original field bytes?

The initial `HUMAN_UNRESOLVED` diagnosis is retained. The alternatives below describe decision policy, **not** an already-executed parser or an observed post-remediation test result.

### Option A — Quarantine affected record (not selected; valid fallback)

- Preserve the complete original RAW file, exact source/line/field evidence and the failed UTF-8 diagnostic.
- Put the affected record in a quarantine/unresolved path: do **not** silently replace characters, discard original bytes, or count that record as accepted CLEAN.
- The remaining records can remain assessable under existing rules, but this source cannot be represented as **fully recovered** on the strength of a partial parse. The reported pre-decision N450 assessment was **449 complete + 1 partial**, subject to verification against local test artifacts.
- **Advantages:** conservative fail-closed behavior; no exceptional decoding code or verifier policy is needed; prevents potentially wrong business text entering CLEAN.
- **Costs:** defers recovery of a record for which a specific candidate spelling is supported; leaves a source-level completion gap and manual case unresolved. Quarantine is **not** RAW deletion and does **not** imply all 8,530 records were discarded.
- **When preferable:** if byte/line/hash identity cannot be reproduced, independent corroboration conflicts, reversible decoding fails, or parser/verifier/Lossless validation fails.

### Option B — Human-approved source-specific encoding exception (SELECTED)

- Approve interpretation of the **original bytes of the single Company Name field** of the exact pinned record/source snapshot using ISO-8859-1 (Latin-1); interpret original `0xC3` as `Ã`, yielding `EXPLORA INVESTIMENTOS GESTÃO DE RECURSOS LTDA`.
- Require a versioned, exact-match parser profile **and** equivalent CLEAN verifier behavior, with original field bytes, row/source locator, decoding method and provenance retained for byte-for-byte reconstruction.
- **Advantages:** can recover the record without rewriting RAW, dropping data, changing M1, or changing policy for the other 449 sources. Captures the human interpretation, evidence and mechanical proof separately.
- **Costs/risks:** an exception adds implementation/test burden and can misinterpret data if mistakenly applied to a different field or snapshot; name matches are not identity/CIK proof.
- **Scope:** only `SRC010128`, pinned RAW SHA-256, physical line 6215, Company Name field and verified exceptional byte locator. This is **not** a file-wide Latin-1 declaration or a general SEC encoding policy.
- **Acceptance:** candidate decoding is *authorized* now, but the affected record/source becomes accepted only after source identity, reversibility, full 8,530-record accounting, parser/verifier and applicable Lossless checks pass.

### Explicit comparison and decision criteria

| Criterion | A — Quarantine | B — Scoped exception |
| --- | --- | --- |
| RAW immutability and forensic bytes | Preserve; diagnosis remains | Preserve; original field bytes and provenance remain reconstructable |
| Affected record in ordinary CLEAN | Withheld while unresolved | Eligible **only after** new validation |
| Result for N450 | Cannot assert 450 fully recovered; prior reported 449 complete / 1 partial remains to be checked | **Potential** 450/450 under versioned profiles, never strict UTF-8; not yet demonstrated |
| Changes required | Quarantine handling and evidence tracking | Exact-match parser-profile and matching CLEAN verifier changes plus tests |
| Risk | Incomplete source, deferred resolution | Wrong decode or accidental exception spillover; fail-closed tests required |
| Effect on Core Model M1 | None | None |
| Other 449 sources | Unchanged | Unchanged; bounded regression evidence required |
| Auditability | Preserves unresolved byte and quarantine reason | Preserves original failure **plus** owner decision, competing option, evidence, reversible rule and validation result |

### Why the owner selected B over A

1. **Specific, reproducible hypothesis rather than a guess at the file encoding.** Owner-supplied original field witness contains one reported exceptional `0xC3`; ISO-8859-1 deterministically maps that byte to `Ã` in the candidate name. The supplied RAW SHA-256, position and row evidence must still be reproduced by Codex against actual bytes.
2. **Independent corroboration at the correct level.** CVM's 2010 meeting record and ANBIMA's 2011 annual report show the same Portuguese organization-name spelling. They corroborate **the proposed field value only**; neither proves full-file Latin-1, exact SEC-row lineage or CIK identity.
3. **Smaller semantic and data-integrity cost.** A is safe but leaves an otherwise potentially recoverable record out of accepted CLEAN. B can retain all original bytes and process the field without losing a record, **if** correctness checks pass.
4. **Blast radius can be bounded and independently tested.** Exact source/hash/line/field predicates and explicit parser-profile versioning prevent the exception becoming a permissive global fallback. Matching verifier reconstruction and regression checks supply mechanical evidence independently of the human judgment.
5. **No M2 justification.** This is a physical source decoding interpretation, not a new business identity, grain, canonical fact or model-schema change. It does not change M1 or authorize entity/CIK linkage.

**Decision:** APPROVE **Option B**, narrowly scoped and reversible, **instead of** Option A quarantine. The choice approves an interpretation and a validation path, **not** automatic acceptance or an upgrade to 450/450. Option A remains the fail-closed handling if any prerequisite fails. A third possibility—globally decoding SEC/this whole file as Latin-1—is **not approved**.

### Required fail-closed and reconsideration triggers

- Mismatch in pinned RAW SHA-256, physical line, field position, exceptional byte(s), or row/source locator.
- Decoded value cannot round-trip to *exactly* the original field bytes, or the verifier disagrees with parser output.
- Additional unexplained encoding anomalies, unapproved changes to other rows/fields, record-count discrepancies or applicable Lossless failures.
- Evidence that the interpreted name is incorrect, or indication that the exception would spill beyond this approved scope.

On a trigger: **do not promote to accepted CLEAN or 450/450**; retain the original failure, use quarantine/unresolved handling for the affected record as appropriate, and reopen Human Review. Do not edit the original decision in place to imply successful implementation.

### Decision authority vs. proof of execution

- **Owner-approved (now):** Option B field interpretation and permission to build an exact-match parser/verifier exception under the stated restrictions.
- **Not yet proven:** local RAW/row identity, byte round-trip, 8,530-record output, complete Lossless results, regression coverage and N450 eligibility.
- **Future mechanical evidence:** implementation commits, versioned parser profile, CLEAN verifier artifacts, test run identifiers and before/after N450 B1 assessment; link these to `DEC-000010` without rewriting the original `HUMAN_UNRESOLVED` finding.

## Resolution contract — for Codex implementation, not an execution claim

1. Preserve the original `HUMAN_UNRESOLVED` finding and immutable diagnostic evidence; link the new decision/resolution rather than overwrite history. Preserve original bytes, line/field locator, row fingerprint if present, source identity, lineage and initial parse failure.
2. Recheck the RAW SHA-256, precise line, column, byte sequence and absolute offset against the registered source; fail closed on any mismatch. Record/retrieve original field bytes.
3. Version an **exact-match** parser profile permitting ISO-8859-1 decoding only for this field of the pinned `SRC010128` source snapshot/record. All other bytes/fields/sources retain their existing approved behavior. Do not treat a text-replacement workaround as byte-preserving decoding.
4. Apply the same bounded interpretation to the CLEAN verifier; prove `decoded_value.encode("iso-8859-1") == original_field_bytes`. Retain the decoding provenance/version in the resulting lineage and verification evidence.
5. Validate full affected source population (owner reports 8,530 records), exact record accounting, applicable Lossless gates and expected field value. Any unreviewed invalid byte or other failure remains FAILED/QUARANTINED/UNRESOLVED as appropriate, not automatically accepted.
6. Regression-check the other 449 sources with bounded, evidence-based checks and unchanged prior authoritative snapshots; do not reprocess everything solely to satisfy a nominal number.
7. Only after all gates pass, update the separately versioned `docs/n450_b1_assessment.md` and associated results to accurately report conditional recovered eligibility. Never rewrite frozen historical 449/1 evidence and never say `450/450 strict UTF-8 PASS`.
8. Commit diagnosis → owner decision → implementation → tests → reassessment with precise artifact references; keep approved decision separate from mechanical validation evidence. Maintain existing source-universe/admission authority boundaries; this approval alone authorizes no new source admission, upload or cohort change.

### Conditional success language (NOT YET CLAIMED)

`N450: 450/450 FITS_EXISTING_MODEL under the approved parser-profile versions; 1 documented source-specific encoding exception.`

This statement may be used **only after** complete scoped test evidence supports it. Core Model M1 stays unchanged. If tests fail, retain the decision but report the actual failed/blocked outcome and reopen targeted Human Review.

## Relationship to Day 3 work

- Existing Day 3/Terminal 2 local state and unpushed commits are not established by the GitHub main-branch document review.
- Review/commit unrelated profiling work first; integrate this decision record into the actual N450 working branch without clobbering local modifications.
- Do not start Day 3 Step 3 on the assertion of 450/450 until the independently verified B1 gate is met.
