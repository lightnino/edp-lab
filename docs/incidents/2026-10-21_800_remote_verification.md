# Step 4 — Retained RAW verification

Incident: **EDP-INC-2026-10-21-001**. This separate evidence report does not change the Incident Report's **OPEN** status. Step 6 owns final consolidation and closure. No Step 5 execution, push or merge is included.

## Scope and authority

The owner's Step 4 instruction authorizes bounded read-only Databricks verification of exactly the 800 recorded retained objects and their known cohort dependencies: 300 NOAA GSOD, 400 World Bank WDI and 100 Treasury annual XML. They remain legitimate retained data outside Approved Universe v1. RAW presence and integrity confer no admission or processing authority.

Universe authority was read from `/Users/lightnino/Projects/edp-lab-scope-gate/metadata/source_universes/approved_v1/manifest.json`, SHA-256 `2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c`, and compared byte-for-byte by digest with approval commit `319281c17d957dc8d442aaa63278df0d5a1596b3`. This is a locally committed membership authorization artifact. Guardrail enforcement is **not established as merged, deployed, live or fully validated** by this report.

The historical [800-reference appendix](2026-10-21_retained_raw_references.md), [evidence index](2026-10-21_evidence_index.md) and [Incident Report](2026-10-21_source_universe_scope_control.md) remain unchanged. Existing Source Instance IDs index this report; publisher identities, RAW paths and acquisition history are not redefined.

## Current remote verification

| Current result | Objects |
| --- | ---: |
| PRESENT | 800 |
| MISSING | 0 |
| INACCESSIBLE | 0 |
| Current listed size matches historical receipt | 800 |
| HASH_MATCH (complete current readback) | 800 |
| HASH_MISMATCH (complete current readback) | 0 |
| HASH_NOT_CHECKED (complete-object integrity unverified) | 0 |

Current listed total and final complete-readback total: **79,225,793 bytes** and **79,225,793 bytes**, respectively. Historical receipt total: **79,225,793 bytes**.

Captured listing interval (UTC): **2026-10-21T10:43:24.905060+00:00** through **2026-10-21T10:43:30.685448+00:00**. Readback interval, including the initial exception and isolated retry (UTC): **2026-10-21T10:43:51.785057+00:00** through **2026-10-21T10:54:15.396438+00:00**. Aggregate finalized at **2026-10-21T10:54:15.429741+00:00**. Per-object timestamps are in `objects.csv`; first-attempt exception timestamps are retained in `readback_exceptions.json`.

Initial incomplete responses (a partial digest does not establish changed RAW):

- `SRC001586`: first response **212,992 / 625,737 bytes**; final isolated retry outcome **HASH_MATCH**.
- `SRC001753`: first response **65,536 / 108,960 bytes**; final isolated retry outcome **HASH_MATCH**.
- `SRC001777`: first response **65,536 / 81,421 bytes**; final isolated retry outcome **HASH_MATCH**.
- `SRC001958`: first response **131,072 / 161,208 bytes**; final isolated retry outcome **HASH_MATCH**.
- `SRC001963`: first response **65,536 / 162,707 bytes**; final isolated retry outcome **HASH_MATCH**.
- `SRC001980`: first response **98,304 / 103,954 bytes**; final isolated retry outcome **HASH_MATCH**.
- `SRC001983`: first response **49,152 / 116,334 bytes**; final isolated retry outcome **HASH_MATCH**.

The initial verifier mechanically labeled incomplete-response digests HASH_MISMATCH; these observations are **HASH_NOT_CHECKED for full-object integrity**. The exact isolated retry budget of **1,360,321 bytes** was recorded before retries. Both attempts are retained in `readback_exceptions.json`. Actual payload read across all attempts: **79,913,921 bytes**, including **688,128** extra partial-attempt bytes (0.87% above the baseline). No broad readback was repeated.

Final unverified objects: **none**.


Each appendix entry was reconstructed and checked against its original upload receipt: receipt SHA-256, Source Instance ID, exact remote path, recorded RAW SHA-256 and historical byte count. All 800 receipt hashes also agree with the original evidence index. These checks establish the historical comparison inputs, separately from the current readback.

Databricks CLI profile `edp-lab` listed only the three known flat upload prefixes. The retained listing evidence contains only entries for the 800 target objects. One initial N450 connectivity listing was not persisted; the subsequent captured listing for each prefix was reused throughout preflight/readback without relisting. Listings expose unrelated names in those same known cohort prefixes, but no unrelated object's bytes were read. No parent-root or unrelated source-family discovery occurred.

Preflight established **800 present, 800 matching sizes, 79,225,793 current listed bytes** before bulk reads, equal to the historical receipt total. Four workers issued read-only UC Files API `GET /api/2.0/fs/files{exact_volume_path}` requests. Bodies were streamed into SHA-256 without persisting RAW. Each body was bounded by its historical size; a Content-Length disagreement would stop that object's read. Where Content-Length is absent the implementation permits one extra byte solely to detect an oversized response (maximum possible extra across this run: 800 bytes). No unrelated RAW read, compute job, upload, overwrite, move, deletion, table change or volume change was performed. Authentication stayed in memory and is absent from committed evidence.

The initial sandboxed subprocess could not access cached credentials. The approved elevated verifier reached preflight, then stopped before readback because the token command combined a positional profile with `-p`. The corrected invocation reused the captured listings and began the current readback. No successful readback was attributed to either failed attempt.

Matching sizes are not treated as hashes. HASH_MATCH means SHA-256 calculated from the **current remote response bytes** equals the recorded RAW SHA-256, with matching readback size. These are interval observations, not an atomic multi-object snapshot or a guarantee against future changes. A point-in-time aggregate refers to the captured listing interval; completed readbacks independently confirm its same byte total.

## Authorization and exclusions

- **800/800 excluded from Approved Universe v1.** None of the 800 recorded RAW hashes occurs in the pinned 3,021-member manifest. Recorded acquisition candidate IDs were also checked for literal overlap; this does not equate their namespace with inventory delivery IDs. Hash disjointness independently establishes exclusion of every exact recorded delivery.
- **800/800 excluded from accepted frozen C300.** Source Instance IDs and RAW hashes have zero overlap with the exact 300-member roster and manifest v3. The canonical roster, manifest and original 300-member review packet match the frozen digests. Packet candidate/delivery identities were inspected without inferring aliases from names or tickers.
- **41/41 Day 13 holdouts remain outside C300.** Every holdout identity and RAW hash in the pinned approved manifest is absent from C300's original packet identities and accepted hashes. No new cohort or admission was created.
- Historical unaccepted membership is preserved: **50** retained objects in C750, **300** in C1500, **800** in C2000. The historical manifests' exact Source Instance ID/hash rows and structural-summary membership digests were checked. Those freezes and manifests are evidence of the earlier unauthorized scope, not accepted experiment baselines or retroactive authorization.

No current or future processing approval for these 800 is established. A new explicit scope decision would be required; this verification does not supply one.

## Known downstream dependencies and limits

| Evidence scope | Observed dependency | Interpretation |
| --- | --- | --- |
| N450, Day 3 | 50 extra NOAA RAW uploads; N450 structural summary and targeted inspection; C750/manifest v4 | Historical upload and structural profiling, unaccepted experiment scope |
| N750, Day 4 | 250 additional NOAA RAW uploads; prefix observations and selected structural checks; C1500/manifest v5 | Historical upload and structural profiling, unaccepted experiment scope |
| N500, Day 5 | 400 WDI and 100 Treasury RAW uploads; ZIP-member/XML envelope observations and selected checks; C2000/manifest v6 | Historical upload and structural profiling, unaccepted experiment scope |
| Accepted C300 physical scope / known M1 recovery | Pinned C300 contract; 300-entry physical evidence; CLEAN publication and QUERYABLE definitions | Zero overlap with the retained 800; this does not certify a fully accepted M1 baseline |

The three historical structural completion files record **zero Databricks processing jobs** for their increments. N750/N500 explicitly record `CLEAN_QUERYABLE: NOT_RUN`; N450 records final M1 fit deferred pending the accepted Day 2 baseline. These statements describe those checkpoints only. Structural profiling is a real historical downstream use and has not been erased by logical rollback.

The bounded C300 evidence is `/Users/lightnino/Projects/edp-lab/runs/c300-m1/main_recovery_20261021_v4/`: `contract.json`, `collected-full/physical.json`, `recovery-main-completion.json`, `publication.json`, `collected-full/queryable.json`, and six `submitted-{stage,clean,gate,publish,query,finish}.json` references. The contract pins the same C300 roster/manifest digests; physical evidence contains exactly those 300 IDs and matching hashes, with **zero** retained-800 ID/hash overlap. The completion records `MAIN_720_COMPLETE_VALIDATED` and `NOT_FROZEN`; no new acceptance or full-C300 Lossless claim is made here.

Known job run IDs are stage `758804395366009`, CLEAN `246744902888746`, gate `1023109119094548`, publish `1020644587126998`, query `1124391195675962`, finish `281723002176292`. Historical publication records version 0 of `workspace.edp_lab.clean_c300_m1_bindings_main_recovery_20261021_v4_full` and `workspace.edp_lab.clean_c300_m1_records_main_recovery_20261021_v4_full`. Known QUERYABLE views are `q_c300_m1_{coverage,fields,records}_main_recovery_20261021_v4_full` and reference pinned version-0 CLEAN tables. These are existing local retained Databricks execution references, not newly queried live statuses.

**UNVERIFIED:** global/current Databricks consumer lineage, ad hoc readers, other jobs/tables/views outside these known dependencies, live state of the listed M1 outputs/jobs, future preservation, and Guardrail deployment/enforcement. No claim that no global consumer exists is supported. No live SQL, lineage or Jobs metadata query was necessary to establish the narrower documented exclusions; none was issued. No unrelated directories or source families were scanned. Local RAW was not rehashed by this task.

## Reproducible evidence and checks

Evidence directory: [evidence/800_remote_verification](evidence/800_remote_verification/).

- `objects.csv`: one current verification record per existing Source Instance ID, including presence, sizes, current SHA-256, status, method and exact UTC timestamps. Join IDs to the unchanged appendix for historical receipt/path references.
- `listings.json`, `preflight.json`, `summary.json`: filtered captured directory metadata, transfer bound and aggregate result. `retry_preflight.json` and `readback_exceptions.json` retain bounded retry authority and both observations for incomplete responses.
- `exclusions.json`, `dependencies.json`, `known_c300_consumers.json`: per-instance/holdout exclusion results and bounded dependency findings.
- `input_digests.json`: exact paths and SHA-256 of inspected authority, frozen cohort and downstream evidence inputs. Original receipt hashes remain in the appendix and were all verified.
- `artifact_digests.json`: SHA-256 of the new evidence files and scripts; its own digest is external to avoid a recursive seal.
- `verify.py`, `retry.py`, `audit.py`, `finalize.py`, `validate.py`: read-only verifier, bounded exception retry, offline authorization/dependency audit, compact evidence generation, and offline evidence validation. `verify.py` generates temporary derived JSON; `finalize.py` removes those redundant representations after writing the compact CSV. Network verification is a new observation and should not be rerun merely to validate these unchanged records.
- `validation.json`: actual offline validation result. Validation checks unique 800 coverage, every current hash against its original receipt, byte sums, timestamps, exclusions, inspected input digests and artifact seals.

Evidence seal `artifact_digests.json` SHA-256: `29e500a806870006bbf1248731f4af405d82277b5855400165350548060c4e1b`. Current per-instance `objects.csv` SHA-256: `f749b1c5b778250ebd2c411196f5c6af9c9945c355102e50fae9583767f38f14`. All other input/output digests are enumerated in the two digest files.

The Git commit containing this report and evidence is reported by `git log -1 --format=%H -- docs/incidents/2026-10-21_800_remote_verification.md` and in the Step 4 completion response; a commit cannot embed its own resulting SHA. Incident closure and Step 5 remain outside this commit.
