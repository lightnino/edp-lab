"""Streaming lexical M1 packaging and independent byte-reference validation.

No source bytes are changed and no original-record BINARY payload is persisted.
Spark publication is implemented in the separately pinned Databricks notebook.
"""
from __future__ import annotations

import hashlib
import json
import resource
import time
from pathlib import Path

from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.parsers.c300_reader_v1 import occurrences
from edp_lab.parsers.c300_v1 import PROFILES, member_stream
from edp_lab.profiling import tools
from edp_lab.profiling.conventions import schema_fingerprint
from edp_lab.profiling.source_reader import SourceTable, canonical_hash

MODEL = "M1_LEXICAL_V1"
RULE = "C300_LITERAL_IDENTITY_V1"
PACKET_SHA = "3873e9d07e4bcc2f357f940d05cf4fc5dc1262358b641d1debba2ef117910e05"
REGISTRY = "runs/section-2-6/discovery-v1/bindings.proposed.json"
AUTHORITY = "runs/c300-post-approval-v1/authorization.json"

RECORD_DDL = """run_id STRING, model_version STRING, rule_version STRING,
source_instance_id STRING, binding_sha256 STRING, source_line BIGINT,
byte_offset BIGINT, byte_length BIGINT, record_kind STRING,
fields ARRAY<STRUCT<field_ordinal:INT,original_name:STRING,lexical_value:STRING,
disposition:STRING>>, admission_outcome STRING, outcome_reason STRING"""
BINDING_DDL = """run_id STRING, model_version STRING, rule_version STRING,
source_instance_id STRING, source_family STRING, raw_path STRING, volume_path STRING,
raw_sha256 STRING, archive_member STRING, member_sha256 STRING, logical_table_name STRING,
binding_sha256 STRING, parser_profile_id STRING, parser_version STRING,
parser_code_sha256 STRING, reader_code_sha256 STRING, registry_sha256 STRING,
approval_packet_sha256 STRING, cohort_sha256 STRING, manifest_sha256 STRING,
ordered_header ARRAY<STRING>, expected_member_bytes BIGINT, processing_status STRING,
reason_code STRING, error_evidence_ref STRING, records_total BIGINT, records_data BIGINT,
fields_data BIGINT, observed_member_sha256 STRING"""


def save_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, default=str)
        stream.write("\n")


def record_schema():
    import pyarrow as pa
    field = pa.struct([pa.field("field_ordinal", pa.int32(), False),
                       pa.field("original_name", pa.string(), False),
                       pa.field("lexical_value", pa.string(), False),
                       pa.field("disposition", pa.string(), False)])
    return pa.schema([
        *[pa.field(n, pa.string(), False) for n in
          ("run_id", "model_version", "rule_version", "source_instance_id", "binding_sha256")],
        *[pa.field(n, pa.int64(), False) for n in
          ("source_line", "byte_offset", "byte_length")],
        pa.field("record_kind", pa.string(), False),
        pa.field("fields", pa.list_(pa.field("element", field, False)), False),
        pa.field("admission_outcome", pa.string()), pa.field("outcome_reason", pa.string())])


def package_record(run_id, binding, occurrence, binding_hash=None):
    data = occurrence.kind == "DATA"
    return {"run_id": run_id, "model_version": MODEL, "rule_version": RULE,
                "source_instance_id": binding["source_instance_id"],
                "binding_sha256": binding_hash or canonical_hash(binding), "source_line": occurrence.source_line,
                "byte_offset": occurrence.byte_offset, "byte_length": len(occurrence.original_bytes),
                "record_kind": occurrence.kind,
                "fields": [{"field_ordinal": i, "original_name": name, "lexical_value": value,
                             "disposition": "DIRECT_MAP"} for i, (name, value) in enumerate(
                                 zip(binding["expected_header"], occurrence.fields, strict=True), 1)]
                if data else [], "admission_outcome": "ACCEPTED" if data else None,
                "outcome_reason": "IDENTITY_LEXICAL_PRESERVATION" if data else None}


def stable_record(row):
    return {k: v for k, v in row.items() if k != "run_id"}


def verify_parquet(root, binding, path):
    """Independent full-population interval/lexical oracle, not a second parser call.

    Parquet rows are checked in emitted physical order, preserving duplicates.
    Reconstruct the member by concatenating the referenced RAW intervals.
    """
    import pyarrow.parquet as pq
    offset = count = data = fields = 0
    binding_hash = canonical_hash(binding)
    rebuilt, logical = hashlib.sha256(), hashlib.sha256()
    prefixes = {p["source_line"] for p in binding["prefix_evidence"]}
    header_line = 6 if binding["source_family"] == "SEC_EDGAR_DAILY_MASTER" else 1
    with member_stream(root / binding["raw_path"], binding["archive_member"]) as source:
        for batch in pq.ParquetFile(path).iter_batches(batch_size=2048):
            for row in batch.to_pylist():
                count += 1
                assert row["source_line"] == count and row["byte_offset"] == offset
                assert row["source_instance_id"] == binding["source_instance_id"]
                assert row["binding_sha256"] == binding_hash
                assert row["model_version"] == MODEL and row["rule_version"] == RULE
                raw = source.read(row["byte_length"])
                assert len(raw) == row["byte_length"] and raw
                # Exactly one physical line, including an optional exact terminator.
                assert b"\n" not in raw[:-1]
                rebuilt.update(raw)
                offset += len(raw)
                kind = ("HEADER" if count == header_line else "METADATA") if (
                    count in prefixes) else "DATA"
                assert row["record_kind"] == kind
                if kind == "DATA":
                    values = raw.removesuffix(b"\n").removesuffix(b"\r").decode(
                        "utf-8", errors="strict").split(PROFILES[binding["source_family"]]["delimiter"])
                    assert len(values) == len(binding["expected_header"]) == len(row["fields"])
                    for ordinal, (name, value, actual) in enumerate(zip(
                            binding["expected_header"], values, row["fields"], strict=True), 1):
                        assert actual == {"field_ordinal": ordinal, "original_name": name,
                                              "lexical_value": value, "disposition": "DIRECT_MAP"}
                    assert row["admission_outcome"] == "ACCEPTED"
                    assert row["outcome_reason"] == "IDENTITY_LEXICAL_PRESERVATION"
                    data += 1
                    fields += len(values)
                else:
                    assert row["fields"] == [] and row["admission_outcome"] is None
                    assert row["outcome_reason"] is None
                    expected = next(p for p in binding["prefix_evidence"] if p["source_line"] == count)
                    assert raw.hex() == expected["raw_hex"]
                logical.update(bytes.fromhex(canonical_hash(stable_record(row))))
        assert not source.read(1)
    assert offset == binding["uncompressed_bytes"]
    assert rebuilt.hexdigest() == binding["member_sha256"]
    return {"records_total": count, "records_data": data, "fields_data": fields,
                "observed_member_sha256": rebuilt.hexdigest(), "bytes": offset,
                "ordered_record_digest": logical.hexdigest()}


def materialize(root, binding, registry, approval, run_id, destination):
    import pyarrow as pa
    import pyarrow.parquet as pq
    started = time.perf_counter()
    schema, batch = record_schema(), []
    binding_hash = canonical_hash(binding)
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    with pq.ParquetWriter(destination, schema, compression="zstd") as writer:
        for occurrence in occurrences(root, registry, binding, approval):
            batch.append(package_record(run_id, binding, occurrence, binding_hash))
            if len(batch) >= 2048:
                writer.write_table(pa.Table.from_pylist(batch, schema=schema))
                batch.clear()
        if batch:
            writer.write_table(pa.Table.from_pylist(batch, schema=schema))
    parse_seconds = time.perf_counter() - started
    verify_start = time.perf_counter()
    result = verify_parquet(root, binding, destination)
    return {**result, "parse_package_integrity_seconds": parse_seconds,
            "independent_validation_seconds": time.perf_counter() - verify_start,
            "parquet_sha256": file_sha256(destination), "parquet_bytes": destination.stat().st_size,
            "peak_rss_platform_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "schema_sha256": schema_fingerprint([(n, "TEXT") for n in binding["expected_header"]])}


def statistical_profile(binding, parquet, result, provenance, destination):
    """Optional isolated subprocess entry. Entire binding or NOT_COMPUTED; no sampling."""
    import pyarrow.parquet as pq
    start = time.perf_counter()
    rows, locators = [], []
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=2048):
        for row in batch.to_pylist():
            if row["record_kind"] == "DATA":
                rows.append(tuple(f["lexical_value"] for f in row["fields"]))
                locators.append({k: row[k] for k in ("source_line", "byte_offset", "byte_length")})
    table = SourceTable(tuple(binding["expected_header"]), tuple(rows), tuple(locators),
                        binding, {**PROFILES[binding["source_family"]], "null_tokens": None,
                                  "quote": None, "escape": None, "types": "ALL_TEXT"},
                        provenance, None, {"DATA": len(rows),
                                           "FRAMING": result["records_total"] - len(rows)})
    scope = {"binding_sha256": canonical_hash(binding), "rows": len(rows),
             "columns": len(table.columns), "mode": "EXACT_FULL_SCAN"}
    functions = [("profile_table", lambda: tools.profile_table(table)),
                 ("find_duplicates", lambda: tools.find_duplicates(table)),
                 ("schema_fingerprint", lambda: tools.schema_fingerprint(table)),
                 ("candidate_key_scan", lambda: tools.candidate_key_scan(
                     table, search_columns=table.columns[:3], max_width=2, max_combinations=256))]
    functions += [(f"profile_column_{i}", lambda name=name: tools.profile_column(table, name))
                  for i, name in enumerate(table.columns, 1)]
    completed = []
    for name, call in functions:
        t = time.perf_counter()
        envelope = call()
        path = Path(destination) / f"{name}.json"
        save_new(path, envelope)
        completed.append({"function": name, "seconds": time.perf_counter() - t,
                          "peak_rss_platform_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                          "sha256": file_sha256(path), "path": str(path), "scope": scope})
        save_new(Path(destination) / f"{name}.telemetry.json", completed[-1])
    save_new(Path(destination) / "completion.json", {"status": "COMPLETE", "scope": scope,
             "seconds": time.perf_counter() - start, "functions": completed})


def measure_inventory(binding):
    return [{"binding_sha256": canonical_hash(binding),
                 "source_instance_id": binding["source_instance_id"],
                 "raw_path": binding["raw_path"], "raw_sha256": binding["raw_sha256"],
                 "archive_member": binding["archive_member"], "member_sha256": binding["member_sha256"],
                 "field_ordinal": i, "original_name": name,
                 "disposition": "PRESERVED_NOT_MODELED", "boundary": MODEL,
                 "unit": "UNRESOLVED", "business_meaning": "UNRESOLVED", "grain": "UNRESOLVED",
                 "group_by_dimensions": "UNRESOLVED", "time_basis": "UNRESOLVED",
                 "eligibility": "NO_INTEGRATED_ECONOMIC_MEASURES_IN_LEXICAL_M1",
                 "conversion_rule": None, "conversion_version": None, "tolerance": None,
                 "expected_equation": "NOT_APPLICABLE", "observed_result": "NOT_APPLICABLE",
                 "exception_status": "LEXICAL_ONLY", "lexical_fidelity_ref": "Lossless 2/3"}
            for i, name in enumerate(binding["expected_header"], 1)]


def export_profiles(out, binding_rows, reused_profile_root=None):
    """Run-scoped authoritative Parquet projections; retain unchanged envelopes."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    tables, columns = [], []
    profile_roots = [Path(out) / "profiles"]
    if reused_profile_root:
        profile_roots.append(Path(reused_profile_root))
    # List directories once: avoid thousands of remote stats on absent profiles.
    directories = {}
    for profile_root in reversed(profile_roots):
        if profile_root.exists():
            directories.update({p.name: p for p in profile_root.iterdir() if p.is_dir()})

    def envelope(path, available):
        if path.name not in available:
            return {}
        try:
            text = path.read_text()
            value = json.loads(text)
            claimed = value.pop("result_sha256")
            if canonical_hash(value) != claimed:
                return {}
            return {"envelope_ref": str(path), "envelope_sha256": file_sha256(path),
                    "envelope_json": text}
        except (ValueError, KeyError, OSError):
            return {}

    for binding in binding_rows:
        sha = binding["binding_sha256"]
        profile = directories.get(sha, Path(out) / "profiles" / sha)
        available = {p.name for p in profile.iterdir()} if sha in directories else set()
        attempt_path = profile / "attempt.json"
        attempt = json.loads(attempt_path.read_text()) if "attempt.json" in available else {
            "status": "NOT_COMPUTED", "reason": binding["reason_code"]}
        base = {"binding_sha256": sha, "source_instance_id": binding["source_instance_id"],
                "raw_sha256": binding["raw_sha256"], "archive_member": binding["archive_member"],
                "processing_status": binding["processing_status"],
                "statistical_status": attempt["status"], "reason": attempt.get("reason"),
                "records_data": binding["records_data"], "fields_data": binding["fields_data"],
                "attempt_ref": str(attempt_path) if "attempt.json" in available else None,
                "sampling": "NONE"}
        absent = {"envelope_ref": None, "envelope_sha256": None, "envelope_json": None}
        tables.append({**base, **absent, **envelope(profile / "profile_table.json", available)})
        for i, name in enumerate(binding["ordered_header"], 1):
            value = envelope(profile / f"profile_column_{i}.json", available)
            columns.append({**base, "field_ordinal": i, "original_name": name,
                            "computation_mode": "EXACT_FULL_SCAN" if value else "NOT_COMPUTED",
                            **absent, **value})
    # Explicit string/int types keep all-null smoke columns reproducibly typed.
    for name, rows in [("table_profiles.parquet", tables), ("column_profiles.parquet", columns)]:
        integer_names = {"records_data", "fields_data", "field_ordinal"}
        schema = pa.schema([(k, pa.int64() if k in integer_names else pa.string()) for k in rows[0]])
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), Path(out) / name, compression="zstd")
    return {"table_rows": len(tables), "column_rows": len(columns),
            "full_profile_bindings": sum(t["statistical_status"] == "COMPLETE" for t in tables),
            "column_envelopes": sum(c["computation_mode"] == "EXACT_FULL_SCAN" for c in columns)}
