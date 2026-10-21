# C300 NUM exception triage V1

Status update: DEC-000007 explicitly APPROVED by the user. See
`docs/c300_num_recovery_authority_v1.md` and append-only DEC-000008.
Recovery job `653857229258835` is running in new exclusive outputs.
The proposal and historical diagnosis below are retained as originally recorded.

Original proposal status: PROPOSED remediation; no parser change or new binding activation approved at proposal time.
All original evidence and the twelve BLOCKED outcomes remain unchanged.

Existing packet: SHA-256
`3873e9d07e4bcc2f357f940d05cf4fc5dc1262358b641d1debba2ef117910e05`.
Detailed bounded witness evidence: `runs/c300-m1/exception-triage-v1/evidence.json`,
SHA-256 `64f1cc12cb9d21ff53b5f4e26f785db234190961d31f4ba92bc960fb58ac9219`.

## Evidence and cause groups

All twelve share an observed strict-literal width failure: extra TAB bytes inside
a double-quote-wrapped seventh token (`segments` in the registered header).
Every first-error witness was retrieved by its existing byte locator after parent
RAW SHA-256 verification; each record hash matched its historical witness. No
full blocked member was parsed and no unrelated historical checks were rerun.
The prior full-scan width histograms are reused, not new accepted populations.

| Binding (`num.txt`) | Existing literal width: occurrence count | First witness line / offset / length | Verified record SHA-256 |
| --- | --- | --- | --- |
| SRC000052 | 10: 3543335, 11: 51, 33: 6 | 16618 / 2242337 / 261 | `305b28380f1e1ac4ad523055ff7d5f27ce9befd23fdd864707a3d2106a8223e7` |
| SRC000053 | 10: 3428660, 11: 10 | 312006 / 42739663 / 181 | `ef74cdc6c58446981899513cebc145171169eb4ec68a4449b96f68f769b81e10` |
| SRC000054 | 10: 3393980, 11: 10 | 337467 / 46589850 / 244 | `2f73b2ed063264ce0a4d0a9a67997a97614c623ecaf234981029d5e89072008d` |
| SRC000056 | 10: 3699112, 11: 12 | 880015 / 122336934 / 190 | `4a849463e2a414df4ba240477518b14fb3c86e0313c0648ed962b1e463e7c52a` |
| SRC000057 | 10: 3428685, 11: 9 | 398796 / 56611025 / 186 | `1ea9488733a6b2ebb91fe686ba23316f78e806320523dbd178be88bd539942db` |
| SRC000058 | 10: 3426152, 11: 18 | 325969 / 45879243 / 197 | `4b386698e40bfcd0302f0e039a0469b586ea9435622e3e0ee0d015ade9103c13` |
| SRC000059 | 10: 3521847, 11: 31 | 84619 / 11934758 / 197 | `141eeaaf10c87208c8ed571c3ec763a6ea0339b303f8b182fc5d4d917f6cff7b` |
| SRC000060 | 10: 3705058, 11: 20 | 64698 / 9197940 / 287 | `612ab6ed87ec08168f042bbd29e65106ed7e3fc967568d78c58947e7aa854ee5` |
| SRC000061 | 10: 3658521, 11: 30 | 180486 / 26152384 / 156 | `43b5a19b63c5f48dd88ef952723964732cef0e30d0d05e5e1e8b08548adc20be` |
| SRC000062 | 10: 3409904, 11: 26 | 1289874 / 203090789 / 287 | `e697a3df237b5f28bcfa8133dfd820160a6796bf585dfb7c6e6a5bc48ba39fe2` |
| SRC000063 | 10: 3720033, 11: 42, 12: 6 | 176125 / 25616549 / 281 | `6a6747211108abfbd9e6754b862d12065623ca0a45c5437d40e9993d0140b4c0` |
| SRC000064 | 10: 3832955, 11: 22 | 231253 / 34068967 / 273 | `96c699e2f7791b9079e3069eed093071c5f412c17cb798e00036ffac5bc57f9c` |

Ten bindings show only width 10/11; SRC000052 also shows width 33 and SRC000063
also width 12. These are severity subgroups of the same observed delimiter/quote
interaction, not proven separate causes. Existing diagnostics show UTF-8 decoding
and physical line locators; none supports an encoding failure. The first witnesses
support unsupported format variation relative to the literal parser configuration.
They do not prove all anomalies are well-formed quoted data. Source malformation
or unresolved quote ambiguity in other occurrences remains possible.

## Smallest proposed source-scoped resolution — human decision required

Authorize a supplemental `C300_FSDS_NUM_QUOTE_BOUNDARY_V1` rule for exactly these
twelve unchanged source/member/hash bindings. Recognize a quoted lexical token
only when a double quote begins the token. TABs inside its balanced wrapper are
content; an unescaped closing quote must be followed by delimiter/end-of-record.
Paired internal quotes remain original bytes; do not unquote or unescape them.
Keep every token's exact lexical spelling, including wrapper quotes and embedded
TABs. All ten original ordered header positions must result. No multiline record
support, repair, trim, cast, NULL interpretation or field reassignment is proposed.
Reject unmatched/ambiguous quote structure and non-ten-field outcomes explicitly.

First validate every occurrence in the twelve scoped members with new versioned
rules and exact locator/hash accounting; conditionally activate/materialize only
bindings completing strict validation under explicit supplemental authority.
Reprocess affected members into new exclusive CLEAN outputs, rerun their actual
Lossless 1–5 and lexical-only 6 inventory, then gate them independently. Never
rewrite the 720-binding approval packet, original parser evidence, RAW or runs.
The M1 table schema stays unchanged; parser/profile versions and binding hashes
must identify the supplemental scope. New rule/code and replay evidence are pinned.

Alternative: retain BLOCKED while obtaining exporter serialization authority or
further bounded diagnostics. This preserves integrity but leaves the twelve
unrecovered. Splitting first/last TABs by assumed meaning, dropping bad rows and
silently applying ordinary CSV unquoting are not proposed.

## Remediation ledger

For all twelve: initial failure and locators above; root cause supported for the
first witness only; proposed resolution above; human decision PENDING; active
human review time UNMEASURED; parser/model changes NONE; reprocessing cost
NOT_STARTED; final outcome BLOCKED pending review. Diagnosis wall time is
1.868 seconds (including twelve parent-hash checks and bounded witness retrieval).
Approval-response elapsed time must not be presented as active human review time.
Unaffected 720 bindings continue under their existing approved rules.
