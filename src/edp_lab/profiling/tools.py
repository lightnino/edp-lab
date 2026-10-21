"""Independently callable deterministic profiling; no semantic key approval."""

from __future__ import annotations

from collections import Counter
from functools import wraps
from inspect import signature
from itertools import combinations

from edp_lab.profiling.conventions import reference_count_metrics
from edp_lab.profiling.conventions import schema_fingerprint as structural_hash
from edp_lab.profiling.parser_fidelity import NULL_REASON
from edp_lab.profiling.source_reader import SourceTable, canonical_hash

VERSION = "PROFILING_OUTPUT_V1"


def metric(value=None, *, mode="EXACT_FULL_SCAN", reason=None):
    result = {"value": value, "computation_mode": mode}
    if reason:
        result["reason"] = reason
    return result


def unavailable(reason):
    return metric(mode="NOT_COMPUTED", reason=reason)


def output(table, function, payload, parameters):
    """Common JSON-compatible evidence envelope; deterministic run and result IDs."""
    identity = {"source": table.source, "config": table.config,
                "provenance": table.provenance, "function": function,
                "parameters": parameters, "output_version": VERSION}
    result = {"output_version": VERSION, "function": function, **identity,
              "run_id": canonical_hash(identity), "parse_status": table.parse_status,
              "errors": list(table.errors),
              "population": {"scope": "FULL_LOGICAL_TABLE_DATA_OCCURRENCES",
                             "preserves_multiplicity": True,
                             "sampling_method": "FULL_SCAN", "sample_size": None,
                             "sampling_seed": None, "accounting": table.accounting},
              "rows_scanned": metric(len(table.rows)), **payload}
    result["result_sha256"] = canonical_hash(result)
    return result


def indices(table, columns):
    names = list(columns)
    if not names or len(set(names)) != len(names):
        raise ValueError("Columns must be nonempty and distinct")
    try:
        return [table.columns.index(name) for name in names]
    except ValueError as exc:
        raise ValueError("Unknown column") from exc


def _duplicates(table, columns, group_limit, witness_limit):
    ix = indices(table, columns)
    counts = Counter(tuple(row[i] for i in ix) for row in table.rows)
    duplicates = {key: count for key, count in counts.items() if count > 1}
    selected = sorted(duplicates)[:group_limit]
    witnesses = {key: [] for key in selected}
    for row, locator in zip(table.rows, table.locators, strict=True):
        key = tuple(row[i] for i in ix)
        if key in witnesses and len(witnesses[key]) < witness_limit:
            witnesses[key].append(locator)
    return {
        "tested_columns": list(columns), "equality": "EXACT_LITERAL_TEXT_TUPLE",
        "duplicate_groups": metric(len(duplicates)),
        "rows_in_duplicate_groups": metric(sum(duplicates.values())),
        "excess_rows": metric(sum(n - 1 for n in duplicates.values())),
        "groups_computation_mode": "EXACT_FULL_SCAN",
        "groups": [{"values": list(key), "frequency": duplicates[key],
                    "source_record_witnesses": witnesses[key]} for key in selected],
        "groups_truncated": len(selected) < len(duplicates),
        "witness_limit_per_group": witness_limit,
        "disposition": "OBSERVATION_ONLY_NO_ERROR_CLASSIFICATION_OR_REMOVAL",
    }


def authorized_table(function):
    """Preserve scope denial without computing metrics on an unauthorized table."""
    @wraps(function)
    def guarded(table, *args, **kwargs):
        if table.authorization_outcome is not None:
            bound = signature(function).bind(table, *args, **kwargs)
            bound.apply_defaults()
            parameters = dict(bound.arguments)
            parameters.pop('table')
            return output(table, function.__name__, {
                'status': 'BLOCKED', 'authorization_outcome': table.authorization_outcome,
                'metrics': unavailable('AUTHORIZATION_REQUIRED'),
                'rows_scanned': unavailable('AUTHORIZATION_REQUIRED')}, parameters)
        return function(table, *args, **kwargs)
    return guarded


@authorized_table
def find_duplicates(table: SourceTable, columns=None, *, group_limit=20,
                    witness_limit=3) -> dict:
    """Count exact lexical repeat occurrences; bounded evidence, exact totals."""
    if group_limit < 0 or witness_limit < 1:
        raise ValueError("Invalid evidence limits")
    columns = tuple(table.columns if columns is None else columns)
    if not table.errors:
        indices(table, columns)
    payload = ({"duplicate_summary": unavailable("PARSE_FAILED")}
               if table.errors else _duplicates(table, columns, group_limit, witness_limit))
    return output(table, "find_duplicates", payload,
                  {"columns": list(columns), "group_limit": group_limit,
                   "witness_limit": witness_limit})


@authorized_table
def profile_table(table: SourceTable) -> dict:
    """Exact occurrence/structural counts plus literal duplicate summary."""
    payload = {
        "row_count": unavailable("PARSE_FAILED") if table.errors else metric(len(table.rows)),
        "column_count": unavailable("PARSE_FAILED") if table.errors
        else metric(len(table.columns)),
        "columns": [{"name": name, "type": "TEXT"} for name in table.columns],
        "duplicate_summary": unavailable("PARSE_FAILED") if table.errors
        else _duplicates(table, table.columns, 20, 3),
    }
    return output(table, "profile_table", payload, {})


@authorized_table
def profile_column(table: SourceTable, column: str, *, top_limit=10,
                   sample_size=5, sample_seed=0) -> dict:
    """Frozen semantic metrics, separately named lexical distributions/samples.

    Min/max are TEXT order only (Python Unicode codepoint ordering), never numeric
    or date inference. Samples select occurrences by SHA-256(seed, source, locator).
    """
    if top_limit < 0 or sample_size < 0 or not isinstance(sample_seed, int):
        raise ValueError("Invalid sample/top parameters")
    parameters = {"column": column, "top_limit": top_limit,
                  "sample_size": sample_size, "sample_seed": sample_seed}
    names = ("null_count", "non_null_count", "null_pct", "distinct_non_null_count",
             "distinct_pct", "unique_count", "min", "max", "top_values", "sample")
    if table.errors:
        return output(table, "profile_column", {"column": column,
                      "statistics": {n: unavailable("PARSE_FAILED") for n in names}}, parameters)
    ix = indices(table, [column])[0]
    values = [row[ix] for row in table.rows]
    literal_counts = Counter(values)
    semantic = table.null_tokens is not None
    nonnull = [v for v in values if v not in table.null_tokens] if semantic else []
    counts = reference_count_metrics(v if v not in table.null_tokens else None for v in values
                                     ) if semantic else {}
    statistics = {name: metric(counts[name]) if semantic else unavailable(NULL_REASON)
                  for name in names[:6]}
    for name, value in (("min", min(nonnull) if nonnull else None),
                        ("max", max(nonnull) if nonnull else None)):
        statistics[name] = metric(value) if semantic else unavailable(NULL_REASON)
    statistics["top_values"] = (metric([
        {"value": v, "count": n} for v, n in
        sorted(Counter(nonnull).items(), key=lambda p: (-p[1], p[0]))[:top_limit]
    ]) if semantic else unavailable(NULL_REASON))
    ranked = sorted(range(len(values)), key=lambda i: (canonical_hash(
        {"seed": sample_seed, "source": table.source, "locator": table.locators[i]}), i))
    chosen = ranked[:sample_size]
    samples = [{"literal_value": values[i], "source_record": table.locators[i],
                "column": column} for i in chosen]
    statistics["sample"] = metric(samples, mode="EXACT_SAMPLE")
    return output(table, "profile_column", {
        "column": column, "logical_type": "TEXT", "statistics": statistics,
        "ordering": "UNICODE_CODEPOINT_TEXT", "null_semantics_known": semantic,
        "literal_statistics": {
            "population": "ALL_DATA_OCCURRENCES_INCLUDING_LITERAL_NULL_TOKENS",
            "equality": "EXACT_TEXT",
            "empty_count": metric(literal_counts[""]),
            "whitespace_only_count": metric(sum(n for v, n in literal_counts.items()
                                                if v and not v.strip())),
            "distinct_text_count": metric(len(literal_counts)),
            "singleton_text_count": metric(sum(n == 1 for n in literal_counts.values())),
            "min_text": metric(min(values) if values else None),
            "max_text": metric(max(values) if values else None),
            "top_text_values": metric([{"value": v, "count": n} for v, n in sorted(
                literal_counts.items(), key=lambda p: (-p[1], p[0]))[:top_limit]]),
        },
        "sample_selection": {"method": "LOWEST_SHA256_SEED_SOURCE_LOCATOR",
                             "seed": sample_seed, "actual_size": len(samples),
                             "population_size": len(values)},
    }, parameters)


@authorized_table
def candidate_key_scan(table: SourceTable, *, composites=(), search_columns=None,
                       max_width=1, max_combinations=256) -> dict:
    """Single columns + supplied composites + bounded exhaustive combinations.

    Minimality checks every proper subset for measured literal uniqueness. No
    semantic eligibility is claimed without explicitly declared NULL rules.
    """
    if not 1 <= max_width <= 8 or not 1 <= max_combinations <= 4096:
        raise ValueError("Search bounds out of range")
    composites = tuple(tuple(c) for c in composites)
    pool = tuple(table.columns if search_columns is None else search_columns)
    if table.errors:
        return output(table, "candidate_key_scan", {"candidates": [],
                      "status": "NOT_COMPUTED", "reason": "PARSE_FAILED"},
                      {"composites": [list(c) for c in composites],
                       "search_columns": list(pool), "max_width": max_width,
                       "max_combinations": max_combinations})
    indices(table, pool)
    candidates = [(n,) for n in table.columns]
    for supplied in composites:
        supplied = tuple(supplied)
        indices(table, supplied)
        if len(supplied) > 8:
            raise ValueError("Supplied composite exceeds width 8")
        candidates.append(tuple(n for n in table.columns if n in supplied))
    for width in range(2, min(max_width, len(pool)) + 1):
        for combo in combinations(pool, width):
            candidates.append(tuple(n for n in table.columns if n in combo))
            if len(set(candidates)) > max_combinations:
                raise ValueError("Search exceeds max_combinations; narrow scope")
    candidates = list(dict.fromkeys(candidates))
    if len(candidates) > max_combinations:
        raise ValueError("Search exceeds max_combinations; narrow scope")
    parameters = {"composites": [list(c) for c in composites], "search_columns": list(pool),
                  "max_width": max_width, "max_combinations": max_combinations}
    cache = {}

    def unique(names):
        key = tuple(names)
        if key not in cache:
            ix = indices(table, key)
            cache[key] = len({tuple(r[i] for i in ix) for r in table.rows}) == len(table.rows)
        return cache[key]

    results = []
    for names in candidates:
        ix = indices(table, names)
        measured = unique(names)
        nonnull = (all(r[i] not in table.null_tokens for r in table.rows for i in ix)
                   if table.null_tokens is not None else None)
        # Empty population supplies no evidence for key eligibility or minimality.
        proper = [subset for width in range(1, len(names))
                  for subset in combinations(names, width)]
        literal_minimal = bool(table.rows) and measured and not any(unique(s) for s in proper)
        results.append({
            "columns": list(names), "row_count": metric(len(table.rows)),
            "mechanically_unique_literal": metric(measured),
            "non_null_eligible": metric(nonnull) if nonnull is not None
            else unavailable(NULL_REASON),
            "mechanically_minimal_literal": metric(literal_minimal),
            "minimality_scope": "ALL_NONEMPTY_PROPER_SUBSETS_EXACT_LITERAL_EQUALITY",
            "candidate_eligible": (metric(bool(table.rows) and measured and nonnull
                                          and literal_minimal) if nonnull is not None
                                   else unavailable(NULL_REASON)),
            "business_key_status": "NOT_APPROVED_NOT_ASSESSED",
        })
    return output(table, "candidate_key_scan", {
        "candidates": results, "search_complete_within_bounds": True,
        "equality": "EXACT_LITERAL_TEXT_TUPLE", "empty_population_policy": "NO_KEY_CLAIM",
    }, parameters)


@authorized_table
def schema_fingerprint(table: SourceTable) -> dict:
    """Frozen, order-sensitive structural hash; excludes distributions/identity."""
    return output(table, "schema_fingerprint", {
        "fingerprint_version": "SCHEMA_SHA256_V1",
        "canonicalization_version": "RAW_HEADER_TEXT_V1",
        "schema_sha256": unavailable("PARSE_FAILED") if table.errors
        else metric(structural_hash([(n, "TEXT") for n in table.columns])),
    }, {})
