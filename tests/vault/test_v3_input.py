"""Accepted M1 adapter fidelity and fail-closed locator checks."""

import copy

import pytest

from edp_lab.vault.v3_input import DATA_NS, c300_occurrence, treasury_entry


def test_c300_adapter_preserves_exact_member_and_field_order():
    binding = {"source_instance_id": "SRC000107", "run_id": "r",
               "binding_sha256": "c" * 64, "processing_status": "COMPLETE",
               "raw_sha256": "a" * 64, "archive_member": "master.20230103.idx",
               "member_sha256": "b" * 64}
    names = ("CIK", "Company Name", "Form Type", "Date Filed", "File Name")
    row = {"record_kind": "DATA", "source_instance_id": "SRC000107",
           "run_id": "r", "binding_sha256": "c" * 64,
           "source_line": 2, "byte_offset": 50, "byte_length": 20,
           "fields": [{"field_ordinal": i, "original_name": name,
                       "disposition": "DIRECT_MAP", "lexical_value": "001"}
                      for i, name in enumerate(names, 1)]}
    converted = c300_occurrence(row, binding, "a" * 64, names)
    assert converted["archive_member"] == "daily_master.idx"
    assert converted["physical_archive_member"] == "master.20230103.idx"
    assert converted["fields"][0]["text"] == "001"
    changed = copy.deepcopy(row)
    changed["fields"][0]["original_name"] = "Issuer"
    with pytest.raises(ValueError, match="FIELD_OR_PARSER_CHANGED"):
        c300_occurrence(changed, binding, "a" * 64, names)


def test_treasury_entry_regroups_properties_and_keeps_byte_lineage():
    props = [{"source_instance_id": "SRC010453", "entry_ordinal": 1,
              "raw_sha256": "a" * 64, "property_ordinal": i,
              "property_qname": "{" + DATA_NS + "}" + name,
              "byte_offset": i * 10, "byte_length": 9,
              "lexical_value": value, "null_marker": False,
              "span_sha256": "b" * 64, "attributes_json": "{}"}
             for i, (name, value) in enumerate(
                 (("QUOTE_DATE", "2025-01-02"), ("RATE_TYPE", "Real_Rate")), 1)]
    source = treasury_entry(props, "a" * 64)
    assert [field["name"] for field in source["fields"]] == ["QUOTE_DATE", "RATE_TYPE"]
    assert source["properties_lineage"][1]["byte_offset"] == 20
    props[1]["property_ordinal"] = 3
    with pytest.raises(ValueError, match="PROPERTY_LINEAGE_CHANGED"):
        treasury_entry(props, "a" * 64)


def test_edgar_standalone_empty_member_preserves_lineage():
    from edp_lab.vault.v3_spark_runtime import _member

    names = ("CIK", "Company Name", "Form Type",
             "Date Filed", "File Name")
    binding = {
        "source_instance_id": "SRC000107",
        "archive_member": "",
        "processing_status": "COMPLETE",
        "run_id": "r",
        "binding_sha256": "c" * 64,
        "raw_sha256": "a" * 64,
        "member_sha256": "b" * 64,
    }
    row = {
        "record_kind": "DATA",
        "source_instance_id": "SRC000107",
        "run_id": "r",
        "binding_sha256": "c" * 64,
        "source_line": 2,
        "byte_offset": 50,
        "byte_length": 20,
        "fields": [
            {
                "field_ordinal": i,
                "original_name": name,
                "disposition": "DIRECT_MAP",
                "lexical_value": "001",
            }
            for i, name in enumerate(names, 1)
        ],
    }

    assert _member(binding) == "daily_master.idx"
    result = c300_occurrence(row, binding, "a" * 64, names)
    assert result["archive_member"] == "daily_master.idx"
    assert result["physical_archive_member"] == ""
    assert result["member_sha256"] == "b" * 64
    assert result["byte_offset"] == 50

    with pytest.raises(ValueError, match="V3_C300_BINDING_OR_RAW_MISMATCH"):
        c300_occurrence(row, binding, "x" * 64, names)

    invalid = dict(binding, archive_member="unrelated.csv")
    with pytest.raises(ValueError, match="V3_UNEXPECTED_C300_MEMBER"):
        _member(invalid)
    with pytest.raises(ValueError, match="V3_C300_MEMBER_OUT_OF_SCOPE"):
        c300_occurrence(row, invalid, "a" * 64, names)
