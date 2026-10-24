# Day 6 C2000 Vault rebaseline

## Step 0: accepted baseline

Remote main `12874dd2aa581a80086afa24a3d21a0a1aa6f3e4` was merged into
the Day 6 branch. The [Step 0 record](../metadata/evaluations/day6_step0_c2000_v1.json)
pins the C2000 input freeze, its 2,000-entry roster and all four listed file
hashes, the accepted 513/513-task Day 5 checkpoint, the result-freeze marker,
and the signed P13 receipt. The receipt was verified against the protected
verifier public key outside this worktree. A live read-only Unity Catalog `get`
returned the expected C2000 view ID and its version-0 new CLEAN dependency.
Day 5's signed evidence reports 321,188,377 source-preserving occurrences and
PASS for FIN_001/002 and TRY_001–004. No Day 5 resource was modified.

The approved Vault Load Contract V1 and serializer hashes remain unchanged.
The contract covers SEC FSDS `num.txt` only. All 60 C2000 FSDS sources are
retained from C1500; none of the N500 additions falls in that contract scope.
This bounds Step 2 to a representative **C2000 member sample of the supported
source type**, without implying coverage of all 2,000 sources or new N500
records. Expanding source types needs a separate semantic review.

The subsequent Step 2 readiness recheck matched all three actual RAW ZIP and
`num.txt` member hashes, the retained M1/M2 version-0 evidence, and the exact
input and plan hashes. See the [0A evidence](../reports/vault_0a_v2_evidence.md)
and [Owner gate packet](operating/day6_c2000_step2_owner_gate_v1.md). No Day 5
query or write was rerun.

## Step 2: prepared bounded prototype

The ignored local input manifest at `runs/day6-vault-c2000-v1/input_manifest.json`
contains 127 occurrences from `SRC000005`, `SRC000054` and `SRC000064`, with
the exact immutable C2000 roster hashes and source locators. The source rows
come from the prior read-only version-0 M1 statement, and the projection was
regenerated with the approved serializer. This is reuse of unchanged physical
sources, **not a new C2000 warehouse sample query**. The later readiness
recheck independently matched the three RAW ZIP/member byte hashes.
The ignored local V2 load plan at `runs/day6-vault-c2000-v1/load_plan.json`
has seven fixed business/quarantine stages, 127 DATA occurrences and six
synthetic negatives. The [run proposal](../metadata/operating/day6_c2000_vault_v1/run_plan_proposal.json)
pins the exact input and plan hashes and expected table counts. The standalone
preparation script checks all C2000 freeze file hashes, exact roster membership,
reprojection equality and plan bounds before regenerating them.

The [scope proposal](../metadata/operating/day6_c2000_vault_v1/scope_approval_proposal.json)
is **not owner approval**. After Vault installation and real protected 0A
tests, the owner must review the source, contract, plan and capacity pins and
sign a fresh C2000 bounded-prototype approval. A protected verifier must
separately produce the `LIVE_VERIFIED` C2000 freeze receipt expected by the V2
eligibility registrar. The Day 5 P13 receipt is sound Step 0 evidence but has
a different schema and does not silently become that Vault receipt. Before
grant issuance, reverify exact RAW ZIP/member bytes and pinned M1/M2 inputs;
then install the signed eligibility record. Only then may the protected Broker
issue a short-lived grant for the fixed run. Real service-principal negative
authorization tests, insert-only Delta writes, replay and quarantine controls,
and independent persisted readback are required to claim Step 2 PASS.

The input, projection and rendered SQL contain derived source values, so they
stay in ignored `runs/` and are absent from Git. The V2 eligibility, Broker,
Executor and verifier accept `protected:` manifest/plan pins only from the
root-owned Vault `artifacts/` directory, with file and directory ownership,
mode and exact hash checks. The owner must create that directory and copy the
two pinned files there after reviewing them; no agent-writable substitution is
accepted. The tracked proposal names the protected paths and local hashes for
review; it is not an eligible receipt.

## Withdrawal and Step 3 boundary

The C1500 exception is `WITHDRAWN_UNEXERCISED`: no C1500 Vault execution,
signed eligibility or protected grant was installed. Its active authorization
file and obsolete V1 policy proposal were removed from this branch. Git
history and the prior read-only reports remain available for audit; the old
V1 installer and client are hard disabled.

Full C2000 integration is a separate owner gate. The current standing policy
explicitly denies `FULL_INTEGRATION` and caps each run at 1,000 occurrences,
20 synthetic rows, 100 statements, one hour and a 2X-Small single-cluster
warehouse. The owner must approve a versioned policy amendment for workload
kind, total capacity and the exact expanded write scope. A new signed scope
approval and independent persisted full-result readback are also required.
The bounded prototype does not imply an approved policy for the full
321,188,377-occurrence result.
