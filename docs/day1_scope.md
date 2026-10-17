# Day 1 scope

Manual observations exist for four source tables/views: SEC `SUBMISSION.tsv`, SEC
`INFOTABLE.tsv`, Nasdaq `nasdaqlisted.txt`, and Nasdaq `otherlisted.txt`.

Verified source bytes / expected hashes are in `metadata/source_inventory.csv`.
`corpus_manifest.csv` is header-only intentionally: freeze cohorts only after
human specification. No enterprise business-key or entity-resolution rules.

SEC 2013 Q2 is a filing dataset and can reference earlier report periods.
The uploaded Nasdaq security directory files were generated 2026-10-15 03:03
(unknown timezone). Do not presume contemporaneous history.
