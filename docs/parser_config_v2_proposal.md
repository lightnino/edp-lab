# Parser configuration V2 proposal — not approved or active

Historical proposal retained. Human Review subsequently approved D1/D3 and the
D4 design, while D2/D5 remain provisional. An **inactive** candidate now exists
at `metadata/parser_fidelity_v2_candidate.json`; the implementation and remaining
activation gates are recorded in
[parser_fidelity_validation.md](parser_fidelity_validation.md). The alternatives
below remain historical proposals, not authority to activate quote decoding.

This proposal is separate from frozen `profiling_conventions_v1.json` and
`parsing_profiling_contract_v1.md`. It does not create an executable binding,
change a parser, or authorize transformations. Evidence and approval questions
D1–D5 are in [parser_evidence_review.md](parser_evidence_review.md).

Three shared dialects are structurally sufficient for the present hashes.
There is no demonstrated table-specific delimiter or encoding exception.
Keep the V1 assignments untouched. If decisions below change effective parsing,
create new immutable `SEC_13F_TSV_V2`, `SEC_FSDS_TSV_V2`, and/or
`NASDAQ_PIPE_V2` profiles with only affected bindings updated in a **new**
configuration file after approval. Preserve V1 and all historical evidence.

| Proposed option | Effective policy | Evidence / consequence | Approval |
| --- | --- | --- | --- |
| Literal preservation | Inherit UTF-8, TAB/pipe, header, quote=null, escape=null, ALL_TEXT, null_tokens=[], no date casts, no JSON | Preserves serialized values; does not claim source NULL or decoded quote semantics | D1–D3 |
| CSV-style quote decoding | quote=`"`, doubled-quote handling explicitly specified; backslash stays literal | Changes values in INFOTABLE/num/tag/pre; wrappers/doubled quotes suggest this option but source intent remains unconfirmed. Requires new option schema and implementation; do not overload `escape` ambiguously | D2, after dialect evidence |
| Narrower table-specific quote profiles | Separate versioned INFOTABLE, NUM, TAG, PRE bindings if evidence proves their exporter rules differ from family defaults | Presence versus absence of quotes alone does not prove different dialects. Avoid splitting solely because one table has quoted examples | D2 |
| Exact schema expectations | Add expected ordered header lists per logical table, retaining family dialect reuse | Detects unique-but-changed headers without renaming them; all seven 13F headers match bundled metadata | D3/D4 |
| Explicit BOM and record handling | Reject BOM/blank records; retain LF/CRLF handling without altering fields; fail on decoding and width errors | Present files have no BOM/blank lines; adverse-input tests required | D4 |
| Strict Nasdaq metadata grammar | Exactly one last footer with raw prefix and MMDDYYYYHH:MM-shaped text; seven pipes for nasdaqlisted, six for otherlisted; empty remaining fields; separately retained locator/bytes | Existing prefix-only probe permits malformed content. Width 7 in otherlisted is observed metadata, not a data-row defect. A broader grammar needs evidence | D4/D5 |
| Per-column missing rules | Only after explicit serialized-token evidence and approval; otherwise keep text and mark semantics unresolved | FSDS prose and 13F nullability do not establish a universal empty→NULL mapping; NA/NAN occur as symbol text | D1 |

Before implementation, record answers, approved scope/hashes, effective options,
profile IDs, and approval reference. Compare literal versus chosen quote behavior
by exact source line/column without overwriting RAW. Exercise malformed encoding,
BOM, empty/duplicate/drifted headers, blank and wrong-width records, absent/duplicate/
malformed footers, and post-footer data. Confirm leading zeros, padding, decimal
scale and date spelling survive. A V2 parser may not silently fall back to V1
or another dialect on failure. Profile status remains PROVISIONAL until explicit
review and successful applicable checks; no production profiler is proposed.
