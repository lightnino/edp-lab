"""Build versioned N750 lexical/M2 Parquet from hash-equivalent verified RAW.

The source originals have the same frozen SHA as independently downloaded remote
objects in the completed Step 8 RAW receipts. This local build is deterministic;
Databricks publication and independent Delta readback are separate phases.
"""
from __future__ import annotations

import hashlib
import json
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from edp_lab.ingestion.n750_step8_authorization import authorize
from edp_lab.materialization.n750_step8 import DATA, META, parse_sec, parse_treasury
from edp_lab.materialization.typed_numeric_v1 import convert

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/n750/step8-v1/clean"
RAW = ROOT / "runs/n750/step8-v1/raw/completion.json"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, default=str)
        stream.write("\n")


def schema_sec():
    fields = [(x, pa.string()) for x in ("run_id", "source_instance_id", "source_identity", "raw_sha256")]
    fields += [("source_line", pa.int64()), ("byte_offset", pa.int64()),
               ("byte_length", pa.int64()), ("line_sha256", pa.string()),
               ("record_kind", pa.string()), ("original_text", pa.string()),
               ("fields", pa.list_(pa.string())), ("model_version", pa.string()),
               ("rule_version", pa.string())]
    return pa.schema(fields)


def schema_xml(*, typed=False):
    fields = [(x, pa.string()) for x in ("run_id", "source_instance_id", "source_identity", "raw_sha256")]
    fields += [("entry_ordinal", pa.int64()), ("property_ordinal", pa.int64()),
               ("property_qname", pa.string()), ("byte_offset", pa.int64()),
               ("byte_length", pa.int64()), ("span_sha256", pa.string()),
               ("lexical_value", pa.string()), ("attributes_json", pa.string()),
               ("null_marker", pa.bool_()), ("model_version", pa.string()),
               ("rule_version", pa.string())]
    if typed:
        fields += [("value_decimal", pa.decimal128(38, 4)),
                   ("conversion_outcome", pa.string()), ("conversion_reason", pa.string()),
                   ("m2_model_version", pa.string()), ("conversion_rule_version", pa.string()),
                   ("source_rule_version", pa.string()), ("present", pa.bool_())]
    return pa.schema(fields)


def verify_sec_readback(reader, index, raw, source):
    rows = reader.read_row_group(index).to_pylist()
    assert rows and all(r["source_instance_id"] == source["source_instance_id"] for r in rows)
    rebuilt = bytearray()
    for number, row in enumerate(rows, 1):
        assert row["source_line"] == number and row["byte_offset"] == len(rebuilt)
        part = raw[row["byte_offset"]:row["byte_offset"] + row["byte_length"]]
        assert hashlib.sha256(part).hexdigest() == row["line_sha256"]
        content = part.removesuffix(b"\n").removesuffix(b"\r").decode("utf-8")
        assert content == row["original_text"]
        assert row["fields"] == (content.split("|") if number > 7 else [])
        assert row["record_kind"] == ("DATA" if number > 7 else "HEADER" if number == 6 else "METADATA")
        rebuilt.extend(part)
    assert rebuilt == raw
    return {"records_total": len(rows), "records_data": len(rows) - 7,
            "fields_data": (len(rows) - 7) * 5}


def verify_xml_readback(lex_reader, typed_reader, index, raw, source):
    rows = lex_reader.read_row_group(index).to_pylist()
    typed = typed_reader.read_row_group(index).to_pylist()
    assert rows and typed
    assert all(r["source_instance_id"] == source["source_instance_id"] for r in rows + typed)
    seen = set()
    for row in rows:
        key = (row["entry_ordinal"], row["property_ordinal"])
        assert key not in seen
        seen.add(key)
        start, end = row["byte_offset"], row["byte_offset"] + row["byte_length"]
        fragment = raw[start:end]
        assert hashlib.sha256(fragment).hexdigest() == row["span_sha256"]
        wrapper = (b'<root xmlns:d="' + DATA.encode() + b'" xmlns:m="' + META.encode() +
                   b'">' + fragment + b'</root>')
        element = ET.fromstring(wrapper)[0]
        assert element.tag == row["property_qname"]
        assert ("" if element.text is None else element.text) == row["lexical_value"]
        assert json.dumps(element.attrib, sort_keys=True) == row["attributes_json"]
    eligible = {(r["entry_ordinal"], r["property_ordinal"]): r for r in rows}
    for row in typed:
        assert row["source_rule_version"] == "TREASURY_RATE_QNAME_SCOPE_V1"
        if row["present"]:
            lexical = eligible[(row["entry_ordinal"], row["property_ordinal"])]
            assert row["lexical_value"] == lexical["lexical_value"]
            assert row["span_sha256"] == lexical["span_sha256"]
            expected = convert(row["lexical_value"], null_marker=row["null_marker"])
        else:
            assert row["property_ordinal"] is None and row["lexical_value"] is None
            assert row["byte_offset"] is None and row["span_sha256"] is None
            expected = convert(None, present=False)
        assert row["conversion_outcome"] == expected.conversion_outcome
        assert row["conversion_reason"] == expected.conversion_reason
        assert row["value_decimal"] == expected.value_decimal
    return {"properties_present": len(rows), "m2_evaluations": len(typed),
            "m2_present": sum(r["present"] for r in typed),
            "m2_missing": sum(not r["present"] for r in typed)}


def main():
    started = time.monotonic()
    bindings = json.loads((ROOT / "metadata/admissions/N750_v1/bindings.json").read_bytes())
    plan = json.loads((ROOT / "proposals/n750-step1-v3/plan.json").read_bytes())
    remote_raw = json.loads(RAW.read_bytes())
    assert remote_raw["status"] == "PASS" and remote_raw["verified_sources"] == 750
    receipts = {r["source_instance_id"]: r for r in remote_raw["receipts"]}
    assert len(receipts) == 750
    authority = authorize(ROOT, "processing", [r["source_instance_id"] for r in bindings])
    assert authority["owner_grant_sha256"] == remote_raw["owner_grant_sha256"]
    assert not OUT.exists()
    OUT.mkdir(parents=True)
    paths = {"sec": OUT / "sec-m1-records.parquet", "xml": OUT / "treasury-m1-properties.parquet",
             "m2": OUT / "treasury-m2-projections.parquet",
             "coverage": OUT / "source-coverage.parquet"}
    summaries = []
    with pq.ParquetWriter(paths["sec"], schema_sec(), compression="zstd") as sec_writer, \
         pq.ParquetWriter(paths["xml"], schema_xml(), compression="zstd") as xml_writer, \
         pq.ParquetWriter(paths["m2"], schema_xml(typed=True), compression="zstd") as m2_writer:
        for source, item in zip(bindings, plan["selected"], strict=True):
            sid = source["source_instance_id"]
            receipt = receipts[sid]
            assert receipt["actual_sha256"] == source["raw_sha256"]
            assert receipt["status"] == "EXACT_REMOTE_BYTES_PASS"
            local = Path(item["physical_raw_path"])
            assert local.is_file() and not local.is_symlink() and sha(local) == source["raw_sha256"]
            raw = local.read_bytes()
            clock = time.monotonic()
            if item["family"] == "SEC_EDGAR_DAILY_MASTER":
                rows = parse_sec(raw, source)
                sec_writer.write_table(pa.Table.from_pylist(rows, schema=schema_sec()))
                counts = {"records_total": len(rows), "records_data": len(rows) - 7,
                          "fields_data": (len(rows) - 7) * 5}
            elif item["family"] == "TREASURY_ANNUAL_XML":
                lexical, projected, entries = parse_treasury(raw, source)
                xml_writer.write_table(pa.Table.from_pylist(lexical, schema=schema_xml()))
                m2_writer.write_table(pa.Table.from_pylist(projected, schema=schema_xml(typed=True)))
                counts = {"entries": entries, "properties_present": len(lexical),
                          "m2_evaluations": len(projected),
                          "m2_present": sum(r["present"] for r in projected),
                          "m2_missing": sum(not r["present"] for r in projected)}
            else:
                raise ValueError("UNAUTHORIZED_SOURCE_FAMILY")
            assert sha(local) == source["raw_sha256"]
            summaries.append({"source_instance_id": sid, "source_identity": source["source_identity"],
                              "raw_sha256": source["raw_sha256"], "remote": receipt["remote"],
                              "family": item["family"], "bytes": len(raw), "status": "COMPLETE",
                              "seconds": round(time.monotonic() - clock, 6), **counts})
            if len(summaries) % 50 == 0:
                print(f"CLEAN built {len(summaries)}/750", flush=True)
    # This verifier reads the persisted Parquet independently and reconstructs
    # every SEC source byte plus each Treasury property from frozen RAW locators.
    sec_reader, xml_reader, m2_reader = (pq.ParquetFile(paths[k]) for k in ("sec", "xml", "m2"))
    assert sec_reader.num_row_groups == 745 and xml_reader.num_row_groups == m2_reader.num_row_groups == 5
    sec_index = xml_index = 0
    for source, item, summary in zip(bindings, plan["selected"], summaries, strict=True):
        raw = Path(item["physical_raw_path"]).read_bytes()
        if item["family"] == "SEC_EDGAR_DAILY_MASTER":
            actual = verify_sec_readback(sec_reader, sec_index, raw, source)
            sec_index += 1
        else:
            actual = verify_xml_readback(xml_reader, m2_reader, xml_index, raw, source)
            xml_index += 1
        assert all(summary[k] == v for k, v in actual.items()), source["source_instance_id"]
    save(OUT / "coverage.json", summaries)
    coverage_fields = [(name, pa.string()) for name in
                       ("source_instance_id", "source_identity", "raw_sha256", "remote", "family", "status")]
    coverage_fields += [(name, pa.int64()) for name in
                        ("bytes", "records_total", "records_data", "fields_data", "entries",
                         "properties_present", "m2_evaluations", "m2_present", "m2_missing")]
    coverage_fields += [("seconds", pa.float64())]
    pq.write_table(pa.Table.from_pylist(summaries, schema=pa.schema(coverage_fields)),
                   paths["coverage"], compression="zstd")
    assert [{k: v for k, v in row.items() if v is not None}
            for row in pq.read_table(paths["coverage"]).to_pylist()] == summaries
    complete = {"status": "PASS", "run_id": "n750_step8_v1",
                "owner_grant_sha256": authority["owner_grant_sha256"],
                "remote_completion_sha256": sha(RAW), "sources_complete": len(summaries),
                "sec_sources": sec_index, "treasury_sources": xml_index,
                "records_data": sum(s.get("records_data", 0) for s in summaries),
                "fields_data": sum(s.get("fields_data", 0) for s in summaries),
                "xml_properties_present": sum(s.get("properties_present", 0) for s in summaries),
                "m2_evaluations": sum(s.get("m2_evaluations", 0) for s in summaries),
                "m2_present": sum(s.get("m2_present", 0) for s in summaries),
                "m2_missing": sum(s.get("m2_missing", 0) for s in summaries),
                "parquet_sha256": {k: sha(v) for k, v in paths.items()},
                "coverage_sha256": sha(OUT / "coverage.json"),
                "started_at_utc": datetime.now(UTC).isoformat(),
                "wall_seconds": round(time.monotonic() - started, 3),
                "readback": "ALL_SEC_BYTES_RECONSTRUCTED_AND_ALL_XML_PROPERTY_SPANS_VERIFIED"}
    save(OUT / "completion.json", complete)
    print(json.dumps({k: v for k, v in complete.items() if k != "parquet_sha256"}), flush=True)


if __name__ == "__main__":
    main()
