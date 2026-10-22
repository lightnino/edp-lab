# Bounded Agent V1 FD/Key/Grain follow-up

Status: **AGENT_V1_GAP_CLOSED**, limited to the checks and population below. This Day 4 addition leaves [Day 3's historical NOT_IMPLEMENTED report](c300_fd_regression.md) unchanged. No permanent business FD, business key, canonical identity, mapping or production join is approved.

## Reuse and minimal addition

Existing `candidate_key_scan()` already checks supplied composites, lexical uniqueness and proper-subset minimality; it is reused unchanged. Agent V0 already provides deterministic read-only orchestration and observation/approval separation; no runtime or authorization layer is added. Existing V2 proposal states, validators and evidence fields are reused unchanged.

The missing function is `declared_fd(table, X, Y)`: exact literal tuple consistency for a caller-declared determinant/dependent set. It returns exact group counts, bounded actual counterexamples with two distinct Y tuples and source locators, duplicate occurrence accounting and hypothetical self-join pair counts. It neither discovers dependencies nor normalizes schemas. It uses the existing SourceTable, authorization guard, evidence envelope and hashing. A small helper attaches these observations to existing V2 reports and cannot promote canonical identity or a business FD/key.

## Real evidence and outcomes

[Observations](../metadata/evaluations/agent_v1/observations_v1.json) reuse four projected fields from **five existing cached SRC000004 FSDS SUB samples**, selected by the original profiler. Profile SHA-256: `4bcce97ed2191e512f29e03ae8a0bf04bea9bc7af016d562f9b0f9a2cb193469`; the file hash and each selected column envelope's canonical fingerprint were verified before extraction. Samples were aligned by identical complete source locators, not zipped by position. No RAW file was opened or replayed for this evaluation. The initial evidence inspection also checked an existing frozen M1 witness archive, but no NUM population was needed or included in the final experiment.

Source: `SRC000004`, `data/raw/sec/2010q2_fsds.zip!sub.txt`; RAW SHA-256 `25f416b020fd3e62a67dbf8c6522c9f239e716099b61cf5d05a59a91ffdef1f1`; member SHA-256 `fca0ff4bf873b46245ac3ca3524f6be6083852cdc7e97a12f307df636834a3e8`. Line/byte locators, exact accessions and all four observed fields are persisted in the observations. These are partial evidence projections, not committed RAW rows. This existing GOLD source is supplementary evidence, not a new C1500 admission.

| Line | Observed CIK | Form | Period |
|---|---|---|---|
| 65 | `797468` | `10-Q` | `20100331` |
| 84 | `1453090` | `10-Q` | `20100331` |
| 281 | `9892` | `10-Q` | `20100331` |
| 308 | `1324404` | `8-K` | `20091231` |
| 341 | `1316631` | `8-K` | `20091231` |

[Exact results](../metadata/evaluations/agent_v1/results_v1.json):

| Declared check | Actual bounded result | Limit |
|---|---|---|
| `adsh → (cik, period)` | Literal PASS: five determinant groups, zero violations | All X values distinct: no repeated-X positive evidence; not a population FD |
| `form → cik` | VIOLATED: two groups; `10-Q` has three distinct CIKs, `8-K` has two | Actual lexical counterexamples; no semantic FD proposed |
| Existing key scan: `adsh` | Mechanically unique on five rows | Semantic eligibility NOT_COMPUTED; no business key |
| Existing composite `(form, period)` | Not mechanically unique | Three and two occurrences per tuple |
| Existing composite `(adsh, period)` | Unique but not minimal | `adsh` alone is unique on this bound |
| Grain/fanout on `form` | Counts 3 and 2; hypothetical literal self-join produces `3²+2²=13` pairs from five occurrences | Eight extra pairs; no join executed; no SQL NULL semantics implied |

Both `10-Q` counterexamples (different CIKs at lines 65/84/281) and `8-K` counterexamples (lines 308/341) retain source locators. Shared form and period cannot justify merging registrants. No TAG, NUM or PRE population, cross-table cardinality, permanent grain or enterprise business key was evaluated.

## Duplicates, NULL and controlled tests

Real source NULL semantics remain unknown: the consistent FD has `literal_status=PASS`, overall `status=AMBIGUOUS`, interpretation UNRESOLVED. This does not negate its bounded literal observation. Exact equality never normalizes case, whitespace, leading zeros or missing values; blank and declared NULL tokens are retained and counted. Explicit missing values (`None`) remain separate from lexical text. No row is excluded or deduplicated.

Clearly labeled synthetic tests cover consistent repeated `(X,Y)` occurrences, conflicting Y values, exact group counts with truncated witnesses, declared/unknown NULL rules, blank/whitespace and explicit missing values, empty populations, denied authorization, parse failure and malformed requests. Equal duplicate rows do not violate a value FD but can prevent occurrence-key uniqueness and increase hypothetical join cardinality. PASS means only literal consistency; empty populations return NO_EVIDENCE. Unknown NULL rules or relevant blanks/NULLs keep interpretation unresolved even if lexical comparison is possible. No source NULL policy is invented.

## V1 → V2 examples and permission boundary

Two new reports live separately in `results_v1.json`; the original 23 V2 cases, labels, proposals, results and scores are unchanged.

- **Useful structural context:** a separate copy of the CIK/cik schema candidate references the SUB `adsh → (cik, period)` observation and existing key scan by exact result fingerprints, source and population. It remains PROPOSED: a five-row key observation does not approve a semantic alias or cross-source identity.
- **Unsafe relationship:** two `10-Q` registrant observations have different native CIKs (`1453090` and `9892`). The canonical-identity candidate references the violated `form → cik` evidence and remains UNRESOLVED; shared form/reporting period is insufficient identity evidence. No canonical relation is created.

The attachment helper validates existing V2 reports, structural evidence fingerprints and source correspondence. Evidence is host-supplied observation, not authority; a hash is not an approval signature. The tests reject modified evidence and mismatched source references. Existing V0/V2 permission-boundary regression remains in scope. No mapping store, canonical table or independent human-review framework is introduced; no new semantic decision or review time is fabricated.

## Reproduction and limitations

```sh
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python scripts/evaluate_declared_fd.py
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python scripts/evaluate_agent_v2.py
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python -m pytest -q tests/agents tests/corpus_invariants/test_profiling_tools.py tests/tool_adapters tests/governance
```

Observed local validation: **124 passed, 2 skipped** (new FD checks, existing V0/V2, profiling tools, adapters and governance); Ruff PASS; both evidence verifiers PASS.

Default reproduction is read-only and checks exact persisted result equality. `--write` is an explicit first-creation option that refuses to overwrite evidence. The cached source profile is externally retained at the pinned path; reproduction from the committed observations verifies derivation equality, while independent extraction requires that exact profile. Unchanged historical artifacts are checked against the feature base. Tests and CI outcomes are recorded with the PR.

Coverage is five pre-existing sampled SUB occurrences, four fields, two declared FDs and two supplied composites; it does not estimate full-source FD confidence or general join safety. No full-corpus scan, Day 3 replay, DuckDB/Spark parity experiment, M1/M2 change, N750 processing, semantic promotion, Step 9/10 evaluation or merge to main occurs. Stop after this follow-up.
