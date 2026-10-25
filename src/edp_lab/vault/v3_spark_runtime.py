"""Fixed bounded C2000 V3 Spark/Delta runtime; never invoke without grant.

The protected submitter must verify the owner-signed semantic decision, exact
scope grant, deployed wheel/artifact hashes and durable one-shot reservation.
This code independently checks the frozen source selection and writes only the
23 approved V3 tables with insert-only MERGE. No automatic retries.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.vault.v3_ddl import COLUMNS, create_sql, insert_only_sql
from edp_lab.vault.v3_input import c300_occurrence, treasury_entry
from edp_lab.vault.v3_mapping import EDGAR_HEADER, FSDS_HEADERS, project
from edp_lab.vault.v3_oracles import evaluate as evaluate_oracles
from edp_lab.vault.v3_readback import collect as collect_readback

C300_TABLES = (
    ("clean_c300_m1_records_main_recovery_20261021_v4_full",
     "clean_c300_m1_bindings_main_recovery_20261021_v4_full"),
    ("clean_c300_m1_records_num_recovery_20261021_v1_recovery",
     "clean_c300_m1_bindings_num_recovery_20261021_v1_recovery"),
)
TREASURY_TABLE = "workspace.edp_lab.clean_n750_m1_treasury_properties_step8_v1"
SEC_IDS = ("SRC000005", "SRC000054", "SRC000064", "SRC000065", "SRC000107")
XML_IDS = ("SRC010451", "SRC010452", "SRC010453", "SRC010454", "SRC010455")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _load(path: Path, expected: str) -> dict:
    if _sha(path) != expected:
        raise ValueError("V3_DEPLOYED_ARTIFACT_HASH_CHANGED:" + str(path))
    return json.loads(path.read_bytes())


def _member(binding: dict) -> str:
    physical = binding["archive_member"]
    if physical in FSDS_HEADERS:
        return physical
    if binding["source_instance_id"] == "SRC000065":
        return Path(physical).name.upper()
    if binding["source_instance_id"] == "SRC000107" and physical.lower().endswith(".idx"):
        return "daily_master.idx"
    raise ValueError("V3_UNEXPECTED_C300_MEMBER")


def _ordinals(spec: dict) -> list[int]:
    values = spec["data_row_ordinals"]
    if spec.get("selection_kind") == "INCLUSIVE_FIRST_N_DATA_ROWS":
        result = list(range(values[0], values[1] + 1))
    elif (spec.get("selection_kind") == "FIRST_N_PLUS_EXACT_CHILD_ACCESSION_PARENTS"
          or "duplicate_witness_pair" in spec):
        result = values
    else:
        raise ValueError("V3_ROW_SELECTION_KIND_INVALID")
    if not result or result != sorted(set(result)) or len(result) != spec["selected_data_rows"]:
        raise ValueError("V3_ROW_ORDINALS_INVALID")
    return result


def _expected_names(sid: str, member: str, row: dict) -> tuple[str, ...]:
    if member in FSDS_HEADERS:
        return FSDS_HEADERS[member]
    if sid == "SRC000107":
        return EDGAR_HEADER
    if sid == "SRC000065":
        return tuple(field["original_name"] for field in row["fields"])
    raise ValueError("V3_HEADER_OUT_OF_SCOPE")


def _bindings(spark, selection: dict) -> dict:
    """Read only accepted version-0 binding rows for the five SEC sources."""
    ids = ",".join("'" + sid + "'" for sid in SEC_IDS)
    found = {}
    for records, bindings in C300_TABLES:
        query = (f"SELECT * FROM workspace.edp_lab.{bindings} VERSION AS OF 0 "
                 f"WHERE source_instance_id IN ({ids}) AND processing_status='COMPLETE'")
        for item in spark.sql(query).collect():
            binding = item.asDict(recursive=True)
            sid = binding["source_instance_id"]
            try:
                member = _member(binding)
            except ValueError:
                continue
            if member not in selection["sources"][sid]["members"]:
                continue
            if binding["raw_sha256"] != selection["sources"][sid]["raw_sha256"]:
                raise ValueError("V3_C300_RAW_HASH_CHANGED")
            key = (sid, member)
            if key in found:
                raise ValueError("V3_DUPLICATE_ACCEPTED_BINDING")
            found[key] = (records, binding)
    expected = {(sid, member) for sid in SEC_IDS
                for member in selection["sources"][sid]["members"]}
    if set(found) != expected:
        raise ValueError("V3_C300_BINDING_COVERAGE_CHANGED")
    return found


def _sec_occurrences(spark, selection: dict) -> list[dict]:
    found = _bindings(spark, selection)
    by_table = defaultdict(list)
    for (sid, member), (records, binding) in found.items():
        by_table[records].append((sid, member, binding))
    output = []
    for records, items in by_table.items():
        hashes = ",".join("'" + binding["binding_sha256"] + "'" for _, _, binding in items)
        clauses = []
        lookup = {}
        for sid, member, binding in items:
            wanted = _ordinals(selection["sources"][sid]["members"][member])
            joined = ",".join(str(value) for value in wanted)
            clauses.append(f"(binding_sha256='{binding['binding_sha256']}' "
                           f"AND run_id='{binding['run_id']}' AND ordinal IN ({joined}))")
            lookup[(binding["run_id"], binding["binding_sha256"])] = (
                sid, member, binding)
        query = ("WITH ranked AS (SELECT r.*, ROW_NUMBER() OVER "
                 "(PARTITION BY run_id,binding_sha256 ORDER BY byte_offset,source_line) "
                 f"AS ordinal FROM workspace.edp_lab.{records} VERSION AS OF 0 r "
                 f"WHERE record_kind='DATA' AND binding_sha256 IN ({hashes})) "
                 "SELECT * FROM ranked WHERE " + " OR ".join(clauses))
        selected = defaultdict(list)
        for value in spark.sql(query).collect():
            row = value.asDict(recursive=True)
            binding_key = (row["run_id"], row["binding_sha256"])
            if binding_key not in lookup:
                raise ValueError("V3_C300_UNEXPECTED_ROW")
            sid, member, binding = lookup[binding_key]
            names = _expected_names(sid, member, row)
            normalized = c300_occurrence(row, binding,
                                         selection["sources"][sid]["raw_sha256"], names)
            selected[(sid, member)].append((row["ordinal"], normalized))
        for sid, member, binding in items:
            spec = selection["sources"][sid]["members"][member]
            values = sorted(selected[(sid, member)], key=lambda pair: pair[0])
            if [ordinal for ordinal, _ in values] != _ordinals(spec):
                raise ValueError("V3_C300_SELECTED_ROWS_MISSING")
            names = tuple(field["name"] for field in values[0][1]["fields"])
            if spec.get("header_sha256") and _digest(list(names)) != spec["header_sha256"]:
                raise ValueError("V3_C300_HEADER_CHANGED")
            lexical = [[ordinal, [field["text"] for field in item["fields"]]]
                       for ordinal, item in values]
            if member == "daily_master.idx":
                lexical = [[ordinal, "|".join(field["text"] for field in item["fields"])]
                           for ordinal, item in values]
            if _digest(lexical) != spec["selected_lexical_sha256"]:
                raise ValueError("V3_C300_SELECTED_LEXICAL_CHANGED")
            output.extend(item for _, item in values)
    if len(output) != 304:
        raise ValueError("V3_C300_SELECTED_COUNT_CHANGED")
    _validate_fsds_parents(spark, output, found)
    return output


def _validate_fsds_parents(spark, selected: list[dict], found: dict) -> None:
    """Resolve only selected PRE references against their full accepted M1 parents."""
    for sid in ("SRC000005", "SRC000054", "SRC000064"):
        pre = [item for item in selected if item["source_instance_id"] == sid
               and item["archive_member"] == "pre.txt"]
        refs = [{field["name"]: field["text"] for field in item["fields"]}
                for item in pre]
        for member, values, indexes in (
            ("sub.txt", {(row["adsh"],) for row in refs}, (0,)),
            ("tag.txt", {(row["tag"], row["version"]) for row in refs}, (0, 1)),
        ):
            table, binding = found[(sid, member)]
            # Values originate in the selected M1 lexical rows; quote as SQL
            # literals and scan only the two accepted parent bindings per source.
            conditions = []
            for parts in sorted(values):
                conditions.append("(" + " AND ".join(
                    f"fields[{index}].lexical_value='{value.replace(chr(39), chr(39) * 2)}'"
                    for index, value in zip(indexes, parts, strict=True)) + ")")
            query = (f"SELECT fields FROM workspace.edp_lab.{table} VERSION AS OF 0 "
                     f"WHERE run_id='{binding['run_id']}' "
                     f"AND binding_sha256='{binding['binding_sha256']}' "
                     "AND record_kind='DATA' AND (" + " OR ".join(conditions) + ")")
            present = {tuple(row["lexical_value"] for row in item["fields"][:len(indexes)])
                       for item in (value.asDict(recursive=True)
                                    for value in spark.sql(query).collect())}
            if not values <= present:
                raise ValueError("V3_FSDS_SELECTED_PARENT_MISSING:" + sid + ":" + member)


def _treasury_occurrences(spark, selection: dict) -> list[dict]:
    ids = ",".join("'" + sid + "'" for sid in XML_IDS)
    query = (f"SELECT * FROM {TREASURY_TABLE} VERSION AS OF 0 "
             f"WHERE source_instance_id IN ({ids})")
    grouped = defaultdict(list)
    for value in spark.sql(query).collect():
        row = value.asDict(recursive=True)
        if row.get("model_version") != "M1_LEXICAL_V1" or row.get(
                "rule_version") != "TREASURY_XML_PROPERTY_LEXICAL_V1":
            raise ValueError("V3_TREASURY_M1_VERSION_CHANGED")
        grouped[(row["source_instance_id"], row["entry_ordinal"])].append(row)
    result = []
    for (sid, ordinal), properties in sorted(grouped.items()):
        spec = selection["sources"][sid]["members"]["atom.entry"]
        if not 1 <= ordinal <= spec["selected_data_rows"]:
            raise ValueError("V3_TREASURY_ORDINAL_OUT_OF_SCOPE")
        result.append(treasury_entry(properties,
                                     selection["sources"][sid]["raw_sha256"]))
    actual = {sid: sum(item["source_instance_id"] == sid for item in result)
              for sid in XML_IDS}
    expected = {sid: selection["sources"][sid]["members"]["atom.entry"]["selected_data_rows"]
                for sid in XML_IDS}
    if len(result) != 1743 or actual != expected:
        raise ValueError("V3_TREASURY_ENTRY_COUNT_CHANGED")
    return result


def _prepare_rows(sources: list[dict], selection: dict,
                  allowed_tables: list[str]) -> tuple[dict[str, list[dict]], dict]:
    if len(sources) != selection["selected_data_rows"]:
        raise ValueError("V3_TOTAL_SELECTED_COUNT_CHANGED")
    selected_parents = Counter(next(field["text"] for field in item["fields"]
                                    if field["name"] == "ACCESSION_NUMBER")
                               for item in sources if item["source_instance_id"] == "SRC000065"
                               and item["archive_member"] == "SUBMISSION.tsv")
    child = {next(field["text"] for field in item["fields"]
                  if field["name"] == "ACCESSION_NUMBER")
             for item in sources if item["source_instance_id"] == "SRC000065"
             and item["archive_member"] != "SUBMISSION.tsv"}
    if any(selected_parents[accession] != 1 for accession in child):
        raise ValueError("V3_13F_PARENT_MISSING_OR_AMBIGUOUS")
    rows = defaultdict(dict)
    counts = defaultdict(int)
    occurrences = set()
    for source in sources:
        sid = source["source_instance_id"]
        feed_id = (selection["sources"][sid]["members"]["atom.entry"]["feed_id"]
                   if sid in XML_IDS else None)
        output = project(source, feed_id=feed_id)
        if output["business_status"] != "PROJECTED":
            raise ValueError("V3_SELECTED_BUSINESS_IDENTITY_BLOCKED:" + sid)
        if output["occurrence_hk"] in occurrences:
            raise ValueError("V3_DUPLICATE_TECHNICAL_OCCURRENCE")
        occurrences.add(output["occurrence_hk"])
        counts[sid] += 1
        for item in output["rows"]:
            table = item["table"]
            if table not in allowed_tables:
                raise ValueError("V3_PROJECTED_TABLE_OUT_OF_SCOPE")
            identity = item["hk"], item["occurrence_hk"]
            prior = rows[table].get(identity)
            if prior is not None and prior["payload_json"] != item["payload_json"]:
                raise ValueError("V3_SAME_KEY_DIFFERENT_PAYLOAD")
            if prior is None:
                rows[table][identity] = item
    expected = {sid: sum(m["selected_data_rows"] for m in entry["members"].values())
                for sid, entry in selection["sources"].items()}
    if dict(counts) != expected:
        raise ValueError("V3_PER_SOURCE_COUNT_CHANGED")
    return {table: list(rows[table].values()) for table in allowed_tables}, dict(counts)


def _write_once(spark, table_rows: dict[str, list[dict]], allowed_tables: list[str]) -> dict:
    """One-shot DDL and insert-only MERGE; caller must reserve protected ledger."""
    namespace = "workspace.edp_lab_day6_vault_proto"
    # Existing targets may represent an uncertain prior operation. Reconcile
    # its protected ledger and Delta state; never silently replay this job.
    for name in allowed_tables:
        if spark.catalog.tableExists(namespace + "." + name):
            raise ValueError("V3_TARGET_ALREADY_EXISTS_RECONCILE_FIRST:" + name)
    from pyspark.sql import types as T

    type_map = {"STRING": T.StringType(), "BIGINT": T.LongType(),
                "TIMESTAMP": T.TimestampType()}
    schema = T.StructType([T.StructField(name, type_map[kind], True)
                           for name, kind in COLUMNS])
    actual = {}
    load_dts = datetime.now(UTC)
    for name in allowed_tables:
        spark.sql(create_sql(name))
        staged = [{column: item[column] for column, _ in COLUMNS if column != "load_dts"}
                  | {"load_dts": load_dts} for item in table_rows[name]]
        if staged:
            frame = spark.createDataFrame(staged, schema=schema)
            frame.createOrReplaceTempView("v3_stage_" + name)
            spark.sql(insert_only_sql(name, "v3_stage_" + name))
        count = spark.sql(f"SELECT COUNT(*) AS n FROM {namespace}.{name}").first()["n"]
        if count != len(staged):
            raise ValueError("V3_PERSISTED_COUNT_MISMATCH:" + name)
        actual[name] = int(count)
    return actual


def run(spark, request: dict, selection: dict, oracle_spec: dict,
        *, execute: bool = False, verify_only: bool = False) -> dict:
    """Run bounded source checks; writes require an independently verified grant."""
    if (request.get("schema") != "EDP_C2000_VAULT_V3_BOUNDED_REQUEST_V1"
            or selection.get("schema") != "EDP_C2000_VAULT_V3_SELECTION_V1"
            or request["selection"]["physical_data_rows"] != 2047
            or request["execution"]["data_rows_max"] != 2048
            or request["execution"]["job_submissions_max"] != 10000000
            or request["execution"]["automatic_retries_max"] != 0
            or len(request["new_v3_table_allowlist"]) != 23):
        raise ValueError("V3_RUNTIME_SCOPE_INVALID")
    oracle_results = evaluate_oracles()
    if (oracle_spec.get("schema") != "EDP_C2000_VAULT_V3_NEGATIVE_ORACLES_V1"
            or {item["id"] for item in oracle_spec["rules"]} != set(oracle_results)
            or oracle_spec.get("fixture_count") != 24):
        raise ValueError("V3_NEGATIVE_ORACLE_SPEC_CHANGED")
    sources = _sec_occurrences(spark, selection)
    sources.extend(_treasury_occurrences(spark, selection))
    rows, per_source = _prepare_rows(sources, selection,
                                     request["new_v3_table_allowlist"])
    if verify_only:
        if execute:
            raise ValueError("V3_VERIFY_ONLY_CANNOT_EXECUTE")
        candidate = collect_readback(spark, rows, per_source)
        return {"status": "INDEPENDENT_V3_READBACK_CANDIDATE",
                "per_source": per_source,
                "isolated_negative_oracles_passed": sorted(oracle_results),
                "readback_candidate": candidate}
    if not execute:
        return {"status": "READ_ONLY_PREPARED", "per_source": per_source,
                "expected_table_rows": {name: len(items) for name, items in rows.items()},
                "isolated_negative_oracles_passed": sorted(oracle_results)}
    if not request["execution"].get("protected_grant_id"):
        raise ValueError("V3_PROTECTED_GRANT_REQUIRED")
    actual = _write_once(spark, rows, request["new_v3_table_allowlist"])
    candidate = collect_readback(spark, rows, per_source)
    return {"status": "PERSISTED_REQUIRES_INDEPENDENT_SIGNED_READBACK",
            "per_source": per_source, "actual_table_rows": actual,
            "isolated_negative_oracles_passed": sorted(oracle_results),
            "readback_candidate": candidate}


def v0a_smoke(spark, request: dict) -> dict:
    """Persist one isolated row through the same wheel and serverless identity."""
    table = request["target_namespace"] + ".v0a_day6_e2e_20261025"
    if request["target_namespace"] != "workspace.edp_lab_day6_vault_proto":
        raise ValueError("V0A_SMOKE_NAMESPACE_CHANGED")
    spark.sql(f"CREATE TABLE {table} (probe_id STRING, probe_value STRING) USING DELTA")
    spark.sql(f"INSERT INTO {table} VALUES ('day6-v0a', 'ready')")
    detail = spark.sql("DESCRIBE DETAIL " + table).first().asDict(recursive=True)
    rows = spark.sql("SELECT probe_id, probe_value FROM " + table).collect()
    if (detail.get("format", "").lower() != "delta" or not detail.get("id")
            or [(row["probe_id"], row["probe_value"]) for row in rows]
            != [("day6-v0a", "ready")]):
        raise ValueError("V0A_SMOKE_PERSISTED_READBACK_FAILED")
    return {"status": "V0A_SMOKE_PERSISTED_REQUIRES_INDEPENDENT_READBACK",
            "table": table, "delta_id": detail["id"], "row_count": len(rows)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--negative-oracles", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--v0a-smoke", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    request = _load(args.request, args.request_sha256)
    selection = _load(args.selection, request["selection"]["sha256"])
    oracle_spec = _load(args.negative_oracles, request["negative_oracles"]["sha256"])
    from pyspark.sql import SparkSession

    if args.v0a_smoke:
        if args.execute or args.verify_only:
            raise ValueError("V0A_SMOKE_AND_V3_EXECUTION_ARE_EXCLUSIVE")
        print(json.dumps(v0a_smoke(SparkSession.builder.getOrCreate(), request),
                         sort_keys=True))
        return
    output = run(SparkSession.builder.getOrCreate(), request, selection, oracle_spec,
                 execute=args.execute, verify_only=args.verify_only)
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
