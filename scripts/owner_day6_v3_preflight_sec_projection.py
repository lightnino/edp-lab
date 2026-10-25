"""Read-only real M1 -> V3 projection for all 304 frozen SEC sample rows.

This has NO job submission, target reads/writes, root signing or durable ledgers.
Only SELECT from accepted C300 Delta VERSION AS OF 0 with owner service auth.
Does not print data/identifiers sourced from lexical field values.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter

from owner_day6_v3_diagnose_lexical import (
    EXPECTED_SELECTION_SHA,
    SELECTION,
    bindings,
    checked_sql_token,
    rows,
)
from owner_day6_v3_one_shot import ROOT, require

from edp_lab.vault.v3_input import c300_occurrence
from edp_lab.vault.v3_mapping import project
from edp_lab.vault.v3_spark_runtime import (
    C300_TABLES,
    SEC_IDS,
    _coverpage_quote_exception,
    _digest,
    _ordinals,
)

EXPECTED_SEC_ROWS = 304


def _physical_literal(value: str) -> str:
    return "''" if value == "" else checked_sql_token(value)


def _full_bindings(found: dict) -> dict:
    """Match an exact frozen selection binding to its accepted member SHA."""
    approved = {}
    ids = ",".join(checked_sql_token(sid) for sid in SEC_IDS)
    for _, binding_table in C300_TABLES:
        query = (
            "SELECT source_instance_id, archive_member, run_id, binding_sha256, "
            "member_sha256 "
            f"FROM workspace.edp_lab.{binding_table} VERSION AS OF 0 "
            f"WHERE source_instance_id IN ({ids}) AND processing_status='COMPLETE'"
        )
        for cells in rows(query):
            require(len(cells) == 5, "V3_SEC_PREFLIGHT_BINDING_WIDTH")
            sid, physical, run_id, sha, member_sha = cells
            if not (isinstance(member_sha, str)
                    and len(member_sha) == 64):
                continue
            key = (sid, run_id, sha, physical)
            require(key not in approved, "V3_SEC_PREFLIGHT_DUPLICATE_BINDING")
            approved[key] = member_sha
    output = {}
    for (sid, member), (record_table, locator) in found.items():
        key = (sid, locator["run_id"],
               locator["binding_sha256"], locator["physical"])
        require(key in approved, "V3_SEC_PREFLIGHT_MEMBER_SHA_UNVERIFIED")
        output[sid, member] = {
            **locator,
            "source_instance_id": sid,
            "member_sha256": approved[key],
            "archive_member": locator["physical"],
            "processing_status": "COMPLETE",
            "records_table": record_table,
        }
    return output


def _data_rows(binding: dict, ordinals: list[int]) -> list[tuple[int, dict]]:
    run_id = checked_sql_token(binding["run_id"])
    digest = checked_sql_token(binding["binding_sha256"])
    wanted = ",".join(str(value) for value in ordinals)
    table = binding["records_table"]
    query = (
        "WITH ranked AS (SELECT source_instance_id, run_id, binding_sha256, "
        "source_line, byte_offset, byte_length, fields, record_kind, "
        "ROW_NUMBER() OVER (PARTITION BY run_id, binding_sha256 "
        "ORDER BY byte_offset, source_line) AS ordinal "
        f"FROM workspace.edp_lab.{table} VERSION AS OF 0 "
        f"WHERE record_kind='DATA' AND binding_sha256={digest} AND run_id={run_id}) "
        "SELECT ordinal, source_instance_id, run_id, binding_sha256, "
        "source_line, byte_offset, byte_length, to_json(fields) "
        f"FROM ranked WHERE ordinal IN ({wanted}) ORDER BY ordinal"
    )
    found = []
    for cells in rows(query):
        require(len(cells) == 8, "V3_SEC_PREFLIGHT_RECORD_WIDTH")
        ordinal, sid, returned_run, returned_binding, line, offset, length, field_json = cells
        require(sid == binding["source_instance_id"]
                and returned_run == binding["run_id"]
                and returned_binding == binding["binding_sha256"],
                "V3_SEC_PREFLIGHT_RECORD_BINDING_CHANGED")
        parsed_fields = json.loads(field_json)
        require(isinstance(parsed_fields, list), "V3_SEC_PREFLIGHT_FIELD_STRUCTURE")
        m1 = {
            "record_kind": "DATA", "source_instance_id": sid,
            "run_id": returned_run, "binding_sha256": returned_binding,
            "source_line": int(line), "byte_offset": int(offset),
            "byte_length": int(length), "fields": parsed_fields,
        }
        found.append((int(ordinal), m1))
    require([o for o, _ in found] == ordinals,
            "V3_SEC_PREFLIGHT_SELECTED_ORDINALS_CHANGED")
    return found


def verify() -> dict:
    require(hashlib.sha256(SELECTION.read_bytes()).hexdigest() ==
            EXPECTED_SELECTION_SHA, "V3_SEC_PREFLIGHT_FROZEN_SELECTION_CHANGED")
    selection = json.loads(SELECTION.read_bytes())
    found = bindings(selection)
    exact = _full_bindings(found)
    require(len(exact) == 17, "V3_SEC_PREFLIGHT_NOT_17_MEMBERS")
    counts = Counter()
    blocked = Counter()
    occurrence_ids = set()
    selected_parents = Counter()
    children = set()
    for sid, member in sorted(exact):
        frozen = selection["sources"][sid]
        spec = frozen["members"][member]
        selected = _data_rows(exact[sid, member], _ordinals(spec))
        for ordinal, m1 in selected:
            names = tuple(x["original_name"] for x in m1["fields"])
            instance = c300_occurrence(m1, exact[sid, member],
                                       frozen["raw_sha256"], names)
            instance = _coverpage_quote_exception(instance, sid, member, ordinal)
            projection = project(instance)
            if projection["business_status"] != "PROJECTED":
                blocked[(sid, member, projection["business_status"])] += 1
            occurrence = projection["occurrence_hk"]
            require(occurrence not in occurrence_ids,
                    "V3_SEC_PREFLIGHT_DUPLICATE_OCCURRENCE")
            occurrence_ids.add(occurrence)
            counts[sid, member] += 1
            if sid == "SRC000065":
                accession = next(field["text"] for field in instance["fields"]
                                 if field["name"] == "ACCESSION_NUMBER")
                if member == "SUBMISSION.tsv":
                    selected_parents[accession] += 1
                else:
                    children.add(accession)
        print(f"{sid}/{member}: PROJECTION_DONE selected={counts[sid, member]} "
              f"blocked={sum(n for (s, m, _), n in blocked.items() if (s, m) == (sid, member))}")
    expected = {(sid, member): spec["selected_data_rows"]
                for sid in SEC_IDS
                for member, spec in selection["sources"][sid]["members"].items()}
    require(dict(counts) == expected
            and sum(counts.values()) == EXPECTED_SEC_ROWS,
            "V3_SEC_PREFLIGHT_SCOPE_COUNT_CHANGED")
    parent_issues = sum(selected_parents[key] != 1 for key in children)
    result = {
        "status": "PASS" if not blocked and not parent_issues else "BLOCKED",
        "selected_source_count": len(SEC_IDS),
        "member_count": len(exact),
        "projected_occurrence_count": len(occurrence_ids),
        "blocked_by_member_and_reason": [
            {"source_instance_id": sid, "member": member, "reason": why, "count": count}
            for (sid, member, why), count in sorted(blocked.items())
        ],
        "13f_parent_reference_problem_count": parent_issues,
        "accepted_c300_delta_version": 0,
        "remote_operations": "SELECT_ONLY",
    }
    return result


def main() -> None:
    result = verify()
    print("V3_SEC_PROJECTION_PREFLIGHT=" + json.dumps(result, sort_keys=True))
    require(result["status"] == "PASS", "V3_SEC_PROJECTION_PREFLIGHT_NOT_READY")


if __name__ == "__main__":
    main()
