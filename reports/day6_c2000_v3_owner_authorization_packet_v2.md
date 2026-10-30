# Day 6 C2000 bounded V3 — final technical preparation and Owner boundary

This packet supersedes the execution-preparation portion of [V1](day6_c2000_v3_owner_authorization_packet_v1.md). The four source-family semantics and five contract pins in V1 remain approved and unchanged. Historical V0A–V3 receipts and the 127-row Step 2 prototype were not replayed or rewritten.

## Fixed scope and artifact pins

| Item | Exact prepared value |
| --- | --- |
| New population | 10 frozen sources, 2,047 selected DATA occurrences; existing 127 NUM occurrences reused only |
| Negative controls | 24 isolated in-memory oracles; none submitted as business facts |
| New targets | 23 `v3_` Delta tables in `workspace.edp_lab_day6_vault_proto`; existing eight tables read-only |
| Selection | `5b84f0a1dc088affc51f631bc34c66f0053b871b67efff13e770021a19a33259` |
| Negative oracle manifest | `54c2aa2add50504cca6a50beed480ef78fef96d962b7f9b6e6a4468ff34f72f2` |
| [Target DDL and insert-only SQL](../metadata/operating/day6_c2000_vault_v3_ddl_v1.json) | `9f92405043ddbe935bc9cf9518d31cb7d18a1b90da20f399519b4e39591ff7e1` |
| Built local wheel | `edp_lab-0.1.0-py3-none-any.whl`; SHA-256 `eada999db14a7db4b5590ab34b4296127e4231fe5289a04180bcf410238cafc9` |
| [Deployment proposal](../metadata/operating/day6_c2000_vault_v3_deployment_v1.json) | `2c5e3614c37d15aa2e03a879b6430f095e46820626aabcfddfa88bcc41d22001`; not installed |
| [Resource proposal](../metadata/operating/day6_c2000_vault_v3_resource_proposal_v1.json) | `9092012d96fcbfbeedc95b9b0bb70cc2d155888e6d50e3e32a1763a4b978d9f2` |
| [Bounded request](../metadata/operating/day6_c2000_vault_v3_bounded_request_v1.json) | `a3ddc0e95fae088a7b3b3dfb9b02826236cec487e0be460a691653ef450a39a8` |
| Unsigned approved semantic payload | `658612d41781f649f42529b9a3cdca34e9ab85d0a6fe7bb48a071fc2ff74f5df` |

The fixed Spark mapping reads version-0 accepted C300 M1 bindings/records for five SEC sources and version-0 N750 M1 XML properties for five Treasury feeds. It checks source/binding hashes, exact SEC row ordinals and lexical fingerprints, parent associations for selected PRE/13F children, Treasury entry counts, source-line/byte/property lineage, table allowlist, and one technical occurrence per selected row. It applies only the approved source-scoped Hub/Link/Satellite keys. The 24 isolated controls execute before writes. Target creation is fail-if-present and every data write is insert-only MERGE with zero automatic retry. The same job forms a readback candidate with Delta IDs, versions, history, exact-row SHA-256 comparisons, counts and per-source occurrence uniqueness. This candidate is **not** an independently signed protected readback.

## Compute and protected operation proposal

One existing-workspace serverless Python-wheel Job, one submission, one concurrent run, 3,600-second Job timeout, zero task retries, 23 new target tables, and no new Warehouse or cluster. The proposed planning exposure is **150 DBU / $60** using the published AWS Lakeflow Jobs Serverless **$0.40/DBU** price. [Databricks pricing](https://www.databricks.com/product/pricing/product-pricing/instance-types) supports that list-rate estimate. [Serverless compute management](https://docs.databricks.com/aws/en/compute/serverless/manage-serverless-compute) gives only directional sizing for rate-limited compute, and [billing records may lag](https://docs.databricks.com/aws/en/compute/serverless). Therefore this is an Owner spend-risk envelope, **not a live enforceable dollar cutoff**. The hard enforceable controls are one Job, a one-hour timeout, zero retries and exact table/row scope. The Owner may instead require a verified rate-limited compute object and a newly pinned configuration before approving execution.

The installed Vault V2 broker/policy covers eight tables and at most 1,000 rows; it does **not** authorize or execute this 23-table Spark V3 operation. The proposed V3 protected extension must remain separate and owner installed. It must verify the signed semantic document, exact wheel/request/selection/oracle/DDL hashes, a new operation-specific Owner authorization, protected service-principal and target permissions, durable one-shot reservation, actual Job run ID, timeout/unknown-status reconciliation, no replay, and independent UC table-ID/Delta-history/count/lineage readback. Only that protected verifier may sign the V3 successor receipt. The present repository code does not claim the V2 Broker/Executor path was tested for V3.

## Read-only validation and limits

The fixed code's 24 in-memory oracles, source adapters, exact DDL allowlist, key encoding and mapping tests pass locally. The wheel rebuilt twice with the same SHA-256. The read-only readiness checker confirms historical receipt and contract pins, the selection, DDL, wheel/deployment and resource pins. An initial Unity Catalog table metadata list returned the existing namespace, but a later metadata refresh was stopped by the Databricks profile's expired cached token. No login, credential rotation, Job submission or SQL statement followed. Live Spark read-only preparation, target-absence confirmation, service-principal permission inspection and Databricks throughput/DBU measurements remain protected preflight checks after Owner authority; they cannot be represented as passed now.

The local `check_day6_c2000_v3_readiness.py` result is `AUTHORIZATION_REQUIRED`: signed semantic envelope, operation grant, and owner-installed V3 protected extension are outstanding. The proposed wheel has **not** been uploaded or installed. Its local `/private/tmp` copy is a reproducible build artifact, not a durable deployment receipt.

## Exact Owner-controlled actions

1. Review the already approved semantic document and reviewed Git commit. In Owner Terminal, invoke `sudo .venv/bin/python scripts/owner_sign_day6_c2000_semantics_v1.py <reviewed-commit-SHA> 658612d41781f649f42529b9a3cdca34e9ab85d0a6fe7bb48a071fc2ff74f5df` from this repository. The script requires root, the exact clean commit and contract pins, the installed outside-worktree trusted policy, and an unused protected output path. It signs only the semantic `document`, verifies it with the installed public trust, and prints the signed envelope SHA-256. Codex must never invoke it or inspect the private key.
2. Separately approve or reject the exact bounded request and spend-risk envelope above, including the proposed serverless compute identity, protected V3 extension installation, 23-table DDL/write grant and independent signed readback. This is **not** an edit to the installed V2 standing policy and does not authorize Full V4 or V9. If a hard DBU/$ stop is required, select a verified rate-limited compute option and repin the proposal before execution.

No new Delta writes, grant issuance, protected installation, Full V4/V9 or Day 7 activity occurred during this preparation.
