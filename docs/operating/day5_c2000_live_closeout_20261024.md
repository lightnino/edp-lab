# Day 5 C2000 live result and P14 review packet

## Accepted run and P11 recovery

The existing protected Supervisor resumed the signed Queue SHA-256
`e43cf9984e1c54b17cbdc44917954bf802acba3241168ea353b302ec41076e34`.
Its final protected checkpoint SHA-256 is
`f775e646e849d093d6e5e495a782f45635b2324f5022e68d594944b27fbbe537`:
513/513 tasks `COMPLETE`, `accepted=true`, `dry_run=false`. No second Day 5
Queue was started. The original 502 completions were retained.

The owner-installed P11 disposition remained the only pre-submission recovery.
The separately signed recovery receipt SHA-256 is
`e3b252b234da0475a8e1afe46279ea0d91930785686966467a0260e193097d85`.
The `sql-roster` checkpoint links the original operation
`day5-c2000-roster-v1` and original ledger SHA-256
`0c6144e51eeee56ca3dbdbfbc095a44396507a5b6813f9768ae9488bbaa9c3f2`
to distinct operation `day5-c2000-roster-v1-recovery-v1`. The latter's signed
receipt SHA-256 is `9298818cc39f3ba0d1e932b8f1474fc442238d0a701f2f32c2ea4971c5f843c8`.
It records Statement ID `01f1cf3d-6016-12f2-a7d2-5379704abd92`, terminal
`SUCCEEDED`, live UC readback for exact target
`workspace.edp_lab.n500_input_roster_day5_v1`, and UC ID
`2e49534e-278c-4e69-99a0-25f83ad8849f`. The protected verifier checks
the signed recovery link and original ledger hash before signing readback.
The ledger directory is root-only; this worktree cannot directly open its
distinct operation file. Both P11 receipts and all six control receipts were
verified locally against the protected verifier's public key.

## Input and live result

The frozen input roster is [C2000_v1](../../metadata/freezes/C2000_v1/freeze.json),
SHA-256 `324ca5e416adabc443d18d8066fbccdf137f4cb50aa20934e645615f4ee77ff3`.
Its four listed file hashes were independently rechecked. All 500 protected RAW
receipt hashes match their exact Queue source identities and frozen receipt
map; P6's protected admission receipt separately passed. The C2000 roster has
2,000 distinct physical source entries, comprising the preserved C1500 and
the approved N500; the 500 new SEC files each contribute one binding. The
historical C1500 has 1,932 operational bindings, giving 2,432 preserved
operational bindings in this source-preserving composition. This binding
total follows the pinned old result and new input roster; P13's remote queries
check source counts and lineage, not a separate full-view distinct-binding
aggregate.

The signed [live freeze receipt](../../metadata/freezes/O_C2000_M2_v1/receipts/c2000-result-freeze.json)
has SHA-256 `e1023289fedb3b682e0afe33bc350997e5d84c5aa27e9d00bf34bc760fe93830`.
The protected remote evidence file SHA-256 is
`512cecc9170f9c3a6abe46da2d21bce5a5eedb995d89f334d8be9a299ea6aea2`.
It verifies live UC ID `a9b7d2ab-4d9d-462a-b046-7f04bf144773` for
`workspace.edp_lab.o_c2000_m2_result_frozen_day5_v1`. The `SHOW CREATE TABLE`
readback is a `UNION ALL` of the existing C1500 frozen view and the new CLEAN
Delta table at `VERSION AS OF 0`. The old result UC ID remains
`43e16098-b123-4689-83d5-4d942bbe4dfc`. New roster and CLEAN Delta history
and detail both returned version 0 with matching UC identities. Live SQL
returned 500 new roster sources, 2,037,138 new CLEAN records, zero wrong-width
records, zero new roster/CLEAN source-hash lineage mismatches, and 2,000
combined sources. P9's signed live count receipt returned 321,188,377 total
occurrences, including exactly 2,037,138 new SEC records; the prior frozen
result contributes 319,151,239 occurrences.

FIN_001/002 and TRY_001–004 all have separate signed `PASS` live Databricks
receipts with Statement IDs and response hashes. The P12 timing receipt records
18.764935 seconds for the comparable SQL table creation phase. The signed
result marker is [databricks_result_freeze_v1.json](../../metadata/freezes/O_C2000_M2_v1/databricks_result_freeze_v1.json).
Treasury economic L6-B remains outside the source-preserving scope and is
`NOT_IMPLEMENTED`; no canonical economic rule is inferred.

The live evidence includes actual Delta properties, which do not list
`delta.appendOnly=true`. The result is a new version-pinned view with verified
live readback; this packet makes no WORM, independent archive, or indefinite
retention claim. A separate agent-side readback using the ordinary CLI profile
could not obtain a cached token after the protected run. The protected
verifier's authenticated live readback and signed response hashes are the
remote evidence for P13.

## P14 decision

P13 is source-preserving `PASS` in the bounded approved scope. P14 requires
review of the scoped PR, required green CI, and explicit human merge approval.
The PR must not be merged from an agent-only decision. Day 6 PR #61 and Incident
PR #63 are separate. Incident #63 may cite the confirmed signed P11 recovery
receipts above at its eventual closeout; it is not changed here.
