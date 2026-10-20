# C300 candidate preparation and acquisition

The user approved the candidate population (60 FSDS + 42 Form 13F + 198 SEC daily
indexes), the minimum admission policy, and a separate versioned manifest. The
subsequent instruction authorizes acquisition tooling and candidate preparation;
it explicitly withholds automatic admission, parser approval and C300 freezing.
Approval identity/timestamp were not supplied and are not invented here. The
historical proposed-policy document and all frozen GOLD artifacts remain unchanged.

## Approved selection

| Family | Physical deliveries | Selection |
| --- | ---: | --- |
| SEC_FSDS | 60 | Every quarter, 2011 Q1 through 2025 Q4 |
| SEC_13F | 42 | Every quarter, 2013 Q3 through 2023 Q4 |
| SEC_EDGAR_DAILY_MASTER | 198 | Earliest 198 actually listed `master.2023MMDD.idx` files, ordered by date across all four 2023 quarter directories |

Publisher catalogs:

- <https://www.sec.gov/dera/data/financial-statement-data-sets.html>
- <https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets>
- `https://www.sec.gov/Archives/edgar/daily-index/2023/QTR{1..4}/index.json`

All 300 are proposed REAL physical deliveries. One ZIP counts once, regardless of
member/record count. Documentation, HTTP receipts and directory listings are
supporting evidence, outside the 300. Candidate IDs (`CAND0001` etc.) are local
work-list references, never admitted `SRC######` identities. No GOLD input is reused.

## Commands and effects

Use the installed environment; no dependency synchronization is needed. All output
is confined to gitignored `runs/c300/`. A directory may be supplied with
`--directory`; relative paths resolve against `--root` (default: current directory).

```bash
# Offline: retain the approved acquisition specification; no invented discoveries.
.venv/bin/python -m edp_lab.ingestion.c300_acquisition spec

# Set SEC_USER_AGENT locally to the actual operator name/organization and email.
# No placeholder identity is sent. Do not commit this contact or put it in source.

# Network: retrieve only two catalog pages and four directory listings.
.venv/bin/python -m edp_lab.ingestion.c300_acquisition prepare

# Offline: rehash discovery evidence and report candidate/acquisition status.
.venv/bin/python -m edp_lab.ingestion.c300_acquisition report
```

`prepare` resolves ZIP links from the actual captured catalogs, requires every
expected quarterly edition, and selects daily files from the actual listings.
It does not download any of the 300 payloads. Missing editions, too few daily
entries or ambiguous links stop preparation with evidence retained. It never
substitutes another edition. The resulting `candidates.json` includes a version,
content hash, tool-content hash, runtime version and hash-linked discovery receipts.
An existing plan is verified offline and reused, never overwritten or rediscovered.

The SEC requests an identifying User-Agent and limits scripted traffic; see
<https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data>.
The client uses one process and at most one request per second including redirects.
Run a single invocation at a time; this limiter is not shared across processes.
Receipt evidence includes the actual contact and stays outside Git.

The following command exists for a later explicit payload-acquisition instruction;
it is not part of candidate preparation:

```bash
.venv/bin/python -m edp_lab.ingestion.c300_acquisition download
# Optional operational batch bound: --limit 1 (or another positive number).
```

Each request attempt gets a unique directory containing the response body and a
versioned receipt with requested/final URL, actual UTC timestamps, response headers,
status, length and hashes. Failed/partial responses remain retained. Retries are
bounded (three attempts) for transport failures and HTTP 500/502/503/504, with
backoff. HTTP 403/429 stop immediately; no bypass or proxy fallback is attempted.
Requests use identity content encoding, require HTTP 200 and check Content-Length
when supplied. SHA-256 is measured while streaming and independently recomputed
after closing the file. No upstream authenticated checksum is claimed.

Downloads never concatenate partial attempts. Completed, hash-verified candidates
are skipped on resumption; changed retained bytes stop the operation instead of
silently triggering a replacement. ZIP inspection streams all file members,
checks CRC through the ZIP reader, records member index/name/size/SHA-256 and does
not extract or parse them. Even duplicate/path-like member names are inventoried
by occurrence without writing them to disk. Member hashes never create sources.
Non-ZIP payloads are screened for empty/HTML error bodies; that is not parser
validation. Inspection failures retain the original response and a failure record.

`report` rehashes acquisition/discovery evidence and verifies stored ZIP inventories.
It reports pending candidates, acquired byte totals, failed requests, inspection
failures and equal-hash groups needing delivery-evidence review. Acquisition is
not admission or proof of source semantics. A changed remote edition remains a
new attempted receipt; it never overwrites previous bytes or the candidate list.

Plan approximately 7–8 GB of payloads and reserve 20 GB for acquisition/retries.
These remain estimates until measured; the report provides actual acquired bytes.
ZIP inventories expose exact uncompressed sizes for later resource planning.

## Preserved boundaries and later work

The tooling writes no RAW path, corpus manifest, source ID, logical-table registry,
parser binding, admission timestamp or C300 roster. It emits NOT_ADMITTED,
NOT_APPROVED and NOT_FROZEN explicitly. Candidate preparation is not cohort freezing.

The accepted separate-manifest approach is necessary because the GOLD_V2 parser
freeze pins the existing manifest hash. Future admission tooling must create a
new versioned twelve-column manifest with unchanged copies of the old four rows,
plus reviewed new admissions; the existing manifest remains untouched. The current
source validator's fixed registry path must be addressed in that later tooling.
This implementation deliberately contains no admission command.

Future parser work needs separately reviewed snapshot bindings for FSDS/13F and
a daily-index profile covering preamble/header/separator accounting. Current GOLD
snapshot authority does not transfer. Preserve exact text and occurrences; leave
source NULL semantics unresolved. Admission, parser approval and cohort freezing
remain separate actions requiring their actual evidence and authority.

Offline tests use clearly synthetic publisher responses and payloads. They do not
establish real C300 downloads, membership, parser validation or execution.
