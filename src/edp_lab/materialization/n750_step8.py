"""Frozen N750 Step 8 lexical adapters and exact Treasury M2 projection.

All outputs retain byte locators into the hash-sealed original RAW object.
No source meaning, identity merge, unit conversion, or deduplication is inferred.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET

from edp_lab.materialization.typed_numeric_v1 import convert

ATOM = "http://www.w3.org/2005/Atom"
DATA = "http://schemas.microsoft.com/ado/2007/08/dataservices"
META = "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"
SEC_HEADER = "CIK|Company Name|Form Type|Date Filed|File Name"
SEC_PREAMBLE = ("Description:", "Last Data Received:", "Comments:",
                "Anonymous FTP:", " ")
RUN = "n750_step8_v1"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def treasury_allowlist(source_id):
    if source_id == "SRC010451":
        return tuple("BC_" + x for x in (
            "1MONTH", "1_5MONTH", "2MONTH", "3MONTH", "4MONTH", "6MONTH",
            "1YEAR", "2YEAR", "3YEAR", "5YEAR", "7YEAR", "10YEAR",
            "20YEAR", "30YEAR", "30YEARDISPLAY"))
    if source_id == "SRC010452":
        return tuple([f"ROUND_B1_{kind}_{week}WK_2"
                      for kind in ("CLOSE", "YIELD") for week in (4, 6, 8, 13, 17, 26, 52)] +
                     [f"CS_{week}WK_{kind}_AVG"
                      for week in (4, 6, 8, 13, 17, 26, 52) for kind in ("CLOSE", "YIELD")])
    if source_id in ("SRC010453", "SRC010455"):
        return ("RATE",)
    if source_id == "SRC010454":
        return tuple("TC_" + x for x in ("5YEAR", "7YEAR", "10YEAR", "20YEAR", "30YEAR"))
    raise ValueError("TREASURY_SOURCE_OUTSIDE_ALLOWLIST")


def parse_sec(raw, source):
    """Return every physical line, preserving the seven-line source framing."""
    assert digest(raw) == source["raw_sha256"]
    rows = []
    offset = 0
    for number, line in enumerate(io.BytesIO(raw), 1):
        if len(line) > 8 * 1024 * 1024:
            raise ValueError(f"RESOURCE_LINE_LIMIT:{number}")
        content = line.removesuffix(b"\n").removesuffix(b"\r")
        if b"\r" in content or (line.endswith(b"\r") and not line.endswith(b"\r\n")):
            raise ValueError(f"UNSUPPORTED_TERMINATOR:{number}")
        text = content.decode("utf-8", errors="strict")
        if number <= 5:
            if not text.startswith(SEC_PREAMBLE[number - 1]) or (number == 5 and text != " "):
                raise ValueError(f"PREAMBLE_MISMATCH:{number}")
            kind, fields = "METADATA", []
        elif number == 6:
            if text != SEC_HEADER:
                raise ValueError("HEADER_MISMATCH")
            kind, fields = "HEADER", []
        elif number == 7:
            if text != "-" * 80:
                raise ValueError("SEPARATOR_MISMATCH")
            kind, fields = "METADATA", []
        else:
            fields = text.split("|")
            if len(fields) != 5 or not content:
                raise ValueError(f"DATA_WIDTH_MISMATCH:{number}")
            kind = "DATA"
        rows.append({"run_id": RUN, "source_instance_id": source["source_instance_id"],
                     "source_identity": source["source_identity"], "raw_sha256": source["raw_sha256"],
                     "source_line": number, "byte_offset": offset, "byte_length": len(line),
                     "line_sha256": digest(line), "record_kind": kind,
                     "original_text": text, "fields": fields,
                     "model_version": "M1_LEXICAL_V1", "rule_version": "C300_LITERAL_IDENTITY_V1"})
        offset += len(line)
    if len(rows) < 7 or offset != len(raw):
        raise ValueError("INCOMPLETE_SEC_SOURCE")
    return rows


def _property_span(raw, cursor, name, limit):
    opening = b"<d:" + name.encode()
    start = raw.find(opening, cursor, limit)
    if start < 0 or (raw.find(b"<d:", cursor, start) >= 0):
        raise ValueError("XML_PROPERTY_LOCATOR_MISMATCH")
    opening_end = raw.find(b">", start, limit)
    if opening_end < 0:
        raise ValueError("XML_PROPERTY_OPEN_UNCLOSED")
    if raw[opening_end - 1:opening_end] == b"/":
        end = opening_end + 1
    else:
        close = b"</d:" + name.encode() + b">"
        closing = raw.find(close, opening_end + 1, limit)
        if closing < 0 or raw.find(b"<d:", opening_end + 1, closing) >= 0:
            raise ValueError("XML_PROPERTY_CLOSE_MISMATCH")
        end = closing + len(close)
    return start, end


def parse_treasury(raw, source):
    """Validate the XML tree against RAW-resolvable property spans."""
    assert digest(raw) == source["raw_sha256"]
    root = ET.fromstring(raw)
    if root.tag != f"{{{ATOM}}}feed":
        raise ValueError("XML_FEED_MISMATCH")
    entries = root.findall(f"{{{ATOM}}}entry")
    spans = list(re.finditer(rb"<entry(?:\s[^>]*)?>.*?</entry\s*>", raw, re.DOTALL))
    if len(spans) != len(entries):
        raise ValueError("XML_ENTRY_LOCATOR_MISMATCH")
    allowlist = treasury_allowlist(source["source_instance_id"])
    lexical, projected = [], []
    for entry_number, (entry, span) in enumerate(zip(entries, spans, strict=True), 1):
        properties = entry.find(f"{{{ATOM}}}content/{{{META}}}properties")
        if properties is None:
            raise ValueError("XML_PROPERTIES_MISSING")
        cursor, seen = span.start(), set()
        for ordinal, prop in enumerate(properties, 1):
            if not prop.tag.startswith("{" + DATA + "}") or len(prop):
                raise ValueError("XML_PROPERTY_STRUCTURE_UNSUPPORTED")
            name = prop.tag.removeprefix("{" + DATA + "}")
            start, end = _property_span(raw, cursor, name, span.end())
            cursor = end
            fragment = raw[start:end]
            wrapper = (b'<root xmlns:d="' + DATA.encode() + b'" xmlns:m="' + META.encode() +
                       b'">' + fragment + b'</root>')
            reparsed = ET.fromstring(wrapper)[0]
            if reparsed.tag != prop.tag or reparsed.text != prop.text or reparsed.attrib != prop.attrib:
                raise ValueError("XML_PROPERTY_VALUE_MISMATCH")
            lexical_value = "" if prop.text is None else prop.text
            null_marker = prop.attrib.get(f"{{{META}}}null") == "true"
            common = {"run_id": RUN, "source_instance_id": source["source_instance_id"],
                      "source_identity": source["source_identity"], "raw_sha256": source["raw_sha256"],
                      "entry_ordinal": entry_number, "property_ordinal": ordinal,
                      "property_qname": prop.tag, "byte_offset": start, "byte_length": end - start,
                      "span_sha256": digest(fragment), "lexical_value": lexical_value,
                      "attributes_json": json.dumps(prop.attrib, sort_keys=True),
                      "null_marker": null_marker, "model_version": "M1_LEXICAL_V1",
                      "rule_version": "TREASURY_XML_PROPERTY_LEXICAL_V1"}
            lexical.append(common)
            if name in allowlist:
                seen.add(name)
                projection = convert(lexical_value, null_marker=null_marker)
                projected.append(dict(common, value_decimal=projection.value_decimal,
                                      conversion_outcome=projection.conversion_outcome,
                                      conversion_reason=projection.conversion_reason,
                                      m2_model_version=projection.model_version,
                                      conversion_rule_version=projection.conversion_rule_version,
                                      source_rule_version="TREASURY_RATE_QNAME_SCOPE_V1",
                                      present=True))
        if raw.find(b"<d:", cursor, span.end()) >= 0:
            raise ValueError("UNACCOUNTED_XML_PROPERTY")
        for name in allowlist:
            if name not in seen:
                projection = convert(None, present=False)
                projected.append({"run_id": RUN, "source_instance_id": source["source_instance_id"],
                                  "source_identity": source["source_identity"],
                                  "raw_sha256": source["raw_sha256"], "entry_ordinal": entry_number,
                                  "property_ordinal": None, "property_qname": f"{{{DATA}}}{name}",
                                  "byte_offset": None, "byte_length": None, "span_sha256": None,
                                  "lexical_value": None, "attributes_json": None,
                                  "null_marker": False, "model_version": "M1_LEXICAL_V1",
                                  "rule_version": "TREASURY_XML_PROPERTY_LEXICAL_V1",
                                  "value_decimal": projection.value_decimal,
                                  "conversion_outcome": projection.conversion_outcome,
                                  "conversion_reason": projection.conversion_reason,
                                  "m2_model_version": projection.model_version,
                                  "conversion_rule_version": projection.conversion_rule_version,
                                  "source_rule_version": "TREASURY_RATE_QNAME_SCOPE_V1", "present": False})
    return lexical, projected, len(entries)
