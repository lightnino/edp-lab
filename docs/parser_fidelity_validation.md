# Parser fidelity validation — inactive V2 candidate

Human Review authorized implementation and local validation only. No configuration
was activated or promoted. The existing V1 execution path, frozen contracts, RAW,
identities, cohorts and Evaluation Contract remain unchanged. This extends the
uncommitted evidence work without repeating the initial investigation.

## Decisions and implementation

| Decision | Human approval | Implemented behavior | Evidence / boundary |
| --- | --- | --- | --- |
| D1 | APPROVED literal missing-value preservation | Empty strings and candidate tokens remain strings; lexical empty/whitespace-only counts and exact token counts are separate. `null_count` and `null_pct` both carry `NOT_COMPUTED` and an explicit unresolved-source-semantics reason. Empty `pre.plabel` is retained and flagged. | Existing evidence review and FSDS README §5.4; line 57071 is empty despite documented non-nullability. Lexical counts are not semantic NULL statistics. |
| D2 | PROVISIONAL quote/escape interpretation | Literal parser uses delimiter splitting only; no unquoting or backslash decoding. Separate evidence-only function compares the first quote-bearing field per table with hypothetical double-quote decoding. | Existing witnesses in INFOTABLE, num, tag, pre; comparison below. No decoded value enters validation or replaces RAW. |
| D3 | APPROVED exact ALL_TEXT preservation | Exact ordered headers and strings; leading zeros, spaces, signs, scale, case, date/timestamp text and duplicate occurrences survive. JSON options stay null. | Ordered schemas and member hashes copied from existing review appendix, not newly inferred. SEC metadata/README references remain in that review. |
| D4 | APPROVED DESIGN | Candidate validates exact table headers, rejects UTF-8 BOM, strict UTF-8 failures, empty physical records, width deviations, unsupported bare-CR terminators, and malformed/nonfinal/absent/duplicate Nasdaq footers. Retains footer bytes and locators. | Rules apply only to registered hashes. Headers/member hashes come from prior evidence; footer first-field text and six/seven trailing delimiters were observed locally. Synthetic failure tests exercise the approved design. |
| D5 | PROVISIONAL Nasdaq documentation | Encoding/quote/missing assumptions remain provisional. No external documentation fetched. | Successful validation only supports these snapshots, not a universal Nasdaq export dialect. |

## Candidate and execution boundary

`metadata/parser_fidelity_v2_candidate.json` is a standalone versioned file with
`activation_status=INACTIVE`, thirteen table specifications and three shared
`*_V2_CANDIDATE` dialect IDs. All profiles remain `PROVISIONAL`. It retains the
V1 dialect options and adds table-level ordered headers, parent/source/member
hashes and exact footer expectations. It is not loaded by the existing CLI,
`conventions` module, ingestion path or production profiler.

Run explicitly from the repository root:

```sh
uv run python -m edp_lab.profiling.parser_fidelity
uv run python -m edp_lab.profiling.parser_fidelity --json
```

The validator reuses the source identity/hash verifier, frozen binding validation,
and the evidence collector's read-only member reader and candidate-token vocabulary.
It rejects unsupported candidate options, profile changes, duplicate/missing bindings
and registry mismatches, verifies all four RAW hashes before member reads, then
verifies each uncompressed member hash before validating records. It never retries
another dialect. Unsupported input raises an error and the CLI exits nonzero.
The public orchestration function returns results only after all tables succeed.
Its low-level record iterator must be exhausted to validate trailing records.

New strict behavior relative to V1: exact ordered schemas, explicit BOM/blank-record
rejection, member-hash binding and footer-content/width validation. V1 checked
nonempty/unique headers, widths and footer prefix/placement but not exact schema
or footer content. Literal field interpretation remains unchanged. V2 recognizes
LF and CRLF, preserving original record bytes; bare CR is outside observed snapshot
formats and fails. An unterminated final record is accepted, without deleting any
bytes. A delimiter-only data row is retained as empty fields, not rejected as an
empty physical record. String whitespace is not stripped from accepted values.

The Nasdaq footer must have the exact snapshot first field
`File Creation Time: 1015202603:03`, followed by seven empty fields for
nasdaqlisted or six for otherlisted. Exact text matching enforces spelling
without converting timestamps or inferring timezone; even a differently dated
well-formed footer is outside these snapshot expectations. The width-seven
otherlisted footer is metadata, not a malformed width-eight data row.

Footer evidence includes complete original bytes as reversible hex (including
record terminators), one-based source line and zero-based byte offset; its
enclosing result carries source identity/path, member and parent/member hashes.
Accounting is `physical_records = HEADER + DATA + FOOTER`, with no silent skips.
Unrecognized same-width data cannot be judged semantically by width checks;
the registered snapshot hash gate prevents silently accepting changed input bytes.

The JSON output includes exact effective profile and table options, lexical
counts by column, exact candidate-token spellings/counts, evidence-only quote
comparisons, footer evidence, inconsistency flags and blocked semantic metrics.
Token matching uses case folding only to find lexical candidates; reported
spellings and parsed values remain exact. Nothing is converted into SQL NULL.
No production profiling functions, official baselines or new source instances
were created. Results are emitted to stdout, not written into RAW.

## Remaining Human Review before activation

Review the effective candidate JSON, `parser_fidelity.py`, synthetic tests and
the local outcomes below. Confirm the snapshot-only schemas, exact timestamp
expectations and seven/six-field footer tails. These implement approved D4;
they are not universal source-format declarations.

D2 remains open: should the serialized wrappers/doubled quotes be retained as
field text or interpreted using an evidenced exporter dialect? Only the literal
path is implemented. Any future unquoting or escape decoding needs explicit
approval, a new version and differential fidelity checks. Compare the four
witnesses below before deciding; no quoted output has been semantically approved.

D5 remains open: authoritative Nasdaq encoding, quote and missing-value
documentation is unavailable locally. Human Review must explicitly decide whether
snapshot-limited provisional evidence is acceptable for a future activation or
whether authoritative documentation is required first. No network collection
is authorized by this implementation request.

D1/D3 do not require reapproval for the implemented literal path. Source NULL
semantics remain unresolved, so semantic NULL metrics must stay NOT_COMPUTED
until separately evidenced and approved. Neither tests nor this report authorize
`RAW_VERIFIED`, V2 activation, a profiling baseline, or business semantics.

## Local validation results

All commands used `UV_OFFLINE=1` with the existing uv environment. The first
attempt at `uv run pytest -q` failed before tests because the sandbox denied
creation of a uv cache lock under `/Users/lightnino/.cache/uv`. It exited 2:
`Could not acquire lock` / `Could not create temporary file` /
`Operation not permitted (os error 1)`. The approved offline rerun passed.

| Command | Actual outcome |
| --- | --- |
| `uv run python -m edp_lab verify-raw` | Exit 0; `PASS source identity structure: 4 distinct instances; 13 registered logical tables`; `PASS RAW bytes and archive members: 4 instances` |
| `uv run python -m edp_lab.profiling.conventions --check-raw` | Exit 0; contract/13 bindings PASS; all 13 structural probes PASS, all profiles PROVISIONAL; production profiler NOT IMPLEMENTED |
| `uv run pytest -q` | Exit 0; `83 passed in 0.19s` (31 existing evidence/prior tests plus 52 candidate cases) |
| `uv run ruff check .` | Exit 0; `All checks passed!` |
| `uv run python -m edp_lab.profiling.parser_fidelity` | Exit 0; all 13 candidate validations PASS; `INACTIVE; profiles PROVISIONAL; semantic null_count/null_pct NOT_COMPUTED` |
| `git diff --check` | Exit 0; no output |

Additional whitespace checks covered the untracked files, which ordinary
`git diff --check` does not inspect. A verification helper initially treated
`git diff --no-index` exit 1 (files differ) as failure despite no whitespace
diagnostics; the corrected helper accepted that status and passed all eight
work files. Frozen V1 contracts, Evaluation Contract and both source registries
were also confirmed byte-identical to HEAD. No test or lint failures occurred.

The candidate's full `--json` evidence was also inspected locally. Results below
are a validation record, not a baseline. Source references and hashes are the
unchanged evidence-review registry and the candidate's exact snapshot references.

## Snapshot validation accounting

Every row below passed both the V1 structural probe and strict candidate validation.
There is one header per table; physical counts include header and footer.
Whitespace-only fields: zero in every local table. Semantic null_count/null_pct:
NOT_COMPUTED in every result, with the unresolved-source-semantics reason.

| Source / member | Data | Footer | Physical | Empty fields | Candidate-token fields |
| --- | ---: | ---: | ---: | ---: | ---: |
| SRC000001 / COVERPAGE.tsv | 166 | 0 | 167 | 1481 | 3 |
| SRC000001 / INFOTABLE.tsv | 87715 | 0 | 87716 | 181433 | 2167 |
| SRC000001 / OTHERMANAGER.tsv | 47 | 0 | 48 | 121 | 0 |
| SRC000001 / OTHERMANAGER2.tsv | 179 | 0 | 180 | 527 | 0 |
| SRC000001 / SIGNATURE.tsv | 166 | 0 | 167 | 0 | 0 |
| SRC000001 / SUBMISSION.tsv | 166 | 0 | 167 | 0 | 0 |
| SRC000001 / SUMMARYPAGE.tsv | 141 | 0 | 142 | 50 | 0 |
| SRC000002 / nasdaqlisted.txt | 5629 | 1 | 5631 | 0 | 1 |
| SRC000003 / otherlisted.txt | 7660 | 1 | 7662 | 0 | 3 |
| SRC000004 / sub.txt | 522 | 0 | 523 | 2026 | 3 |
| SRC000004 / num.txt | 136044 | 0 | 136045 | 376222 | 0 |
| SRC000004 / tag.txt | 8477 | 0 | 8478 | 1256 | 0 |
| SRC000004 / pre.txt | 57596 | 0 | 57597 | 1 | 0 |

## Quote comparison — evidence only

Deterministic first quote-bearing field in each of the four tables. One-based
physical lines include the header. CSV hypothesis: quoteChar=double quote,
doublequote=true, escapeChar=null. Backslashes are never decoded. Values below
are shown literally inside code spans, not JSON-escaped. No proposed value is active.

| Source / member | Source line | Exact column | Literal value | Proposed decoded value (unapproved) |
| --- | ---: | --- | --- | --- |
| SRC000001 / INFOTABLE.tsv | 73518 | NAMEOFISSUER | `"FORD MOTOR CO DEL ""NEW"""` | `FORD MOTOR CO DEL "NEW"` |
| SRC000004 / num.txt | 42226 | footnote | `"Effective October 3, 2009, we adopted ASC 470-20 - Debt, Debt with Conversions and Other Options (""ASC 470-20"") in accordance with GAAP. Our financial statements and the accompanying footnotes for all prior periods presented have been adjusted to reflect the retrospective adoption of this new accounting principle. See Note 7 to the Consolidated Financial Statements for further discussion."` | `Effective October 3, 2009, we adopted ASC 470-20 - Debt, Debt with Conversions and Other Options ("ASC 470-20") in accordance with GAAP. Our financial statements and the accompanying footnotes for all prior periods presented have been adjusted to reflect the retrospective adoption of this new accounting principle. See Note 7 to the Consolidated Financial Statements for further discussion.` |
| SRC000004 / tag.txt | 260 | doc | `"The value of the stock converted in a noncash (or part noncash) transaction. Noncash is defined as transactions during a period that do not result in cash receipts or cash payments in the period. ""Part noncash"" refers to that portion of the transaction not resulting in cash receipts or cash payments in the period."` | `The value of the stock converted in a noncash (or part noncash) transaction. Noncash is defined as transactions during a period that do not result in cash receipts or cash payments in the period. "Part noncash" refers to that portion of the transaction not resulting in cash receipts or cash payments in the period.` |
| SRC000004 / pre.txt | 5158 | plabel | `"Investment in Toys ""R"" Us"` | `Investment in Toys "R" Us` |

The retained inconsistency is SRC000004 / pre.txt line 57071, column plabel:
`DOCUMENTED_NON_NULLABLE_FIELD_IS_EMPTY`, disposition
`PRESERVED_LITERAL_NOT_REJECTED`. The existing source hash and member hash
identify the original record; no replacement or row removal occurred.
