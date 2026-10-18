# Source Profile — SEC Form 13F INFOTABLE

**Status:** Preliminary source observation; no canonical security/issuer mappings have been approved.

## Source and evidence

| Field | Observation |
| --- | --- |
| Source | SEC EDGAR — Form 13F Information Table |
| RAW archive | `2013q2_form13f.zip` |
| Source member | `INFOTABLE.tsv` |
| Repository RAW path | `data/raw/sec/2013q2_form13f.zip` |
| Archive SHA-256 | `569d56e978f7dee3775e544a1e46019389e22adcf482386fcfaba51ceb6c7e84` |
| Member SHA-256 | `04216106355c19768cc31019e6028e2d888cf527b34ab522cd805d54d6f40152` |
| Observed record count | 87,715 |
| Purpose | Contains individual securities holding lines reported in Form 13F Information Tables |
| **Grain guess** | **One row appears to represent one reported holding line within a particular 13F submission.** |
| Candidate identifiers | `ACCESSION_NUMBER` + `INFOTABLE_SK`: member-level composite row identifier observed unique in this dataset; `CUSIP`: security identifier; `FIGI`: additional instrument identifier field |
| Date fields | No direct date fields; filing/reporting dates available by relating `ACCESSION_NUMBER` to `SUBMISSION` (subject to verified join behavior) |
| Numerical measures | `VALUE`: reported market value, in USD thousands for this 2013 dataset; `SSHPRNAMT`: shares or principal amount; `VOTING_AUTH_SOLE`, `VOTING_AUTH_SHARED`, `VOTING_AUTH_NONE`: voting authority quantities |
| Source-specific terminology | `SH` shares; `PRN` principal amount; `PUTCALL`; `INVESTMENTDISCRETION` (`SOLE`/`DFND`/`OTR`); `OTHERMANAGER` |

## Actual source record

| ACCESSION_NUMBER | NAMEOFISSUER | CUSIP | VALUE | SSHPRNAMT | SSHPRNAMTTYPE |
| --- | --- | --- | ---: | ---: | --- |
| `0001487438-13-000014` | 3M COMPANY | `88579Y101` | 440 | 5,267 | `SH` |

- Reported `VALUE = 440` represents USD 440,000 because the source unit is USD thousands for this archive.
- `SSHPRNAMT = 5267` with `SSHPRNAMTTYPE = SH` represents 5,267 reported shares.

## Confirmed observations

- 87,715 holding lines associated with 141 distinct accession numbers.
- `SSHPRNAMTTYPE`: 86,533 `SH`; 1,182 `PRN`.
- `PUTCALL`: 5,475 Call; 5,315 Put; 76,925 blank.
- `FIGI` is blank in all 87,715 observed records.
- `CUSIP` is **not** unique per reported holding line: multiple rows may carry the same CUSIP within a submission.
- Some records share a CUSIP despite different reported issuer names. This is an **unresolved source anomaly**, not evidence that these issuers are equivalent.
- A holding line includes security description, value, amount/type, investment discretion, and voting authority; it is not merely a security × shares pair.

## Unknowns / questions

- Why do some accessions include multiple rows with the same CUSIP?
- Why do some rows share a CUSIP but report different issuer names: filing error, source extraction error, or another source-specific circumstance?
- How should amendments affect earlier reported holdings lines?
- How should Put/Call holdings be interpreted versus ordinary share holdings?
- What do `SOLE`, `DFND`, and `OTR` imply for investment discretion interpretation?
- What independent evidence is needed to map a CUSIP to an enterprise Security?

**Boundary:** Repetition of a CUSIP or similarity of reported issuer names does not authorize automatic deduplication, normalization, or cross-source matching.
