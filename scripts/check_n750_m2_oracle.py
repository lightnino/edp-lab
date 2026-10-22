"""Independent read-only N750 manifest, lineage and exact Decimal check."""
from __future__ import annotations

import collections
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "runs/n750/step8-v1"
OUT = ROOT / "runs/c1500-m2-stability/v1/local-oracle.json"
DATA = "http://schemas.microsoft.com/ado/2007/08/dataservices"
NUMERIC = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?\Z", re.ASCII)
SPACE = set(" \t\r\n\f\v")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def oracle(text: str | None, present: bool, null_marker: bool):
    if not present:
        return "MISSING", "SOURCE_FIELD_ABSENT", None
    if null_marker:
        return "NULL_UNRESOLVED", "SOURCE_NULL_MARKER_UNINTERPRETED", None
    if text is None:
        raise AssertionError("unexplained NULL")
    if all(c in SPACE for c in text):
        return "BLANK", "EMPTY_TEXT" if text == "" else "WHITESPACE_ONLY", None
    if NUMERIC.fullmatch(text) is None:
        return "INVALID", "LEXICAL_GRAMMAR", None
    signed = text.removeprefix("+").removeprefix("-")
    integer, dot, fraction = signed.partition(".")
    if len(fraction) > 4:
        return "SCALE_EXCEEDED", "FRACTIONAL_DIGITS_GT_4", None
    if len(integer.lstrip("0")) > 34:
        return "OVERFLOW", "INTEGER_DIGITS_GT_34", None
    value = Decimal(text + ("" if dot else ".") + "0" * (4 - len(fraction)))
    return "VALID", "EXACT_PROJECTION", value


def main() -> None:
    old = json.loads((ROOT / "metadata/freezes/C750_v1/C750.bindings.json").read_bytes())
    new = json.loads((ROOT / "metadata/admissions/N750_v1/bindings.json").read_bytes())
    combined = json.loads((ROOT / "metadata/freezes/C1500_v1/C1500.bindings.json").read_bytes())
    freeze = json.loads((ROOT / "metadata/freezes/C1500_v1/freeze.json").read_bytes())
    old_execution = json.loads((ROOT / "metadata/freezes/O_C750_M1_v1/references.json").read_bytes())
    for name, expected in freeze["files_sha256"].items():
        assert sha(ROOT / "metadata/freezes/C1500_v1" / name) == expected
    keys = lambda rows: {(r["source_instance_id"], r["source_identity"], r["raw_sha256"], r["raw_path"]) for r in rows}
    assert len(old) == len(new) == 750 and len(combined) == 1500
    assert keys(old).isdisjoint(keys(new)) and keys(combined) == keys(old) | keys(new)
    assert len({r["source_instance_id"] for r in combined}) == 1500
    raw = json.loads((BASE / "raw/completion.json").read_bytes())
    receipts = {r["source_instance_id"]: r for r in raw["receipts"]}
    assert len(receipts) == 750
    for binding in new:
        r = receipts[binding["source_instance_id"]]
        assert r["source_identity"] == binding["source_identity"]
        assert r["actual_sha256"] == r["expected_sha256"] == binding["raw_sha256"]
    assert collections.Counter(r["disposition"] for r in receipts.values()) == {
        "EXISTING_REUSED": 450, "UPLOADED_NEW": 300}
    clean = json.loads((BASE / "clean/completion.json").read_bytes())
    for key, name in {"sec": "sec-m1-records.parquet", "xml": "treasury-m1-properties.parquet",
                      "m2": "treasury-m2-projections.parquet", "coverage": "source-coverage.parquet"}.items():
        assert sha(BASE / "clean" / name) == clean["parquet_sha256"][key]
    rows = pq.read_table(BASE / "clean/treasury-m2-projections.parquet").to_pylist()
    lexical = pq.read_table(BASE / "clean/treasury-m1-properties.parquet").to_pylist()
    coverage = pq.read_table(BASE / "clean/source-coverage.parquet").to_pylist()
    lexical_by_key = {(r["source_instance_id"], r["entry_ordinal"], r["property_ordinal"]): r
                      for r in lexical}
    assert len(lexical_by_key) == len(lexical) == 21616
    bindings = {r["source_instance_id"]: r for r in new}
    outcomes = collections.Counter()
    by_source = collections.Counter()
    names = collections.defaultdict(set)
    property_names = collections.defaultdict(set)
    metadata_types = collections.defaultdict(lambda: collections.defaultdict(set))
    declared_rate_types = collections.defaultdict(set)
    entries = collections.defaultdict(set)
    empty_properties = collections.Counter()
    absent = collections.Counter()
    present_empty = collections.Counter()
    m2_present_keys = set()
    m2_missing_keys = set()
    per_entry_qnames = collections.defaultdict(list)
    for x in lexical:
        sid = x["source_instance_id"]
        name = x["property_qname"].removeprefix("{" + DATA + "}")
        property_names[sid].add(name)
        entries[sid].add(x["entry_ordinal"])
        metadata_types[sid][name].update(json.loads(x["attributes_json"]).values())
        if name == "RATE_TYPE":
            declared_rate_types[sid].add(x["lexical_value"])
        if x["lexical_value"] == "":
            empty_properties[(sid, name)] += 1
    for r in rows:
        sid = r["source_instance_id"]
        assert r["raw_sha256"] == bindings[sid]["raw_sha256"]
        assert r["source_identity"] == bindings[sid]["source_identity"]
        assert r["run_id"] == "n750_step8_v1"
        assert r["model_version"] == "M1_LEXICAL_V1"
        assert r["m2_model_version"] == "M2_ADDITIVE_TYPED_NUMERIC_V1"
        assert r["conversion_rule_version"] == "EXACT_DECIMAL_38_4_V1"
        assert r["source_rule_version"] == "TREASURY_RATE_QNAME_SCOPE_V1"
        expected = oracle(r["lexical_value"], r["present"], r["null_marker"])
        assert (r["conversion_outcome"], r["conversion_reason"], r["value_decimal"]) == expected
        if r["present"]:
            k = sid, r["entry_ordinal"], r["property_ordinal"]
            assert k not in m2_present_keys
            m2_present_keys.add(k)
            x = lexical_by_key[k]
            for col in ("property_qname", "lexical_value", "span_sha256", "byte_offset",
                        "byte_length", "attributes_json", "null_marker"):
                assert r[col] == x[col]
            if r["lexical_value"] == "":
                present_empty[sid] += 1
        else:
            k = sid, r["entry_ordinal"], r["property_qname"]
            assert k not in m2_missing_keys
            m2_missing_keys.add(k)
            absent[sid] += 1
            assert r["property_ordinal"] is None and r["byte_offset"] is None
            assert r["lexical_value"] is None and r["span_sha256"] is None
        outcomes[r["conversion_outcome"]] += 1
        by_source[sid] += 1
        local_name = r["property_qname"].removeprefix("{" + DATA + "}")
        names[sid].add(local_name)
        per_entry_qnames[(sid, r["entry_ordinal"])].append(local_name)
    assert outcomes == {"VALID": 12793, "MISSING": 155}
    assert len(m2_present_keys) == 12793 and len(m2_missing_keys) == 155
    assert len(rows) == clean["m2_evaluations"] == 12948
    cov = {r["source_instance_id"]: r for r in coverage}
    assert len(cov) == 750
    for sid, count in by_source.items():
        assert cov[sid]["m2_evaluations"] == count
        assert cov[sid]["m2_missing"] == absent[sid]
    expected_names = {
        "SRC010451": {"BC_" + x for x in ("1MONTH", "1_5MONTH", "2MONTH", "3MONTH", "4MONTH", "6MONTH", "1YEAR", "2YEAR", "3YEAR", "5YEAR", "7YEAR", "10YEAR", "20YEAR", "30YEAR", "30YEARDISPLAY")},
        "SRC010452": {f"ROUND_B1_{kind}_{week}WK_2" for kind in ("CLOSE", "YIELD") for week in (4, 6, 8, 13, 17, 26, 52)} | {f"CS_{week}WK_{kind}_AVG" for week in (4, 6, 8, 13, 17, 26, 52) for kind in ("CLOSE", "YIELD")},
        "SRC010453": {"RATE"}, "SRC010454": {"TC_" + x for x in ("5YEAR", "7YEAR", "10YEAR", "20YEAR", "30YEAR")},
        "SRC010455": {"RATE"},
    }
    assert {sid: names[sid] for sid in expected_names} == expected_names
    for (sid, _), qnames in per_entry_qnames.items():
        assert len(qnames) == len(expected_names[sid])
        assert set(qnames) == expected_names[sid]
    summary = {"schema": "N750_M2_INDEPENDENT_ORACLE_V1", "status": "PASS",
               "population": {"old_sources": 750, "new_sources": 750, "combined_sources": 1500,
                              "old_source_roster_entries": len(old),
                              "new_source_roster_entries": len(new),
                              "combined_source_roster_entries": len(combined),
                              "old_execution_bindings_reused": old_execution["population"]["C750"]["bindings"],
                              "new_execution_bindings": 750,
                              "combined_execution_bindings": old_execution["population"]["C750"]["bindings"] + len(new)},
               "oracle": {"evaluations": len(rows), "outcomes": dict(outcomes),
                          "mismatches": 0, "present_empty": dict(present_empty),
                          "structurally_absent": dict(absent)},
               "treasury_property_names": {k: sorted(v) for k, v in names.items()},
               "present_empty_xml_properties": [
                   {"source_instance_id": sid, "qname_local": name, "count": count}
                   for (sid, name), count in sorted(empty_properties.items())],
               "treasury_source_metadata": {
                   sid: {"entry_count": len(entries[sid]),
                         "date_qnames": sorted(n for n in property_names[sid] if "DATE" in n),
                         "tenor_labeled_qnames": sorted(n for n in property_names[sid]
                                                        if any(t in n for t in ("YEAR", "MONTH", "WK"))),
                         "rate_type_values": sorted(declared_rate_types[sid]),
                         "explicit_unit_qnames": sorted(n for n in property_names[sid]
                                                        if n in {"UNIT", "UNITS", "UOM"}),
                         "metadata_types": {n: sorted(v) for n, v in metadata_types[sid].items()}}
                   for sid in sorted(entries)},
               "evidence_sha256": {"c1500_bindings": sha(ROOT / "metadata/freezes/C1500_v1/C1500.bindings.json"),
                                   "n750_bindings": sha(ROOT / "metadata/admissions/N750_v1/bindings.json"),
                                   "o_c750_m1_references": sha(ROOT / "metadata/freezes/O_C750_M1_v1/references.json"),
                                   "raw_completion": sha(BASE / "raw/completion.json"),
                                   "clean_completion": sha(BASE / "clean/completion.json")}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "PASS", "population": summary["population"],
                      "oracle": summary["oracle"], "evidence_sha256": sha(OUT)}))


if __name__ == "__main__":
    main()
