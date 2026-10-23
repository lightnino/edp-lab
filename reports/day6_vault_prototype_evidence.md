# Day 6 Step 2 — C1500 bounded Vault prototype evidence

**Current outcome: `DAY6_STEP2_PARTIAL` / `PROTOTYPE_BLOCKED_WRITE_AUTHORIZATION`.** The owner-approved one-time [C1500 exception](../metadata/authorizations/day6_vault_c1500_prototype_exception_v1.json) is separate from D1–D5. The original [contract](../docs/vault_load_contract_v1.md) SHA-256 remains `681c3f6a9a4446b5357c3ab6c6534e6fd5b8cf944f967ea9ab27dcc2c8b5aabe` and was not edited.

## Step 2.1 — input evidence

The C1500 freeze's three membership files match its recorded SHA-256 values: `C1500.bindings.json` `810c6898df0cb5e5c478305f71c190ffe4a7c7a2bb40133efa79a16de630e703`, `C1500.csv` `d3b02109268ce77bcd07f6f5f455fb7e4a1989319b2cf60867e372ffc3b87ae5`, and `C750.original.csv` `81162007d42146333e2822d8c9ed2a720ebdd36422db6649291e51bd25e0d85d`. The O_C1500_M2 live freeze is `FROZEN_IN_DATABRICKS_SOURCE_PRESERVING`; its physical M1 refs pin version 0. The initial read-only binding query `01f1cf23-776f-1e12-a9fe-095832b05f64` returned the approved source hashes and COMPLETE rows for all three selected bindings, while alternate main/recovery rows are BLOCKED.

| Source | RAW SHA-256 | NUM member SHA-256 | Binding SHA-256 | Pinned M1 binding |
| --- | --- | --- | --- | --- |
| `SRC000005` | `e63b781a5e57e55d68e110a06d3f697e942a60e17f093bbdc1a16ac7152a7df5` | `f1660e54b9f9d98de3ff73b4cff0129108ad5ed608b35ec413117f528e1be570` | `4c31160a13729f427e15e60f8f7175e8312596237c6b1617df703f144bc5fade` | main recovery v4 full, version 0 |
| `SRC000054` | `f028f1e8d24313e7619aa87c7c683a459452e7e81a8e5ba72d7ce39ddf62bda9` | `72b948228b2d692e8e36353e8c02c9a7845fa5ddbc7d644b8f7b4661db05d4ba` | `54c47c4f0d6793d327c3bb998d6c8b6a1393a819014c601a0f0a55d53cad8fd5` | NUM recovery v1, version 0 |
| `SRC000064` | `2b36ac3850c022cf19edd882e31c3c453c7666677b9fdd2e1f7748fdb5768c6e` | `29154c19d61e87ed5a143e800eb56a848ee578e76ea55473c26d3a9c060fca51` | `e0783a95487f7765df28d162ad80d437abc2983a77bd4fff0baacee8a0ffee6a` | NUM recovery v1, version 0 |

Read-only selection statement `01f1cf23-e739-1d06-87d3-293a7fee758b` returned exactly 127 DATA rows and was not truncated. Its SQL SHA-256 is `03d04d9835328b58f181b78fd8e4b856c535f43d74f4c5a3d68793044ff7c939`; saved row SHA-256 is `366ca59ac251fa54d0a2c97ebdd8f9cacbcf773231c61aa20a504196a3cf31dc`. It contains 102 Assertions in 51 full-context collision groups plus 25 normal rows, with distinct Contexts, Concepts, units and segments. All seven named source lines and exact historical byte offsets were present. `SRC000054` line 337467 retained its embedded literal TAB in the quoted segment. The ignored manifest preserves every selected source line, offset, length, all ten ordinal/name/lexical fields, run and binding, and RAW/member hashes. No RAW ZIP bytes are present in this worktree; the prior Step 1 RAW verification was reused, while this run checked the pinned M1 representation. Fresh byte-level rehash of these three sources is outstanding.

## Steps 2.2–2.5 — boundary and results

Read-only preflight statements `01f1cf23-dc22-1773-8421-a4839e029482`, `01f1cf23-de21-141b-81d8-6a7e375d2278`, and `01f1cf23-dfaf-127f-9725-7ee1bb3e39e1` showed principal `chengzhu13@gmail.com`, only `USE CATALOG` in the shown workspace catalog grants, and no `edp_lab_day6_vault_proto` schema. `DESCRIBE DETAIL` statement IDs `01f1cf23-e0f5-1a88-9ab6-251790c7a798` and `01f1cf23-e2f4-1d33-a586-b42562227f82` matched the two recorded M1 Delta IDs. Binding-version statement `01f1cf24-239b-119f-8665-936a02674e8e` confirmed actual M1 parser/profile/model/rule versions.

There is no configured protected trust directory, broker socket, signed prototype grant, protected write adapter, or verified isolated `CREATE SCHEMA` permission. No Databricks write was submitted. The [eight-table migration and write plan](../docs/vault_prototype_v1.md) is reviewable but undeployed. No actual load counts, replay, quarantine rows, persisted hash parity, Delta readback, or resource usage for writes exist.

Local projection produced 20 Filing hashes, 24 Concept hashes, 76 Fact Slots, 127 unique occurrence/Assertion hashes, 51 collision slots / 102 collision Assertions, 50 differing-value groups and one exact-equal payload pair. M2 local outcomes are 125 `VALID`, two `BLANK`; these are **not** persisted M2 rows. The pure projection explicitly tests field order, missing BK, member SHA, archive member, payload drift, same-slot multiplicity and blank typed scope. Synthetic negative controls have not been run in Databricks or quarantined there.

Read-only sample query client wall time was about 48 seconds. Its retained Databricks response contains no compute-unit metric. The warehouse ID was `589e80595c7c8cb8`. The full-member Lossless1–6 gates and C2000 integration are outside this sample; sample-scoped persisted Lossless checks remain pending because the Delta prototype was not loaded.

## Remaining gates

An independent authority must provision or identify a permitted isolated Dev Schema and protected signed operation path, with bounded compute and table scope. The three RAW bytes must be reverified at their pinned hashes and selected locators before promotion. Then deploy, load, replay, run controlled negatives, independently read back every Delta table, record statement IDs and resource counts, and verify all source/identity/Lossless gates. Until those steps pass, the result is `DAY6_STEP2_PARTIAL`.

## Step 2.6 — local regression

`uv run pytest -q tests/vault`: **15 passed**. `uv run pytest -q`: **562 passed, 82 skipped in 89.43s**. `uv run ruff check .`: **All checks passed**. These tests cover local projection and synthetic rejection paths only; they do not establish live Delta persistence. Commit `532850f` was pushed on `day6/vault-prototype-c1500`; [PR #61](https://github.com/lightnino/edp-lab/pull/61) is open against `main`. Both observed `deterministic-smoke` CI jobs passed before this documentation-only evidence update. The complete diff contains no Day 5 or Step 0 edits; `docs/vault_load_contract_v1.md` is byte-for-byte unchanged.

Day 6 Step 0: `WAITING_C2000_RESULT_FREEZE`. Day 6 Step 3: `BLOCKED_BY_STEP0_AND_STEP2`.
