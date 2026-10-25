"""Fixed, source-scoped V3 projection from accepted lexical occurrences.

Pure code: no Spark, credentials, Delta calls or semantic inference. Runtime
adapters must supply an occurrence from the pinned source-preserving inputs.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from edp_lab.vault.v3_keys import concept_key, filing_key, key, occurrence_key

FSDS_HEADERS = {
    "sub.txt": ("adsh", "cik", "name", "sic", "countryba", "stprba", "cityba",
                "zipba", "bas1", "bas2", "baph", "countryma", "stprma", "cityma",
                "zipma", "mas1", "mas2", "countryinc", "stprinc", "ein", "former",
                "changed", "afs", "wksi", "fye", "form", "period", "fy", "fp",
                "filed", "accepted", "prevrpt", "detail", "instance", "nciks", "aciks"),
    "tag.txt": ("tag", "version", "custom", "abstract", "datatype", "iord",
                "crdr", "tlabel", "doc"),
    "pre.txt": ("adsh", "report", "line", "stmt", "inpth", "rfile", "tag",
                "version", "plabel", "negating"),
}
EDGAR_HEADER = ("CIK", "Company Name", "Form Type", "Date Filed", "File Name")
THIRTEEN_F_MEMBERS = {
    "SUBMISSION.tsv": "v3_s_13f_submission_assertion",
    "COVERPAGE.tsv": "v3_s_13f_coverpage_assertion",
    "INFOTABLE.tsv": "v3_s_13f_infotable_assertion",
    "OTHERMANAGER.tsv": "v3_s_13f_othermanager_assertion",
    "OTHERMANAGER2.tsv": "v3_s_13f_othermanager2_assertion",
    "SIGNATURE.tsv": "v3_s_13f_signature_assertion",
    "SUMMARYPAGE.tsv": "v3_s_13f_summarypage_assertion",
}
TREASURY_DATE = {"SRC010451": "NEW_DATE", "SRC010452": "INDEX_DATE",
                 "SRC010453": "QUOTE_DATE", "SRC010454": "NEW_DATE",
                 "SRC010455": "QUOTE_DATE"}
TREASURY_RATE_TYPE = {"SRC010453"}


def _payload(value: Mapping) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _source_payload(source: dict) -> dict:
    return {"fields": source["fields"],
            "properties_lineage": source.get("properties_lineage"),
            "m1_run_id": source.get("m1_run_id"),
            "binding_sha256": source.get("binding_sha256"),
            "source_identity": source.get("source_identity")}


def _row(table: str, hk: str, occurrence_hk: str, source: dict,
         payload: Mapping, contract: str) -> dict:
    return {"table": table, "hk": hk, "occurrence_hk": occurrence_hk,
            "source_instance_id": source["source_instance_id"],
            "archive_member": source.get("physical_archive_member", source["archive_member"]),
            "source_line": source.get("source_line"),
            "byte_offset": source.get("byte_offset"),
            "byte_length": source.get("byte_length"),
            "raw_sha256": source["raw_sha256"],
            "member_sha256": source.get("member_sha256"),
            "contract_version": contract, "payload_json": _payload(payload)}


def _fields(source: dict, expected: tuple[str, ...] | None = None) -> dict:
    fields = source["fields"]
    if (not isinstance(fields, list) or not fields
            or any(set(item) != {"name", "state", "text"} for item in fields)
            or any(item["state"] not in {"PRESENT", "ABSENT", "NULL_MARKER"}
                   for item in fields)
            or any(item["state"] == "PRESENT" and not isinstance(item["text"], str)
                   for item in fields)):
        raise ValueError("V3_FIELDS_INVALID")
    names = tuple(item["name"] for item in fields)
    if len(set(names)) != len(names) or expected is not None and names != expected:
        raise ValueError("V3_FIELD_ORDER_OR_SCHEMA_CHANGED")
    return {item["name"]: item for item in fields}


def _text(fields: dict, name: str) -> str | None:
    item = fields.get(name)
    return item["text"] if item and item["state"] == "PRESENT" else None


def _technical(source: dict) -> str:
    if source["source_instance_id"] in TREASURY_DATE:
        ordinal = source.get("entry_ordinal")
        if type(ordinal) is not int or ordinal < 1:
            raise ValueError("V3_XML_ENTRY_ORDINAL_INVALID")
        return key("TREASURY_ENTRY_OCCURRENCE_V1", (
            source["source_instance_id"], source["raw_sha256"], str(ordinal)))
    if (not source.get("member_sha256") or type(source.get("byte_offset")) is not int
            or type(source.get("byte_length")) is not int
            or source["byte_offset"] < 0 or source["byte_length"] < 1):
        raise ValueError("V3_BYTE_LOCATOR_INVALID")
    return occurrence_key(source["source_instance_id"],
                          source.get("physical_archive_member", source["archive_member"]),
                          source["member_sha256"], source["byte_offset"],
                          source["byte_length"])


def project(source: dict, *, feed_id: str | None = None,
            parent_valid: bool = True) -> dict:
    """Return candidate rows plus an explicit blocked business disposition."""
    sid = source["source_instance_id"]
    member = source["archive_member"]
    occurrence = _technical(source)
    if sid in TREASURY_DATE:
        contract = "TREASURY_FEEDS_V1"
        fields = _fields(source)
    elif member in FSDS_HEADERS:
        contract = "FSDS_OTHER_V1"
        fields = _fields(source, FSDS_HEADERS[member])
    elif member in THIRTEEN_F_MEMBERS:
        contract = "SEC_13F_V1"
        fields = _fields(source)
    elif member == "daily_master.idx":
        contract = "EDGAR_MASTER_V1"
        fields = _fields(source, EDGAR_HEADER)
    else:
        raise ValueError("V3_SOURCE_MEMBER_OUT_OF_SCOPE")
    rows = [_row("v3_r_source_occurrence", occurrence, occurrence, source,
                 {**_source_payload(source), "entry_ordinal": source.get("entry_ordinal")},
                 contract)]
    blocked = None
    if contract == "FSDS_OTHER_V1":
        if member == "sub.txt":
            adsh = _text(fields, "adsh")
            if adsh:
                filing = filing_key(adsh)
                rows += [_row("v3_h_filing", filing, "", source, {"adsh": adsh}, contract),
                         _row("v3_s_fsds_sub_assertion", filing, occurrence, source,
                              _source_payload(source), contract)]
            else:
                blocked = "MISSING_FILING_REFERENCE"
        elif member == "tag.txt":
            tag, version = _text(fields, "tag"), _text(fields, "version")
            if tag and version:
                concept = concept_key(tag, version)
                rows += [_row("v3_h_concept", concept, "", source,
                              {"tag": tag, "version": version}, contract),
                         _row("v3_s_fsds_tag_assertion", concept, occurrence, source,
                              _source_payload(source), contract)]
            else:
                blocked = "MISSING_CONCEPT_REFERENCE"
        else:
            adsh, tag, version = (_text(fields, name) for name in ("adsh", "tag", "version"))
            context = [fields[name] for name in ("report", "line", "stmt", "inpth", "rfile")]
            if (adsh and tag and version and parent_valid
                    and all(item["state"] == "PRESENT" for item in context)):
                filing, concept = filing_key(adsh), concept_key(tag, version)
                parts = [filing, concept]
                for item in context:
                    parts.extend((item["name"], item["state"], item["text"]))
                link = key("FSDS_PRESENTATION_V1", parts)
                rows += [_row("v3_h_filing", filing, "", source, {"adsh": adsh}, contract),
                         _row("v3_h_concept", concept, "", source,
                              {"tag": tag, "version": version}, contract),
                         _row("v3_l_fsds_presentation", link, "", source,
                              {"filing_hk": filing, "concept_hk": concept,
                               "context": context}, contract),
                         _row("v3_s_fsds_pre_assertion", link, occurrence, source,
                              _source_payload(source), contract)]
            else:
                blocked = ("UNRESOLVED_PRESENTATION_PARENT" if not parent_valid else
                           "MISSING_PRESENTATION_IDENTITY")
    elif contract == "EDGAR_MASTER_V1":
        path = _text(fields, "File Name")
        if path:
            reference = key("EDGAR_FILE_REFERENCE_V1", ("SEC_EDGAR_DAILY_MASTER", path))
            rows += [_row("v3_h_edgar_file_reference", reference, "", source,
                          {"file_name": path}, contract),
                     _row("v3_s_edgar_index_assertion", reference, occurrence, source,
                          _source_payload(source), contract)]
        else:
            blocked = "MISSING_FILE_REFERENCE"
    elif contract == "SEC_13F_V1":
        accession = _text(fields, "ACCESSION_NUMBER")
        if accession and parent_valid:
            submission = key("THIRTEEN_F_SUBMISSION_V1", ("SEC_13F", accession))
            rows += [_row("v3_h_13f_submission", submission, "", source,
                          {"accession_number": accession}, contract),
                     _row(THIRTEEN_F_MEMBERS[member], submission, occurrence, source,
                          {**_source_payload(source), "member_type": member}, contract)]
        else:
            blocked = ("UNRESOLVED_SUBMISSION_PARENT" if not parent_valid else
                       "MISSING_SUBMISSION_REFERENCE")
    else:
        date_name = TREASURY_DATE[sid]
        date_value = _text(fields, date_name)
        type_state = fields.get("RATE_TYPE", {"state": "ABSENT", "text": None})["state"]
        rate_type = _text(fields, "RATE_TYPE")
        if feed_id and date_value and (sid not in TREASURY_RATE_TYPE or rate_type):
            feed = key("TREASURY_FEED_V1", ("TREASURY_ANNUAL_XML", feed_id))
            observation = key("TREASURY_OBSERVATION_V1", (
                feed, date_name, date_value, type_state, rate_type))
            link = key("TREASURY_FEED_OBSERVATION_V1", (feed, observation))
            rows += [_row("v3_h_treasury_feed", feed, "", source,
                          {"feed_id": feed_id}, contract),
                     _row("v3_h_treasury_observation", observation, "", source,
                          {"feed_hk": feed, "date_field": date_name, "date": date_value,
                           "rate_type_state": type_state, "rate_type": rate_type}, contract),
                     _row("v3_l_treasury_feed_observation", link, "", source,
                          {"feed_hk": feed, "observation_hk": observation}, contract),
                     _row("v3_s_treasury_entry_assertion", observation, occurrence, source,
                          _source_payload(source), contract)]
        else:
            blocked = "MISSING_TREASURY_BUSINESS_IDENTITY"
    if blocked:
        rows.append(_row("v3_vault_reject_quarantine", occurrence, occurrence,
                         source, {"reason": blocked, **_source_payload(source)}, contract))
    rows.append(_row("v3_r_load_event", occurrence, occurrence, source,
                     {"business_status": "BLOCKED" if blocked else "PROJECTED"}, contract))
    return {"occurrence_hk": occurrence, "business_status": blocked or "PROJECTED",
            "rows": rows}
