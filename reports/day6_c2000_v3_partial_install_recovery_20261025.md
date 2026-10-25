# Day 6 V3 partial installation: Job creation checkpoint

**Status:** PARTIAL_INSTALL_BLOCKED. This is read-only reconciliation and a
reviewable Owner recovery path, not an installation receipt or V3 result.

The Owner reported that the original `jobs create` returned exit 1 after the
source and target privilege checks. The original CLI helper captured stderr
but raised an exception that did not display or retain it. The exact historical
Jobs API error is therefore **UNRESOLVED**; an empty Jobs list does not by
itself prove that the original request had no effect. Do not rerun `install`.

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

The Owner must review the original CLI stderr and decide whether a distinct
Job creation attempt is safe under the [Operating Contract recovery matrix](../docs/workflows/agent_operating_contract_v1.md#recovery-decision-matrix).
The repaired helper will expose the exit status and sanitized stderr on a
future failure. A local code fix cannot reconstruct the original stderr.
`issue`, `execute`, the independent signed Delta readback and V3 acceptance
remain separate blocked gates. No source, target or semantic scope changed.
