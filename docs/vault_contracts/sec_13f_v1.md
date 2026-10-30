# SEC_13F_V1 — C2000 source-scoped Vault contract

**Semantic status:** Owner approved as revised on 2026-10-25. This contract is not a signed protected grant. Applies only to all seven TSV members in the 42 frozen C2000 SEC 13F ZIP deliveries.

## Identity and member assertions

- `H_13F_SUBMISSION` key is `(SEC_13F, exact ACCESSION_NUMBER)`. No FSDS/EDGAR filing equivalence, CIK issuer identity, security canonicalization or amendment winner is implied.
- Seven separate multi-active assertion Satellites correspond exactly to `SUBMISSION`, `COVERPAGE`, `INFOTABLE`, `OTHERMANAGER`, `OTHERMANAGER2`, `SIGNATURE`, `SUMMARYPAGE`: `S_13F_SUBMISSION_ASSERTION`, `S_13F_COVERPAGE_ASSERTION`, `S_13F_INFOTABLE_ASSERTION`, `S_13F_OTHERMANAGER_ASSERTION`, `S_13F_OTHERMANAGER2_ASSERTION`, `S_13F_SIGNATURE_ASSERTION`, `S_13F_SUMMARYPAGE_ASSERTION`. Each assertion grain is `(submission_hk, member_type, technical_occurrence)`, using a validated source-native accession reference. The technical occurrence remains retained when parent association is missing or ambiguous; do not manufacture a Submission Hub.
- There is **no `L_13F_MEMBER_ASSERTION` Business Link** in V1. Member source-native SKs are lexical payload/lineage, not assumed cross-delivery Business Keys.

## Payload, history and acceptance

Preserve every member column, original lexical identifier (including padding/leading zeros), source row order, ZIP/member hashes, source ID, member/line/byte locator, physical state, parser version and append-only delivery history. Source filing/report dates and amendment flags remain literal; no winner, holdings aggregation, cross-period alignment, DISTINCT or overwrite.

All 42 hash-verified ZIPs have the same seven member headers and total 88,398,060 DATA rows. Three deep ZIP probes found no duplicate SUBMISSION accession or INFOTABLE_SK within those ZIPs and no INFOTABLE orphan, but global uniqueness is unproven; submission fanout reached 64,943 INFOTABLE rows. V3 must test all seven member associations, missing/ambiguous parent, duplicate member payload, blank FIGI, identifier padding and high fanout. A material relationship/cardinality mismatch requires Owner escalation. Evidence: `runs/day6-vault-pilot/13f-member-counts-v1.json` SHA `2e497f0a431a906ab0a6e92a72dbd151a25d5e4e919fb9aad106bd00895300af`; three deep profiles are in `runs/day6-vault-pilot/family-d1-d5-profile-v2.json` SHA `356bf90e9fd0c230918fb6e30b6bbb3cb489abfa766772ca8a204d74f1834a50`.
