# Acquisition / Cohort RAW ownership — runtime enforcement

**Scope:** prospective, code-enforced separation of RAW staging authority. This complements the [PR #62](https://github.com/lightnino/edp-lab/pull/62) workflow specification and [PR #59](https://github.com/lightnino/edp-lab/pull/59) standing 0A broker; it is not a historical rerun and does not alter the immutable Day 5 Queue, grants, receipts or C2000 freeze.

## New execution boundaries

- **Cohort Runner** (`operating.runner.run`) refuses all declared RAW mutating task kinds **before** it requests a broker grant, writes a checkpoint, creates a lock or performs external operations. Its `raw_stage` adapter dispatch has been deleted.
- **Cohort Broker** (`operating.policy_broker`) refuses a RAW mutating queue even if the installed standing policy happens to list `raw_stage`. Its protected execute endpoint separately rejects RAW mutating operations, including a direct socket request using an old signed grant. No automatic fallback to Cohort staging exists.
- **Low-level RAW adapter** (`operating.boundaries.raw_stage`) requires an Acquisition-only owner-signed grant with `authority=owner-acquisition-v1` and `cohort=ACQUISITION`. Historical Cohort grants cannot invoke the adapter, even by bypassing the normal Runner.
- **Separate Acquisition executor** (`operating.acquisition_executor.execute_acquisition_stage`) is a protected owner-controlled *stage-new* entrypoint. It requires a cryptographically verified current owner-signed grant, exactly pinned source bytes and execution plan, plus an independently verifier-signed `STAGE_NEW_AFTER_DISCOVERY` disposition tied to the source identity/SHA/bytes and specific destination. Only when all checks pass can it call the protected RAW adapter. Mere missing Cohort receipt never grants upload.
- **Delegation, not execution:** `acquisition_remediation_request` emits a non-authorizing `RAW_HANDOFF_BLOCKED` packet addressed to the Acquisition actor. Cohort pauses; the Acquisition lifecycle separately searches historical RAW and either verifies a reusable existing locator or authorizes an actual new stage. Cohort may resume **only after** the U10 independently verified remote locator/readback handoff, never because an Agent claims a missing file.
- **Signed U10 input gate:** A successor **owner-signed Cohort Standing Policy** can set `require_verified_raw_handoff=true`. The protected Broker will then refuse a Cohort Queue that lacks a source-complete, byte-pinned independent `EDP_U10_RAW_HANDOFF_V1` verifier receipt. The receipt binds selected physical identities, remote locator, SHA-256, byte size and readback evidence. If the agent omits it, the grant request is `RAW_HANDOFF_BLOCKED`. The Cohort Runner independently checks any supplied U10 receipt before execution. **Old standing policies do not automatically enable the gate**: a separate owner-reviewed policy installation is required to make it mandatory on a protected host.

## Workflow responsibilities

1. Acquisition U3 → search local/historical remote receipts across physical identity + exact SHA/size, independently read back known RAW. Missing or unresolved historic receipt is not absence.
2. If verified RAW exists → U10 publishes the signed verified locator, no transfer.
3. If no reusable RAW can be established → only independent Acquisition discovery and Acquisition-specific owner/broker authorization can stage new bytes, with exclusive ledger and independently signed readback.
4. Universe U10 → immutable remote locator, physical identity, RAW SHA-256/bytes and verifier receipt for exact eligible source.
5. Cohort P0/P1/P8 → verify the handoff and read the existing RAW to produce CLEAN/QUERYABLE. `RAW_HANDOFF_BLOCKED` delegates back upstream without any Cohort RAW write.
6. Neither the Cohort broker nor agent may interpret a signed historical Day 5 RAW grant as reusable future upload permission. Historical PR #64 freeze remains accepted and unchanged.

## Day 6 bounded validation plan (no active PR #61 modification)

Day 6 must test **both** the negative boundary and the correct agent decision:

- Test A — Existing U10 RAW handoff: supply valid source/URI/SHA/byte/readback evidence from a *frozen fixture*. Agent chooses Cohort read-only processing; **0 RAW upload calls**; receipts and result freeze unchanged.
- Test B — Missing/ambiguous receipt: agent emits `RAW_HANDOFF_BLOCKED` + Acquisition remediation packet; no Cohort Runner stage, no protected broker stage and **0 bytes transmitted**.
- Test C — Old broad Standing Policy or signed Cohort grant lists `raw_stage`: Runner, Broker grant issuance, direct Broker protected execute and low-level adapter all **DENY**.
- Test D — Acquisition dry run using cryptographically signed, owner-controlled grant and verifier-signed discovery result; test rejects absent/altered evidence, arbitrary destinations or previously reusable RAW.
- Test E — Only after a **separately approved** Acquisition fixture exists: protected staged-upload/readback and signed U10 handoff; then resume the same Cohort checkpoint. Do not run against Day 5 or Day 6 live RAW in order to test.

**Current limits:** This PR does not create/install the protected Acquisition grant broker, new standing Acquisition signing policy, historical RAW locator index, general remote resolver, or a production signed U10 handoff publisher. The owner must review/install those separately, including a successor standing policy that requires signed U10 handoff, before declaring the *whole autonomous two-workflow lifecycle* operational. This PR **does enforce** removal of Cohort RAW uploads at its Runtime task/authorization/adapter boundaries, with offline tests, without modifying Day 6.

## Protected migration and status

Existing signed historical Day 5 `EDP_QUEUE_V1` bytes are retained as evidence but intentionally **cannot be replayed through this stricter Cohort Runner**. All future Cohort runs must use verified pre-staged RAW. The prior Day 5 report and original Source Universe remain historical facts, not retroactively failed runs.

No code or state in Day 6 PR #61, PR #66, `metadata/authorizations/`, `metadata/freezes/`, `metadata/operating/`, Databricks objects or protected owner host is changed. Do not merge while CI is red or without owner review.
