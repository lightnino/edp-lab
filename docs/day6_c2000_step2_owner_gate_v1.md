# C2000 bounded Vault Step 2: Owner gate packet

**Historical and superseded for the DEV prototype.** The Owner subsequently authorized the exact bounded C2000 sample to run through a separate direct DEV profile path without the proposed `LIVE_VERIFIED` receipt, eligibility registration, Broker grant or Owner scope signature. The executed result is in the [Step 2 closeout](../reports/day6_c2000_vault_step2_closeout_v1.md). This packet remains an audit record of the earlier proposed protected route, not a current execution instruction.

**Decision requested:** approve or decline only the three-source, 127-DATA-occurrence, six-synthetic-negative `BOUNDED_PROTOTYPE` in `workspace.edp_lab_day6_vault_proto`. This packet is evidence and a proposed scope; it is not a signature, eligibility registration, grant, or permission for a Delta write. Full C2000 integration remains outside this decision.

## Reviewed pins

| Item | SHA-256 or exact value |
| --- | --- |
| Installed 0A receipt, Owner Terminal PASS pin | `04b555202469cd1aa9423da7d6f7639900202693c986859e1b229f3d1427c7b2` |
| Installed signed policy envelope, separately verified read-only | `1d38ae7d26ebeaaf3ff2a113adb09e4c27a261244446b4e6309600d60e58dca5` |
| Reviewed policy proposal | `7200b417a3321580147c8d135eef99868c5fb79dbe78ae236f54266240fa3316` |
| C2000 input Freeze | `324ca5e416adabc443d18d8066fbccdf137f4cb50aa20934e645615f4ee77ff3` |
| C2000 source roster | `2a72b8f8483e2181a3112a26b5d68d702b92308def6e74978838b155cfd85312` |
| Day 5 Databricks result freeze | `942fa887ceea8cf5c9bc64c603c2044e1b643b01fcbc29909ce264c024b69374` |
| Day 5 signed P13 receipt | `e1023289fedb3b682e0afe33bc350997e5d84c5aa27e9d00bf34bc760fe93830` |
| Day 5 protected live-evidence copy / queue contract | `512cecc9170f9c3a6abe46da2d21bce5a5eedb995d89f334d8be9a299ea6aea2` / `e43cf9984e1c54b17cbdc44917954bf802acba3241168ea353b302ec41076e34` |
| Vault Contract V1 / serializer | `681c3f6a9a4446b5357c3ab6c6534e6fd5b8cf944f967ea9ab27dcc2c8b5aabe` / `c80c43e299424947d1d4c6bcd2211235bebd79efc03923e2a9db55bc682a659a` |
| Local input / projected manifest / load plan | `ee7adf7c39d3fc702692d3b5fe8561d14ecdac33c592f823ae0ddea4d4daf613` / `993e9588617ea5132d80bf3dfc84cacd5e382f01a50adcb86c97ee141a11efbb` / `241ed0e10e041587bcd132f667960f7e7f1521c537275460c2f2ab08647c931f` |
| Historical M1 sample response / row manifest | `f38bbf0dc99644bdc9057f5815ce35d01d39dfa9ecd9876385d038024e572d77` / `fd73e3b25ddd3d88261f895fb0b84ae7c3206f02344d962950e5c0e315c6906f` |
| Historical M2 projected manifest | `a73d325c814ebcb4bbb7d4b27f8925e7dd7702af64192fb315df077a9f89a41d` |

The [0A evidence](../reports/vault_0a_v2_evidence.md) gives each RAW ZIP/member hash and the read-only verification results. The exact sample is `SRC000005` (10 rows), `SRC000054` (9), and `SRC000064` (108). The plan has seven stages, six synthetic rejects, zero automatic write retries, a 60-statement cap, a one-hour cap, and one existing 2X-Small single-cluster Warehouse. The [scope proposal](../metadata/operating/day6_c2000_vault_v1/scope_approval_proposal.json) and [run proposal](../metadata/operating/day6_c2000_vault_v1/run_plan_proposal.json) remain unsigned and ineligible.

The P13 receipt signature was reverified with the existing protected verifier public key (SHA-256 `88a3101fa3039356c537ac0146baa78ef116dd05025f71c99f301a7f6f69b3da`). The saved M1 statement was `01f1cf23-e739-1d06-87d3-293a7fee758b`, with 127 rows and canonical row SHA-256 `366ca59ac251fa54d0a2c97ebdd8f9cacbcf773231c61aa20a504196a3cf31dc`. The retained M2 projection equals fresh local application of the approved bindings. Both retained evidence files remain ignored under `runs/`; their hashes above identify the exact reviewed bytes.

## Protected `LIVE_VERIFIED` freeze procedure for Owner review

1. In the Owner Terminal, use owner-controlled protected trust. Rehash the C2000 input Freeze, its four files, source roster, Day 5 result freeze, signed P13 receipt, and protected live-evidence copy. Verify the P13 receipt signature against the existing `/private/var/db/edp-lab/trust/verifier_ed25519_public.pem` whose pinned SHA-256 is `88a3101fa3039356c537ac0146baa78ef116dd05025f71c99f301a7f6f69b3da`. Require the receipt's C2000 cohort, input-freeze hash, view ID, and live-readback claims to match the freeze. A historical signed receipt alone is insufficient for a fresh `LIVE_VERIFIED` claim.
2. Make only read-only live calls on the existing Warehouse and Unity Catalog. Confirm `workspace.edp_lab.o_c2000_m2_result_frozen_day5_v1` remains a VIEW with table ID `a9b7d2ab-4d9d-462a-b046-7f04bf144773`, references `workspace.edp_lab.o_c1500_m2_result_frozen_v1`, and references `workspace.edp_lab.clean_n500_m1_records_day5_v1 VERSION AS OF 0`. Confirm that CLEAN table and the N500 roster have the pinned UC IDs `7f55b1de-c174-47a0-8dbd-2139dbd75f50` and `2e49534e-278c-4e69-99a0-25f83ad8849f`; compare version-0 history and readback counts to the pinned Day 5 live evidence: 2,037,138 new CLEAN records, 500 new sources, zero bad-width records, and 321,188,377 combined source-preserving occurrences. Save statement IDs and exact returned values in the protected receipt evidence. Any mismatch is a stop, not a tolerance decision.
3. Recheck the three ZIP/member hashes and the pinned M1/M2 version-0 sample against the local hashes above immediately before handoff. The protected verifier must read the reviewed `input_manifest.json` and `load_plan.json`, require those exact hashes, and stage them as root-owned `artifacts/c2000-input-v1.json` and `artifacts/c2000-load-v1.json` with protected directory/file modes. Rehash after the copy. The ignored `runs/` files are evidence, not trusted executable pins.
4. Only after steps 1–3 pass, the independent protected verifier may create one new `receipts/c2000-freeze-live-v1.signed.json` with `authority: protected-verifier-v1`, `status: LIVE_VERIFIED`, `cohort_id: C2000`, `freeze_sha256: 324ca5e416adabc443d18d8066fbccdf137f4cb50aa20934e645615f4ee77ff3`, exact result, source, input and plan hashes, UC IDs, version-0 readbacks, statement IDs, verifier timestamp and signature. Verify the completed envelope against protected trust and record its SHA-256. Do not relabel or reuse the Day 5 P13 envelope as this new receipt.
5. Present that receipt hash and the [scope proposal](../metadata/operating/day6_c2000_vault_v1/scope_approval_proposal.json) to the Owner. If approved, the Owner signs a fresh `EDP_VAULT_COHORT_SCOPE_APPROVAL_V1` for `C2000`, `BOUNDED_PROTOTYPE`, the exact three sources, contract/rule, Freeze, roster, protected input/plan pins, 127/6 limits, and the new `independent_freeze_receipt_sha256`. The protected eligibility registrar checks both signatures and pin equality. Registration and grant issuance are later actions; no such action is authorized by this packet.

## Owner Terminal action at this stop

Review this packet and the three source rows/hashes in the [0A evidence](../reports/vault_0a_v2_evidence.md). Return the complete one-line JSON from the already run read-only acceptance probe for durable evidence, then explicitly **approve or decline this exact bounded C2000 Step 2 scope** and authorize the protected read-only freeze verification in steps 1–4. If the scope is approved and live verification passes, the resulting signed `LIVE_VERIFIED` receipt SHA-256 must be returned before the separate owner scope signature can be prepared. No grant, Delta write, or full integration should be started at this gate.

The only current evidence discrepancy is that the complete Owner Terminal acceptance JSON (including `runtime_files_verified`) was not provided; the PASS status was reported and the signed policy hash was independently verified. No hash mismatch was found in the local C2000 artifacts or three RAW ZIP/member byte checks.
