# Day 6 V3 partial installation: Job creation checkpoint

**Status:** PARTIAL_INSTALL_BLOCKED. This is read-only reconciliation and a
reviewable Owner recovery path, not an installation receipt or V3 result.

The Owner reported that the original `jobs create` returned exit 1 after the
source and target privilege checks. The later Owner-provided error identifies
unknown-field warnings for Job-level `max_retries`, `retry_on_timeout`, and
`disable_auto_optimization`, followed by denial because the Owner lacks
`servicePrincipal.user` on the existing run-as principal. The original CLI
helper did not retain stderr, so this error account remains Owner-provided
rather than independently recovered from the original call. An empty Jobs list
alone does not prove that the request had no effect. Do not rerun `install`.

Read-only authenticated reconciliation on 2026-10-25 found:

| Item | Observed state |
| --- | --- |
| Saved Jobs | Empty list; no Job ID observed |
| Existing service principal | ID `72304318628585`, application ID `87df13c2-1bb7-4a0b-b84a-84e01bdc1764`, active |
| Historical Vault tables | Exactly the eight existing tables; no `v3_` table |
| Wheel SHA-256 | `eada999db14a7db4b5590ab34b4296127e4231fe5289a04180bcf410238cafc9` |
| Selection SHA-256 | `5b84f0a1dc088affc51f631bc34c66f0053b871b67efff13e770021a19a33259` |
| Negative oracles SHA-256 | `54c2aa2add50504cca6a50beed480ef78fef96d962b7f9b6e6a4468ff34f72f2` |
| Derived request SHA-256 | `5e9a095de53fc38fdfc46604260be7a2f3db33f820048ba5b7ed4ca415f03000`; matches independently derived canonical bytes |
| Effective source/target rights | `USE_CATALOG`, both required `USE_SCHEMA` rights, target `CREATE_TABLE`, and `SELECT` on each of five named source tables |
| Protected local state | Root-owned private/receipt/ledger directories are inaccessible to the agent. Owner reported no V3 installation receipt. The resume command must check the derived request bytes, protected permissions and absence of later V3 receipt/grant/ledger records itself. |

A fresh read-only check on 2026-10-25 used the Owner Databricks profile and
observed both the full Jobs list and the exact-name
`day6-c2000-v3-one-shot` filter empty. This supports absence at the visible
scope and time of the check; the Owner resume must repeat its own checks.

PR #75 commit `73cb6c696dc934bf1a5a71e1cc02ac13bffc3d7a` moves all three
retry/optimization fields to the supported task level and makes saved-Job
verification require `max_retries=0`, `retry_on_timeout=false`, and
`disable_auto_optimization=true` there. The run-as principal, grants, uploaded
artifacts, 23-table allowlist, and one-shot checkpoints are unchanged. The
`servicePrincipal.user` denial remains an Owner-side prerequisite; this change
does not grant that permission or select a different identity.

The Owner's subsequent `resume-install` reached `jobs create` and returned
`Either base environment or version must be provided for environment
'v3_fixed_runtime'.` This is an Owner-reported API rejection, not an install
receipt. Read-only authenticated reconciliation again found the full Jobs list
and exact-name `day6-c2000-v3-one-shot` filter empty. Those checks establish
no visible saved Job at the checked scope and time; the Owner resume must
repeat its own absence and checkpoint checks before any distinct attempt.

The proposed Job environment now pins `environment_version: "4"` alongside the
same wheel dependency. The saved-Job verifier requires that exact spec and
rejects a missing, different or additional base environment. Databricks lists
version 4 as a supported serverless Jobs environment with Python 3.12.3,
matching this wheel's `>=3.12,<3.13` requirement. The request and deployment
manifests, uploaded artifacts, permissions, run-as, one-shot ledger and
submission limits are unchanged. This code change alone does not authorize
another Job creation attempt.

`resume-install` starts at this exact checkpoint. It performs the usual reviewed
commit, clean worktree, installed V2 trust and signed semantic checks; verifies
the local protected derived request against the canonical request plus fixed
grant ID; confirms the admin identity, service principal, eight historical
table IDs, empty Jobs list, workspace directory, all four remote hashes and
effective grants. It performs no import or grant update. Only after those
checks does it create one Job, independently read back its exact settings and
historical table IDs, and write a signed install receipt. Any mismatch stops.
An uncertain create response, failed saved-Job readback or missing receipt
requires fresh Owner reconciliation; the command has no automatic retry.

The Owner must independently settle the run-as permission prerequisite and
decide whether a distinct Job creation attempt is safe under the
[Operating Contract recovery matrix](../docs/workflows/agent_operating_contract_v1.md#recovery-decision-matrix).
The helper will expose the exit status and sanitized stderr on a future
failure. A local code fix cannot reconstruct the original stderr.
`issue`, `execute`, the independent signed Delta readback and V3 acceptance
remain separate blocked gates. No source, target or semantic scope changed.
