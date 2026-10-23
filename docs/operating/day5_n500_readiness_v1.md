# Day 5 N500 → C2000 readiness: source membership preflight (review-only)

**Status: IMPLEMENTATION + OWNER REVIEW PACKET; NO new Cohort Approval, no source processing, no Databricks operations.**

This implements the first non-Databricks gate needed before the Day 5 autonomous pilot. It builds on PR #56's guarded Databricks execution adapters and merged PR #55's signed DAG runner. It does not invent or autonomously select the 500 source instances.

## Inputs anchored to current approved history

- Owner-approved original **Universe v1**: `metadata/source_universes/approved_v1/manifest.json` and its separate `owner_authorization.json`. Owner approval authorizes **Universe membership only**, including nonprocessing holdouts.
- Frozen **C1500**: `metadata/freezes/C1500_v1/C1500.csv`, `C1500.bindings.json`, and `freeze.json`. All relevant files and digest pins must match. Historical input is read-only.
- **Proposed N500 candidate bindings**: a local JSON **array of exactly 500 existing registered physical source records**, each having `source_instance_id`, `source_identity`, `raw_sha256`, `raw_path`. These are **not generated or assigned by this preflight**. The user/Agent must first produce an actual evidence-backed candidate selection with original identity registration, within approved Universe and not previously used.

## What is mechanically checked

1. Approved Universe is exactly its pinned version 1 with 3,021 unique physical members, and its separate owner-approval record matches the actual manifest digest.
2. Frozen C1500 source membership file and C1500 binding hashes exactly match its immutable freeze record. The 1,500 original records are cross-checked against Universe identity/hash/path, and original registered source IDs match the preserved CSV ordering.
3. Proposed N500 is **exactly 500**, disjoint from C1500 by both registered source ID and physical source identity. Reject duplicate IDs and physical duplicates within N500.
4. Every candidate must be in the approved Universe and **not** in a protected holdout. Candidate `raw_sha256` and physical original path must reconcile with the pinned Universe member.
5. The resulting review-only packet states the verified metadata counts/digests and the **pending** physical RAW and Databricks remote SHA checks. It always returns `PROPOSED_NOT_AUTHORIZED`, never `APPROVED`, and cannot sign a grant or publish a new C2000 cohort.

**Zero download is a valid future pilot scenario:** a proposed source can reuse an already acquired/verified RAW. Separate signed acquisition and cohort execution authority remain necessary; file existence never grants eligibility.

## CLI (metadata review only; never use as processing authorization)

```sh
uv run python -m edp_lab.operating.n500_preflight \
    /owner-reviewed/n500-proposal-bindings.json \
    runs/day5/n500-review-packet.json
```

This command **requires an existing candidate list**, performs no downloads and writes only an exclusive review packet. It does **not** approve that proposal, allocate Source Instance IDs, inspect actual local RAW bytes, verify live Databricks objects or trigger a Jobs/SQL operation. The owner independently reviews the exact 500 members before any actual admission freeze.

## Further pilot start gates (not implemented by this file)

- Verify actual new RAW bytes, source identity registration and pinned remote staging receipts for all candidates. If a source is absent from Databricks, acquisition/staging needs an **independent approved grant**, never automatic authorization from this preflight.
- Observe N500 B1 requirements; determine `CORPUS_ONLY`, `ADDITIVE` or `CORRECTIVE` from real source evidence, not a hardcoded Day 5 model assumption.
- Obtain owner authorization for exact N500 membership, C2000 input-cohort freeze, parser/model/rule, scoped Databricks Notebook/runtime/output, per-phase budget and source family/field-specific Lossless/Stability oracles.
- Deploy code in a protected executor; preflight source hash, runtime export and DBFS runtime SHA, then run signed DAG/guarded Jobs. The agent cannot sign its own receipts.
- Wire independent SQL/Delta/UC result verification and protected P13 LIVE freeze signing. Verify protected P14 Git closeout and negative denial tests; never label successful Jobs submit as accepted data output.

**Do not treat this PR as `AUTONOMOUS_END_TO_END_PASS`.** Even a successful metadata preflight only moves a real candidate proposal to independent owner review.
