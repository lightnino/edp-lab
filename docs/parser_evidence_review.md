# §1.4 Layer 2 — Parser profile evidence review

Subsequent Human Review approved D1 literal missing-value preservation, D3 exact
ALL_TEXT preservation, and the D4 strict-validation design. D2 and D5 remain
PROVISIONAL. The investigation below is retained as historical evidence;
its original approval questions are superseded by the decision record in
[parser_fidelity_validation.md](parser_fidelity_validation.md). V1 remains unchanged.

Investigation date: 2026-10-20. Scope: the four admitted immutable local RAW
artifacts and thirteen GOLD_V2 logical tables only. This is parser evidence,
not a profiling baseline, semantic admission, or profile approval. All three
configured profiles remain `PROVISIONAL`; none was marked `RAW_VERIFIED`.

The three shared profiles fit the observed delimiters, headers and row widths.
They are **not yet sufficient to freeze interpreted field values**: quote
interpretation and missing-value semantics remain unresolved. Table-specific
schemas and evidence are necessary; separate runtime dialects are not yet
justified by the available evidence. Proposed changes and alternatives are in
[parser_config_v2_proposal.md](parser_config_v2_proposal.md), outside frozen V1.

## Reproduction and provenance

Run from the repository root, offline, using the existing locked environment:

```sh
.venv/bin/python -m edp_lab verify-raw
.venv/bin/python -m edp_lab.profiling.conventions
.venv/bin/python -m edp_lab.profiling.conventions --check-raw
.venv/bin/python -m edp_lab.profiling.parser_evidence
.venv/bin/python -m pytest -q
.venv/bin/ruff check src/edp_lab/profiling/parser_evidence.py tests/corpus_invariants/test_parser_evidence.py
```

The evidence collector verifies all admitted hashes before reading table
members, emits deterministic lexical inspection to stdout, and makes no data
changes. Its candidate-token/date/number regexes are searches, **not type or
NULL inference**. For example, CUSIP `06738E204` resembles exponent notation;
an eight-digit surrogate key resembles a date. Neither may be cast on that basis.
No distributions, distinctness metrics, or official profiling baselines were generated.

Parser code at investigation start: Git `71d4ba15a603b9c9d90b3998f7db88ec658fec26`.
The new evidence collector is an uncommitted addition; its contents accompany
this review. Runtime: Python 3.12.15, DuckDB 1.5.6.
`uv.lock` SHA-256: `62a95abca6cf980c2f68d97fa34fdcdf4330ab1da49bf01e8bed6b36617a1803`.
No dependency sync or network requests were made.

Source paths, identities and parent archive hashes are frozen in
`metadata/gold_set_logical_tables_v2.csv` and `metadata/corpus_manifest.csv`:

| Source | Local RAW path | Verified SHA-256 |
| --- | --- | --- |
| SRC000001 | `data/raw/sec/2013q2_form13f.zip` | `569d56e978f7dee3775e544a1e46019389e22adcf482386fcfaba51ceb6c7e84` |
| SRC000002 | `data/raw/nasdaq/nasdaqlisted.txt` | `1d3656d26cfddd35363ce8022d50cbb5342ae2b1cfebee74f3c3b168b0f0f808` |
| SRC000003 | `data/raw/nasdaq/otherlisted.txt` | `7f099cd61db347f2199251dfe45dc132ffc8c75bd68a91471c30e217e4265d3d` |
| SRC000004 | `data/raw/sec/2010q2_fsds.zip` | `25f416b020fd3e62a67dbf8c6522c9f239e716099b61cf5d05a59a91ffdef1f1` |

## Documentation evidence

* **D13:** SRC000001 `FORM13F_readme.htm`, §4 File Formats and §5.1–5.7
  Table Definitions. Member SHA-256
  `305c668f11001802b067a99512cb0440a4f88c21b4b71bcce9a2f8a9abc8e992`.
  Declares tab-delimited UTF-8 text, source types and per-column nullability,
  and DD-MON-YYYY date fields. Nullability is not a serialized NULL-token rule.
* **M13:** same archive, `FORM13F_metadata.json`, SHA-256
  `42a43366dcee0fe70399db36825cdce18ecba74d95b5a4e18406cf0f0b43ca01`.
  `dialect` declares header=true, headerRowCount=1 and delimiter=`\t`;
  all seven ordered `tableSchema.columns[].name` lists match RAW headers.
  It contains no explicit top-level NULL/quote/escape rule. CSVW defaults
  must not be adopted implicitly as approval to change V1. `titles` are display
  labels, not replacement headers; primary-key declarations are not enterprise keys.
* **DFS:** SRC000004 `readme.htm`, §4 and §5.1–5.4, SHA-256
  `25e0a9e16de0b6cabdb3a07b85ab2dbf2263c9f3e4800d62ad9430728322eb5d`.
  Declares UTF-8, TAB, LF and first-line lowercase column names. Describes
  nullable fields, `num.value` NUMERIC(28,4), `num.footnote` blank when absent,
  `num.coreg` NULL for consolidated entity, and date/time representations.
  These descriptions do not fully specify byte-level NULL serialization.
  README itself declares Windows-1252 and fails strict UTF-8 at byte 17148
  (`0x92`); it was inspected using its declared charset. This does not change
  the table encoding: every selected table decoded strictly as UTF-8.
* **DN:** `metadata/source_profiles/nasdaq_listed.md` and
  `nasdaq_otherlisted.md` supply preliminary local observations, not an
  authoritative serialization specification. No authoritative Nasdaq format
  document is bundled with these standalone files. External references were
  not fetched. The other two source profiles (`sec_submission.md`,
  `sec_infotable.md`) were also read as preliminary evidence, not normative rules.

The HTML documents were inspected locally, excluding style/script content;
13F HTML was rendered with Windows-1252 for readable punctuation despite its
us-ascii declaration. No README encoding choice was applied to table bytes.

## Thirteen-table review matrix

`PASS` below means the existing full structural probe passed, not semantic
approval. Line references are one-based physical lines including the header;
columns use exact source names. D1–D5 refer to approval questions below.
Statuses: `EVIDENCE_CONFIRMED` means the full proposed parser behavior is
supported in scope; `REVIEW_REQUIRED` means evidence exists but a consequential
policy choice or conflict needs approval; `INSUFFICIENT_EVIDENCE` means required
source documentation is absent. None of these statuses promotes a profile.

| Source / logical table | Profile ID | Evidence / validation result (columns; data rows; metadata rows) | Unresolved questions | Proposed status |
| --- | --- | --- | --- | --- |
| SRC000001 COVERPAGE.tsv | SEC_13F_TSV_V1 | D13 §5.2 + M13; PASS 21; 166; 0. 1,481 empty fields; line 87 STREET2=`N/A`; ZIPCODE has `-`. Dates are DD-MON-YYYY text. | D1: blanks, N/A and hyphen stay distinct? D2/D3: retain literal dialect and exact headers? | REVIEW_REQUIRED |
| SRC000001 INFOTABLE.tsv | SEC_13F_TSV_V1 | D13 §5.7 + M13; PASS 15; 87,715; 0. FIGI blank in all rows; 3 quote-bearing fields. Line 73518 NAMEOFISSUER has outer/doubled quotes; line 640 CUSIP ends in a space. | D1: blank FIGI/PUTCALL/OTHERMANAGER and NONE variants? D2: literal quotes or unquoting? D3: preserve padded CUSIP and numeric-looking identifiers? | REVIEW_REQUIRED |
| SRC000001 OTHERMANAGER.tsv | SEC_13F_TSV_V1 | D13 §5.3 + M13; PASS 7; 47; 0. CIK blank 27 times; CRDNUMBER and SECFILENUMBER blank 47 each; no quote/backslash fields. | D1: blank nullable identifiers remain empty text? D2: absence of quotes only supports this snapshot. | REVIEW_REQUIRED |
| SRC000001 OTHERMANAGER2.tsv | SEC_13F_TSV_V1 | D13 §5.6 + M13; PASS 7; 179; 0. CIK blank 108; FORM13FFILENUMBER blank 61; CRDNUMBER/SECFILENUMBER blank 179 each. | D1: blank handling? Source key declarations do not authorize merging or deduplication. D2/D3 apply. | REVIEW_REQUIRED |
| SRC000001 SIGNATURE.tsv | SEC_13F_TSV_V1 | D13 §5.4 + M13; PASS 8; 166; 0. No empty, quote, or backslash fields; line 2 SIGNATUREDATE=`27-JUN-2013`. | D1/D2: approve bounded literal policy despite no missing/quoted examples here? D3: date and phone remain text? | REVIEW_REQUIRED |
| SRC000001 SUBMISSION.tsv | SEC_13F_TSV_V1 | D13 §5.1 + M13; PASS 5; 166; 0. No empty/quote/backslash fields; line 2 CIK=`0000823621`, FILING_DATE=`31-MAY-2013`. | D1/D2: no missing/quote examples cannot prove a general convention. D3: preserve CIK zeros and date text? | REVIEW_REQUIRED |
| SRC000001 SUMMARYPAGE.tsv | SEC_13F_TSV_V1 | D13 §5.5 + M13; PASS 5; 141; 0. ISCONFIDENTIALOMITTED blank 50; totals are digit text; no quote/backslash fields. | D1: blank flag remains empty? D3: preserve totals without float conversion or sums? | REVIEW_REQUIRED |
| SRC000002 nasdaqlisted.txt | NASDAQ_PIPE_V1 | DN + RAW; PASS 8; 5,629; 1. Pipe header; no empty data fields. Symbol=`NA` at line 3351; 5 fields have edge spaces. | D1: preserve NA symbol? D4: footer policy? D5: accept snapshot-only evidence or supply authoritative format documentation? | INSUFFICIENT_EVIDENCE |
| SRC000003 otherlisted.txt | NASDAQ_PIPE_V1 | DN + RAW; PASS 8; 7,660; 1. No empty data fields. `NAN` in three symbol fields; 65 fields have edge spaces. Footer width is 7, header width 8. | D1: preserve NAN symbols? D4: explicitly permit seven-field metadata footer? D5: authoritative dialect evidence absent. | INSUFFICIENT_EVIDENCE |
| SRC000004 sub.txt | SEC_FSDS_TSV_V1 | DFS §5.1; PASS 36; 522; 0. 2,026 empty fields; one backslash-bearing name at line 242; accepted line 2=`2010-05-07 13:14:00.0`. | D1: afs/aciks/other blanks versus NULL prose? D2: literal backslashes? D3: timestamp fractional suffix differs from README's seconds-only notation. | REVIEW_REQUIRED |
| SRC000004 num.txt | SEC_FSDS_TSV_V1 | DFS §5.3; PASS 10; 136,044; 0. 600 empty value fields; 135,444 decimal strings, e.g. line 2 `-116000000.0000`; 15 quote-bearing footnotes. | D1: nullable value/coreg/segments versus blank footnote? D2: outer/doubled quotes in footnotes? D3: retain scale and date text? | REVIEW_REQUIRED |
| SRC000004 tag.txt | SEC_FSDS_TSV_V1 | DFS §5.2; PASS 9; 8,477; 0. Empty crdr/doc/tlabel; 79 quote-bearing and 4 backslash-bearing fields. Line 260 doc has outer/doubled quotes. | D1: field-specific nullable text? D2: quoted descriptions and literal backslashes? D3: preserve taxonomy/version spelling? | REVIEW_REQUIRED |
| SRC000004 pre.txt | SEC_FSDS_TSV_V1 | DFS §5.4; PASS 10; 57,596; 0. 21 quote-bearing plabel values; line 5158 quoted Toys R Us label; line 57071 plabel empty. | D1: README says plabel may not be NULL, yet one blank occurs. Preserve and flag rather than repair/drop? D2: unquoting? | REVIEW_REQUIRED |

## Cross-table findings and limits

All thirteen tables strictly decode as UTF-8, contain only ASCII bytes, have no
BOM, no empty/duplicate header names, no blank physical lines, and end with a
newline. ASCII-only evidence cannot distinguish UTF-8 from compatible legacy
encodings; SEC documentation supports UTF-8, while Nasdaq's encoding is a
snapshot-compatible assumption. SEC tables use LF; Nasdaq uses CRLF.
Every data record has the header width under literal delimiter splitting.
No width exceptions, extra SEC metadata records or multiline records were
observed under that interpretation. This cannot exclude same-width exceptional
records whose meaning is unknown. No source occurrences were discarded.

Accounting is exact for physical records: SEC = 1 header + data rows; Nasdaq =
1 header + data rows + 1 explicitly inventoried footer. Nasdaq footers are
`File Creation Time: 1015202603:03` followed by seven pipes (nasdaqlisted,
line 5631) or six pipes (otherlisted, line 7662). The raw spelling is not ISO
timestamp syntax. Timezone and conversion are unapproved; earlier local
profile rendering of 2026-10-15 03:03 is not authority to cast it.

No exact literal `NULL` (case-insensitive), `\\N`, or quoted empty token `""`
was observed in data fields. Empty fields were observed in nine tables;
SIGNATURE, SUBMISSION and both Nasdaq tables had none. No whitespace-only
fields were found. Candidate strings are preserved, including `N/A`, `NONE`,
`None`, `none`, `-`, `.`, `NA`, and `NAN`. There is no evidence for a global
missing-token substitution list. Counts are lexical occurrences, not null_count.

The four quote-bearing tables contain exporter-like outer/doubled quotes.
V1's QUOTE_NONE preserves those characters; conventional CSV unquoting would
change them while still passing the width probe. Neither successful parse
establishes which is the intended field value. Backslashes in sub.name and
tag.doc likewise must not trigger an undocumented escape convention.

ALL_TEXT, exact header spelling/order, no trim/case folding, no numeric/date
casts and no deduplication preserve the inspected representations. Accession
numbers and CIK/CUSIP/ZIP-like fields contain leading zeros; decimal text has
signs and trailing zeros. These are fidelity evidence, not approved identifier
semantics. D13 documents DD-MON-YYYY dates; DFS documents YYYYMMDD dates,
MMDD fiscal year-end, YYYY year, and timestamp text. The observed `.0` timestamp
suffix must survive. No timezone inference, float rounding, rescaling, date
alignment, amendment selection or economic reconciliation was performed.

JSON options are inapplicable to all thirteen logical tables. The bundled
13F JSON is documentation about tabular files, not a fourteenth admitted table
or permission for JSON fallback. Keep json_format/json_max_depth null.

## Fail-closed assessment

Code inspection of `conventions.probe_raw_parsers` confirms strict decoding,
duplicate/empty header rejection, width rejection, required single Nasdaq
footer, and rejection of data after that footer. The existing synthetic parser
test executes footer accounting and width rejection; the new collector tests
execute integrity-before-read and lexical preservation. Valid RAW cannot by
itself demonstrate all malformed-input behavior.

Limits requiring D4 review: the probe recognizes any first field starting
`File Creation Time:` as footer and does **not** validate its timestamp spelling,
width, or empty remaining fields. A footer with arbitrary additional content
could pass. A UTF-8 BOM would become part of the first header rather than
trigger a specific BOM error. Changed but unique/nonempty headers are accepted;
unexpected same-width trailing SEC text cannot be detected by widths alone.
The current probe is not a full implementation of the future production
FAIL_CLOSED guarantee. No parser implementation was silently strengthened here.

## Required human decisions before configuration freeze

1. **D1 — Missing representations:** Do you approve retaining every blank and
   candidate token as exact text with `null_tokens=[]` for this bounded parser,
   explicitly withholding source-NULL interpretation and semantic NULL metrics?
   Alternatively, which source-evidenced per-column rules should a separately
   versioned configuration implement? Global blank/NA/NAN/NONE conversion would
   conflate observed representations, including Nasdaq symbols. Resolve or
   explicitly withhold `pre.plabel` nullability interpretation; retain the row.
2. **D2 — Quotes/escapes:** Do you approve literal preservation, or require a
   documented exporter dialect and unquoting for INFOTABLE/num/tag/pre? The
   first alternative preserves serialized quote wrappers; the second changes
   field values and requires a new version and differential validation. Should
   the other tables share that reviewed dialect or use table-specific bindings?
   Keep backslashes literal unless separately evidenced and approved.
3. **D3 — Text scope/schema:** Do you approve exact ALL_TEXT values, ordered RAW
   headers, leading zeros, padding and precision, empty date/timestamp format
   maps, and null JSON options for these thirteen tables? This leaves source
   types documentary and preserves sub.accepted's `.0`; typed interpretation
   would require separate evidence and approval. No business keys are proposed.
4. **D4 — Fail-closed boundaries:** Do you approve explicit BOM rejection,
   table-specific exact expected headers and the two observed Nasdaq footer
   shapes in a future version (including width 7 for otherlisted metadata),
   retaining each footer's raw bytes/locator separately? Or what broader footer
   grammar should be admitted? Exact snapshot rules detect drift but block new
   shapes until reviewed. Require malformed-input tests before promotion.
5. **D5 — Evidence scope:** Will you approve a freeze limited to these exact
   hashes with Nasdaq encoding/quote/missing conventions explicitly provisional,
   or provide/authorize collection of authoritative Nasdaq serialization
   documentation before freeze? Local preliminary profiles alone cannot close
   this gap. No external access has been authorized or performed.

Approval of this review alone must not auto-promote profiles. After decisions,
review the effective versioned configuration, implementation revision and
targeted fidelity checks before any `RAW_VERIFIED` promotion or baseline run.

## Executed validation

RAW identity/hash/archive membership: PASS, 4 instances and 13 registered
tables. Metadata convention validation: PASS, 13 bindings. Existing structural
probes: PASS on all 13, counts in the matrix. Existing test suite initially:
29 passed. With the two new collector tests: 31 passed. Initial lint found
one C408 in the new test fixture; it was corrected before final validation.
Final rerun: 31 passed in 0.13s; targeted Ruff checks and `git diff --check`
passed. The standalone metadata convention command also passed.
No RAW, cohort, registry, profile, frozen V1 or Evaluation Contract was changed.

## Exact table evidence appendix

Generated from the read-only collector on the verified parent hashes above.
Member hashes identify uncompressed bytes; standalone hashes repeat RAW hashes.
Header order is literal. Counts below concern lexical inspection only.

### SRC000001 / COVERPAGE.tsv

Member SHA-256: `21287ddc712db9553e7c7295f2713ecb3c8b63891be622811b29e5cc5836790e`. Physical lines: 167; data: 166; metadata: 0.

Ordered header:

```text
ACCESSION_NUMBER
REPORTCALENDARORQUARTER
ISAMENDMENT
AMENDMENTNO
AMENDMENTTYPE
CONFDENIEDEXPIRED
DATEDENIEDEXPIRED
DATEREPORTED
REASONFORNONCONFIDENTIALITY
FILINGMANAGER_NAME
FILINGMANAGER_STREET1
FILINGMANAGER_STREET2
FILINGMANAGER_CITY
FILINGMANAGER_STATEORCOUNTRY
FILINGMANAGER_ZIPCODE
REPORTTYPE
FORM13FFILENUMBER
CRDNUMBER
SECFILENUMBER
PROVIDEINFOFORINSTRUCTION5
ADDITIONALINFORMATION
```

Quote-bearing fields: 0; backslash-bearing: 0; edge-whitespace: 0; empty: 1481.

Empty-field occurrences by exact column: `ISAMENDMENT`=87; `AMENDMENTNO`=104; `AMENDMENTTYPE`=104; `CONFDENIEDEXPIRED`=146; `DATEDENIEDEXPIRED`=162; `DATEREPORTED`=162; `REASONFORNONCONFIDENTIALITY`=162; `CRDNUMBER`=166; `SECFILENUMBER`=166; `ADDITIONALINFORMATION`=157; `FILINGMANAGER_STREET2`=65.

### SRC000001 / INFOTABLE.tsv

Member SHA-256: `04216106355c19768cc31019e6028e2d888cf527b34ab522cd805d54d6f40152`. Physical lines: 87716; data: 87715; metadata: 0.

Ordered header:

```text
ACCESSION_NUMBER
INFOTABLE_SK
NAMEOFISSUER
TITLEOFCLASS
CUSIP
FIGI
VALUE
SSHPRNAMT
SSHPRNAMTTYPE
PUTCALL
INVESTMENTDISCRETION
OTHERMANAGER
VOTING_AUTH_SOLE
VOTING_AUTH_SHARED
VOTING_AUTH_NONE
```

Quote-bearing fields: 3; backslash-bearing: 0; edge-whitespace: 945; empty: 181433.

Empty-field occurrences by exact column: `FIGI`=87715; `PUTCALL`=76925; `OTHERMANAGER`=16793.

### SRC000001 / OTHERMANAGER.tsv

Member SHA-256: `1b0b933ae18d2f2598ce08a04b55905a3d067daaae7411cdd9c72ba77e1e4aee`. Physical lines: 48; data: 47; metadata: 0.

Ordered header:

```text
ACCESSION_NUMBER
OTHERMANAGER_SK
CIK
FORM13FFILENUMBER
CRDNUMBER
SECFILENUMBER
NAME
```

Quote-bearing fields: 0; backslash-bearing: 0; edge-whitespace: 0; empty: 121.

Empty-field occurrences by exact column: `CIK`=27; `CRDNUMBER`=47; `SECFILENUMBER`=47.

### SRC000001 / OTHERMANAGER2.tsv

Member SHA-256: `5ed5e425554684488b0ec6f8de65266bd10531c625107fd0906fec710495c3be`. Physical lines: 180; data: 179; metadata: 0.

Ordered header:

```text
ACCESSION_NUMBER
SEQUENCENUMBER
CIK
FORM13FFILENUMBER
CRDNUMBER
SECFILENUMBER
NAME
```

Quote-bearing fields: 0; backslash-bearing: 0; edge-whitespace: 0; empty: 527.

Empty-field occurrences by exact column: `CIK`=108; `FORM13FFILENUMBER`=61; `CRDNUMBER`=179; `SECFILENUMBER`=179.

### SRC000001 / SIGNATURE.tsv

Member SHA-256: `5985b6fe2576041d0493ce8913b1d4ca7d865be42f89ca0df0d77658e4cfae17`. Physical lines: 167; data: 166; metadata: 0.

Ordered header:

```text
ACCESSION_NUMBER
NAME
TITLE
PHONE
SIGNATURE
CITY
STATEORCOUNTRY
SIGNATUREDATE
```

Quote-bearing fields: 0; backslash-bearing: 0; edge-whitespace: 0; empty: 0.

Empty-field occurrences by exact column: none.

### SRC000001 / SUBMISSION.tsv

Member SHA-256: `94494b45570e698a13b700a510b818d0008ccaa86a93786adb37676433113d2d`. Physical lines: 167; data: 166; metadata: 0.

Ordered header:

```text
ACCESSION_NUMBER
FILING_DATE
SUBMISSIONTYPE
CIK
PERIODOFREPORT
```

Quote-bearing fields: 0; backslash-bearing: 0; edge-whitespace: 0; empty: 0.

Empty-field occurrences by exact column: none.

### SRC000001 / SUMMARYPAGE.tsv

Member SHA-256: `78fe8497b0fa92b7ee715a43fdcef6200b458724db3f880222bd532743deb263`. Physical lines: 142; data: 141; metadata: 0.

Ordered header:

```text
ACCESSION_NUMBER
OTHERINCLUDEDMANAGERSCOUNT
TABLEENTRYTOTAL
TABLEVALUETOTAL
ISCONFIDENTIALOMITTED
```

Quote-bearing fields: 0; backslash-bearing: 0; edge-whitespace: 0; empty: 50.

Empty-field occurrences by exact column: `ISCONFIDENTIALOMITTED`=50.

### SRC000002 / nasdaqlisted.txt

Member SHA-256: `1d3656d26cfddd35363ce8022d50cbb5342ae2b1cfebee74f3c3b168b0f0f808`. Physical lines: 5631; data: 5629; metadata: 1.

Ordered header:

```text
Symbol
Security Name
Market Category
Test Issue
Financial Status
Round Lot Size
ETF
NextShares
```

Quote-bearing fields: 0; backslash-bearing: 0; edge-whitespace: 5; empty: 0.

Empty-field occurrences by exact column: none.

### SRC000003 / otherlisted.txt

Member SHA-256: `7f099cd61db347f2199251dfe45dc132ffc8c75bd68a91471c30e217e4265d3d`. Physical lines: 7662; data: 7660; metadata: 1.

Ordered header:

```text
ACT Symbol
Security Name
Exchange
CQS Symbol
ETF
Round Lot Size
Test Issue
NASDAQ Symbol
```

Quote-bearing fields: 0; backslash-bearing: 0; edge-whitespace: 65; empty: 0.

Empty-field occurrences by exact column: none.

### SRC000004 / sub.txt

Member SHA-256: `fca0ff4bf873b46245ac3ca3524f6be6083852cdc7e97a12f307df636834a3e8`. Physical lines: 523; data: 522; metadata: 0.

Ordered header:

```text
adsh
cik
name
sic
countryba
stprba
cityba
zipba
bas1
bas2
baph
countryma
stprma
cityma
zipma
mas1
mas2
countryinc
stprinc
ein
former
changed
afs
wksi
fye
form
period
fy
fp
filed
accepted
prevrpt
detail
instance
nciks
aciks
```

Quote-bearing fields: 0; backslash-bearing: 1; edge-whitespace: 0; empty: 2026.

Empty-field occurrences by exact column: `bas2`=343; `mas2`=361; `former`=252; `changed`=252; `aciks`=499; `countryinc`=46; `stprinc`=70; `countryma`=21; `stprma`=57; `cityma`=21; `zipma`=22; `mas1`=21; `stprba`=44; `afs`=1; `zipba`=4; `bas1`=3; `baph`=8; `countryba`=1.

### SRC000004 / num.txt

Member SHA-256: `8d25184552932ca8fc99a38a39e6e430d82ca8064bdad9e80ae5043ccd26ec11`. Physical lines: 136045; data: 136044; metadata: 0.

Ordered header:

```text
adsh
tag
version
ddate
qtrs
uom
segments
coreg
value
footnote
```

Quote-bearing fields: 15; backslash-bearing: 0; edge-whitespace: 0; empty: 376222.

Empty-field occurrences by exact column: `coreg`=130105; `footnote`=135765; `segments`=109752; `value`=600.

### SRC000004 / tag.txt

Member SHA-256: `f695d9ebf9cf4eb0494aaf56b3d44d36f11097a34e5064aef1008953506cfe41`. Physical lines: 8478; data: 8477; metadata: 0.

Ordered header:

```text
tag
version
custom
abstract
datatype
iord
crdr
tlabel
doc
```

Quote-bearing fields: 79; backslash-bearing: 4; edge-whitespace: 0; empty: 1256.

Empty-field occurrences by exact column: `crdr`=987; `doc`=268; `tlabel`=1.

### SRC000004 / pre.txt

Member SHA-256: `7040ebadfa443df1d392fc988f625761606d8396fe5103e6c0129f4e113beaea`. Physical lines: 57597; data: 57596; metadata: 0.

Ordered header:

```text
adsh
report
line
stmt
inpth
rfile
tag
version
plabel
negating
```

Quote-bearing fields: 21; backslash-bearing: 0; edge-whitespace: 0; empty: 1.

Empty-field occurrences by exact column: `plabel`=1.
