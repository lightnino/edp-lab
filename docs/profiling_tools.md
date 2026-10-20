# Deterministic profiling tools V1

All five tools in `edp_lab.profiling.tools` accept the same `SourceTable` from
`edp_lab.profiling.source_reader`. No Agent or network access is involved.

```python
from pathlib import Path
from edp_lab.profiling.source_reader import read_registered
from edp_lab.profiling.tools import (
    profile_table, profile_column, find_duplicates,
    candidate_key_scan, schema_fingerprint,
)

table = read_registered(Path.cwd(), "SRC000004", "num.txt")
summary = profile_table(table)
column = profile_column(table, "value", sample_seed=42)
duplicates = find_duplicates(table, ["adsh", "tag"], group_limit=20, witness_limit=3)
keys = candidate_key_scan(table, composites=[("adsh", "tag")],
                          search_columns=["adsh", "tag", "version"], max_width=2)
schema = schema_fingerprint(table)
```

Read once and reuse the returned occurrences; functions never reopen sources.
`read_registered` verifies the approved freeze/config and reviewed reader code,
manifest/source hashes and member hashes before strict snapshot lexical parsing.
It retains exact TEXT fields, line/byte locators and header/data/footer accounting.
`read_synthetic` separately accepts an explicit UTF-8 dialect, ordered header and
NULL-token rule; this path does not grant registered snapshots different semantics.
NULL tokens match decoded text exactly, including quoted tokens. `None` means
unknown NULL semantics; `()` explicitly declares no NULL token. Blank text is
preserved unless the explicit synthetic NULL rule includes it.

Outputs are JSON-compatible `PROFILING_OUTPUT_V1` dictionaries with source/config,
freeze hash, installed dependencies, Python version, lock hash, actual Git revision,
working-tree status and code-content hashes. Each output has deterministic run and
result hashes, parse status, errors, declared full-scan population and per-statistic
computation modes. No execution timestamp is introduced into the deterministic
payload. `rows_scanned` counts successfully parsed data occurrences even on failure;
failed scans do not yield completed-table metrics. Unknown columns or invalid search
parameters raise ValueError; parse/integrity failures are retained as structured
errors. No failed scan is published as full-table PASS.

Count formulas and structural hashing reuse the frozen V1 conventions. Unknown
source NULL semantics leave NULL/non-NULL/distinct-non-NULL/singleton counts, ratios,
semantic min/max/top values and candidate eligibility NOT_COMPUTED with a reason.
Separately named literal metrics use exact TEXT equality, including blanks and
literal tokens. TEXT min/max use Unicode codepoint ordering; no numeric/date casts
are implied. Top values sort by descending frequency, then exact text. Samples
select occurrences by lowest SHA-256 of seed/source/locator, with ties by occurrence
index; report method, seed, actual size, population and field/record witnesses.
Sample mode is EXACT_SAMPLE; counts and lexical distributions remain full scan.

Duplicates measure exact literal tuples. Group count, rows in groups and excess
rows are full-scan exact even when displayed groups/witnesses are bounded.
Groups sort by exact tuple; witnesses follow source order. Equal-looking records
are never removed or classified as errors. Candidate scans check all singles,
supplied composites and bounded combinations in selected columns (width 1–8,
maximum 4096 candidates; defaults 1/256). Over-limit requests fail explicitly.
Minimality tests every nonempty proper subset using literal equality, independently
of the requested search scope. Empty populations cannot establish eligible keys.
Mechanical uniqueness/minimality never approve a Business Key. Any unknown NULL
eligibility prevents a candidate-validity claim. Structure hashes use ordered
`(exact name, TEXT)` pairs with SCHEMA_SHA256_V1 / RAW_HEADER_TEXT_V1; distributions,
source identities and operational provenance do not enter that structural hash.

The current implementation materializes one logical table in memory. Evidence
lists are bounded; exact counts still scan all occurrences. This is suitable for
the measured GOLD_V2 inputs, with no larger-corpus performance claim.

Offline execution of all five tools on every registered table, including each
column, all singleton candidates and bounded pairs within the first three columns:

```bash
.venv/bin/python -m edp_lab.profiling.run_gold
```

Evidence files go under gitignored `runs/profiling/`, keyed by source/table/run ID.
Existing unequal evidence is never overwritten. No RAW/config/registry is written.
The frozen V1 files' original NOT_IMPLEMENTED labels and the V2 freeze's historical
configuration-only status remain intact; this new implementation explicitly uses
the approved snapshot scope under the current implementation instruction.

§2.1 execution is complete for GOLD_V2: 13 tables, 304,508 data occurrences and
149 column profiles, with no hash or parse failures. The retained report and
machine-readable index are linked from [completion evidence](preflight_exit_checklist.md).
The [output contract](profiling_output_contract.md) describes the implemented fields.

The shared profiling functions can be reused for future C300 mechanical profiling
once sources are admitted and their parsers are reviewed and registered. The
current registered reader accepts only frozen GOLD_V2 bindings; neither synthetic
fixtures nor GOLD_V2 approval grant parser authority for new snapshots. C300
creation/execution and §2.2–§2.4 implementation are outside this completion scope.
