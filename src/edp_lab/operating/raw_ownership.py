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
