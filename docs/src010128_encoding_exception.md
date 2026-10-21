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

## Human decision — why B rather than Quarantine

- **A / quarantine:** technically safe and remains a valid fallback if scoped validation fails, but withholds an entire otherwise potentially usable record due to one field's encoding question.
- **B / targeted encoding exception — APPROVED:** permits the exact affected field's original bytes to be decoded as ISO-8859-1, subject to source/hash/locator identity checks, reversible round-trip and independent parser/verifier/lossless tests.
- Rationale: exact reported byte-level anomaly, reversible field interpretation and two independent historic names make the limited interpretation supportable. This is an owner decision about the interpretation **only**; executable acceptance remains gated.
- No alteration of the original RAW, exclusion of records, global Latin-1 default, model/semantic promotion, or modifications to the 449 other sources.

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
