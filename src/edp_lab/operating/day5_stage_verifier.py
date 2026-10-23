"""Independent bounded live readbacks for the Day 5 smoke and result stages."""

import json
import subprocess
import time
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    canonical,
    digest,
    file_digest,
    load_grant,
    verified_document,
)
from edp_lab.operating.protected_cli import databricks_argv
from edp_lab.operating.protected_verifier import _sign
from edp_lab.operating.runner import task_request

WAREHOUSE = "589e80595c7c8cb8"
SQL_TASK = {"P7": "sql-smoke", "P8": "sql-full_clean", "P9": "sql-result_view"}


def _query(sql: str, *, expected_rows: int | None = 1) -> dict:
    request = {"warehouse_id": WAREHOUSE, "statement": sql, "wait_timeout": "50s",
               "on_wait_timeout": "CONTINUE", "disposition": "INLINE"}
    command = databricks_argv("api", "post", "/api/2.0/sql/statements", "--json",
                              json.dumps(request), "-p", "edp-lab", "-o", "json")
    result = subprocess.run(command, capture_output=True, text=True, timeout=180,
                            check=False)
    if result.returncode:
        raise Denied("STAGE_LIVE_QUERY_FAILED")
    response = json.loads(result.stdout)
    started = time.monotonic()
    while response.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        if time.monotonic() - started > 900:
            raise Denied("STAGE_LIVE_QUERY_LIMIT")
        time.sleep(5)
        result = subprocess.run(databricks_argv(
            "api", "get", "/api/2.0/sql/statements/" + response["statement_id"],
            "-p", "edp-lab", "-o", "json"), capture_output=True, text=True,
            timeout=180, check=False)
        if result.returncode:
            raise Denied("STAGE_LIVE_QUERY_READBACK_FAILED")
        response = json.loads(result.stdout)
    rows = response.get("result", {}).get("data_array", [])
    if (response.get("status", {}).get("state") != "SUCCEEDED"
            or response.get("manifest", {}).get("truncated")
            or (expected_rows is not None and len(rows) != expected_rows)):
        raise Denied("STAGE_LIVE_QUERY_NOT_VERIFIED")
    return response


def attest_stage(root: Path, queue_path: Path, grant_path: Path, state_path: Path,
                 stage: str, trust: Path, key: Path) -> dict:
    root = root.resolve()
    if stage not in SQL_TASK or any(p.resolve().is_relative_to(root)
                                    for p in (trust, key)):
        raise Denied("STAGE_VERIFIER_OUT_OF_SCOPE")
    queue_path = queue_path.resolve(strict=True)
    if not queue_path.is_relative_to(root):
        raise Denied("QUEUE_OUTSIDE_REPO")
    queue = json.loads(queue_path.read_bytes())
    if queue.get("cohort") != "C2000":
        raise Denied("STAGE_COHORT_OUT_OF_SCOPE")
    grant = load_grant(root, grant_path, trust)
    state = json.loads(state_path.read_bytes())
    if (grant["authority"] != "policy-broker-v1"
            or state["queue_sha256"] != file_digest(queue_path)
            or grant["contracts"]["queue"]["sha256"] != state["queue_sha256"]
            or state["grant_id"] != grant["grant_id"]):
        raise Denied("STAGE_CHECKPOINT_MISMATCH")
    tasks = {task["id"]: task for task in queue["tasks"]}
    gate = tasks[stage]
    sql_task = tasks[SQL_TASK[stage]]
    if (gate["kind"] != "stage_gate" or gate["stage"] != stage
            or state["tasks"][SQL_TASK[stage]]["status"] != "COMPLETE"
            or state["tasks"][stage]["status"] != "PLANNED"):
        raise Denied("STAGE_DEPENDENCY_INCOMPLETE")
    proof = verified_document(root, Path(sql_task["external_receipt"]), trust)
    exact_request = task_request(root, queue, queue_path, sql_task, grant_path)
    if (proof.get("schema") != "EDP_EXTERNAL_OPERATION_RECEIPT_V1"
            or proof.get("authority") != "protected-verifier-v1"
            or proof.get("operation_id") != sql_task["operation_id"]
            or proof.get("request_sha256") != digest(canonical(exact_request))
            or proof.get("table") != sql_task["databricks_table"]
            or proof.get("status") != "VERIFIED" or proof.get("live_readback") is not True):
        raise Denied("STAGE_SQL_RECEIPT_INVALID")
    candidate = json.loads((root / queue["contracts"]["candidate"]["path"]).read_bytes())
    new = json.loads((root / "runs/day5/p6_candidate_v1/N500.bindings.json").read_bytes())
    if (file_digest(root / queue["contracts"]["candidate"]["path"])
            != grant["contracts"]["candidate"]["sha256"]
            or candidate["outputs_sha256"]["N500.bindings.json"]
            != file_digest(root / "runs/day5/p6_candidate_v1/N500.bindings.json")
            or len(new) != 500):
        raise Denied("STAGE_CANDIDATE_CHANGED")
    table = sql_task["databricks_table"]
    if stage in {"P7", "P8"}:
        sql = (f"SELECT count(*) AS records, count(DISTINCT source_identity) AS sources, "
               f"count_if(field_count <> 5) AS invalid_width FROM {table} VERSION AS OF 0")
        expected = ([new[0]["data_records"], 1, 0] if stage == "P7" else
                    [sum(row["data_records"] for row in new), 500, 0])
    else:
        sql = (f"SELECT count(*) AS records, count(DISTINCT source_instance_id) AS sources, "
               f"count_if(occurrence_class = 'NEW_N500_SEC_RECORD') AS new_records "
               f"FROM {table}")
        expected = [None, 2000, sum(row["data_records"] for row in new)]
    observed = _query(sql)
    values = [int(value) for value in observed["result"]["data_array"][0]]
    if (len(values) != 3 or any(want is not None and got != want
                                for got, want in zip(values, expected, strict=True))):
        raise Denied("STAGE_LIVE_COUNTS_MISMATCH")
    receipt = Path(gate["receipt"])
    if receipt.parent.resolve() != (trust.parent / "receipts").resolve():
        raise Denied("RECEIPT_OUTSIDE_PROTECTED_STORE")
    document = {"schema": "EDP_STAGE_RECEIPT_V1",
                "authority": "protected-verifier-v1", "stage": stage,
                "cohort": "C2000", "output": queue["output"],
                "queue_sha256": file_digest(queue_path), "status": "VERIFIED",
                "independent_verifier": True, "execution_kind": "LIVE",
                "live_statement_id": observed["statement_id"],
                "observed_counts": values, "evidence_sha256": digest(canonical(observed))}
    _sign(document, key, receipt)
    return {"status": "VERIFIED", "receipt_sha256": file_digest(receipt),
            "stage": stage, "observed_counts": values}
