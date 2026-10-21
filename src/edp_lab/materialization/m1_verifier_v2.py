"""M1 readback oracle with DEC-000010 exact field interpretation.

Derived from frozen c300_m1.verify_parquet (code SHA
cd2b580b56e819dee2e49933a658161ce92675fd4ba5c1abc2f9ffc3a4e1b2ea).
The frozen implementation/artifacts remain untouched. M1 schema and packaging
are unchanged. Step 3 must pin this verifier and the versioned parser profile.
"""
import hashlib

from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.parsers import src010128_v1 as exception
from edp_lab.parsers.c300_v1 import PROFILES, member_stream
from edp_lab.profiling.source_reader import canonical_hash

MODEL = "M1_LEXICAL_V1"
RULE = "C300_LITERAL_IDENTITY_V1"


def stable_record(row):
    return {k: v for k, v in row.items() if k != "run_id"}


def verify_parquet(root, binding, path):
    """Independent full-population interval/lexical oracle, not a second parser call.

    Parquet rows are checked in emitted physical order, preserving duplicates.
    Reconstruct the member by concatenating the referenced RAW intervals.
    """
    import pyarrow.parquet as pq
    scoped = binding.get('profile_id') == exception.PROFILE
    if scoped:
        exception.check_scope(root, binding)
    if file_sha256(root / binding['raw_path']) != binding['raw_sha256']:
        raise ValueError('RAW_SHA256_MISMATCH')
    offset = count = data = fields = 0
    binding_hash = canonical_hash(binding)
    rebuilt, logical = hashlib.sha256(), hashlib.sha256()
    prefixes = {p["source_line"] for p in binding["prefix_evidence"]}
    header_line = 6 if binding["source_family"] == "SEC_EDGAR_DAILY_MASTER" else 1
    with member_stream(root / binding["raw_path"], binding["archive_member"]) as source:
        for batch in pq.ParquetFile(path).iter_batches(batch_size=2048):
            for row in batch.to_pylist():
                count += 1
                assert row["source_line"] == count and row["byte_offset"] == offset
                assert row["source_instance_id"] == binding["source_instance_id"]
                assert row["binding_sha256"] == binding_hash
                assert row["model_version"] == MODEL and row["rule_version"] == RULE
                raw = source.read(row["byte_length"])
                assert len(raw) == row["byte_length"] and raw
                # Exactly one physical line, including an optional exact terminator.
                assert b"\n" not in raw[:-1]
                rebuilt.update(raw)
                offset += len(raw)
                kind = ("HEADER" if count == header_line else "METADATA") if (
                    count in prefixes) else "DATA"
                assert row["record_kind"] == kind
                if kind == "DATA":
                    if scoped and count == exception.LINE:
                        # Independent value oracle: inspect RAW, not parser-produced values.
                        parts = exception.check_record(binding, count, row["byte_offset"], raw)
                        values = [part.decode("iso-8859-1" if i == 1 else "utf-8", errors="strict")
                                  for i, part in enumerate(parts)]
                        assert values[1] == exception.COMPANY
                        assert values[1].encode("iso-8859-1") == parts[1]
                    else:
                        values = raw.removesuffix(b"\n").removesuffix(b"\r").decode(
                            "utf-8", errors="strict").split(
                                PROFILES[binding["source_family"]]["delimiter"])
                    assert len(values) == len(binding["expected_header"]) == len(row["fields"])
                    for ordinal, (name, value, actual) in enumerate(zip(
                            binding["expected_header"], values, row["fields"], strict=True), 1):
                        assert actual == {"field_ordinal": ordinal, "original_name": name,
                                              "lexical_value": value, "disposition": "DIRECT_MAP"}
                    assert row["admission_outcome"] == "ACCEPTED"
                    assert row["outcome_reason"] == "IDENTITY_LEXICAL_PRESERVATION"
                    data += 1
                    fields += len(values)
                else:
                    assert row["fields"] == [] and row["admission_outcome"] is None
                    assert row["outcome_reason"] is None
                    expected = next(p for p in binding["prefix_evidence"] if p["source_line"] == count)
                    assert raw.hex() == expected["raw_hex"]
                logical.update(bytes.fromhex(canonical_hash(stable_record(row))))
        assert not source.read(1)
    if scoped:
        assert count == 8537 and data == 8530 and fields == 42650
    assert file_sha256(root / binding['raw_path']) == binding['raw_sha256']
    assert offset == binding["uncompressed_bytes"]
    assert rebuilt.hexdigest() == binding["member_sha256"]
    return {"records_total": count, "records_data": data, "fields_data": fields,
                "observed_member_sha256": rebuilt.hexdigest(), "bytes": offset,
                "ordered_record_digest": logical.hexdigest()}
