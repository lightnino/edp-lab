"""Bounded approved V3 semantic grains on source-preserving lexical rows."""

import copy

from edp_lab.vault.v3_mapping import EDGAR_HEADER, FSDS_HEADERS, project


def source(member, names, *, sid="SRC000005", values=None, offset=1):
    values = values or {}
    return {"source_instance_id": sid, "archive_member": member,
            "raw_sha256": "a" * 64, "member_sha256": "b" * 64,
            "byte_offset": offset, "byte_length": 20, "source_line": 2,
            "fields": [{"name": name, "state": "PRESENT",
                        "text": values.get(name, "")}
                       for name in names]}


def table_rows(value, name):
    return [row for row in value["rows"] if row["table"] == name]


def test_fsds_presentation_context_and_duplicate_occurrences():
    fields = {"adsh": "0001", "tag": "Assets", "version": "us-gaap/2025",
              "report": "1", "line": "20", "stmt": "BS", "inpth": "0", "rfile": "H"}
    first = source("pre.txt", FSDS_HEADERS["pre.txt"], values=fields)
    second = copy.deepcopy(first)
    second["byte_offset"] = 21
    a, b = project(first), project(second)
    assert a["business_status"] == b["business_status"] == "PROJECTED"
    assert table_rows(a, "v3_l_fsds_presentation")[0]["hk"] == (
        table_rows(b, "v3_l_fsds_presentation")[0]["hk"])
    assert table_rows(a, "v3_s_fsds_pre_assertion")[0]["occurrence_hk"] != (
        table_rows(b, "v3_s_fsds_pre_assertion")[0]["occurrence_hk"])
    changed = copy.deepcopy(first)
    next(f for f in changed["fields"] if f["name"] == "line")["text"] = "21"
    assert table_rows(project(changed), "v3_l_fsds_presentation")[0]["hk"] != (
        table_rows(a, "v3_l_fsds_presentation")[0]["hk"])


def test_edgar_missing_path_retains_technical_occurrence():
    row = source("daily_master.idx", EDGAR_HEADER, sid="SRC000107",
                 values={"File Name": "edgar/data/0001/a.txt"})
    assert table_rows(project(row), "v3_h_edgar_file_reference")
    next(f for f in row["fields"] if f["name"] == "File Name")["text"] = ""
    result = project(row)
    assert result["business_status"] == "MISSING_FILE_REFERENCE"
    assert table_rows(result, "v3_r_source_occurrence")
    assert table_rows(result, "v3_vault_reject_quarantine")
    assert not table_rows(result, "v3_h_edgar_file_reference")


def test_13f_member_is_satellite_without_business_link():
    row = source("INFOTABLE.tsv", ("ACCESSION_NUMBER", "CUSIP", "FIGI"),
                 sid="SRC000065", values={"ACCESSION_NUMBER": "0001", "CUSIP": "001234500"})
    result = project(row)
    assert table_rows(result, "v3_s_13f_infotable_assertion")
    assert not any(item["table"].startswith("v3_l_13f") for item in result["rows"])
    assert "001234500" in table_rows(result, "v3_s_13f_infotable_assertion")[0]["payload_json"]


def test_treasury_date_type_grain_and_missing_type():
    row = source("atom.entry", ("QUOTE_DATE", "RATE_TYPE", "RATE"),
                 sid="SRC010453", values={"QUOTE_DATE": "2025-01-02",
                                                 "RATE_TYPE": "Real_Rate", "RATE": "4.86"})
    row["entry_ordinal"] = 1
    feed_id = "https://home.treasury.gov/example"
    real = project(row, feed_id=feed_id)
    changed = copy.deepcopy(row)
    next(f for f in changed["fields"] if f["name"] == "RATE_TYPE")["text"] = "BC_20year"
    other = project(changed, feed_id=feed_id)
    assert table_rows(real, "v3_h_treasury_observation")[0]["hk"] != (
        table_rows(other, "v3_h_treasury_observation")[0]["hk"])
    missing = copy.deepcopy(row)
    next(f for f in missing["fields"] if f["name"] == "RATE_TYPE")["text"] = ""
    assert project(missing, feed_id=feed_id)["business_status"] == (
        "MISSING_TREASURY_BUSINESS_IDENTITY")
