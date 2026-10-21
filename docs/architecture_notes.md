# Architecture Notes

**Version:** v0.2 — reviewed conceptual baseline  
**Status:** Architecture hypotheses and intended engineering constraints, **not** a claim that the pipelines or tests already implement them.  
**Scope:** Conceptual architecture and source inspection of SEC Form 13F 2013 Q2, Nasdaq `nasdaqlisted.txt`, and Nasdaq `otherlisted.txt`.

## 1. What problem does an EDW solve?

An Enterprise Data Warehouse (EDW) supports **consistent cross-source analysis, historical inquiry, and reproducible reporting**. Operational systems (OLTP) are built primarily to carry out business transactions reliably and efficiently; they are not necessarily designed to answer complex questions that span many systems, periods, and definitions. An EDW serves analytical (OLAP) workloads without requiring analysts to reconstruct each source's identity, timing, and business rules for every query.

The problems to address include:
- **Integration:** Different systems describe overlapping real-world entities, but use different identifiers, definitions, and observation times.
- **Historical interpretation:** What was reported, effective, or known at a particular time must be distinguishable from what is known now.
- **Analytical consistency:** Users need agreed measures, valid aggregation rules, and reusable query structures.
- **Evidence:** Reported results should be traceable to source records and declared transformations.

3NF, Data Vault 2.0, and dimensional modeling are **possible modeling techniques**, not three mandatory sequential problems that OLTP systems cannot solve. OLTP databases can already be normalized. An EDW complements rather than replaces the transaction systems.

## 2. Source systems vs analytical systems

Each source is responsible for producing records for its own purpose; receiving multiple files does not automatically give the enterprise a coherent analytical view.

| Source | Primary purpose | What should not be assumed |
|---|---|---|
| **OMS** | Manage and record orders and execution-related workflow/status | An order row is necessarily one fill or an immutable event |
| **Custodian** | Record custody balances, holdings, movements, and/or settlement information under its reporting conventions | Its position date, unit, and ownership conventions equal those of the OMS |
| **SEC Form 13F** | Publish institutional investment managers' submitted holdings reports and related filing metadata | A manager's filer `CIK` is the held issuer's CIK; a filing date equals the holdings reporting period |
| **Nasdaq symbol directories** | Describe listed securities, market/symbol conventions, and related directory fields | A ticker is a permanent global security identifier or proves historical listing status |

The **analytical system** allows approved users to ask questions using explicit identity, time, unit, grain, and aggregation rules. It is designed for interpretation and comparison, not for originating orders or making custody transactions.

**Observed source constraint:** The SEC package is from 2013 Q2, whereas the uploaded Nasdaq files are later snapshots (2026-10-15). A present-day Nasdaq symbol entry cannot by itself establish a security's 2013 listing status.

## 3. What is raw representation?

RAW is **faithfully retained, source-native evidence before enterprise-level reinterpretation**. A valid RAW artifact preserves the original file bytes and enough acquisition context to establish where they came from, which source version or delivery was received, and whether the bytes later changed.

RAW is **not synonymous with dirty**: a source record can be well-formed and correct in its own domain while lacking an enterprise-wide identity or using a different unit, reporting period, or classification. Conversely, RAW can also contain genuine source mistakes. Neither case authorizes silently changing the retained source artifact.

**Intended constraints:** Keep source originals immutable; record filename, local raw path, SHA-256, source/delivery metadata, and ingestion context. Perform parsing and normalization into separate derived structures. Preserve the original source value when producing normalized values so that corrections and reinterpretations remain auditable.

## 4. What is grain?

**Grain is a precise declaration of what one row represents**. A list of columns does not define grain, and a business subject (e.g., “security holding”) may still be too vague. Grain determines which measures belong together and how records may safely be joined or aggregated.

| Source/table | One row represents... | Important key/time distinction |
|---|---|---|
| `SUBMISSION.tsv` | **One Form 13F submission** | `ACCESSION_NUMBER` identifies the submission; `FILING_DATE` and `PERIODOFREPORT` have different meanings |
| `INFOTABLE.tsv` | **One reported information-table holding line within a particular submission** | The source declares `(ACCESSION_NUMBER, INFOTABLE_SK)` as its key; `CUSIP` alone, or `(ACCESSION_NUMBER, CUSIP)`, is not necessarily unique |
| `nasdaqlisted.txt` | **One Nasdaq-listed security directory entry in the captured file snapshot** | `Symbol` is a source symbol, not a guaranteed permanent enterprise security ID |
| `otherlisted.txt` | **One other-exchange-listed security directory entry in the captured file snapshot** | `ACT Symbol`, `CQS Symbol`, and `NASDAQ Symbol` can be alternate representations for one directory entry |

The SEC filing metadata is not at the same grain as individual holdings lines. Likewise, listing directory rows are not the same kind of observation as holdings. A join can multiply a measure if it crosses a one-to-many relationship without an explicit aggregation/selection rule.

## 5. Why RAW → integrated representation?

Placing SEC and Nasdaq source tables into one database is **co-location, not yet semantic integration**. They differ in what each record represents, identifier namespaces (CUSIP versus exchange symbols), reporting/effective dates, terminology, and source responsibility.

The intended integration representation must make the following explicit:
- **Object boundaries:** Separate Issuer, Security, Listing, and Identifier. Same or similar names alone do not establish identity.
- **Source-to-enterprise mappings:** Preserve source identifiers and the evidence, validity period, and confidence/status of any proposed identity relationship. Do not infer `CUSIP → Symbol` from string similarity.
- **Relationship and time semantics:** A security may have multiple listings, and a current listing record may not support a historical 2013 claim.
- **Source fidelity:** Keep distinct observations, conflicting source claims, original units, and provenance rather than manufacturing a single unqualified “truth.”

Some mappings can eventually be verified by deterministic authoritative rules; others will require human review. Neither 3NF, Data Vault, nor dimensional modeling **automatically decides** which entities are equivalent. All can represent a resolved relationship using different structures.

**Current implementation boundary:** No canonical identity matching, business-key selection, or entity merging has been approved or implemented.

## 6. Why integrated → dimensional representation?

An integrated representation can correctly maintain identities, source relationships, and history yet remain inconvenient for repeated business questions. Dimensional modeling organizes a **chosen analytical business process and grain** into measurements (Facts) and descriptive contexts (Dimensions), making filtering, grouping, and appropriate aggregation more understandable and reusable.

For example, a future **13F holding-line fact** might expose reported value and quantity alongside filing-manager, security, and reporting-period context **only after** identity mappings, filing versions, units, and the precise fact grain are defined. Dimensions do not create missing source truth; they present validated context in a query-friendly form.

Integrated tables may themselves be queried with SQL. A distinct dimensional layer is a **design choice for analytical serving**, not a universal requirement to duplicate every record into a Star Schema. Dimensional modeling also does not automatically prevent fan-out or inappropriate sums; grain and aggregation rules remain mandatory.

## 7. Lossless

**Lossless is a set of intended validation obligations across a declared transformation**, not merely “the output has the same number of rows.” Record filtering, derived views, and valid aggregation may change physical row counts, but they must be declared and accountable. I will use the following six categories:

1. **Record-level accountability:** Every input observation is accounted for in declared outcomes (accepted, rejected, or quarantined), with no unexplained disappearance or duplication. Define these categories so counts are disjoint and reconcilable.
2. **Field-level accountability:** Every source field is retained, mapped, or deliberately excluded with a recorded reason; meaning-bearing fields must not silently disappear.
3. **Field fidelity / no distortion:** For mapped values, `derived_value = declared_transformation(source_value, context)`; the identity transform applies when no conversion is authorized. Preserve leading zeros, numeric precision, NULL versus blank, date meaning, units, and source multiplicity.
4. **RAW immutability:** Compare retained artifact hashes against the frozen inventory. A derived repair must never rewrite the original input.
5. **Lineage / reconstructability:** Every derived output must identify the source records and transformation versions that contributed to it. Source-to-output accountability must also identify excluded/quarantined observations.
6. **Reconciliation:** Apply numerical/economic checks **only at compatible declared grains and units**. A successful total is supporting evidence, not proof that each identity or record is correct.

**Current implementation status:** RAW SHA-256 verification exists in the starter; the other guarantees are **requirements for future tests**, not completed functionality.

## 8. Stability

Stability asks whether expanding the input corpus or changing a model causes **unexplained changes** in already-understood data. Freeze the raw artifacts, source membership, source identifiers, ground-truth decisions (where available), and previous model outputs before comparison.

Example: `C300` = frozen original cohort, `N450` = new records, `C750 = C300 ∪ N450`; `M1` = existing model, `M2` = proposed change.

| Situation | Required behavior |
|---|---|
| **New cohort fits M1** | Process `N450` under M1, validate Lossless 1–6, retain/check frozen `C300` baseline without unnecessary historical replay, then test `C750` for cross-source identity, multiplicity, temporal, and reconciliation issues |
| **M2 additive extension** | Preserve the meaning of existing outputs; validate new fields and `N450`. Backfill/replay `C300` only if historical support or downstream contracts require it. Compare unaffected prior fields against their frozen baseline |
| **M2 corrects an old defect** | Identify affected `C300` scope and intended corrections; replay affected historical RAW through M2 and rebuild dependent CLEAN/QUERYABLE outputs; validate intended changes, protect unaffected results, then validate `C750` |
| **New data inconsistent or unresolved** | Preserve source evidence, quarantine/escalate as appropriate, and block promotion of unverified semantic conclusions; do not force a mapping just to make the pipeline pass |

**Allowed does not mean unchanged outputs forever.** Compatible extensions and approved corrections may change outputs. What is unacceptable is **unexplained regression, unaccounted distortion, or silent rewriting of history**. Replay is a processing action; validation is a separate requirement. Combined-corpus checks must also catch failures that would not appear when validating `C300` or `N450` independently.

**Current implementation status:** These are future stability/replay design rules, not automated tests that already exist.

### 8.1 Day 3–5 experiment design — isolate change axes (planned)

Test one variable first, then its interaction with others. Freeze each historical input/output before comparison; do not conflate corpus growth, additive model change, and corrective semantics.

| Model / cohort | C300 (old scope) | C750 (expanded scope) |
|---|---|---|
| **M1** | `O_C300_M1` — frozen baseline | `O_C750_M1` — corpus-only growth |
| **M2 additive** | `O_C300_M2` — old-scope replay | `O_C750_M2` — combined replay |

- **Day 3 — horizontal:** Add authorized N450 to reach C750; keep M1 unchanged. Compare old C300 outputs and validate new/combined scope. Do not start Stability A/B/C until `O_C300_M1` is frozen.
- **Day 4 — vertical, intentionally exercise additive M2:** On a bounded SEC FSDS `num.txt` scope, add a typed `value_decimal` projection while preserving `lexical_value`, occurrence identity, and provenance. Verify old SQL/amounts remain equivalent and new conversion behavior is correct; replay FIN_001/FIN_002 and Tests A/B/C over the four cells. Expand to C1500 only after the small experiment is understood.
- **Day 5 — corrective experiment:** Preserve M2, then use FIN_002's parent-equity versus equity-including-NCI distinction as a *controlled negative/repair case*; it is not evidence that approved M1/M2 was wrong. If a genuine model defect is evidenced, version a corrective candidate (M3 if justified), replay affected historical scope, rebuild dependent outputs, and classify intended versus unexpected differences. Expand toward C2000 separately.

Keep source/cohort authorization independent of model approval. Do not introduce new source families, semantic mappings, and corrective logic in the same first test. The normative pass/fail criteria remain in `docs/evaluation_contract.md`.

## 9. Lineage and provenance

- **Provenance:** The original evidence behind a value — source system, delivery/file, exact source record, raw hash, relevant source time and ingestion context.
- **Lineage:** The path by which that evidence contributed to an output — extraction/parsing, source row selection, identity/mapping decisions, unit conversions, transformations, job runs, and rule/model versions. Lineage may be traced backward to explain a result and forward to identify affected consumers.

**Illustrative 13F question:** Why does a later analysis show a reported holding value of USD 440,000?
- Provenance should point to the precise SEC `INFOTABLE` record (`ACCESSION_NUMBER`, `INFOTABLE_SK`), original `VALUE = 440`, the retained ZIP and its hash, and the applicable source metadata.
- Lineage should show the declared 2013 rule **reported values are in USD thousands**, the conversion `440 × 1,000 = 440,000`, and the exact transformation version/run producing the analytical value.
- Correctness remains a third question: whether the selected filing version, holding line, currency/unit interpretation, and any aggregation are appropriate for the analyst's question.

Table-level lineage alone would not identify the specific source record behind a specific measure. Value/record-level evidence or a reproducible reconstruction path is needed for that explanation.

**Current implementation status:** Artifact hashes are available; complete field-level/record-level lineage and provenance tracking are future implementation work.
