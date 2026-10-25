# FSDS_OTHER_V1 — C2000 source-scoped Vault contract

**Semantic status:** Owner approved with specified revisions on 2026-10-25. This text is a versioned transcription of that decision, not a signed protected authorization or permission to write Delta. Applies only to `sub.txt`, `tag.txt`, and `pre.txt` in the 60 frozen C2000 SEC FSDS source instances. The approved [`num.txt` Contract V1](../vault_load_contract_v1.md) is unchanged.

## Identities and relationship

- Reuse `H_FILING` at `(SEC_FSDS, exact adsh)` and `H_CONCEPT` at `(SEC_FSDS, exact tag, exact version)`. TAG uses the same source-native Concept reference as NUM. No CIK/name Hub, issuer equivalence, taxonomy version merge or amendment winner follows.
- `L_FSDS_PRESENTATION` key is Filing HK + Concept HK + ordered dependent context `report,line,stmt,inpth,rfile`, with each field's physical state and exact lexical value. A missing/invalid reference blocks the business association while its technical occurrence remains retained. A plain Filing–Concept Link loses presentation multiplicity and is outside this contract.
- `S_FSDS_SUB_ASSERTION`, `S_FSDS_TAG_ASSERTION`, `S_FSDS_PRE_ASSERTION` are occurrence-anchored and multi-active. SUB/TAG associate with their respective Hub; PRE associates with the complete Presentation Link when source references validate. Every physical DATA occurrence, including exact duplicates, remains separate.

## Payload, history and lineage

Keep every ordered source field and physical state: SUB 36 fields, TAG 9, PRE 10. Keep source instance, frozen RAW ZIP SHA, exact member, member SHA when established, source line, byte interval, parser version, physical occurrence key and load event. Technical occurrence identity is never a Business Key. Use append-only delivery history; source filing/acceptance dates and PRE line/report text remain lexical source attributes. No inferred effective interval, DISTINCT, conflict winner or overwrite. Changed payload at an existing occurrence is an integrity failure.

## Acceptance and evidence

The frozen profile counts 414,990 SUB, 4,617,832 TAG and 43,717,018 PRE rows across 60 hash-verified ZIPs, zero width errors. The complete historical SUB inventory found 414,990 distinct nonblank accessions. In the three already accepted prototype ZIPs, a bounded probe covered 1,776,145 PRE rows and found no SUB/TAG orphan or complete-context collision within a ZIP. These observations do not establish global uniqueness or grant V3 execution.

V3 must test exact duplicate retention, changed TAG label, PRE context/label collision, missing SUB/TAG reference, state-aware context keys, embedded TAB parsing and replay. A material key or cardinality failure escalates to Owner; it does not change this contract automatically. Evidence: `runs/day6-vault-pilot/fsds-other-member-counts-v1.json` SHA `9902a600301c372f4bb88c04b713c0a935194b793a6e0d9da0328c6cd5ba0ef7`; `runs/day6-vault-pilot/fsds-relationship-probe-v1.json` SHA `a497a07320dc5322b245c82fe44c91534dd6f5c68b9a0efb3204bf329a7334a0`.
