"""Fail-closed runtime boundary between Acquisition RAW writes and Cohort reads.

Historical C2000 signed receipts/queues are immutable evidence. This guard
governs *new* Cohort executions: RAW mutation is never a Cohort capability,
even if a stale standing policy lists it.
"""

from edp_lab.operating.authority import Denied

# These names are denied even if an untrusted queue attempts a new variant.
RAW_WRITE_OPERATIONS = frozenset({
    "raw_stage", "raw_upload", "raw_copy", "raw_move", "raw_restage",
    "raw_overwrite", "raw_delete", "raw_mkdir",
})


def require_cohort_readonly(queue: dict) -> None:
    """Refuse RAW writes before a grant, ledger or checkpoint is created."""
    if not isinstance(queue, dict) or not isinstance(queue.get("tasks"), list):
        raise Denied("INVALID_COHORT_QUEUE")
    if any(not isinstance(task, dict) for task in queue["tasks"]):
        raise Denied("INVALID_COHORT_TASK")
    if any(task.get("kind") in RAW_WRITE_OPERATIONS
           for task in queue["tasks"]):
        raise Denied("COHORT_RAW_MUTATION_FORBIDDEN")


def require_cohort_operation_readonly(operation: dict) -> None:
    """The protected Cohort Broker rejects bypasses of queue validation."""
    if not isinstance(operation, dict):
        raise Denied("INVALID_COHORT_OPERATION")
    if operation.get("operation") in RAW_WRITE_OPERATIONS:
        raise Denied("COHORT_RAW_MUTATION_FORBIDDEN")


def acquisition_remediation_request(
    *, identity: str, raw_sha256: str, byte_size: int,
    reason_code: str, cohort: str,
) -> dict:
    """Sanitized *request* for upstream Acquisition, never a write grant."""
    import re

    if (not isinstance(identity, str) or not identity
            or not isinstance(cohort, str) or not re.fullmatch(r"C[0-9]+", cohort)
            or not isinstance(raw_sha256, str)
            or not re.fullmatch(r"[a-f0-9]{64}", raw_sha256)
            or type(byte_size) is not int or byte_size < 0
            or reason_code not in {
                "RAW_LOCATOR_MISSING", "RAW_RECEIPT_MISSING",
                "REMOTE_RAW_HASH_MISMATCH", "REMOTE_RAW_UNVERIFIED",
            }):
        raise Denied("INVALID_RAW_HANDOFF_REMEDIATION_SCOPE")
    return {
        "schema": "EDP_ACQUISITION_REMEDIATION_REQUEST_V1",
        "status": "RAW_HANDOFF_BLOCKED",
        "target_actor": "ACQUISITION",
        "source_identity": identity,
        "raw_sha256": raw_sha256,
        "byte_size": byte_size,
        "cohort": cohort,
        "reason_code": reason_code,
        "operations_authorized": [],
        "write_authorized": False,
        "resume_requires": "INDEPENDENTLY_VERIFIED_RAW_HANDOFF",
    }


def verify_u10_raw_handoff(root, queue: dict, trust) -> dict:
    """Verify immutable signed Acquisition/U10 receipt before Cohort processing.

    Can be required by a separately owner-signed standing Cohort policy; old
    historical Queue V1 bytes stay unchanged and are not silently upgraded.
    This verifies trusted retained readback evidence, not live remote object
    freshness. It never stages RAW or issues an Acquisition write grant.
    """
    import re
    from pathlib import Path

    from edp_lab.operating.authority import file_digest, verified_document

    root = Path(root).resolve()
    path_info = queue.get("raw_handoff")
    if (not isinstance(path_info, dict)
            or set(path_info) != {"path", "sha256"}
            or not re.fullmatch(r"[a-f0-9]{64}", str(path_info["sha256"]))):
        raise Denied("RAW_HANDOFF_BLOCKED")
    path = Path(path_info["path"])
    if (not path.is_absolute() or path.is_symlink()
            or path.resolve().is_relative_to(root)):
        raise Denied("RAW_HANDOFF_BLOCKED")
    try:
        if file_digest(path) != path_info["sha256"]:
            raise Denied("RAW_HANDOFF_BLOCKED")
        receipt = verified_document(root, path, trust)
    except (OSError, ValueError, KeyError) as exc:
        raise Denied("RAW_HANDOFF_BLOCKED") from exc
    if (receipt.get("schema") != "EDP_U10_RAW_HANDOFF_V1"
            or receipt.get("authority") != "protected-verifier-v1"
            or receipt.get("status") != "VERIFIED"
            or receipt.get("live_remote_readback") is not True
            or receipt.get("cohort") != queue.get("cohort")
            or not isinstance(receipt.get("sources"), list)
            or not isinstance(queue.get("sources"), list)):
        raise Denied("RAW_HANDOFF_BLOCKED")
    sources = queue["sources"]
    entries = receipt["sources"]
    if len(entries) != len(sources):
        raise Denied("RAW_HANDOFF_BLOCKED")
    originals = {}
    for source in sources:
        if (not isinstance(source, dict) or not isinstance(source.get("identity"), str)
                or not re.fullmatch(r"[a-f0-9]{64}", str(source.get("sha256", "")))
                or source["identity"] in originals):
            raise Denied("RAW_HANDOFF_BLOCKED")
        originals[source["identity"]] = source["sha256"]
    seen = set()
    for item in entries:
        if not isinstance(item, dict):
            raise Denied("RAW_HANDOFF_BLOCKED")
        identity = item.get("identity")
        uri = item.get("remote_raw_path")
        if (not isinstance(identity, str) or identity in seen
                or originals.get(identity) != item.get("sha256")
                or item.get("remote_readback_sha256") != item.get("sha256")
                or type(item.get("byte_size")) is not int
                or item["byte_size"] < 0
                or not isinstance(uri, str)
                or not uri.startswith("dbfs:/Volumes/")
                or any(part in {"", ".", ".."} for part in uri[6:].split("/"))
                or not re.fullmatch(
                    r"[a-f0-9]{64}", str(item.get("readback_receipt_sha256", "")))):
            raise Denied("RAW_HANDOFF_BLOCKED")
        seen.add(identity)
    if seen != set(originals):
        raise Denied("RAW_HANDOFF_BLOCKED")
    return {"status": "RAW_HANDOFF_VERIFIED", "verified_sources": len(entries),
            "handoff_sha256": path_info["sha256"], "raw_write_authorized": False}
