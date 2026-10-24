# Agent-ready deterministic tool contract V1 (§2.5)

`edp_lab.tool_adapters` exposes five independently callable typed adapters. It
imports no Agent SDK and performs no API calls. The underlying §2.1 profiling
functions and frozen artifacts are unchanged. The supplied §2.5 requirements are
the implementation specification; standalone Study Notes are not in this repo.

```python
from pathlib import Path
from edp_lab.profiling.source_reader import read_registered
from edp_lab.tool_adapters import (
    Authorization, ProfilingAdapters, ToolRequest, ColumnParameters,
)

table = read_registered(Path.cwd(), "SRC000002", "nasdaqlisted.txt")
adapters = ProfilingAdapters({"gold_listing": table}, {"local_user": {"gold_listing"}})
request = ToolRequest(
    tool="profile_column",
    source=adapters.source_ref("gold_listing"),
    authorization=Authorization("local_user"),
    parameters=ColumnParameters(column="Symbol"),
)
response = adapters.profile_column(request)
wire_response = response.to_dict()
```

The same host exposes `profile_table`, `find_duplicates`, `candidate_key_scan`
and `schema_fingerprint`, plus generic `invoke`. Named methods reject a mismatched
tool name. Requests accept dataclasses or decoded JSON objects; unknown fields,
wrong parameter types (including booleans as integers), unsupported versions and
scopes fail with structured errors. Parameter dataclasses mirror existing function
signatures. `EmptyParameters` applies to table and schema calls.

The host owns the source bindings and principal grants. A request's principal is
an assertion supplied by an already authenticated local caller, not authentication
or a credential. An external transport must authenticate and bind that principal
before invoking this library. Requests cannot create grants or provide file paths.
The adapter deep copies bindings on construction; replace the host to refresh a
snapshot. `SourceRef` pins the full source identity and configuration by canonical
SHA-256; the underlying registered reader remains responsible for verifying RAW,
member, freeze and parser hashes before materialization. Use `read_synthetic` only
for explicit synthetic fixtures. No C300 adapter binding or admission is added.

Execution is read-only over the full materialized logical table. Row and cell
budgets reject oversized tables before calling profiling; evidence parameters are
bounded to 4096 and existing candidate width/combination bounds still apply.
Budgets cover profiling invocation, not source loading, memory already allocated by
the reader, elapsed-time deadlines, or a process sandbox. Hosts needing hard memory
or time limits must separately constrain ingestion and process execution. Limits
never silently truncate the profiling population.

The response contains `status`, the unchanged profiling `result`, `input_refs`,
`evidence_refs`, `metrics`, `warnings`, `errors`, `unresolved_questions`, `run_id`,
`tool_version`, `result_fingerprint`, `approval_required`, and `side_effects`.
Evidence retains source/config/provenance and underlying run/result hashes; record
and field witnesses remain inside the original result. No evidence files are
written. Side effects are always empty.

- `SUCCESS`: execution completed and no requested metric is NOT_COMPUTED.
- `PARTIAL`: parsing failed after scanning some occurrences, or requested metrics
  have unresolved semantics. A partial parse retains the underlying unavailable
  completed-table metrics; scanned rows are accounting, not a completed result.
- `FAILED`: malformed parameters, missing source, or scan failure without rows.
- `BLOCKED`: denied host grant, identity/config mismatch, or row/cell budget.

Authorization denial sets `approval_required`; this is a signal for a host to
resolve authority, never an automatic approval or authorization bypass. Unknown
NULL-dependent metrics retain their exact reason in `unresolved_questions`.
Bounded duplicate witnesses and samples are documented selections within completed
full-scan statistics and do not alone make execution partial.

Run identity hashes the validated request, contract version and bound provenance.
The response fingerprint hashes the entire envelope except itself using existing
canonical JSON. There are no timestamps. Replay requires identical source,
configuration, parameters, scope, authority assertion and provenance; code/runtime
changes captured by the reader change identity. Malformed requests share a sentinel
run identity and have no execution or source evidence. Successful evidence remains
entirely deterministic and duplicate preserving.

Validation covers all five independent calls against the existing functions,
JSON replay and fingerprints, malformed contracts, missing sources, grant denial,
identity/config mismatches, resource rejection before dispatch, unknown semantics,
partial/failed scans, invalid columns, candidate limits and GOLD_V2 frozen evidence.
Agent V0, semantic decisions, and actual C300 integration remain deferred until
formal C300 freeze and reviewed parser registration.
