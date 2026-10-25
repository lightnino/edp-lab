# Day 6 C2000 — bounded V3 Owner authorization packet V1

**Current state:** Owner approved four revised source-family *business semantics* on 2026-10-25. No new Delta write, grant, runtime deployment or compute expenditure is authorized. The completed V0A/V0/V1 receipts and historical V2/V3 `PARTIAL` receipts remain byte-for-byte unchanged. [Additive successor record](../metadata/evaluations/day6_c2000_vault_semantic_successor_v1.json) pins their hashes and cannot become V2 PASS until the trusted Owner signature is verified; V3 cannot PASS until actual bounded live evidence exists.

## Approved semantic contract pins

| Version | Contract SHA-256 | Approved model |
| --- | --- | --- |
| Existing `VAULT_LOAD_CONTRACT_V1` | `681c3f6a9a4446b5357c3ab6c6534e6fd5b8cf944f967ea9ab27dcc2c8b5aabe` | FSDS `num.txt`; unchanged |
| [`FSDS_OTHER_V1`](../docs/vault_contracts/fsds_other_v1.md) | `99eeee6d28189512fb6d1a978493cc5ef3d0a50e57bc2b6d3e78a8f974c89035` | exact Filing/Concept, complete-context Presentation Link, three multi-active assertion Satellites |
| [`EDGAR_MASTER_V1`](../docs/vault_contracts/edgar_master_v1.md) | `84871b7e126adfac1eb8c514ad5845c2c4cfe5f8d2c936b3887bb0d90132f8fd` | exact File Name Hub and occurrence assertion; CIK literal; no Link |
| [`SEC_13F_V1`](../docs/vault_contracts/sec_13f_v1.md) | `7e35c24bd3592ef571b8e9baffe921386046951f74ebb54c396ae7fa46ac682b` | exact accession Submission Hub, seven member Satellites; no member Business Link |
| [`TREASURY_FEEDS_V1`](../docs/vault_contracts/treasury_feeds_v1.md) | `75f8bbae9c7b3b875262fb47b2685d5093d9d8cf9b18a156639e74b774017a51` | verified source-native Feed and feed/date/type Observation Hubs, containment Link and entry Satellite |

The [unsigned Owner semantic document request](../metadata/authorizations/day6_c2000_full_semantics_owner_decision_v1.unsigned.json) pins those exact contracts and the frozen C2000 roster/bindings. SHA-256 `658612d41781f649f42529b9a3cdca34e9ab85d0a6fe7bb48a071fc2ff74f5df`. It transcribes the Owner's decision but **has no signature** and is deliberately not an accepted `verified_document` envelope. The Owner-controlled issuer must sign the canonical `document` payload using the existing trusted mechanism and place the signed envelope where the protected verifier can read it. No Agent-generated signature or repository file can substitute. A material contract change requires a new Owner decision and new pin.

## Exact V3 population and tests

The [selection manifest](../metadata/evaluations/day6_c2000_vault_v3_selection_v1.json), SHA-256 `5b84f0a1dc088affc51f631bc34c66f0053b871b67efff13e770021a19a33259`, first verified each selected RAW file against frozen C2000 SHA-256, then pinned source/member and inclusive DATA row ordinal selection plus a lexical selection fingerprint. It authorizes no read or write by itself. The frozen bindings SHA-256 is `2a72b8f8483e2181a3112a26b5d68d702b92308def6e74978838b155cfd85312`.

| Source selection | DATA rows | Purpose |
| --- | ---: | --- |
| `SRC000005`, `SRC000054`, `SRC000064`: first 16 rows of each `sub.txt`, `tag.txt`, `pre.txt` | 144 | three accepted version/shape witnesses; new FSDS members only |
| `SRC000065`: first 16 rows of each of seven 13F TSV members plus the 30 unique Submission parent rows referenced by selected child rows | 142 | all member assertion shapes and verified parent associations |
| `SRC000107`: first 16 EDGAR DATA rows plus duplicate witness ordinals **437, 438** | 18 | exact file-reference and duplicate multiplicity |
| `SRC010451`–`SRC010455`: every frozen XML entry | 1,743 | all five feed property shapes, missing fields and three RATE_TYPEs/date |
| **Total** | **2,047** | 10 physical sources; no FSDS NUM reload |

The [24 isolated negative oracles](../metadata/evaluations/day6_c2000_vault_v3_negative_oracles_v1.json), SHA-256 `54c2aa2add50504cca6a50beed480ef78fef96d962b7f9b6e6a4468ff34f72f2`, cover duplicate preservation, missing identity/parent association, lexical state, false cross-family joins, rate-type/date grain and high fanout. They are controlled fixtures, never admitted as source business facts. Some test cases must **preserve** an odd but valid source assertion; quarantine is only for invalid association/identity outcomes. The accepted historical 127 NUM rows and six Step 2 negatives are reused as baseline evidence, not replayed.

## Proposed bounded execution and readback

The [machine-readable V3 request](../metadata/operating/day6_c2000_vault_v3_bounded_request_v1.json) requests only the existing namespace `workspace.edp_lab_day6_vault_proto`, **23 new `v3_` tables** (isolated from all eight existing prototype tables), one protected Databricks Spark Job on existing workspace serverless Jobs compute if verified available, at most 2,048 source DATA rows, 24 isolated fixture rows, 3,600 seconds and zero automatic retry. No new Warehouse, RAW change, frozen C2000 change, Day 5 rerun, Full V4 or V9. The 23-table allowlist is exact in the request; all existing eight Vault tables are read-only. New DDL and rows require the separate signed V3 authority.

The job must verify the signed semantic record, frozen roster/source/member hashes, selected row ordinals and lexical fingerprints, exact approved M1/M2/view versions and source line/byte lineage before promotion. It must validate all Hub key components and parent associations, retain invalid physical occurrences without fabricated business keys, and write only insert-only/idempotent selected rows to the `v3_` allowlist. It must independently read back every new table's UC ID, Delta version/history, persisted row count and selected occurrence/field/key/relationship checks. The protected ledger reserves the operation before submit, records the actual Jobs run and SQL/Delta operation IDs, and treats timeout or unknown write status as `UNCERTAIN_REQUIRES_READBACK`; no blind retry. Material key, cardinality, source or lineage failures are Owner escalations, not auto-changed mappings. Historical 127-row prototype remains unchanged.

**Resource evidence and limit:** preparation rehashed only the 10 selected RAW objects and selected 2,047 rows; local selection completed in 0.13 seconds in this environment. This is *not* a Databricks throughput/DBU benchmark. The proposed one-job/one-hour cap limits exposure, but DBU/$ remains unmeasured; the Owner must approve a specific compute configuration and maximum spend before the protected issuer signs. The existing Vault V2 policy forbids full C2000 writes and its eight-table/1,000-row scope does not authorize this V3 job.

**Final pin required before execution approval:** the [request](../metadata/operating/day6_c2000_vault_v3_bounded_request_v1.json) currently has `runtime_artifact_sha256`, `deployment_sha256` and `protected_grant_id` set to `null`. No pinned Spark loader/deployment has been installed or demonstrated. The protected issuer must receive the reviewed exact runtime/deployment hashes and approve that fixed payload before any V3 write. Until those pins and a signed grant exist, this is a bounded execution *proposal*, not a runnable protected operation. This missing implementation/installation is a technical readiness gap, not a request to waive a control.

Local, read-only readiness command: `PYTHONPATH=src:. .venv/bin/python scripts/check_day6_c2000_v3_readiness.py`. It verifies the preserved historical receipt hashes, contract pins and selection, then lists missing protected inputs. It never submits a Job or writes Delta.

## Exact Owner decisions still required

1. Have the existing Owner-controlled issuer produce the signed semantic envelope for the pinned five-contract `document`, without adding write authority to that semantic record.
2. After reviewing the final fixed Spark runtime/deployment hashes and target DDL, authorize **only** this 10-source, 2,047-DATA-row, 24-fixture, 23-table V3 job with the stated one-run/one-hour/zero-retry bounds, compute identity/configuration and explicit DBU/$ ceiling. Authorize the independent protected readback receipt for this V3 scope. No standing V2 policy edit or Full V4 authority follows.

The runner now recognizes additive `v2-successor-v1.json` and `v3-successor-v1.json` receipts only when each pins its unchanged historical predecessor SHA-256. V2 successor `PASS` requires the exact Owner-signed semantic document; V3 successor `PASS` requires a separate protected-verifier signed live readback covering all 10 sources, 23 tables, 2,047 selected DATA rows, all 24 negative oracles and an unchanged historical prototype. The durable checkpoint pins successor hashes on resume. Historical receipts are never rewritten. V4/V9 remain outside this request.
