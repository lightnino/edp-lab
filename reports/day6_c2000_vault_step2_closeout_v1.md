# Day 6 C2000 bounded Vault Step 2 closeout

**PASS — `VAULT_PROTOTYPE_VALIDATED`; Day 6 Step 2 COMPLETE.** This is the separately Owner-authorized direct DEV execution path using the existing `edp-lab` Databricks profile, shared Warehouse `589e80595c7c8cb8`, and the eight existing Delta tables in `workspace.edp_lab_day6_vault_proto`. It does not claim protected V2 Broker, Executor, eligibility, grant, or signed receipt coverage. Full C2000 Step 3 was not started.

## Pinned scope and actual results

The run checked the accepted C2000 Freeze SHA-256 `324ca5e416adabc443d18d8066fbccdf137f4cb50aa20934e645615f4ee77ff3`, input manifest `ee7adf7c39d3fc702692d3b5fe8561d14ecdac33c592f823ae0ddea4d4daf613`, projection `993e9588617ea5132d80bf3dfc84cacd5e382f01a50adcb86c97ee141a11efbb`, load plan `241ed0e10e041587bcd132f667960f7e7f1521c537275460c2f2ab08647c931f`, and unchanged Vault Contract V1 `681c3f6a9a4446b5357c3ab6c6534e6fd5b8cf944f967ea9ab27dcc2c8b5aabe`. It rechecked the three RAW ZIP/member hashes and the retained M1/M2 projection before the first write. Sources were `SRC000005` (10), `SRC000054` (9), `SRC000064` (108): 127 DATA occurrences.

| Delta table | Persisted rows | Exact readback |
| --- | ---: | --- |
| `h_filing` | 20 | PASS |
| `h_concept` | 24 | PASS |
| `l_fact_slot` | 76 | PASS |
| `r_source_occurrence` | 127 | PASS |
| `s_fact_assertion` | 127 | PASS |
| `s_num_m2_value` | 127 | PASS: 125 `VALID`, 2 `BLANK` |
| `r_load_event` | 127 | PASS: each `ADMITTED`, exact occurrence coverage and input hash |
| `vault_reject_quarantine` | 6 | PASS: six synthetic negatives only |

The readback compared all nonstamp columns of the seven prepared plan tables against the pinned expected rows, including Hub/Link/Satellite keys, source occurrence locator, RAW/member/binding hashes, original lexical fields, M1 versions, M2 lexical and decimal values, and the six quarantine identities/reasons. The event table was checked for all 127 occurrence keys, `ADMITTED`, input manifest hash, and actual occurrence write statement ID `01f1cfc5-aff2-1200-a619-9300506bca95`. The six negatives were not promoted to business rows.

## Statement audit and bounded recovery

| Action | Databricks statement ID | Outcome |
| --- | --- | --- |
| Filing Hub | `01f1cfc5-990e-1336-8ec6-c3a0d47c7b1c` | SUCCEEDED |
| Concept Hub | `01f1cfc5-a231-1b79-961d-07c0841a8b38` | SUCCEEDED |
| Fact Link | `01f1cfc5-a813-1503-bb29-72d6aea7e159` | SUCCEEDED |
| Source occurrences | `01f1cfc5-aff2-1200-a619-9300506bca95` | SUCCEEDED |
| Fact assertions | `01f1cfc5-b66b-1b7e-8f6e-05a60cf4e283` | SUCCEEDED |
| M2 values | `01f1cfc5-bcd0-1e9e-a407-494eb27936fe` | SUCCEEDED |
| Synthetic quarantine | `01f1cfc5-c26a-1712-9bd1-d56841db53e0` | SUCCEEDED |
| First load-event SQL | `01f1cfc5-c66a-1b95-9e60-81c5a5584fe3` | Terminal FAILED: `INVALID_INLINE_TABLE`; no rows persisted |
| Load-event reconciliation count | `01f1cfc5-d093-1a52-9836-55c8aa692c50` | SUCCEEDED; 0 rows |
| Repaired load-event SQL | `01f1cfc5-fa5d-153a-9322-a0cdc66cf315` | SUCCEEDED; 127 rows |

The first event SQL placed a `decode` expression inside a `VALUES` cell, which Databricks rejected before execution. Its exact statement was queried and found terminal `FAILED`, and the event table read back empty. The repair put hex literals in `VALUES` and decoded them in the source projection. The seven successful load stages were not replayed. The subsequent workflow reconciled all eight counts before the event write and then completed exact persisted readback. The initial sandbox attempt failed before any SQL because its profile token was unavailable; its journal records zero statements.

The retained failed-statement response `failed-event-status.json` has SHA-256 `0fcbf65c75726f3975a110fb7aaa526602d459873630eba4bf2c040b99dab8b2`; the zero-row count response `failed-event-zero-count.json` has SHA-256 `b43bf5656ff20b3b5906d8daee23454f98c85b9f360542be4485f612fe3699d4`. Both are in the ignored local evidence directory and were fetched by statement ID without submitting new SQL.

The successful workflow journal records 50 SQL submissions, including the terminal failed event statement and readbacks. One additional manual read-only reconciliation query makes 51 total, below the 60-statement cap. Its start and completion times are `2026-10-24T16:10:50.845919+00:00` and `2026-10-24T16:14:54.215854+00:00` (about 244 seconds), below 3,600 seconds. There was no automatic retry of an uncertain write.

Ignored local evidence is under `runs/day6-vault-c2000-step2-live-v1/`. The completed journal SHA-256 is `ae31ec211d48133c06c676bdb1fe5486d74d45e38550bde77bb14ebb9e519864`; the zero-submission sandbox journal SHA-256 is `4f0efe6778484610d31fa67a46ddd97d1961e876d25d5c3f50de74ca99e9a5a6`. The eight exact readback response hashes are retained there. [Evaluation V2](../metadata/evaluations/day6_c2000_vault_step2_v2.json) records the final outcome; the original C1500 partial [evaluation V1](../metadata/evaluations/day6_vault_prototype_step2_v1.json) remains historical.

| Exact readback response | SHA-256 |
| --- | --- |
| `exact-h_filing.json` | `623dd178f19b199ec9982bb7f03a481c4f7e118c93e2b7da7714aaa8495b5877` |
| `exact-h_concept.json` | `f324441ca91bff485e4bf6a17efb67acdf0c19f05c63a6828d48b0d0415bfe71` |
| `exact-l_fact_slot.json` | `fa3f788dc55c0fac6f370bf77daef7c733ee665c8653426ed9898ebf0dcdce9a` |
| `exact-r_source_occurrence.json` | `8d491ae5296f3f44e27c34a39da4f1c6698d3f0b162d5dd2fdf391358636376e` |
| `exact-s_fact_assertion.json` | `921e6dceb13e1ba4dd30d75775b1a8505a679144022f96ad1ccfd2eab9ee1ba5` |
| `exact-s_num_m2_value.json` | `c8474944ac4239e86036e3d1ec991111261cbca0a03bc5499a10262a003a43e7` |
| `exact-r_load_event.json` | `1244cde03c94db6379f1925da67b100d324b987cb7bf1eb57b26b43807f32c05` |
| `exact-vault_reject_quarantine.json` | `a10b5feb48a3a0d74b4b620a21b0cd2d3c4297f7c4cff4ba9ad051cc9c7d165f` |
