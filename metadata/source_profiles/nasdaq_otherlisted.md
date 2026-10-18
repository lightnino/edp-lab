# Source Profile — Nasdaq Other Listed Securities Directory

**Status:** Preliminary source observation; symbol equivalence is restricted to observed source-defined representations.

## Source and evidence

| Field | Observation |
| --- | --- |
| Source | Nasdaq Trader — Other Listed Securities Directory |
| Filename | `otherlisted.txt` |
| Repository RAW path | `data/raw/nasdaq/otherlisted.txt` |
| SHA-256 | `7f099cd61db347f2199251dfe45dc132ffc8c75bd68a91471c30e217e4265d3d` |
| Observed record count | 7,660 security records plus 1 file-creation metadata/footer line |
| Purpose | Directory of securities listed on exchanges other than Nasdaq, with exchange and symbol-format information |
| **Grain guess** | **One row appears to represent one other-exchange-listed security-directory entry in this file snapshot.** |
| Candidate identifiers | `ACT Symbol`, `CQS Symbol`, and `NASDAQ Symbol`: different market-data symbol representations appearing on each directory row |
| Date fields | No per-record date fields. File creation timestamp: `2026-10-15 03:03` (timezone not established) |
| Numerical measures | `Round Lot Size`; not a holdings quantity or market value |
| Source-specific terminology | `Exchange` codes; `CQS`; `ACT Symbol`; `NASDAQ Symbol`; `ETF`; `Test Issue` |

## Actual source records

| ACT Symbol | Security Name | Exchange | CQS Symbol | NASDAQ Symbol |
| --- | --- | --- | --- | --- |
| `A` | Agilent Technologies, Inc. Common Stock | `N` | `A` | `A` |
| `AAC.W` | Ares Acquisition Corporation III Warrants | `N` | `AAC.WS` | `AAC+` |
| `AAC.U` | Ares Acquisition Corporation III Units | `N` | `AAC.U` | `AAC=` |

## Confirmed observations

- 7,660 actual directory entries.
- Exchange distribution: `N = 2,905`, `P = 2,752`, `Z = 1,664`, `A = 314`, `F = 21`, `V = 3`, `M = 1`.
- `ETF = Y` on 4,479 records.
- Distinct symbol columns represent different naming conventions for the same directory row's instrument.
- For example, `AAC.W`, `AAC.WS`, and `AAC+` are three representations appearing in a single source record—not automatically three distinct securities.
- `Exchange = N` denotes NYSE in this directory.
- File creation time is snapshot-level metadata, not each security's listing effective date.

## Unknowns / questions

- What are the complete authoritative meanings of every `Exchange` code in this snapshot?
- Which downstream market-data/trading systems use each symbol convention?
- How should historical ticker changes and symbol reassignment be represented?
- What independent evidence is required to match these directory rows to SEC CUSIP holdings?
- How can point-in-time analysis be supported without historical listing start/end dates in this snapshot?

**Boundary:** The co-occurrence of symbols on a single directory row is source evidence for symbol representation, not authorization to infer canonical enterprise identity across other datasets or dates.
