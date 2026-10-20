# Databricks notebook source
"""Bounded GOLD_V2 lexical execution; no semantic normalization or deduplication."""
import base64
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path

from pyspark.sql import functions as F
from pyspark.sql.types import BinaryType, LongType, StringType, StructField, StructType

BASE = "/Volumes/workspace/edp_lab/raw/edp-native-v1"
TABLE = "workspace.edp_lab.bronze_nasdaq_listed"
contract = json.loads(Path(f"{BASE}/contract.json").read_bytes())
config = contract["config"]
binding = contract["binding"]
raw_path = f"{BASE}/nasdaqlisted.txt"
# Native Spark reads the original uploaded bytes; no CSV inference or NULL coercion.
files = spark.read.format("binaryFile").load(raw_path).select("content").collect()  # noqa: F821
assert len(files) == 1
raw = bytes(files[0].content)
assert hashlib.sha256(raw).hexdigest() == binding["raw_sha256"]
assert len(raw) == contract["raw_size"]
lines = raw.splitlines(keepends=True)
assert b"".join(lines) == raw
assert all(line.endswith(b"\r\n") for line in lines)
header = config["table"]["expected_header"]
assert lines[0][:-2].decode("utf-8", errors="strict").split("|") == header
footer = config["table"]["footer"]
assert lines[-1][:-2].decode("utf-8") == footer["first_field"] + "|" * 7
assert len(lines) == contract["expected_rows"] + 2
records = []
offset = len(lines[0])
for line_number, line in enumerate(lines[1:-1], 2):
    text = line[:-2].decode("utf-8", errors="strict")
    records.append((line_number - 1, line_number, offset, offset + len(line), line, text))
    offset += len(line)
assert offset + len(lines[-1]) == len(raw)
schema = StructType([
    StructField("_occurrence", LongType(), False),
    StructField("_line_number", LongType(), False),
    StructField("_byte_start", LongType(), False),
    StructField("_byte_end", LongType(), False),
    StructField("_raw_record", BinaryType(), False),
    StructField("_raw_text", StringType(), False),
])
source = spark.createDataFrame(records, schema).withColumn(  # noqa: F821
    "_fields", F.split(F.col("_raw_text"), r"\|", -1))
assert source.where(F.size("_fields") != len(header)).count() == 0
frame = source.select("*", *[
    F.col("_fields")[i].alias(name) for i, name in enumerate(header)
]).drop("_fields")
for name, value in {
    "_source_instance_id": binding["source_instance_id"],
    "_logical_table_name": binding["logical_table_name"],
    "_registered_raw_path": binding["raw_path"],
    "_volume_path": raw_path,
    "_raw_sha256": binding["raw_sha256"],
    "_freeze_sha256": config["freeze_sha256"],
    "_profile_id": config["profile_id"],
    "_gold_evidence_sha256": contract["gold_evidence_sha256"],
}.items():
    frame = frame.withColumn(name, F.lit(value))
# Existing tables are never overwritten; reruns validate the existing exact snapshot.
if not spark.catalog.tableExists(TABLE):  # noqa: F821
    frame.createOrReplaceTempView("_edp_native_nasdaq_input")
    spark.sql(f"""CREATE TABLE {TABLE} USING DELTA
        TBLPROPERTIES ('delta.columnMapping.mode' = 'name')
        AS SELECT * FROM _edp_native_nasdaq_input""")  # noqa: F821
actual = spark.table(TABLE)  # noqa: F821
assert frame.exceptAll(actual.select(frame.columns)).count() == 0
assert actual.select(frame.columns).exceptAll(frame).count() == 0
queries = {
    "counts": f"""SELECT count(*) AS occurrences, count(DISTINCT _occurrence) AS locators,
        min(_line_number) AS first_line, max(_line_number) AS last_line FROM {TABLE}""",
    "duplicates": f"""SELECT count(*) AS duplicate_groups, coalesce(sum(n-1),0) AS excess_rows
        FROM (SELECT {','.join('`'+c+'`' for c in header)}, count(*) n FROM {TABLE}
        GROUP BY {','.join('`'+c+'`' for c in header)} HAVING count(*) > 1)""",
    "provenance": f"""SELECT _source_instance_id, _raw_sha256, _freeze_sha256,
        _registered_raw_path, _volume_path, count(*) AS occurrences FROM {TABLE}
        GROUP BY ALL""",
    "blank_null": "SELECT " + ",".join(
        f"sum(CASE WHEN `{c}` = '' THEN 1 ELSE 0 END) AS blank_{i}, "
        f"sum(CASE WHEN `{c}` IS NULL THEN 1 ELSE 0 END) AS null_{i}"
        for i, c in enumerate(header)) + f" FROM {TABLE}",
    "literal_na": f"SELECT Symbol, _line_number FROM {TABLE} WHERE Symbol = 'NA'",
    "blank_null_probe": """SELECT size(split('x|', '[|]', -1)) AS width,
        split('x|', '[|]', -1)[1] = '' AS blank_preserved,
        split('x|', '[|]', -1)[1] IS NULL AS blank_is_null,
        CAST(NULL AS STRING) IS NULL AS explicit_null_is_null""",
    "history": f"DESCRIBE HISTORY {TABLE}",
    "detail": f"DESCRIBE DETAIL {TABLE}",
}
results = {name: {"sql": sql, "rows": [r.asDict(recursive=True) for r in
           spark.sql(sql).collect()]} for name, sql in queries.items()}  # noqa: F821
counts = results["counts"]["rows"][0]
assert counts["occurrences"] == counts["locators"] == contract["expected_rows"]
assert results["duplicates"]["rows"][0]["duplicate_groups"] == 0
assert all(v == 0 for v in results["blank_null"]["rows"][0].values())
assert results["blank_null_probe"]["rows"][0] == {
    "width": 2, "blank_preserved": True, "blank_is_null": False, "explicit_null_is_null": True}
# Reconstruct original bytes and compare every persisted text field and occurrence.
persisted = actual.orderBy("_occurrence").collect()
rebuilt = lines[0] + b"".join(bytes(r._raw_record) for r in persisted) + lines[-1]
assert rebuilt == raw
for row, original in zip(persisted, records, strict=True):
    assert tuple(row[c] for c in header) == tuple(original[-1].split("|"))
    assert (row._occurrence, row._line_number, row._byte_start, row._byte_end) == original[:4]
assert Counter(tuple(r[c] for c in header) for r in persisted) == Counter(
    tuple(r[-1].split("|")) for r in records)
result = {
    "status": "TESTED", "table": TABLE, "queries": results,
    "runtime": {"spark": spark.version, "python": platform.python_version()},  # noqa: F821
    "contract_sha256": hashlib.sha256(Path(f"{BASE}/contract.json").read_bytes()).hexdigest(),
    "notebook_sha256": hashlib.sha256(Path(f"{BASE}/notebook-v3.py").read_bytes()).hexdigest(),
    "reconstructed_raw_sha256": hashlib.sha256(rebuilt).hexdigest(),
    "integrity": {"all_text_equal": True, "all_lineage_equal": True,
                  "multiplicity_equal": True, "bidirectional_except_all": True},
    "metadata": {"header_line": 1, "footer_line": len(lines), "data_occurrences": len(records),
                 "header_base64": base64.b64encode(lines[0]).decode(),
                 "footer_base64": base64.b64encode(lines[-1]).decode(),
                 "footer_byte_start": offset},
    "source_null_semantics": "UNRESOLVED",
    "coverage": "Exact registered snapshot; zero observed empty fields or duplicate groups. "
                "Synthetic blank/NULL probe is separate from source observations.",
}
serialized = json.dumps(result, indent=2, sort_keys=True, default=str)
with Path(f"{BASE}/native-results.json").open("x") as stream:
    stream.write(serialized + "\n")
dbutils.notebook.exit(serialized)  # noqa: F821
