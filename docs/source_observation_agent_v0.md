# Study Notes §2.6 — Source observation Agent V0

Implementation scope is offline lexical observation. No optional Agent SDK or LLM
is imported. No source equivalence, entity integration, business keys, deduplication,
NULL semantics, date normalization or later study section is implemented.

`edp_lab.agents.analyst_v0` is the single deterministic statistical orchestrator.
Its host supplies already verified SourceTables and principal grants; the Agent
cannot create grants, load arbitrary paths or write files. Its fixed plan invokes
the five §2.5 typed adapters, profiles every column and checks bounded singleton/pair
candidates. All tool implementation remains in the existing profiling functions.
The report includes ordered requests/responses, exact source/config/evidence
references, execution errors, unresolved metrics, tool/run/result fingerprints and
an Agent fingerprint. No wall-clock time enters deterministic results.

`SOURCE_OBSERVATION_REPORT_V1` is specified by
`metadata/source_observation_report_v1.schema.json`. Findings distinguish OBSERVED,
PROPOSED, VALIDATED, REJECTED and UNRESOLVED. These are finding dispositions; none
means human semantic approval. Literal duplicates remain separate occurrences.
Mechanical candidate results never become business keys. Execution PASS means
all requested tools executed without errors; adapter PARTIAL statuses for unknown
NULL-dependent metrics remain explicit, and do not become successful statistics.
The report's population declares the requested scope; on parsing failure, completed
population statistics remain unavailable in the underlying tool result.

## C300 discovery and proposed registration

`edp_lab.parsers.c300_v1` reads the canonical frozen manifest and verifies its
persisted freeze. Every source is SHA-256 checked before archive access. Every
archive member (including readme/metadata) is streamed and hashed. Discovery stores
member sizes, physical line counts, UTF-8 decoding errors, line endings, observed
width distributions, ordered headers, header/preamble byte witnesses and schema
variants linked to exact source IDs. Non-UTF-8 supporting metadata is recorded as
unresolved encoding; no fallback encoding is inferred. Supporting HTML is not a
logical data table, and its encoding failures are not table parser failures.

Proposed bindings pin RAW identity, member identity, exact header, exact metadata
prefix, profile/version and uncompressed size. They are immutable evidence under
`runs/`, not amendments to the GOLD freeze or C300 admission. Proposed activation
is explicitly INACTIVE_PENDING_HUMAN_APPROVAL. The reader rejects changed RAW,
member, header or prefix bytes. Discovery and validation of candidate rules do not
authorize operational consumption or profiling.

All three families use strict UTF-8, literal delimiters and ALL_TEXT fields.
Quotes and escape characters remain literal. Daily Master Index requires its five
metadata records, exact five-column header on line six and 80-hyphen separator on
line seven. Exact source metadata spelling is pinned per member, including dates;
no meaning or time alignment is inferred. TSV headers are edition-specific.
Physical LF, CRLF and unterminated final records are supported; bare CR, BOM,
blank data records, wrong widths and malformed prefixes fail explicitly.

`c300_reader_v1.validated_occurrences` is a validation iterator emitting exact bytes,
text fields, kind, line and byte offset, preserving duplicate occurrences. Public
`occurrences` requires the exact-registry human approval and frozen membership.
Integrity gates precede the first emitted record. Any raised exception invalidates
completion; callers must never publish an interrupted iteration as a full scan.
The final member hash and parent hash are verified again to detect changes during
iteration. Existing GOLD reader/fidelity code is reused as the lexical contract;
its frozen code is preserved, so the bounded implementation is additive.

Memory is bounded by an 8 MiB physical-record cap and decoded/split representations
of that record, plus small counters and prefix evidence. Full uncompressed archive
members are never held in memory. Oversized records fail; discovery drains and
hashes remaining bytes but marks its parse scan INCOMPLETE. This is a deterministic
record-size limit, not an operating-system memory/time guarantee. Existing profiling
adapters still materialize GOLD tables; no C300-scale profiling performance claim
is made. `agents.c300_shallow_v0` is a read-only extension for separately authorized
full-member lexical scans, explicitly `full_profiling: false`.

## Reproduction and evaluation

Use the existing environment without dependency installation or network access:

```sh
.venv/bin/python -m edp_lab.parsers.c300_v1 --output runs/section-2-6/discovery-NEW
.venv/bin/python -m edp_lab.agents.checkpoint_v0 c300 \
  --registry runs/section-2-6/discovery-NEW/bindings.proposed.json \
  --output runs/section-2-6/validation-NEW
.venv/bin/python -m edp_lab.agents.checkpoint_v0 gold \
  --output runs/section-2-6/gold-NEW
```

Output directories must be new, resolved paths under gitignored `runs/`. JSON
artifacts use exclusive creation. An interrupted directory is incomplete; retain
it and use a new version. The host checkpoint writer is separate from the read-only
Agent. Prior RAW, manifests, cohort files, freezes and historical results are never
written. The final checkpoint reference links hashes; operational results stay
untracked.

For GOLD, evaluation invokes each underlying deterministic function independently
of Agent dispatch, compares complete results (including source/record provenance),
replays each typed request and repeats the entire Agent plan. This checks
orchestration fidelity, not an independent implementation of statistical formulas;
existing profiling tests cover their formulas. Runtime provenance includes actual
Git revision/status, code hashes, dependency versions and lockfile hash. Replaying
under changed code/status produces different provenance and fingerprints by design.

C300 candidate validation re-verifies parent and member hashes before structural
validation and compares exact bound headers/prefixes/sizes. All 300 source instances
receive instance-level coverage, and each discovered logical table gets independent
validation and activation statuses. Human parser activation remains a separate gate.
No C300 Agent execution PASS is claimed before that authority exists.

## Observed C300 structural exception

Discovery found 732 logical tables: 240 FSDS, 294 Form 13F and 198 Daily Master
Index. The proposed literal TSV rules passed 720 and failed 12 FSDS `num.txt`
tables (SRC000052–SRC000054 and SRC000056–SRC000064). Ordered headers have no
observed schema variants within each family/member name. This does not establish
semantic stability or source equivalence across editions.

The first failing record is SRC000052 / `num.txt`, physical line 16618, byte offset
2242337, length 261. Its record SHA-256 is
`305b28380f1e1ac4ad523055ff7d5f27ce9befd23fdd864707a3d2106a8223e7`.
Literal splitting yields 33 fields under a ten-column header. The bytes include
quotes surrounding text containing tabs. These are evidence for a possible
quote-aware dialect, not authority to choose one, remove quotes, combine fields,
repair rows or discard occurrences. Source-specific scope and field fidelity would
need review before any alternative is implemented or activated. The strict V1
implementation retains FAILED coverage for these twelve tables.

The approval request covers only the 720 PASS table bindings. Failed bindings
remain in the immutable diagnostic inventory and cannot activate. Supporting
readme HTML encoding is unresolved in all 60 FSDS archives; those bytes are fully
hashed and retained, and no readme-to-table conversion is proposed.
