# Source Profile — SEC Form 13F SUBMISSION

**Status:** Preliminary source observation; grain, identifiers, and semantics have not been promoted to enterprise definitions.

## Source and evidence

| Field | Observation |
| --- | --- |
| Source | SEC EDGAR — Form 13F |
| RAW archive | `2013q2_form13f.zip` |
| Source member | `SUBMISSION.tsv` |
| Repository RAW path | `data/raw/sec/2013q2_form13f.zip` |
| Archive SHA-256 | `569d56e978f7dee3775e544a1e46019389e22adcf482386fcfaba51ceb6c7e84` |
| Member SHA-256 | `94494b45570e698a13b700a510b818d0008ccaa86a93786adb37676433113d2d` |
| Observed record count | 166 |
| Purpose | Records Form 13F submissions, who filed, when they filed, and the holdings reporting period |
| **Grain guess** | **One row appears to represent one SEC Form 13F submission identified by `ACCESSION_NUMBER`.** |
| Candidate identifiers | `ACCESSION_NUMBER`: submission identifier; observed unique in this dataset. `CIK`: filing manager identifier, not an issuer identifier. |
| Date fields | `FILING_DATE`: date of filing; `PERIODOFREPORT`: holdings reporting period |
| Numerical measures | None — no security-level positions, quantities, or values |
| Source-specific terminology | `13F-HR` holdings report; `13F-HR/A` amended holdings report; `13F-NT` notice; `13F-NT/A` amended notice |

## Actual source record

| ACCESSION_NUMBER | FILING_DATE | SUBMISSIONTYPE | CIK | PERIODOFREPORT |
| --- | --- | --- | --- | --- |
| `0001172661-13-000924` | `31-MAY-2013` | `13F-HR/A` | `0000823621` | `31-MAR-2013` |

## Confirmed observations

- 166 unique submissions from 95 distinct filer CIKs.
- Submission types: 83 `13F-HR`, 58 `13F-HR/A`, 21 `13F-NT`, 4 `13F-NT/A`.
- Filing dates lie in May–June 2013; reporting periods extend from 2009 through 2013.
- 85 submissions refer to `31-MAR-2013`; the other 81 refer to earlier periods.
- The 2013 Q2 archive represents submissions in that released collection, **not exclusively holdings as of the second quarter of 2013**.
- `CIK` identifies the filing manager, not automatically any portfolio security's issuer.

## Unknowns / questions

- How should original filings and subsequent amendments be linked?
- For historical holdings, which filing version is authoritative at a given point in time?
- How are `13F-NT` submissions related to other managers' holdings reporting?
- Does the archive contain all submissions received during that period, or only those within this published collection's coverage?

**Boundary:** A source-native identifier or observed key is not an approved enterprise business key.
