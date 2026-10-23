"""Independently attest the actual version-pinned C2000 Databricks result."""

import json
import os
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    canonical,
    file_digest,
    load_grant,
)
from edp_lab.operating.day5_stage_verifier import _query
from edp_lab.operating.protected_verifier import _remote_json, _sign

OLD = "workspace.edp_lab.o_c1500_m2_result_frozen_v1"


def _values(response: dict) -> list[str]:
    rows = response.get("result", {}).get("data_array", [])
    if len(rows) != 1 or response.get("manifest", {}).get("truncated"):
        raise Denied("FREEZE_QUERY_RESULT_INVALID")
    return rows[0]


def attest_freeze(root: Path, queue_path: Path, grant_path: Path,
                  state_path: Path, trust: Path, key: Path) -> dict:
    root = root.resolve()
    if any(path.resolve().is_relative_to(root) for path in (trust, key)):
        raise Denied("VERIFIER_MUST_BE_PROTECTED")
    queue = json.loads(queue_path.read_bytes())
    grant = load_grant(root, grant_path, trust)
    state = json.loads(state_path.read_bytes())
    if (queue.get("cohort") != "C2000" or grant["authority"] != "policy-broker-v1"
            or state["queue_sha256"] != file_digest(queue_path)
            or state["grant_id"] != grant["grant_id"]
            or state["tasks"]["P12-budget"]["status"] != "COMPLETE"
            or state["tasks"]["P13"]["status"] != "PLANNED"):
        raise Denied("FREEZE_CHECKPOINT_MISMATCH")
    folder = root / "metadata/freezes/C2000_v1"
    freeze = json.loads((folder / "freeze.json").read_bytes())
    if (freeze.get("status") != "FROZEN_INPUT_NOT_RESULT"
            or freeze.get("queue_sha256") != file_digest(queue_path)
            or len(freeze.get("raw_receipts_sha256", {})) != 500):
        raise Denied("INPUT_FREEZE_NOT_VERIFIED")
    targets = {task["statement_contract"]: task["databricks_table"]
               for task in queue["tasks"] if task["kind"] == "databricks_write"}
    if set(targets) != {"roster", "smoke", "full_clean", "candidate_view", "result_view"}:
        raise Denied("FREEZE_TARGET_SET_CHANGED")
    names = [targets[name] for name in ("roster", "smoke", "full_clean", "result_view")]
    names.append(OLD)
    uc = {name: _remote_json("/api/2.1/unity-catalog/tables/" + name, 180)
          for name in names}
    for name in names:
        item = uc[name]
        if item.get("full_name") != name or not item.get("table_id"):
            raise Denied("FREEZE_UC_IDENTITY_MISMATCH")
    if uc[OLD]["table_id"] != "43e16098-b123-4689-83d5-4d942bbe4dfc":
        raise Denied("PRIOR_RESULT_VIEW_CHANGED")
    for name in names[:3]:
        if uc[name].get("data_source_format") != "DELTA":
            raise Denied("FREEZE_DELTA_FORMAT_CHANGED")
    if uc[targets["result_view"]].get("table_type") != "VIEW":
        raise Denied("RESULT_FREEZE_NOT_VIEW")
    histories = {}
    details = {}
    for name in names[:3]:
        history = _query(f"DESCRIBE HISTORY {name} LIMIT 1")
        history_row = _values(history)
        history_columns = [column["name"] for column in history["manifest"]["schema"]["columns"]]
        version = dict(zip(history_columns, history_row, strict=True)).get("version")
        if str(version) != "0":
            raise Denied("FREEZE_DELTA_VERSION_CHANGED")
        histories[name] = history
        detail = _query(f"DESCRIBE DETAIL {name}")
        columns = [column["name"] for column in detail["manifest"]["schema"]["columns"]]
        row = dict(zip(columns, _values(detail), strict=True))
        if row.get("format", "").lower() != "delta" or not row.get("id"):
            raise Denied("FREEZE_DELTA_DETAIL_INVALID")
        details[name] = detail
    definition_response = _query("SHOW CREATE TABLE " + targets["result_view"])
    definition = " ".join(str(value) for value in _values(definition_response))
    if (OLD not in definition or targets["full_clean"] not in definition
            or "VERSION AS OF 0" not in definition.upper()
            or "UNION ALL" not in definition.upper()):
        raise Denied("FREEZE_QUERYABLE_DEFINITION_CHANGED")
    clean = _query(f"SELECT count(*) AS records, count(DISTINCT source_identity) AS sources, "
                   f"count_if(field_count <> 5) AS bad_width FROM {targets['full_clean']} "
                   "VERSION AS OF 0")
    if list(map(int, _values(clean))) != [2037138, 500, 0]:
        raise Denied("FREEZE_CLEAN_COUNT_MISMATCH")
    roster = _query(f"SELECT count(*) AS sources FROM {targets['roster']} VERSION AS OF 0")
    if list(map(int, _values(roster))) != [500]:
        raise Denied("FREEZE_ROSTER_COUNT_MISMATCH")
    prior = _query(f"SELECT count(DISTINCT source_instance_id) AS sources FROM {OLD}")
    if list(map(int, _values(prior))) != [1500]:
        raise Denied("FREEZE_PRIOR_SOURCE_COUNT_MISMATCH")
    result = _query(f"SELECT count(DISTINCT source_instance_id) AS sources, "
                    "count_if(occurrence_class = 'NEW_N500_SEC_RECORD') AS new_records "
                    f"FROM {targets['result_view']}")
    if list(map(int, _values(result))) != [2000, 2037138]:
        raise Denied("FREEZE_RESULT_COUNT_MISMATCH")
    lineage = _query(f"SELECT count(*) AS mismatches FROM {targets['full_clean']} "
                     f"VERSION AS OF 0 c LEFT JOIN {targets['roster']} VERSION AS OF 0 r "
                     "ON c.source_instance_id=r.source_instance_id "
                     "WHERE r.source_instance_id IS NULL OR c.source_identity<>r.source_identity "
                     "OR c.raw_sha256<>r.raw_sha256")
    if list(map(int, _values(lineage))) != [0]:
        raise Denied("FREEZE_SOURCE_LINEAGE_MISMATCH")
    evidence = {"uc": uc, "delta_history": histories, "delta_detail": details,
                "queryable_definition": definition_response, "roster": roster,
                "clean": clean, "prior": prior, "result": result, "lineage": lineage}
    receipt = Path(next(task for task in queue["tasks"] if task["id"] == "P13")["receipt"])
    if receipt.parent.resolve() != (trust.parent / "receipts").resolve():
        raise Denied("RECEIPT_OUTSIDE_PROTECTED_STORE")
    evidence_path = receipt.with_name("c2000-result-freeze-live-evidence.json")
    fd = os.open(evidence_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical(evidence))
        stream.flush()
        os.fsync(stream.fileno())
    document = {"schema": "EDP_LIVE_FREEZE_RECEIPT_V1",
                "authority": "protected-verifier-v1", "cohort": "C2000",
                "output": queue["output"], "status": "C2000_RESULT_FROZEN",
                "input_freeze_sha256": file_digest(folder / "freeze.json"),
                "queue_sha256": file_digest(queue_path),
                "delta_ids": "VERIFIED", "delta_history": "VERIFIED",
                "delta_properties": "VERIFIED", "row_counts": "VERIFIED",
                "source_lineage": "VERIFIED", "queryable_versions": "VERIFIED",
                "live_readback": "VERIFIED",
                "remote_receipt_sha256": file_digest(evidence_path),
                "remote_readback_evidence": str(evidence_path),
                "result_uc_table_id": uc[targets["result_view"]]["table_id"]}
    _sign(document, key, receipt)
    return {"status": "C2000_RESULT_FROZEN", "receipt_sha256": file_digest(receipt),
            "live_evidence_sha256": file_digest(evidence_path)}
