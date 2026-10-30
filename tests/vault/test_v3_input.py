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



def test_thirteen_f_all_seven_members_preserve_lowercase_extension():
    """Observed frozen 13F members use uppercase stem and lowercase .tsv."""
    from edp_lab.vault.v3_mapping import THIRTEEN_F_MEMBERS
    from edp_lab.vault.v3_spark_runtime import _member

    assert len(THIRTEEN_F_MEMBERS) == 7
    names = ("ACCESSION_NUMBER",)
    row = {
        "record_kind": "DATA", "source_instance_id": "SRC000065",
        "run_id": "c300-run", "binding_sha256": "c" * 64,
        "source_line": 2, "byte_offset": 50, "byte_length": 20,
        "fields": [{
            "field_ordinal": 1, "original_name": names[0],
            "disposition": "DIRECT_MAP", "lexical_value": "000001",
        }],
    }
    for member in THIRTEEN_F_MEMBERS:
        binding = {
            "source_instance_id": "SRC000065",
            "archive_member": member,
            "run_id": "c300-run",
            "binding_sha256": "c" * 64,
            "processing_status": "COMPLETE",
            "raw_sha256": "a" * 64,
            "member_sha256": "b" * 64,
        }
        assert _member(binding) == member
        result = c300_occurrence(row, binding, "a" * 64, names)
        assert result["archive_member"] == member
        assert result["physical_archive_member"] == member
        assert result["fields"][0]["text"] == "000001"

        # Normalizing every character with .upper() breaks the frozen
        # selection and must not silently normalize unknown case variants.
        invalid = dict(binding, archive_member=member.upper())
        with pytest.raises(ValueError, match="V3_UNEXPECTED_C300_MEMBER"):
            _member(invalid)
        with pytest.raises(ValueError, match="V3_C300_MEMBER_OUT_OF_SCOPE"):
            c300_occurrence(row, invalid, "a" * 64, names)


def test_c300_all_17_frozen_sec_bindings_are_discoverable():
    """Regression for real read-only canary failure, previously 10/17."""
    import json
    from pathlib import Path
    from types import SimpleNamespace

    from edp_lab.vault.v3_spark_runtime import C300_TABLES, _bindings

    root = Path(__file__).resolve().parents[2]
    selection = json.loads((root / "metadata/evaluations/"
                            "day6_c2000_vault_v3_selection_v1.json").read_bytes())
    sec_ids = ("SRC000005", "SRC000054", "SRC000064", "SRC000065", "SRC000107")
    expected = {(sid, name) for sid in sec_ids
                for name in selection["sources"][sid]["members"]}
    assert len(expected) == 17

    rows = [{
        "source_instance_id": sid,
        "archive_member": ("" if sid == "SRC000107" else name),
        "raw_sha256": selection["sources"][sid]["raw_sha256"],
        "processing_status": "COMPLETE",
    } for sid, name in sorted(expected)]
    rows.append(dict(rows[0], archive_member="num.txt"))

    class Spark:
        def sql(self, query):
            assert "VERSION AS OF 0" in query
            selected = rows if C300_TABLES[0][1] in query else []
            return SimpleNamespace(
                collect=lambda: [
                    SimpleNamespace(asDict=lambda recursive, row=row: row)
                    for row in selected
                ]
            )

    found = _bindings(Spark(), selection)
    assert set(found) == expected
    assert len(found) == 17
    for sid, name in expected:
        _, binding = found[(sid, name)]
        assert binding["raw_sha256"] == selection["sources"][sid]["raw_sha256"]



def test_real_standalone_edgar_c300_to_v3_projection_empty_member_is_valid():
    """Regression for v3 canary run 588435072660254, INVALID_OCCURRENCE_LOCATOR."""
    from edp_lab.vault.v3_keys import occurrence_key
    from edp_lab.vault.v3_mapping import EDGAR_HEADER, project

    fields = [{
        "field_ordinal": n,
        "original_name": name,
        "disposition": "DIRECT_MAP",
        "lexical_value": "edgar/data/1001/data.txt"
        if name == "File Name" else "001",
    } for n, name in enumerate(EDGAR_HEADER, 1)]
    binding = {
        "source_instance_id": "SRC000107", "archive_member": "",
        "processing_status": "COMPLETE", "run_id": "r",
        "binding_sha256": "c" * 64, "raw_sha256": "a" * 64,
        "member_sha256": "b" * 64,
    }
    row = {
        "record_kind": "DATA", "source_instance_id": "SRC000107",
        "run_id": "r", "binding_sha256": "c" * 64,
        "source_line": 2, "byte_offset": 50, "byte_length": 20,
        "fields": fields,
    }
    before = copy.deepcopy(row), copy.deepcopy(binding)
    source = c300_occurrence(row, binding, "a" * 64, EDGAR_HEADER)
    assert source["physical_archive_member"] == ""
    result = project(source)
    assert result["business_status"] == "PROJECTED"
    assert result["occurrence_hk"] == occurrence_key(
        "SRC000107", "daily_master.idx", "b" * 64, 50, 20
    )
    assert all(item["archive_member"] == "" for item in result["rows"])
    assert all(item["source_line"] == 2 for item in result["rows"])
    assert (row, binding) == before
