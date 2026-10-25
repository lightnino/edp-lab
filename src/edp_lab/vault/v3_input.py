"""Source-preserving C300 and Treasury M1 adapters for the fixed V3 sample."""

from __future__ import annotations

from pathlib import Path

from edp_lab.vault.v3_mapping import THIRTEEN_F_MEMBERS

DATA_NS = "http://schemas.microsoft.com/ado/2007/08/dataservices"


def c300_occurrence(row: dict, binding: dict, raw_sha256: str,
                    expected_names: tuple[str, ...]) -> dict:
    """Use only one COMPLETE, version-0 M1 binding and its original locator."""
    if (row.get("record_kind") != "DATA"
            or row.get("source_instance_id") != binding.get("source_instance_id")
            or row.get("run_id") != binding.get("run_id")
            or row.get("binding_sha256") != binding.get("binding_sha256")
            or binding.get("processing_status") != "COMPLETE"
            or binding.get("raw_sha256") != raw_sha256):
        raise ValueError("V3_C300_BINDING_OR_RAW_MISMATCH")
    physical = binding["archive_member"]
    if physical in {"sub.txt", "tag.txt", "pre.txt"}:
        logical = physical
    elif Path(physical).name.upper() in THIRTEEN_F_MEMBERS:
        logical = Path(physical).name.upper()
    elif physical.lower().endswith(".idx"):
        logical = "daily_master.idx"
    else:
        raise ValueError("V3_C300_MEMBER_OUT_OF_SCOPE")
    original = row.get("fields")
    if not isinstance(original, list) or len(original) != len(expected_names):
        raise ValueError("V3_C300_FIELD_WIDTH_CHANGED")
    fields = []
    for ordinal, (item, name) in enumerate(zip(original, expected_names, strict=True), 1):
        if (item.get("field_ordinal") != ordinal or item.get("original_name") != name
                or item.get("disposition") != "DIRECT_MAP"
                or not isinstance(item.get("lexical_value"), str)):
            raise ValueError("V3_C300_FIELD_OR_PARSER_CHANGED")
        fields.append({"name": name, "state": "PRESENT", "text": item["lexical_value"]})
    return {"source_instance_id": row["source_instance_id"],
            "archive_member": logical, "physical_archive_member": physical,
            "raw_sha256": raw_sha256, "member_sha256": binding["member_sha256"],
            "source_line": row["source_line"], "byte_offset": row["byte_offset"],
            "byte_length": row["byte_length"], "binding_sha256": row["binding_sha256"],
            "m1_run_id": row["run_id"], "fields": fields}


def treasury_entry(properties: list[dict], raw_sha256: str) -> dict:
    """Regroup accepted M1 property occurrences to their physical XML entry."""
    if not properties:
        raise ValueError("V3_TREASURY_ENTRY_EMPTY")
    ordered = sorted(properties, key=lambda item: item["property_ordinal"])
    first = ordered[0]
    sid, ordinal = first["source_instance_id"], first["entry_ordinal"]
    fields, lineage = [], []
    for index, item in enumerate(ordered, 1):
        if (item.get("source_instance_id") != sid
                or item.get("entry_ordinal") != ordinal
                or item.get("run_id") != first.get("run_id")
                or item.get("source_identity") != first.get("source_identity")
                or item.get("raw_sha256") != raw_sha256
                or item.get("property_ordinal") != index
                or not item.get("property_qname", "").startswith("{" + DATA_NS + "}")
                or type(item.get("byte_offset")) is not int
                or type(item.get("byte_length")) is not int
                or not isinstance(item.get("lexical_value"), str)):
            raise ValueError("V3_TREASURY_PROPERTY_LINEAGE_CHANGED")
        name = item["property_qname"].removeprefix("{" + DATA_NS + "}")
        fields.append({"name": name,
                       "state": "NULL_MARKER" if item["null_marker"] else "PRESENT",
                       "text": item["lexical_value"]})
        lineage.append({"ordinal": index, "qname": item["property_qname"],
                        "byte_offset": item["byte_offset"],
                        "byte_length": item["byte_length"],
                        "span_sha256": item["span_sha256"],
                        "attributes_json": item["attributes_json"]})
    if len({field["name"] for field in fields}) != len(fields):
        raise ValueError("V3_TREASURY_DUPLICATE_PROPERTY")
    return {"source_instance_id": sid, "archive_member": "atom.entry",
            "physical_archive_member": "atom.entry", "raw_sha256": raw_sha256,
            "m1_run_id": first.get("run_id"),
            "source_identity": first.get("source_identity"),
            "entry_ordinal": ordinal, "source_line": None,
            "byte_offset": None, "byte_length": None,
            "member_sha256": None, "fields": fields,
            "properties_lineage": lineage}
