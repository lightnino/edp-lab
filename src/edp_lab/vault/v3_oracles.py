"""Twenty-four isolated, in-memory V3 semantic regression oracles.

These fixtures never enter Delta or the frozen source population. A result is
accepted only when each rule has a direct observable projection assertion.
"""

from __future__ import annotations

from copy import deepcopy

from edp_lab.vault.v3_mapping import EDGAR_HEADER, FSDS_HEADERS, project


def _source(sid: str, member: str, names: tuple[str, ...], values: dict,
            *, ordinal: int = 1) -> dict:
    result = {"source_instance_id": sid, "archive_member": member,
              "raw_sha256": "a" * 64, "member_sha256": "b" * 64,
              "source_line": ordinal + 1, "byte_offset": ordinal * 40,
              "byte_length": 39,
              "fields": [{"name": name, "state": "PRESENT", "text": values.get(name, "")}
                         for name in names]}
    if sid.startswith("SRC010"):
        result["entry_ordinal"] = ordinal
    return result


def _set(row: dict, name: str, text: str, state: str = "PRESENT") -> dict:
    changed = deepcopy(row)
    field = next(item for item in changed["fields"] if item["name"] == name)
    field["text"], field["state"] = text, state
    return changed


def _rows(result: dict, table: str) -> list[dict]:
    return [item for item in result["rows"] if item["table"] == table]


def evaluate() -> dict[str, bool]:
    pre = _source("SRC000005", "pre.txt", FSDS_HEADERS["pre.txt"],
                  {"adsh": "0001", "tag": "Assets", "version": "v1", "report": "1",
                   "line": "20", "stmt": "BS", "inpth": "0", "rfile": "H",
                   "plabel": "Assets"})
    pre2 = deepcopy(pre)
    pre2["byte_offset"] += 40
    edgar = _source("SRC000107", "daily_master.idx", EDGAR_HEADER,
                    {"CIK": "000123", "Company Name": "A", "File Name": "edgar/a.txt"})
    edgar2 = deepcopy(edgar)
    edgar2["byte_offset"] += 40
    f13 = _source("SRC000065", "INFOTABLE.tsv",
                  ("ACCESSION_NUMBER", "INFOTABLE_SK", "FIGI", "CUSIP", "CIK"),
                  {"ACCESSION_NUMBER": "0001", "INFOTABLE_SK": "7",
                   "CUSIP": " 00123 ", "CIK": "000123"})
    f13b = deepcopy(f13)
    f13b["byte_offset"] += 40
    treasury = _source("SRC010453", "atom.entry",
                       ("QUOTE_DATE", "RATE_TYPE", "RATE"),
                       {"QUOTE_DATE": "2025-01-02", "RATE_TYPE": "Real_Rate",
                        "RATE": "4.86"})
    feed = "https://home.treasury.gov/frozen-feed"
    a, b = project(pre), project(pre2)
    e1, e2 = project(edgar), project(edgar2)
    f1, f2 = project(f13), project(f13b)
    t1 = project(treasury, feed_id=feed)
    changed_label = project(_set(pre2, "plabel", "Total assets"))
    changed_company = project(_set(edgar2, "Company Name", "B"))
    changed_rate = project(_set(treasury, "RATE_TYPE", "BC_20year"), feed_id=feed)
    optional = deepcopy(treasury)
    optional["fields"].append({"name": "BC_1MONTH", "state": "ABSENT", "text": ""})
    empty = deepcopy(optional)
    empty["fields"][-1]["state"] = "PRESENT"
    cross_feed = project(treasury, feed_id=feed + "-other")
    no_parent_pre = project(pre, parent_valid=False)
    no_parent_13f = project(f13, parent_valid=False)
    blank_filing = project(_set(pre, "adsh", ""))
    blank_path = project(_set(edgar, "File Name", ""))
    no_date = project(_set(treasury, "QUOTE_DATE", ""), feed_id=feed)
    no_type = project(_set(treasury, "RATE_TYPE", ""), feed_id=feed)
    tests = {
        "FSDS_01": _rows(a, "v3_l_fsds_presentation")[0]["hk"] ==
                   _rows(changed_label, "v3_l_fsds_presentation")[0]["hk"] and
                   _rows(a, "v3_s_fsds_pre_assertion")[0]["payload_json"] !=
                   _rows(changed_label, "v3_s_fsds_pre_assertion")[0]["payload_json"],
        "FSDS_02": no_parent_pre["business_status"] == "UNRESOLVED_PRESENTATION_PARENT"
                   and bool(_rows(no_parent_pre, "v3_r_source_occurrence"))
                   and not _rows(no_parent_pre, "v3_l_fsds_presentation"),
        "FSDS_03": no_parent_pre["business_status"] == "UNRESOLVED_PRESENTATION_PARENT"
                   and bool(_rows(no_parent_pre, "v3_vault_reject_quarantine")),
        "FSDS_04": blank_filing["business_status"] == "MISSING_PRESENTATION_IDENTITY"
                   and not _rows(blank_filing, "v3_h_filing"),
        "FSDS_05": _rows(a, "v3_s_fsds_pre_assertion")[0]["occurrence_hk"] !=
                   _rows(b, "v3_s_fsds_pre_assertion")[0]["occurrence_hk"],
        "FSDS_06": "\\t" in _rows(project(_set(pre, "plabel", "A\tB")),
                                   "v3_s_fsds_pre_assertion")[0]["payload_json"],
        "EDGAR_01": _rows(e1, "v3_s_edgar_index_assertion")[0]["occurrence_hk"] !=
                    _rows(e2, "v3_s_edgar_index_assertion")[0]["occurrence_hk"],
        "EDGAR_02": _rows(e1, "v3_h_edgar_file_reference")[0]["hk"] ==
                    _rows(e2, "v3_h_edgar_file_reference")[0]["hk"],
        "EDGAR_03": blank_path["business_status"] == "MISSING_FILE_REFERENCE"
                    and bool(_rows(blank_path, "v3_r_source_occurrence")),
        "EDGAR_04": "000123" in _rows(e1, "v3_s_edgar_index_assertion")[0]["payload_json"]
                    and not any("issuer" in row["table"] for row in e1["rows"]),
        "EDGAR_05": _rows(e1, "v3_h_edgar_file_reference")[0]["hk"] ==
                    _rows(changed_company, "v3_h_edgar_file_reference")[0]["hk"]
                    and _rows(e1, "v3_s_edgar_index_assertion")[0]["payload_json"] !=
                    _rows(changed_company, "v3_s_edgar_index_assertion")[0]["payload_json"],
        "EDGAR_06": not any("13f" in row["table"] for row in e1["rows"]),
        "13F_01": no_parent_13f["business_status"] == "UNRESOLVED_SUBMISSION_PARENT"
                   and bool(_rows(no_parent_13f, "v3_r_source_occurrence"))
                   and not _rows(no_parent_13f, "v3_s_13f_infotable_assertion"),
        "13F_02": _rows(f1, "v3_s_13f_infotable_assertion")[0]["occurrence_hk"] !=
                   _rows(f2, "v3_s_13f_infotable_assertion")[0]["occurrence_hk"],
        "13F_03": '"text":""' in _rows(f1, "v3_s_13f_infotable_assertion")[0]["payload_json"]
                   and not any("security" in row["table"] for row in f1["rows"]),
        "13F_04": " 00123 " in _rows(f1, "v3_s_13f_infotable_assertion")[0]["payload_json"]
                   and "000123" in _rows(f1, "v3_s_13f_infotable_assertion")[0]["payload_json"],
        "13F_05": _rows(f1, "v3_s_13f_infotable_assertion")[0]["hk"] ==
                   _rows(f2, "v3_s_13f_infotable_assertion")[0]["hk"]
                   and _rows(f1, "v3_s_13f_infotable_assertion")[0]["occurrence_hk"] !=
                   _rows(f2, "v3_s_13f_infotable_assertion")[0]["occurrence_hk"],
        "13F_06": len({_rows(result, "v3_s_13f_infotable_assertion")[0]["occurrence_hk"]
                       for result in (f1, f2)}) == 2,
        "TREASURY_01": no_date["business_status"] == "MISSING_TREASURY_BUSINESS_IDENTITY"
                       and bool(_rows(no_date, "v3_r_source_occurrence")),
        "TREASURY_02": no_type["business_status"] == "MISSING_TREASURY_BUSINESS_IDENTITY"
                       and not _rows(no_type, "v3_h_treasury_observation"),
        "TREASURY_03": _rows(t1, "v3_h_treasury_observation")[0]["hk"] !=
                       _rows(changed_rate, "v3_h_treasury_observation")[0]["hk"],
        "TREASURY_04": '"state":"ABSENT"' in _rows(project(optional, feed_id=feed),
                                "v3_s_treasury_entry_assertion")[0]["payload_json"],
        "TREASURY_05": _rows(project(optional, feed_id=feed),
                             "v3_s_treasury_entry_assertion")[0]["payload_json"] !=
                       _rows(project(empty, feed_id=feed),
                             "v3_s_treasury_entry_assertion")[0]["payload_json"],
        "TREASURY_06": _rows(t1, "v3_h_treasury_observation")[0]["hk"] !=
                       _rows(cross_feed, "v3_h_treasury_observation")[0]["hk"],
    }
    if len(tests) != 24 or not all(tests.values()):
        raise ValueError("V3_NEGATIVE_ORACLE_FAILED:" +
                         ",".join(name for name, passed in tests.items() if not passed))
    return tests
