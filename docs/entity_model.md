# Candidate entity model for Day 4

This is a bounded description of source observations and review questions, not an approved enterprise key or deployed identity model. The [existing candidate ERD](agent_v2_candidate_erd.md), [fixed input witnesses](../metadata/evaluations/agent_v2/inputs_v1.json), [proposals](../metadata/evaluations/agent_v2/proposals_v1.json), and [quality result](day4_step10_agent_v2_quality_regression.md) supply the details and locators. Every key and relationship below is **PROPOSED/UNRESOLVED**.

| Topic | Observed source role and candidate key question | Relationship, grain/time issue, approval |
| --- | --- | --- |
| MANAGER | 13F SUBMISSION and COVER report CIK/name in particular filing roles; ask whether namespace + CIK + role + validity could identify a source reporting party. | Manager-to-filing cardinality and Mirae USA/Hong Kong relation unresolved; no canonical merge. |
| FILING | Native accession and source snapshot identify source filing observations; accession prefix cannot supply manager CIK. | Filing-to-holding is observed as repeated native rows; amendment precedence and cross-source link unresolved. |
| ISSUER | FSDS registrant CIK and 13F NAMEOFISSUER are separate contexts. | Issuer-to-security and manager/issuer role distinctions unresolved; names alone do not join. |
| SECURITY | Holdings carry CUSIP/class; FIGI can be blank. | Multiple occurrences share CUSIP without deduplication; temporal security identity unresolved. |
| LISTING | ACT full symbols `AAC.U` and `AAC.W` are distinct source listing observations. | Full symbol, venue and validity are candidate qualifiers; stem equality does not link listings. |
| IDENTIFIER | CIK, CUSIP, accession, FIGI and ACT symbol are different namespaces with literal tokens and source locators. | Token assignment to subjects and valid times unresolved; no cross-namespace canonical key. |
| HOLDING | 13F INFOTABLE rows have distinct accessions, INFOTABLE_SK and physical locators. | Holding grain is source occurrence; CUSIP equality never collapses rows or creates a position. |
| REPORTING_PERIOD | 13F period, filing date, FSDS ddate/qtrs and Treasury daily date are source-specific time roles. | Shared date text does not prove same business period or grain; normalization unresolved. |

Possible MANAGER→FILING, FILING→HOLDING, HOLDING→SECURITY, SECURITY→ISSUER/LISTING and IDENTIFIER→subject links are review questions. No cardinality is approved beyond exact native observations. The [editable diagram](../models/enterprise_erd.md) displays them as unresolved edges. The [crosswalk CSV](../metadata/entity_crosswalk.csv) records native-token/occurrence decisions without semantic promotion.
