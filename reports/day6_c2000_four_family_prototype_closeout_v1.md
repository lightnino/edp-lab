# Day 6 four-family Vault Prototype: scoped closeout decision

**Owner scope change, 2026-10-25:** Day 6 now targets only the four-family prototype. Full C2000 Vault integration is no longer a Day 6 requirement. The approved C2000 roster and earlier 2,000-source inventory remain historical evidence and upstream identity pins; they do not require a 2,000-source V4 load or full-population V9 claim. This is an execution-scope reduction, not a new business-semantic decision or a protected write grant.

## Population and reuse

The bounded [V3 request](../metadata/operating/day6_c2000_vault_v3_bounded_request_v1.json) selects 2,047 physical DATA occurrences from 10 frozen sources: three SEC FSDS witnesses, one SEC 13F source, one EDGAR daily master, and five Treasury XML feeds. It targets exactly 23 new `v3_` tables in `workspace.edp_lab_day6_vault_proto` with 24 isolated negative controls. Reuse the accepted 127-row FSDS NUM Delta prototype and its six historical negatives; do not reload them. The existing eight tables remain read-only. The [Free Edition Owner packet](day6_c2000_v3_free_edition_owner_packet_v3.md) owns the current exact request and hash pins. The Owner-approved five contract pins and signed semantic document must be verified through protected trust; the unsigned repository copy is not proof of signing.

## Applicable stage exit for this scope

| Stage | Required proof for the four-family prototype | Current verified state |
| --- | --- | --- |
| V0A, V0, V1 | Reuse accepted infrastructure, frozen source identity, prior prototype and 2,000-source inventory as context | Historical evidence reusable; V2 installed policy does not cover 23 new tables |
| V2 | Five approved contract hashes and Owner-signed semantic receipt verified against protected public trust | Contract hashes pinned; root-only signed receipt awaits independent read-only verification in this session |
| V3 | One bounded live Delta result for all 2,047 selected rows, 24 negatives, 23 table IDs/versions/history/lineage and unchanged 127-row baseline, with independent signed readback | Historical V3 receipt is `PARTIAL`; no V3 successor or signed live readback is present in the accessible checkpoint |
| Scoped V4 | Adopt **the same** independently verified persisted V3 tables as the actual scoped integration result, with exact source and row coverage; no duplicate load | Depends on live V3 proof. The existing full-population runner's V4 PASS criterion is inapplicable to this reduced scope; use a distinct scoped receipt and never relabel the historical full-C2000 checkpoint |
| V5 | Run applicable Lossless 1–6, key/link/history, multiplicity, source lineage and isolated negative controls against those persisted tables | Requires actual Delta candidate and protected readback |
| V6 | Compare the reused 127-row FSDS baseline to its accepted immutable result, verify no mutation and source isolation; full old-vs-new Vault regression is not applicable | Conditional, pending loaded result |
| V7 | Trigger only for an observed failure; follow the shared recovery matrix and reconcile uncertain writes | No repair run authorized by this scope change |
| V8 | Record actual prototype coverage, runtime, throughput, Free Edition quota interruptions/retries and human minutes; leave unavailable figures null | Local build/probe evidence reusable; live compute figures unavailable |
| Scoped V9 | Independently verify and sign a **prototype-only** live freeze pinning exact UC/Delta IDs, versions, contract hashes, row coverage and unresolved scope, then PR/CI and explicit Owner merge approval | Protected freeze and live result absent; no full-C2000 freeze may be claimed |

Free Edition quota exhaustion or interrupted Jobs must stop at `UNCERTAIN_REQUIRES_READBACK`. Reconcile the original run, ledger and every affected Delta target, record a terminal `PARTIAL` disposition and stop. No automatic retry, continuation or original-request replay is part of Day 6. Future full C2000 work, if ever requested, is a separate lifecycle scope and cannot inherit this prototype's grant or PASS.

## Observed boundary

The durable [checkpoint](../metadata/evaluations/day6_c2000_vault_pilot_checkpoint_v1.json) remains paused before V4 with historical V2/V3 partial outcomes. The local wheel and request have unchanged, verified hashes. The signed semantic receipt is in a root-only Owner approvals directory; a read-only agent `sudo -n` invocation required a password. The Owner CLI profile performed authenticated read-only calls outside the sandbox; sandboxed keyring failures were not evidence that Owner credentials needed rotation. Live UC metadata confirmed exactly the eight historical tables and no `v3_` target. The proposed wheel path was absent, the saved Jobs list was empty, and the existing service principal had `USE_CATALOG`/`USE_SCHEMA` grants but no observed `CREATE_TABLE` right. No V3 extension installation, operation grant, Job run or 23-table live readback has been verified. Until those specific gates are satisfied, V3 and downstream live stage claims are **BLOCKED**, while the existing 127-row prototype remains accepted.

PR #75 may receive this scoped plan, local tests and CI. Its merge remains an explicit Owner review gate; merging code does not authorize a protected service, Delta write or live freeze. Day 7 is outside this closeout.
