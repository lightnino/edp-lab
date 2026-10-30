# TREASURY_FEEDS_V1 — C2000 source-scoped Vault contract

**Semantic status:** Owner approved as revised on 2026-10-25. This contract is not a signed protected grant. Applies only to the five frozen C2000 Treasury annual XML source instances and their five observed feed shapes.

## Identities and source relationship

- `H_TREASURY_FEED` uses the exact verified source-native Atom root `<id>` text plus feed scope. The five frozen feeds have distinct nonblank root IDs corresponding to yield curve, bill rates, long-term rates, real yield curve and real long-term average. This verifies identity in the frozen five-file scope; stability across future deliveries is not asserted. A missing, changed or ambiguous root ID blocks business promotion and escalates.
- `H_TREASURY_OBSERVATION` key is Feed HK + exact physical date field name and value (`NEW_DATE`, `INDEX_DATE` or `QUOTE_DATE` as present) + `RATE_TYPE` state and exact value **only where that field is physically applicable**. Date alone is insufficient in the long-term feed, which has three RATE_TYPE rows per date. Missing required identity components block business promotion while retaining the technical entry.
- `L_TREASURY_FEED_OBSERVATION` represents the feed-declared XML containment relationship. It does not join different feeds or infer tenor/economic equivalence.
- `S_TREASURY_ENTRY_ASSERTION` is multi-active by physical XML entry occurrence. Preserve every property, element order, namespace/path, exact text and missing-versus-empty state.

## History, lineage and acceptance

Keep source ID, RAW hash, XML entry path/ordinal, parser version, original field sequence and append-only source history. Do not use a technical entry identity as a Hub key, infer a business-effective interval, normalize rates, interpolate yields, align dates or overwrite entries. The five verified source files contain 1,743 entries and distinct 17/48/5/7/2-property schemas. The long-term file has 747 entries, three RATE_TYPEs on each of 249 dates; the date/type pair has no duplicate in that file. Optional IDs are absent in some entries. V3 must test missing date/type, repeated date, false cross-feed association, missing/empty tenor, lexical precision and namespace/entry-order fidelity. Evidence: `runs/day6-vault-pilot/family-d1-d5-profile-v2.json` SHA `356bf90e9fd0c230918fb6e30b6bbb3cb489abfa766772ca8a204d74f1834a50`.
