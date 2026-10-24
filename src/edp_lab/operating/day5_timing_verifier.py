"""Sign measured SQL creation time from protected submission and live readback."""

import json
from datetime import datetime
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    file_digest,
    load_grant,
    verified_document,
)
from edp_lab.operating.protected_verifier import _sign


def attest_timing(root: Path, queue_path: Path, grant_path: Path,
                  state_path: Path, trust: Path, key: Path) -> dict:
    root = root.resolve()
    if any(path.resolve().is_relative_to(root) for path in (trust, key)):
        raise Denied("VERIFIER_MUST_BE_PROTECTED")
    queue = json.loads(queue_path.read_bytes())
    grant = load_grant(root, grant_path, trust)
    state = json.loads(state_path.read_bytes())
    if (queue["cohort"] != "C2000" or grant["authority"] != "policy-broker-v1"
            or state["queue_sha256"] != file_digest(queue_path)
            or state["grant_id"] != grant["grant_id"]
            or state["tasks"]["P10-P11"]["status"] != "COMPLETE"
            or state["tasks"]["P12-budget"]["status"] != "PLANNED"):
        raise Denied("TIMING_CHECKPOINT_MISMATCH")
    tasks = {task["id"]: task for task in queue["tasks"]}
    sql_receipt = Path(tasks["sql-full_clean"]["external_receipt"])
    proof = verified_document(root, sql_receipt, trust)
    if (proof.get("schema") != "EDP_EXTERNAL_OPERATION_RECEIPT_V1"
            or proof.get("authority") != "protected-verifier-v1"
            or proof.get("operation_id") != tasks["sql-full_clean"]["operation_id"]
            or proof.get("status") != "VERIFIED" or proof.get("live_readback") is not True):
        raise Denied("TIMING_SQL_RECEIPT_INVALID")
    try:
        began = datetime.fromisoformat(proof["submitted_at_utc"])
        ended = datetime.fromisoformat(proof["attested_at_utc"])
        elapsed = (ended - began).total_seconds()
    except (KeyError, TypeError, ValueError) as exc:
        raise Denied("TIMING_EVIDENCE_MISSING") from exc
    if began.tzinfo is None or ended.tzinfo is None or elapsed < 0:
        raise Denied("TIMING_EVIDENCE_INVALID")
    policy_path = (root / queue["contracts"]["budget_policy"]["path"]).resolve(strict=True)
    if (not policy_path.is_relative_to(root)
            or file_digest(policy_path) != grant["contracts"]["budget_policy"]["sha256"]):
        raise Denied("TIMING_POLICY_CHANGED")
    policy = json.loads(policy_path.read_bytes())
    phase = next((row for row in policy["phase_limits"]
                  if row["id"] == "sql_table_creation"), None)
    if phase is None or phase["metric"] != "SQL request-to-result":
        raise Denied("TIMING_PHASE_NOT_COMPARABLE")
    output = Path(tasks["P12-budget"]["receipt"])
    if output.parent.resolve() != (trust.parent / "receipts").resolve():
        raise Denied("RECEIPT_OUTSIDE_PROTECTED_STORE")
    document = {"schema": "EDP_PHASE_TIMING_RECEIPT_V1",
                "authority": "protected-verifier-v1", "cohort": "C2000",
                "output": queue["output"], "phase_id": "sql_table_creation",
                "policy_sha256": file_digest(policy_path), "observed_live": True,
                "measurement_receipt_sha256": file_digest(sql_receipt),
                "timing_method": "SQL request-to-result", "phase_comparable": True,
                "elapsed_seconds": elapsed,
                "source_statement_id": proof["statement_id"]}
    _sign(document, key, output)
    return {"status": "MEASURED", "elapsed_seconds": elapsed,
            "receipt_sha256": file_digest(output)}
