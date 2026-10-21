# N450 profiling and B1 model-fit assessment

Outcome: **449 FITS_EXISTING_MODEL; 1 HUMAN_UNRESOLVED**. No M2 requirement has
been established. The admitted N450 remains 450 members and frozen C750 remains
750 members; holding a source for processing does not change physical membership.

Current owner authority is the explicit “DAY 3 — STEP 2: N450 Profiling + B1 Model
Fit” instruction. The installed Admission/Freeze grant is used as sealed physical
registration evidence, not as parser or processing authority. The read-only driver
reuses the existing C300 engineering inspector and occurrence validator plus
`edp_lab.profiling.tools`. It creates neither an activation grant nor CLEAN output.
The complete input set is checked against Universe v1, exact admitted bindings,
frozen C750, paths, sizes and hashes before observation. No synthetic-source reader
or alternative decoding profile is used for registered RAW.

## Actual coverage

| Observation | Coverage |
| --- | --- |
| Full-byte structural scans and source/member/schema fingerprints | 450/450 sources |
| Existing strict UTF-8 Daily Master profile | 449 PASS; 1 held |
| Ordered schema | One five-TEXT-column schema across all 450 headers |
| Complete eligible-source lexical/occurrence checks | 1,891,175 DATA occurrences; 9,455,875 fields across 449 sources |
| Bounded statistical profiling | Three complete selected tables; 11,683 DATA occurrences; 15 column profiles |
| Selected statistical sources | SRC010001, SRC010226, SRC010450 |
| Semantic NULL-dependent statistics | 135 metric positions NOT_COMPUTED |
| C300 profiling replay | None; frozen Day 2 evidence reused |

Statistics select the first, middle and last passing source in approved roster
order, bounded to at most three whole tables and 20,000 DATA records per selected
table. Metrics are exact within those three tables, not estimates or full-population
claims about N450. The selected tables contain 179 excess literal duplicate rows;
all occurrences are retained. No business key, FD search, NULL meaning, numeric
conversion or date interpretation was inferred.

All 450 files contain 1,902,855 physical records and 1,899,705 candidate DATA lines
under the existing seven-line framing rule. The held file accounts for 8,530
candidate DATA lines; 8,529 decode successfully and one fails. The entire binding
is held. Those partial successes are not promoted to a completed profile or partial
CLEAN population. Per-source evidence preserves the partial counters.

The observation run took **13.468 seconds**; measured peak process RSS was
73,285,632 bytes on this macOS host. This is a local source-observation/profiling
measurement, not a Databricks CLEAN or platform throughput benchmark.

## Held source and exact evidence

`SRC010128`, `master.20120104.idx`, physical identity
`d0dc0ef10dabfaff1d02bb75b5efae1ef047e938418f08fb8cb92c1cb332e7f7`:

- RAW/member SHA-256: `5869c2d2e76ec56302291d7812add9d8cc1a0b9788478050344e40d14927e71d`.
- Physical line 6215, record byte offset 516310, length 114.
- Invalid UTF-8 byte `0xc3` at record offset 34 / absolute offset 516344, field ordinal 2.
- Record SHA-256: `0204d6e8cca1a45efd0ef5956cfe49766ea7ee5a1e3143e3d5a60a7eaa60591a`.
- Existing schema, framing, RAW hash and source identity remain valid; text decoding
  does not. Alternate encoding, replacement characters and byte repair were not used.

This establishes an unsupported source occurrence under the current profile. It
does not establish the publisher's intended encoding or distinguish source corruption
from an unregistered encoding. Therefore SC7 is **HUMAN_UNRESOLVED**, with the whole
source held. Owner alternatives are to retain the hold, review source/encoding
provenance before any scoped parser change, or—only if arbitrary invalid-byte field
values must be accepted—review a representation extension. None is implemented.

## B1 against unchanged M1

| Dimension | Assessment |
| --- | --- |
| Parser and format | The exact existing UTF-8/literal-pipe profile fits 449; no new header schema; one invalid UTF-8 binding held |
| Record and field representation | Existing five ordered string fields; original framing and byte locators retained; no CLEAN records written |
| Lexical preservation | Strict decode/split/join byte reconstruction passed for every DATA occurrence of the 449 eligible bindings; no normalization or NULL mapping |
| Multiplicity | Existing iterator emits every occurrence with a distinct source-line/byte locator, including equal-looking rows |
| RAW lineage/provenance | Exact sealed physical/registered bindings, RAW/member/profile/code fingerprints and record locators retained |
| Identifiers, dates, units, relationships | Source strings preserved; canonical namespaces, business mappings, date alignment and economic-unit semantics remain unmodeled |
| CLEAN/QUERYABLE contracts | Existing M1 STRING fields/ordinals and BIGINT locators can represent the 449 bindings without a model change; native execution compatibility has not been run |
| Lossless | Input lexical/occurrence invariants support fit; N450 output Lossless, FIN evaluation and Stability are NOT_RUN |

The reviewed C300 registry has 198 Daily Master bindings with the identical ordered
header. Its parser-code SHA exactly matches the current reused parser:
`12d794670b95f6631175840f2885790141cc244f4fcfe812d4d74f156e488b06`.
The frozen Day 2 marker/contracts and original parser approval packet/registry
were verified as metadata references; C300 RAW and profiling outputs were not replayed.
Frozen Day 2 partial/statistical/semantic acceptance limits remain unchanged.

## Processing eligibility and artifacts

**449 exact bindings are model-eligible for unchanged M1 in Step 3.** The explicit
ordered ID list and the single held binding are in
`metadata/evaluations/n450_b1_v1.json`. This assessment does not activate a native
N450 parser/runtime or extend the installed Admission/Freeze grant. Step 3 still
requires its execution scope and runtime integration; no Step 3 action was run.
The one-source hold must survive downstream failure accounting; do not silently
remove it from the frozen N450 or C750 populations.

- Reproducible driver: `scripts/observe_n450_b1.py`.
- Detailed, gitignored observations: `runs/n450/b1-v1/summary.json`, `sources/*.json`,
  and `statistics/*.json`; the assessment indexes their exact fingerprints.
- No new profiling framework, FD engine, model version, financial semantics,
  diversification, source mutation or RAW network transfer was introduced.
- Focused fixture checks: eight pass, covering scope denial, changed bytes,
  duplicate/locator fidelity, malformed width and the observed UTF-8 failure shape.

Stop after B1. Continue the 449 compatible bindings only under a later Step 3
instruction; keep SRC010128 held pending an actual source/encoding decision.
