"""Pure C1500 NUM-to-Vault projection; no warehouse side effects."""
from __future__ import annotations

import json
from collections.abc import Mapping

from edp_lab.materialization.typed_numeric_v1 import convert
from scripts.day6_vault_contract_v1 import (
    assertion_key,
    concept_key,
    fact_slot_key,
    filing_key,
    lexical_hashdiff,
    occurrence_key,
)

HEADER = ("adsh", "tag", "version", "ddate", "qtrs", "uom", "segments",
          "coreg", "value", "footnote")
MODEL = "M2_ADDITIVE_TYPED_NUMERIC_V1"
RULE = "EXACT_DECIMAL_38_4_V1"
SOURCE_RULE = "FSDS_NUM_VALUE_SCOPE_V1"


def project(row: Mapping, approved: Mapping[str, Mapping]) -> dict:
    """Fail closed on pinned identity, field order, context and M2 applicability."""
    sid = row["source_instance_id"]
    expected = approved.get(sid)
    if expected is None or any(row.get(name) != expected.get(name) for name in
                               ("raw_sha256", "member_sha256", "binding_sha256", "run_id")):
        raise ValueError("UNAPPROVED_SOURCE_OR_BINDING")
    if row.get("archive_member") != "num.txt" or not row.get("raw_path"):
        raise ValueError("UNAPPROVED_MEMBER_OR_MISSING_PATH")
    parser = expected.get("parser_version")
    if parser not in {"C300_PARSER_V1", "C300_FSDS_NUM_QUOTE_BOUNDARY_V1"}:
        raise ValueError("UNAPPROVED_PARSER_VERSION")
    fields = row["m1_fields"]
    if len(fields) != 10 or [f.get("field_ordinal") for f in fields] != list(range(1, 11)):
        raise ValueError("FIELD_ORDER_OR_WIDTH")
    if [f.get("original_name") for f in fields] != list(HEADER):
        raise ValueError("FIELD_NAME_OR_ORDER")
    if any(f.get("disposition") != "DIRECT_MAP" or f.get("lexical_value") is None
           for f in fields):
        raise ValueError("UNSUPPORTED_FIELD_DISPOSITION")
    values = {name: field["lexical_value"] for name, field in zip(HEADER, fields, strict=True)}
    if not values["adsh"] or not values["tag"] or not values["version"]:
        raise ValueError("MISSING_BUSINESS_KEY_COMPONENT")
    offset, length, line = (row[name] for name in ("byte_offset", "byte_length", "source_line"))
    if not isinstance(line, int) or line < 2:
        raise ValueError("INVALID_SOURCE_LINE")
    if not isinstance(offset, int) or not isinstance(length, int):
        raise TypeError("INVALID_BYTE_LOCATOR")
    filing = filing_key(values["adsh"])
    concept = concept_key(values["tag"], values["version"])
    slot = fact_slot_key(values, HEADER)
    occurrence = occurrence_key(sid, "num.txt", row["member_sha256"], offset, length)
    fields_exact = tuple((i, name, "PRESENT", values[name]) for i, name in enumerate(HEADER, 1))
    payload = lexical_hashdiff(fields_exact)
    assertion = assertion_key(slot, occurrence, parser)
    numeric = convert(values["value"])
    return {
        "filing_hk": filing, "concept_hk": concept, "fact_slot_hk": slot,
        "occurrence_hk": occurrence, "assertion_hk": assertion,
        "payload_hashdiff": payload, "parser_contract_version": parser,
        "parser_profile_id": expected["parser_profile_id"],
        "m1_model_version": expected["model_version"],
        "m1_rule_version": expected["rule_version"],
        "source_instance_id": sid, "run_id": row["run_id"],
        "raw_path": row["raw_path"], "raw_sha256": row["raw_sha256"],
        "archive_member": "num.txt", "member_sha256": row["member_sha256"],
        "binding_sha256": row["binding_sha256"], "source_line": line,
        "byte_offset": offset, "byte_length": length,
        "adsh": values["adsh"], "tag": values["tag"], "version": values["version"],
        "context_json": json.dumps({name: {"state": "PRESENT", "text": values[name]}
                                    for name in ("ddate", "qtrs", "uom", "coreg", "segments")},
                                   ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        "fields_json": json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        "value_lexical": values["value"], "footnote_lexical": values["footnote"],
        "m2_outcome": numeric.conversion_outcome,
        "m2_reason": numeric.conversion_reason,
        "m2_decimal": str(numeric.value_decimal) if numeric.value_decimal is not None else None,
        "m2_model_version": MODEL, "m2_rule_version": RULE,
        "m2_source_rule_version": SOURCE_RULE,
    }


def validate_batch(rows: list[dict]) -> None:
    """Detect occurrence drift and unexplained hash collisions before writes."""
    by_occurrence: dict[str, dict] = {}
    by_key: dict[str, tuple] = {}
    for row in rows:
        old = by_occurrence.setdefault(row["occurrence_hk"], row)
        if old is not row:
            raise ValueError("DUPLICATE_OR_DRIFTED_OCCURRENCE_IN_BATCH")
        for key, signature in (
            (row["filing_hk"], (row["adsh"],)),
            (row["concept_hk"], (row["tag"], row["version"])),
            (row["fact_slot_hk"], (row["filing_hk"], row["concept_hk"], row["context_json"])),
        ):
            prior = by_key.setdefault(key, signature)
            if prior != signature:
                raise ValueError("HASH_COMPONENT_COLLISION")
