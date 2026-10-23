"""Render bounded, source-preserving Vault Delta MERGEs from pinned projections.

Rendering has no external side effects. The protected executor must verify the
whole rendered plan against an owner-signed policy before any statement runs.
"""
from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from collections.abc import Iterable

NAMESPACE = "workspace.edp_lab_day6_vault_proto"
TABLES = (
    "h_filing", "h_concept", "l_fact_slot", "r_source_occurrence",
    "s_fact_assertion", "s_num_m2_value", "r_load_event",
    "vault_reject_quarantine",
)


def _hex(value: str | None) -> str:
    if value is None:
        return "NULL"
    if not isinstance(value, str):
        raise TypeError("TEXT_REQUIRED")
    return "'" + value.encode("utf-8").hex() + "'"


def _decode(name: str) -> str:
    return f"decode(unhex(v.{name}), 'UTF-8')"


def _merge(table: str, key: tuple[str, ...], columns: tuple[str, ...],
           records: Iterable[tuple[str | None, ...]], *, decimal: str | None = None,
           stamp: str = "first_load_dts") -> tuple[str, str]:
    """An immutable-component check and insert-only Delta merge."""
    if table not in TABLES or any(not name.isidentifier() for name in (*key, *columns)):
        raise ValueError("INVALID_TABLE_SPEC")
    rows = list(records)
    if not rows or any(len(row) != len(columns) for row in rows):
        raise ValueError("INVALID_MERGE_ROWS")
    raw_cols = ", ".join(f"c{i}" for i in range(len(columns)))
    values = ",\n    ".join("(" + ", ".join(_hex(value) for value in row) + ")" for row in rows)
    projections = []
    for i, name in enumerate(columns):
        expression = _decode(f"c{i}")
        if name in {"byte_offset", "byte_length", "source_line", "field_ordinal"}:
            expression = f"CAST({expression} AS BIGINT)"
        elif name == "synthetic_negative_control":
            expression = f"CAST({expression} AS BOOLEAN)"
        elif name == decimal:
            expression = f"CAST({expression} AS DECIMAL(38,4))"
        projections.append(f"{expression} AS {name}")
    projections.append(f"current_timestamp() AS {stamp}")
    all_cols = (*columns, stamp)
    predicate = " AND ".join(f"t.{name}=s.{name}" for name in key)
    source = (f"SELECT {', '.join(projections)} FROM VALUES\n    {values}\n"
              f"AS v({raw_cols})")
    mismatch = " OR ".join(f"NOT (t.{name} <=> s.{name})" for name in columns)
    check = (f"SELECT COUNT(*) AS mismatches FROM {NAMESPACE}.{table} AS t\n"
             f"JOIN ({source}) AS s ON {predicate}\nWHERE {mismatch}")
    merge = (f"MERGE INTO {NAMESPACE}.{table} AS t\n"
             f"USING ({source}) AS s\nON {predicate}\n"
             f"WHEN NOT MATCHED THEN INSERT ({', '.join(all_cols)})\n"
             f"VALUES ({', '.join('s.' + name for name in all_cols)})")
    return check, merge


def _unique(rows: list[dict], key: str, names: tuple[str, ...]) -> list[tuple[str | None, ...]]:
    values: OrderedDict[str, tuple[str | None, ...]] = OrderedDict()
    for row in rows:
        signature = tuple(row[name] for name in names)
        old = values.setdefault(row[key], signature)
        if old != signature:
            raise ValueError("KEY_COMPONENT_DRIFT")
    return list(values.values())


def render(rows: list[dict]) -> dict:
    """Prepare all business-table DML for the previously pinned 127-row sample."""
    if len(rows) != 127 or len({r["occurrence_hk"] for r in rows}) != 127:
        raise ValueError("PINNED_SAMPLE_SIZE_OR_OCCURRENCE_CHANGED")
    stages = []

    def add(name: str, key: tuple[str, ...], columns: tuple[str, ...], data,
            *, decimal=None, stamp="first_load_dts", stage_id=None):
        check, statement = _merge(name, key, columns, data, decimal=decimal, stamp=stamp)
        stages.append({"id": stage_id or f"load-{name}", "table": f"{NAMESPACE}.{name}",
                       "kind": "MERGE_INSERT_ONLY", "statement": statement,
                       "statement_sha256": hashlib.sha256(statement.encode()).hexdigest(),
                       "precheck": check,
                       "precheck_sha256": hashlib.sha256(check.encode()).hexdigest()})

    add("h_filing", ("filing_hk",), ("filing_hk", "source_namespace", "adsh"),
        _unique([{**r, "source_namespace": "SEC_FSDS"} for r in rows],
                "filing_hk", ("filing_hk", "source_namespace", "adsh")))
    add("h_concept", ("concept_hk",),
        ("concept_hk", "source_namespace", "tag", "version"),
        _unique([{**r, "source_namespace": "SEC_FSDS"} for r in rows],
                "concept_hk", ("concept_hk", "source_namespace", "tag", "version")))
    add("l_fact_slot", ("fact_slot_hk",),
        ("fact_slot_hk", "filing_hk", "concept_hk", "context_json"),
        _unique(rows, "fact_slot_hk", ("fact_slot_hk", "filing_hk", "concept_hk", "context_json")))
    add("r_source_occurrence", ("occurrence_hk",),
        ("occurrence_hk", "source_instance_id", "archive_member", "member_sha256",
         "byte_offset", "byte_length", "source_line", "raw_path", "raw_sha256",
         "binding_sha256", "m1_run_id", "record_kind", "fields_json"),
        ((r["occurrence_hk"], r["source_instance_id"], r["archive_member"],
          r["member_sha256"], str(r["byte_offset"]), str(r["byte_length"]),
          str(r["source_line"]), r["raw_path"], r["raw_sha256"],
          r["binding_sha256"], r["run_id"], "DATA", r["fields_json"]) for r in rows))
    add("s_fact_assertion", ("assertion_hk",),
        ("assertion_hk", "fact_slot_hk", "occurrence_hk", "parser_contract_version",
         "parser_profile_id", "m1_model_version", "m1_rule_version", "payload_hashdiff",
         "value_lexical", "footnote_lexical"),
        (tuple(r[name] for name in (
            "assertion_hk", "fact_slot_hk", "occurrence_hk", "parser_contract_version",
            "parser_profile_id", "m1_model_version", "m1_rule_version", "payload_hashdiff",
            "value_lexical", "footnote_lexical")) for r in rows))
    add("s_num_m2_value", ("occurrence_hk", "field_ordinal", "conversion_rule_version"),
        ("occurrence_hk", "field_ordinal", "source_rule_version", "model_version",
         "conversion_rule_version", "lexical_value", "value_decimal", "conversion_outcome",
         "conversion_reason"),
        ((r["occurrence_hk"], "9", r["m2_source_rule_version"], r["m2_model_version"],
          r["m2_rule_version"], r["value_lexical"], r["m2_decimal"],
          r["m2_outcome"], r["m2_reason"]) for r in rows), decimal="value_decimal")
    for event_kind, execution_id in (("ADMITTED", "day6-vault-proto-c1500-first-v1"),
                                      ("REPLAY", "day6-vault-proto-c1500-replay-v1")):
        add("r_load_event", ("occurrence_hk", "execution_id"),
            ("occurrence_hk", "execution_id", "event_kind", "statement_id",
             "input_manifest_sha256"),
            ((r["occurrence_hk"], execution_id, event_kind, None,
              "366ca59ac251fa54d0a2c97ebdd8f9cacbcf773231c61aa20a504196a3cf31dc")
             for r in rows), stamp="load_dts", stage_id=f"event-{event_kind.lower()}")
    negative = []
    first = rows[0]
    for reason, mutation in (
        ("REPLAY_DRIFT", {"value_lexical": "SYNTHETIC_CHANGED_VALUE"}),
        ("FIELD_ORDER_MISMATCH", {"field_order": "REVERSED"}),
        ("MEMBER_SHA_MISMATCH", {"member_sha256": "0" * 64}),
        ("BAD_BYTE_LOCATOR", {"byte_offset": first["byte_offset"] + 1}),
        ("MISSING_BUSINESS_KEY_COMPONENT", {"adsh": ""}),
        ("M2_INELIGIBLE", {"field_ordinal": 8}),
    ):
        identity = "SYNTHETIC_NEGATIVE_" + reason
        payload = json.dumps({"original_occurrence_hk": first["occurrence_hk"],
                              "mutation": mutation, "original_fields_json": first["fields_json"]},
                             sort_keys=True, separators=(",", ":"))
        negative.append((identity, "day6-vault-proto-c1500-negative-v1", reason,
                         "Controlled synthetic mutation; reject promotion", first["source_instance_id"],
                         first["archive_member"], first["member_sha256"],
                         str(first["byte_offset"]), str(first["byte_length"]),
                         str(first["source_line"]), first["raw_sha256"],
                         first["binding_sha256"], payload, "true"))
    add("vault_reject_quarantine", ("input_identity", "execution_id"),
        ("input_identity", "execution_id", "reason_code", "reason_detail",
         "source_instance_id", "archive_member", "member_sha256", "byte_offset",
         "byte_length", "source_line", "raw_sha256", "binding_sha256", "input_json",
         "synthetic_negative_control"), negative,
        stamp="rejected_dts", stage_id="synthetic-negative-quarantine")
    payload = json.dumps(stages, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return {"schema": "DAY6_VAULT_BOUNDED_LOAD_PLAN_V1", "namespace": NAMESPACE,
            "data_occurrences": len(rows), "stages_sha256": hashlib.sha256(payload).hexdigest(),
            "stages": stages}
