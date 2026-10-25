# EDGAR_MASTER_V1 — C2000 source-scoped Vault contract

**Semantic status:** Owner approved as revised on 2026-10-25. This contract is not a signed protected grant. Applies only to the 1,893 frozen C2000 SEC EDGAR daily master source instances with the observed five-field physical schema.

## Identity and assertion

- `H_EDGAR_FILE_REFERENCE` Business Key is `(SEC_EDGAR_DAILY_MASTER, exact File Name)`. This is a source-native file reference, not a Filing/Issuer/Security identity. Missing or invalid File Name blocks Hub promotion but retains the technical occurrence. No invented reference is substituted.
- `S_EDGAR_INDEX_ASSERTION` is occurrence-anchored and multi-active, preserving all five original fields (`CIK`, `Company Name`, `Form Type`, `Date Filed`, `File Name`) and every duplicate physical row. CIK remains literal source payload, never an Issuer Hub key under V1.
- There is **no `L_EDGAR_INDEX_LISTING` Business Link** in V1. No cross-family join, repeated-path winner or date-derived precedence is authorized.

## History, lineage and acceptance

Retain exact row bytes/lexical fields, original order, source ID, RAW hash, source line/byte interval, parser version, technical occurrence and append-only delivery history. Date Filed is retained as source text. Character decoding must preserve input bytes; no case fold, trim, normalization, DISTINCT or overwrite. A changed RAW hash or replay payload blocks load.

The complete read-only profile observed 7,940,373 DATA rows and zero five-field width failures. Within files, 104,731 rows repeat an exact earlier row and 101,140 distinct File Name values recur. V3 must demonstrate their occurrence multiplicity and test missing/invalid path, leading-zero CIK, changed company name, false cross-family linkage and byte-safe decoding. Source-null or enterprise identity interpretation requires separate approval. Evidence: `runs/day6-vault-pilot/family-d1-d5-profile-v2.json` SHA `356bf90e9fd0c230918fb6e30b6bbb3cb489abfa766772ca8a204d74f1834a50`.
