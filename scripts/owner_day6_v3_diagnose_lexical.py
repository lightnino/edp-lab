"""Read-only V7 diagnosis of the exact frozen SEC C300 lexical checksum.

Only SELECT queries against accepted C300 Delta VERSION AS OF 0 tables.
No Databricks Jobs, no signed receipts, no target writes or retry calls.
Print digests, keys, ordinals, counts; never print lexical field contents.
"""

from __future__ import annotations

import json
import re
from collections import Counter

from owner_day6_v3_one_shot import ROOT, require
from owner_setup_day6_vault_0a import admin_sql

from edp_lab.vault.v3_spark_runtime import (
    C300_TABLES,
    SEC_IDS,
    _digest,
    _member,
    _ordinals,
)

SELECTION = ROOT / "metadata/evaluations/day6_c2000_vault_v3_selection_v1.json"
EXPECTED_SELECTION_SHA = "5b84f0a1dc088affc51f631bc34c66f0053b871b67efff13e770021a19a33259"


def checked_sql_token(value: str) -> str:
    require(isinstance(value, str) and value
            and len(value) <= 256
            and re.fullmatch(r"[A-Za-z0-9_.:/-]+", value) is not None,
            "V3_DIAG_UNSAFE_SQL_VALUE")
    return "'" + value + "'"


def rows(sql: str) -> list[list[str | None]]:
    require(sql.lstrip().upper().startswith(("SELECT ", "WITH "))
            and " VERSION AS OF 0 " in sql.upper()
            and "workspace.edp_lab." in sql,
            "V3_DIAG_ONLY_VERSION_PINNED_C300_SELECT")
    result = admin_sql(sql)
    if result.get("result", {}).get("truncated") is True:
        raise RuntimeError("V3_DIAG_TRUNCATED_SQL_RESULT")
    data = result.get("result", {}).get("data_array")
    require(isinstance(data, list), "V3_DIAG_INLINE_DATA_UNAVAILABLE")
    return data


def bindings(selection: dict) -> dict[tuple[str, str], tuple[str, dict]]:
    expected = {
        (sid, member)
        for sid in SEC_IDS
        for member in selection["sources"][sid]["members"]
    }
    require(len(expected) == 17, "V3_DIAG_FROZEN_EXPECTED_NOT_17")
    got = {}
    ids = ",".join(checked_sql_token(sid) for sid in SEC_IDS)
    for records, table in C300_TABLES:
        sql = (
            "SELECT source_instance_id, archive_member, raw_sha256, "
            "run_id, binding_sha256 "
            f"FROM workspace.edp_lab.{table} VERSION AS OF 0 "
            f"WHERE source_instance_id IN ({ids}) AND processing_status='COMPLETE'"
        )
        for data in rows(sql):
            require(len(data) == 5, "V3_DIAG_BINDING_WIDTH_CHANGED")
            sid, physical, raw_sha, run_id, binding_sha = data
            try:
                logical = _member({
                    "source_instance_id": sid, "archive_member": physical
                })
            except ValueError:
                continue
            key = sid, logical
            if key not in expected:
                continue
            require(raw_sha == selection["sources"][sid]["raw_sha256"],
                    "V3_DIAG_FROZEN_RAW_SHA_CHANGED:" + sid)
            require(key not in got, "V3_DIAG_DUPLICATE_BINDING:" + str(key))
            require(isinstance(binding_sha, str)
                    and re.fullmatch(r"[a-fA-F0-9]{64}", binding_sha) is not None,
                    "V3_DIAG_BINDING_DIGEST_INVALID")
            got[key] = records, {
                "run_id": run_id, "binding_sha256": binding_sha,
                "physical": physical,
            }
    require(set(got) == expected, "V3_DIAG_BINDING_COVERAGE_NOT_17:"
            + repr(sorted(expected - set(got))))
    return got


def selected_rows(table: str, binding: dict, expected_ordinals: list[int]) -> list[tuple[int, list[dict], int, int]]:
    # Mirror the production ROW_NUMBER partition/rank exactly.
    run = checked_sql_token(binding["run_id"])
    digest = checked_sql_token(binding["binding_sha256"])
    ords = ",".join(str(n) for n in expected_ordinals)
    sql = (
        "WITH ranked AS ("
        "SELECT run_id, binding_sha256, byte_offset, source_line, fields, "
        "ROW_NUMBER() OVER (PARTITION BY run_id, binding_sha256 "
        "ORDER BY byte_offset, source_line) AS ordinal "
        f"FROM workspace.edp_lab.{table} VERSION AS OF 0 "
        f"WHERE record_kind='DATA' AND binding_sha256={digest} AND run_id={run}) "
        "SELECT ordinal, to_json(fields), byte_offset, source_line "
        f"FROM ranked WHERE ordinal IN ({ords}) ORDER BY ordinal"
    )
    result = []
    for ordinal, fields_json, offset, line in rows(sql):
        require(fields_json is not None, "V3_DIAG_FIELDS_JSON_ABSENT")
        fields = json.loads(fields_json)
        require(isinstance(fields, list) and all(
            isinstance(f, dict)
            and isinstance(f.get("field_ordinal"), int)
            and isinstance(f.get("original_name"), str)
            and isinstance(f.get("lexical_value"), str)
            for f in fields), "V3_DIAG_FIELDS_STRUCTURE_CHANGED")
        result.append((int(ordinal), fields, int(offset), int(line)))
    return result


def diagnose() -> None:
    import hashlib

    require(hashlib.sha256(SELECTION.read_bytes()).hexdigest() ==
            EXPECTED_SELECTION_SHA, "V3_DIAG_SELECTION_PIN_CHANGED")
    selection = json.loads(SELECTION.read_bytes())
    found = bindings(selection)
    print("=== FROZEN C300 LEXICAL CHECK, DELTA VERSION 0 (READ ONLY) ===")
    print("EXPECTED_BINDINGS=17 OBSERVED_BINDINGS=17")
    all_good = True
    first_issue = None
    for sid, member in sorted(found):
        table, binding = found[sid, member]
        spec = selection["sources"][sid]["members"][member]
        wanted = _ordinals(spec)
        selected = selected_rows(table, binding, wanted)
        actual_ord = [ordinal for ordinal, _, _, _ in selected]
        if actual_ord != wanted:
            print(f"{sid}/{member}: ORDINAL_MISMATCH "
                  f"expected={len(wanted)} actual={len(selected)}")
            all_good = False
            first_issue = first_issue or (sid, member, "ORDINAL")
            continue
        widths = Counter()
        lexical = []
        for ordinal, fields, _, _ in selected:
            widths[len(fields)] += 1
            require([f["field_ordinal"] for f in fields] ==
                    list(range(1, len(fields) + 1)),
                    "V3_DIAG_FIELD_ORDER_INVALID:" + member)
            values = [f["lexical_value"] for f in fields]
            lexical.append([ordinal, "|".join(values) if member == "daily_master.idx"
                            else values])
        digest = _digest(lexical)
        header = _digest([f["original_name"] for f in selected[0][1]])
        expected = spec["selected_lexical_sha256"]
        good = digest == expected
        all_good &= good
        if not good and first_issue is None:
            first_issue = sid, member, "LEXICAL"
        if header != spec.get("header_sha256"):
            all_good = False
            first_issue = first_issue or (sid, member, "HEADER")
        # For possible tie diagnosis; do not print source line/byte offset.
        positions = [(offset, line) for _, _, offset, line in selected]
        ties = len(positions) - len(set(positions))
        print(
            f"{sid}/{member}: {'MATCH' if good else 'LEXICAL_MISMATCH'} "
            f"rows={len(selected)} field_widths={dict(sorted(widths.items()))} "
            f"header_match={header == spec.get('header_sha256')} "
            f"rank_ties={ties} expected={expected} actual={digest}"
        )
    print("=== RESULT ===")
    print("ALL_17_MATCH" if all_good else "CHECKSUM_MISMATCH_DETECTED")
    if first_issue:
        print("FIRST_ISSUE=" + "/".join(first_issue))
    print("NO_TARGET_WRITE_NO_CANARY_RETRY")


if __name__ == "__main__":
    diagnose()
