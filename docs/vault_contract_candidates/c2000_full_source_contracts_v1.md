# C2000 full-source Vault contract candidates V1

**Status: PROPOSED FOR OWNER DECISION. No business key, relationship, mapping, or full-corpus write is approved by this document.** The approved [FSDS `num.txt` Contract V1](../vault_load_contract_v1.md) remains unchanged. All candidates below use exact source lexical values, no issuer/security canonicalization, no amendment winner, no source NULL interpretation and no economic corrections. Names are proposed target structures, not deployed Delta tables.

## Common D5 and history rule proposed for review

For every DATA row, retain `(source_instance_id, RAW SHA-256, physical member, member SHA-256 if archived, byte offset/length or XML entry path plus occurrence ordinal, source line, parser version)` and the exact ordered lexical fields. The locator is a technical occurrence key, **never a business Hub key**. An append-only assertion satellite retains every physical duplicate, its presence/blank state and its source reporting text. A technical load timestamp is separate from source dates. Repeated source-native references can point to one Hub only if the specific relationship below is approved; they never collapse occurrence assertions. Exact zip/member hashes and frozen version pins are checked at load. No historical rows are overwritten.

Where an existing M1 binding supplies an exact byte locator, consume that pinned representation. For newly parsed members, the parser and locator derivation require a versioned contract and a bounded lossless prototype before use. A CSV/TSV delimiter split is insufficient for embedded delimiters; XML namespace and element-order preservation need explicit fixtures. Header/framing occurrences have separate technical accounting.

## SEC FSDS `sub.txt`, `pre.txt`, `tag.txt` — candidate FSDS_OTHER_V1

All 60 frozen ZIPs contain one header variant per member; 414,990 SUB, 43,717,018 PRE and 4,617,832 TAG DATA rows. NUM's 176,060,325 `value` occurrences retain their approved Contract V1. The historical 60-SUB complete accession inventory found 414,990 distinct nonblank SUB accessions; this supports an exact source-native filing reference, not cross-feed or issuer equivalence.

A further hash-verified probe of the three existing prototype ZIPs (`SRC000005`, `SRC000054`, `SRC000064`) inspected 1,776,145 PRE rows, 15,842 SUB rows and 215,718 TAG rows. It found zero PRE rows with an `adsh` absent from SUB or `(tag,version)` absent from TAG, zero duplicate `(tag,version)` TAG rows, and zero duplicate PRE rows at the complete eight-field candidate presentation context **within each ZIP**. This supports the proposed associations in those three deliveries only; it does not establish global cross-delivery uniqueness or approve the relationship.

| D1–D4 | Proposed structure and grain | Owner question / alternative |
| --- | --- | --- |
| SUB identity | Reuse approved `H_FILING(SEC_FSDS, exact adsh)`. Add `S_FSDS_SUB_ASSERTION` at `(filing_hk, technical occurrence)` with all 36 lexical fields, form/period/filed/accepted text and delivery history. No CIK or name Hub. | Approve SUB as a multi-active filing description? If same accession appears in another delivery with conflicting text, keep both assertions; a winner requires separate approval. |
| TAG identity | Reuse approved `H_CONCEPT(SEC_FSDS, exact tag, exact version)` only if TAG's pair is accepted as the same **source-native reference scope** as NUM's pair. Add `S_FSDS_TAG_ASSERTION` at `(concept_hk, occurrence)` with the nine original fields. | Approve this cross-member reference? Alternative: technical TAG-only assertions with no Hub association, which retains data but leaves TAG business integration partial. No cross-taxonomy version merge. |
| PRE relation | Candidate `L_FSDS_PRESENTATION` joins exact `adsh` to exact `(tag,version)` plus **complete** `report,line,stmt,inpth,rfile` source context; `S_FSDS_PRE_ASSERTION` is multi-active by occurrence and preserves `plabel,negating` and all ten fields. No row deduplication. | Approve this as a presentation relationship, and define whether the five context fields are dependent Link key components or only assertion payload? A plain Filing–Concept Link would lose line/report multiplicity. A technical-only PRE assertion remains possible. |
| History | Every SUB/TAG/PRE delivery occurrence appends; source dates and line order remain literal; no amendment precedence or inferred effective interval. | Approve append-only source history? If business-effective dating is required, supply a rule; it is not inferred here. |

**Negatives/limits:** Test same PRE context with different labels, exact duplicate PRE rows, changed TAG labels, missing SUB/TAG references, blank CIK, leading-zero `adsh` text and embedded TAB. The complete SUB uniqueness result does not prove PRE or TAG key uniqueness. A bounded cross-member orphan/collision profile is required in V3 before business association is accepted as live; candidate equality alone is insufficient.

## SEC EDGAR daily master — candidate EDGAR_MASTER_V1

1,893 files share the five-field header `CIK|Company Name|Form Type|Date Filed|File Name` and contain 7,940,373 DATA rows, zero bad-width rows in the read-only profile. Within files, 104,731 rows repeat an exact earlier row; 101,140 distinct file-path values occur more than once. Those counts forbid `DISTINCT` or a unique path-as-occurrence rule.

| D1–D4 | Proposed structure and grain | Owner question / alternative |
| --- | --- | --- |
| Identity | Candidate `H_EDGAR_FILE_REFERENCE(SEC_EDGAR_DAILY_MASTER, exact File Name)` is a **file reference**, not a filing/issuer/security identity. No name or CIK canonical Hub. | Approve exact path as a source-native reference? Alternative: preserve only technical index assertions until referenced file semantics are established. |
| Relationship | Candidate `L_EDGAR_INDEX_LISTING` links the exact path reference to literal `CIK` text, with source delivery and physical row occurrence as dependent context; or use no business Link and store CIK in the assertion. | Decide whether literal CIK is a source-native reference role and whether it warrants a Hub. Never equate it to FSDS/13F CIK without evidence. |
| Satellite/history | `S_EDGAR_INDEX_ASSERTION` keyed by occurrence, preserving all five fields and duplicate multiplicity. Date Filed is lexical source text; daily index delivery is source history, not an authority ranking. | Approve occurrence grain and append-only delivery history? Repeated paths across or within files remain distinct assertions. |

**Negatives/limits:** Exact duplicate rows and repeated paths are real observed cases. Test blank/path anomalies, leading-zero CIK, changed company name, same path on different dates, false cross-family accession joins and byte-safe decoding. The profile uses Latin-1 as a reversible byte display for at least one non-UTF-8 file; source character encoding remains a versioned parser decision, not a business normalization.

## SEC 13F seven-member ZIP — candidate SEC_13F_V1

All 42 ZIPs have the same seven TSV member headers. Counts: SUBMISSION 292,618; COVERPAGE 292,618; SIGNATURE 292,618; SUMMARYPAGE 228,496; INFOTABLE 87,012,867; OTHERMANAGER 156,841; OTHERMANAGER2 122,002. Three deep ZIP probes found no duplicate SUBMISSION accession or INFOTABLE_SK **within those ZIPs**, no INFOTABLE accession without SUBMISSION, and maximum INFOTABLE fanout per accession of 25,369, 43,655 and 64,943. These are bounded observations, not a global uniqueness proof. Blank FIGI counts were 1,533,636, 2,040,197 and 2,679,745 respectively.

| D1–D4 | Proposed structure and grain | Owner question / alternative |
| --- | --- | --- |
| Identity | Candidate `H_13F_SUBMISSION(SEC_13F, exact ACCESSION_NUMBER)`. Do not merge with FSDS/EDGAR filing Hub. | Approve exact accession as a 13F source-native filing reference? If cross-delivery conflicts occur, preserve each assertion. |
| Relationships | Candidate member-specific `L_13F_MEMBER_ASSERTION` from submission to each child member's occurrence, with member type and any source-native child SK as attributes. The child occurrence remains the unique technical anchor. | Approve accession equality as the relationship for all seven members? For a missing or ambiguous parent, quarantine semantic association while retaining the child occurrence. `INFOTABLE_SK` is not yet proven globally stable. |
| Payload/history | Member-specific multi-active satellites preserve every original field, padded CUSIP/CIK/FIGI text, amendment flags, source dates and row order. Technical event time and report period stay separate. | Approve one occurrence per member row and append-only history? No holdings aggregation, issuer/security merge, amendment precedence or period alignment is proposed. |

**Negatives/limits:** Test blank FIGI, missing parent accession, child SK collision across ZIPs, padded/leading-zero identifiers, false CUSIP merge, amendment winner, duplicate child payload and large submission fanout. Full 42-ZIP cross-member orphan and collision checks are V3 prerequisites before live relationship PASS.

## Treasury five XML feeds — candidate TREASURY_FEEDS_V1

Five frozen files contain 1,743 Atom entries total and five distinct `<properties>` shapes: yield curve 249 (`NEW_DATE`, 17 properties), bill rates 249 (`INDEX_DATE`, 48), long-term rates 747 (`QUOTE_DATE`, `RATE_TYPE`, five), real yield 249 (`NEW_DATE`, seven), real long-term 249 (`QUOTE_DATE`, two). In long-term rates, 249 dates recur across three `RATE_TYPE` values (`BC_20year`, `Over_10_Years`, `Real_Rate`); `(QUOTE_DATE,RATE_TYPE)` had no duplicate in that file. `Id`/feed-specific IDs can be absent, so cannot be required universally.

| D1–D4 | Proposed structure and grain | Owner question / alternative |
| --- | --- | --- |
| Identity | Candidate `H_TREASURY_FEED(exact source-native Atom feed ID, frozen feed family)`. Candidate `H_TREASURY_OBSERVATION` is scoped to feed + exact date field/text + `RATE_TYPE` where physically present; keep occurrence distinct even if that tuple repeats. | Approve feed-scoped observation identity? Alternative: no observation Hub, only occurrence assertions. A date alone is demonstrably insufficient for the long-term feed. |
| Relationship | Candidate `L_TREASURY_FEED_OBSERVATION` connects feed to its observation; no Link across feeds or years and no tenor equivalence. | Approve the feed/entry relationship from XML containment? Should missing date entries remain technical-only rather than acquire a synthetic business key? |
| Payload/history | `S_TREASURY_ENTRY_ASSERTION` retains element path, order, exact property names/text, missing versus empty, repeated entries and source publication text. Tenor fields remain literal payload, with no yield interpolation or economic equivalence. | Approve append-only source history and five feed-specific property sets? A normalized tenor entity or rate semantic rule needs separate evidence. |

**Negatives/limits:** Test missing tenor fields (31 in the yield-curve file), missing optional ID (110 in bill and real-yield files), duplicate dates, false cross-feed date joins, lexical precision, absent versus empty elements and XML namespace/entry-order changes. The historical Treasury L3 dispositions do not approve these Vault business definitions.

## One consolidated Owner semantic decision

For each of `FSDS_OTHER_V1`, `EDGAR_MASTER_V1`, `SEC_13F_V1`, `TREASURY_FEEDS_V1`, the Owner can approve the source-scoped proposal, require specified changes, or authorize technical occurrence preservation with explicit `PARTIAL` business coverage. Approval must pin this exact contract version or its revised successor and accepted negative/relationship rules. No approval is implied by branch merge, candidate code, profiling or a prior FSDS NUM prototype.
