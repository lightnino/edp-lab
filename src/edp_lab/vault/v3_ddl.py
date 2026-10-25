"""Exact V3-only Delta table and insert-only SQL definitions."""

from __future__ import annotations

import re

from edp_lab.vault.standing_v2 import NAMESPACE

COLUMNS = (
    ("hk", "STRING"),
    ("occurrence_hk", "STRING"),
    ("source_instance_id", "STRING"),
    ("archive_member", "STRING"),
    ("source_line", "BIGINT"),
    ("byte_offset", "BIGINT"),
    ("byte_length", "BIGINT"),
    ("raw_sha256", "STRING"),
    ("member_sha256", "STRING"),
    ("contract_version", "STRING"),
    ("payload_json", "STRING"),
    ("load_dts", "TIMESTAMP"),
)
NAMES = tuple(name for name, _ in COLUMNS)
TABLES = (
    "v3_h_13f_submission", "v3_h_concept", "v3_h_edgar_file_reference",
    "v3_h_filing", "v3_h_treasury_feed", "v3_h_treasury_observation",
    "v3_l_fsds_presentation", "v3_l_treasury_feed_observation",
    "v3_r_load_event", "v3_r_source_occurrence",
    "v3_s_13f_coverpage_assertion", "v3_s_13f_infotable_assertion",
    "v3_s_13f_othermanager2_assertion", "v3_s_13f_othermanager_assertion",
    "v3_s_13f_signature_assertion", "v3_s_13f_submission_assertion",
    "v3_s_13f_summarypage_assertion", "v3_s_edgar_index_assertion",
    "v3_s_fsds_pre_assertion", "v3_s_fsds_sub_assertion",
    "v3_s_fsds_tag_assertion", "v3_s_treasury_entry_assertion",
    "v3_vault_reject_quarantine",
)


def _table(name: str) -> str:
    if not re.fullmatch(r"v3_[a-z0-9_]+", name):
        raise ValueError("V3_TABLE_OUT_OF_SCOPE")
    return NAMESPACE + "." + name


def create_sql(name: str) -> str:
    table = _table(name)
    columns = ", ".join(f"{column} {type_name}" for column, type_name in COLUMNS)
    return (f"CREATE TABLE {table} ({columns}) USING DELTA "
            "TBLPROPERTIES ('edp.vault.stage'='V3')")


def insert_only_sql(name: str, stage_view: str) -> str:
    table = _table(name)
    if not re.fullmatch(r"v3_stage_[a-z0-9_]+", stage_view):
        raise ValueError("V3_STAGE_VIEW_OUT_OF_SCOPE")
    columns = ", ".join(NAMES)
    values = ", ".join("s." + column for column in NAMES)
    return (f"MERGE INTO {table} t USING {stage_view} s "
            "ON t.hk=s.hk AND t.occurrence_hk=s.occurrence_hk "
            f"WHEN NOT MATCHED THEN INSERT ({columns}) VALUES ({values})")


def plan(tables: list[str]) -> dict:
    if tuple(tables) != TABLES:
        raise ValueError("V3_TABLE_ALLOWLIST_CHANGED")
    return {"schema": "EDP_C2000_VAULT_V3_DDL_V1", "namespace": NAMESPACE,
            "columns": [{"name": name, "type": kind} for name, kind in COLUMNS],
            "tables": [{"name": name, "create_sql": create_sql(name),
                        "insert_only_sql": insert_only_sql(name, "v3_stage_" + name)}
                       for name in tables]}
