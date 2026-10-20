# Whole Lab physical source corpus tooling

The user authorized organization of six existing local datasets followed by
discovery/acquisition from SEC, Nasdaq, US Treasury, ECB, CFTC and NYC TLC, targeting
more than 3,000 verified eligible physical deliveries. Requested expansion sizes are
300, 700, 1500, 2000 and 3000. Earlier frozen contracts and historical cohort labels
remain unchanged. This work does not automatically admit sources, approve parsers,
or freeze cohorts; those explicit earlier boundaries remain in force.

## Local availability

`runs/local_inventory/availability.json` is a local, versioned physical-availability
inventory, separate from the pinned twelve-column admitted manifest. It holds the
four existing GOLD deliveries and two existing, unadmitted bulk dataset candidates.
Each physical representation records its exact location, bytes, SHA-256, integrity
observations, original path and available provenance. Unknown publisher receipt,
edition and acquisition time remain unknown. A directory has a child-file inventory
and inventory hash; it is not assigned a fabricated original ZIP hash. Invalid
archives and interrupted inventories are retained as failures, not counted as data.

Organization receipts and exact operational findings live alongside that inventory
outside Git. Source moves use exclusive same-volume renames and preserve inode and
bytes; existing verified GOLD destinations are reused without overwriting them or
deleting the user's separate Downloads copies. Cross-volume transfers are checked
for headroom and withheld by the move primitive pending a verified-copy operation.

`local_sources.local_match` verifies retained bytes before reuse. A publisher URL or
period label alone cannot establish an immutable edition. A known local delivery
slot without a matching expected hash blocks duplicate downloading; it does not
silently treat a mutable current endpoint as a historical copy. A changed expected
hash requires separately evidenced publisher-edition metadata. New editions retain
separate candidate/receipt/storage references. Both downloaders consult the local
inventory and retained Whole Lab deliveries before requesting a known edition.
The C300 command accepts an alternate local inventory with `--local-inventory`.

## Discovery and acquisition

```bash
.venv/bin/python -m edp_lab.ingestion.whole_lab discover
.venv/bin/python -m edp_lab.ingestion.whole_lab download --limit 3015
.venv/bin/python -m edp_lab.ingestion.whole_lab report
# After acquisition finishes, organize without copying or editing receipts:
.venv/bin/python -m edp_lab.ingestion.whole_lab organize
# Offline unified inventory and draft nested candidate selections:
.venv/bin/python -m edp_lab.ingestion.whole_lab packet
```

Acquisition evidence is retained in gitignored `runs/whole_lab/`. The offline
`organize` command moves verified payloads by exclusive same-volume rename into
`data/raw/<publisher>/<family>/<delivery-candidate-id>/`, retaining receipts and
separate hash-checked relocation audits. Failed/partial attempts stay in the
evidence directory. Offline verification and download resumption follow those
audits and rehash the final bytes; moving a file never manufactures a new delivery.
Delivery candidate references include the discovery plan and actual payload hash;
updated editions get separate paths. They are not admitted Source Instance IDs.
The `packet` command combines these deliveries with the six existing local dataset
slots and emits a content-addressed review inventory. Its nested candidate
selections are explicitly unadmitted and unfrozen, with missing/equal-hash inputs
shown as blocked rather than silently replaced. Discovery preserves two SEC
catalog pages, quarterly machine-readable directory listings and the other five
publishers' official documentation/catalog pages. Its versioned candidate plan
records each physical URL, edition label, publisher and discovery reference, plus
content hashes and retrieval failures. An existing candidate plan is reverified and
reused, never silently regenerated. New discovery populations require a separate
run directory; historical plans and receipt evidence stay available.

Selection reuses the approved 60 FSDS / 42 13F / 198 daily-index C300 population,
then adds publisher-native ECB reference-rate ZIP, closed-year CFTC ZIP releases,
2025 January–March TLC Parquet releases, five Treasury 2025 annual XML exports,
an additional Nasdaq directory product, and actually listed historical SEC daily
master-index deliveries. No guessed trading dates or archive members are counted.
Treasury responses are complete documented annual exports, not arbitrary API pages.
Catalog snapshots/documentation are supporting evidence, outside the delivery count.

Official entry points:

- [SEC catalogs and directory documentation](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- [Nasdaq directory definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs)
- [Treasury XML exports](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed)
- [ECB reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
- [CFTC historical compressed reports](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm)
- [NYC TLC monthly releases](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)

The client uses macOS curl with normal certificate verification; TLS verification
is never disabled. SEC identification uses explicit `SEC_USER_AGENT` or the actual
configured Git email; other publishers receive only the application identifier.
Contacts, response headers and operational receipts stay outside Git. The client
uses up to three workers sharing a three-initial-request-per-second limiter,
below SEC's published maximum. The retained initial operational daily-tail run
documents its disjoint selection and aggregate bound; subsequent resumptions
use the single shared limiter.

Each attempt retains its exact body, HTTP headers, transfer metadata, actual UTC,
curl outcome, publisher URL and SHA-256. Incomplete bodies are never resumed by
concatenation, published as successes or used to manufacture instances. New retries
get separate attempt paths. Transport/5xx retries are bounded; 403/429 blocks that
publisher within the invocation. HTTP/1.1 and a low-speed timeout address observed
transport stalls without changing publisher content or weakening certificate checks.

Successful candidate evidence includes a hash-linked receipt and body, ZIP CRC and
member hashes where applicable, Parquet magic checks, or nonempty Treasury XML
structure. These are mechanical physical/format checks, not reviewed source parsers.
Exact old source NULL semantics, GOLD parsing rules and all historical evidence
remain untouched. API record counts, ZIP members, packaging sidecars and repeated
references to the same URL never increase the physical-delivery count.

## Review and cohort boundaries

A discovered URL is not an acquired physical delivery. A verified body is not an
admission or semantic approval. Review evidence must distinguish these counts and
retain failures, equal-hash groups and unresolved provenance. Local bulk packages
with unknown original publisher identity remain unadmitted even when their bytes
and ZIP integrity pass. They are not claimed as independently authenticated SEC
archive deliveries.

The existing manifest, GOLD rosters and parser freezes remain immutable. The approved
future separate-manifest approach preserves their hashes. No `SRC######` is allocated
by these tools. Requested cohort sizes describe candidate-selection plans only until
actual membership/evidence and admission/freeze authority have been reviewed. The
approved C300 population must remain the initial scope; missing or difficult inputs
cannot be silently replaced. Larger reviewed cohorts must contain every prior member.

Use local run reports for actual measured counts, hashes, failures and storage;
this document makes no claim that a planned count has completed acquisition.


The active physical inventory is referenced by
`runs/whole_lab/active-inventory.json`. Layout v2 inventory, SHA-256 verification,
and the complete old-path to new-path mapping are in `runs/whole_lab/layout-v2/`.
Original acquisition receipts, delivery records, v1 inventory and review packets
remain historical evidence. The downloader follows the append-only
`publisher-relocations/` audits, verifies their linkage to earlier relocation
records and rehashes bytes before reuse. No network is needed to resume a fully
available plan. Existing destinations are rejected; interrupted moves resume
from their prepared audit. Family directories use the recorded family label;
immutable delivery directories include plan, URL and actual source SHA-256.
The four GOLD paths and two existing SEC bulk ZIP paths are unchanged.
