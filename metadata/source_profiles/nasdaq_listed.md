# Source Profile — Nasdaq Listed Securities Directory

**Status:** Preliminary source observation; the snapshot does not establish historical listing validity.

## Source and evidence

| Field | Observation |
| --- | --- |
| Source | Nasdaq Trader — Nasdaq Listed Securities Directory |
| Filename | `nasdaqlisted.txt` |
| Repository RAW path | `data/raw/nasdaq/nasdaqlisted.txt` |
| SHA-256 | `1d3656d26cfddd35363ce8022d50cbb5342ae2b1cfebee74f3c3b168b0f0f808` |
| Observed record count | 5,629 security records plus 1 file-creation metadata/footer line |
| Purpose | Directory of Nasdaq-listed securities with symbols, names, and listing/trading-related attributes |
| **Grain guess** | **One row appears to represent one Nasdaq-listed security-directory entry in this file snapshot.** |
| Candidate identifiers | `Symbol`: Nasdaq listing-symbol representation; `Security Name` is descriptive, not a demonstrated permanent unique identifier |
| Date fields | No per-record date fields. File creation timestamp: `2026-10-15 03:03` (timezone not established) |
| Numerical measures | `Round Lot Size`: trading-unit parameter, not a security valuation or holdings measure |
| Source-specific terminology | `Market Category` Q/G/S; `Financial Status` N/D/E/H; `Test Issue`; `ETF`; `NextShares` |

## Actual source record

| Symbol | Security Name | Market Category | Financial Status | Round Lot Size |
| --- | --- | --- | --- | ---: |
| `AAPL` | Apple Inc. - Common Stock | `Q` | `N` | 40 |

## Additional observed instrument types

| Symbol | Security Name / type |
| --- | --- |
| `AACI` | Armada Acquisition Corp. III — Class A Ordinary Share |
| `AACIU` | Armada Acquisition Corp. III — Units |
| `AACIW` | Armada Acquisition Corp. III — Warrant |

## Confirmed observations

- 5,629 directory entries, including common shares, ETFs, ADRs, units, warrants, and other security types.
- Market Category: `G = 2,514`, `S = 1,671`, `Q = 1,444`.
- Financial Status: `N = 5,286`, `D = 316`, `E = 21`, `H = 6`.
- `ETF = Y` on 1,296 records.
- The directory contains `Test Issue = Y` entries.
- Observed `Round Lot Size` values include 100, 40, and 10; 100 is not universal.
- File creation time describes the snapshot artifact, **not** the listing start/effective date of every security.
- One issuer can have separate directory entries for different instrument types; these are not interchangeable securities.

## Unknowns / questions

- When did each security first list? Did its symbol change over time?
- During which historical interval was each directory entry valid?
- What independent evidence links a Nasdaq symbol to a SEC CUSIP?
- Does the source identify issuers independently from the displayed security name?
- How should test issues and non-common-stock instruments be treated in later analysis?

**Boundary:** A 2026 snapshot does not establish the 2013 listing status of a security mentioned in a 2013 filing.
