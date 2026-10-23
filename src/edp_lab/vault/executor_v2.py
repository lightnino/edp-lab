"""Protected, cohort-neutral Vault executor with no uncertain-write retry."""
from __future__ import annotations

import argparse
import fcntl
import grp
import hashlib
import json
import os
import socketserver
import subprocess
from pathlib import Path

from edp_lab.operating.authority import Denied, file_digest
from edp_lab.operating.boundaries import _reserve
from edp_lab.vault.broker_v2 import (
    _eligibility,
    _prepare_socket,
    _protected,
    _signed,
    load_run_grant,
)
from edp_lab.vault.protected_sql import _cli, scalar, statement
from edp_lab.vault.standing_v2 import NAMESPACE, TABLES, authorize_stage, validate_standing_policy


def _budget(grant: dict) -> dict:
    return {"run_sha256": grant["run_sha256"],
            "max_statements": grant["max_statements"],
            "max_runtime_seconds": grant["max_runtime_seconds"]}


def _save(path: Path, document: dict) -> None:
    staged = path.with_suffix(".next")
    fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(document, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(staged, path)


def _ready(root: Path, base: Path, policy: dict) -> None:
    warehouse = _cli(root, base, "warehouses", "get", policy["warehouse_id"])
    if (warehouse.get("name") != policy["warehouse_name"]
            or warehouse.get("cluster_size") != policy["warehouse_max_cluster_size"]
            or warehouse.get("max_num_clusters") != policy["warehouse_max_clusters"]):
        raise Denied("VAULT_DEDICATED_COMPUTE_CHANGED")


def _audit_sql(plan: dict, grant: dict) -> tuple[str, str, str, int]:
    """Generate a run-specific audit append from the pinned occurrence manifest."""
    source = plan.get("expected_tables", {}).get("r_source_occurrence", {})
    rows = source.get("rows")
    if (not isinstance(rows, list) or len(rows) != grant["data_occurrences"]
            or any(not isinstance(row, list) or not isinstance(row[0], str)
                   or len(row[0]) != 64 for row in rows)):
        raise Denied("VAULT_AUDIT_OCCURRENCE_MANIFEST_INVALID")
    occurrences = [row[0] for row in rows]
    if len(set(occurrences)) != len(occurrences):
        raise Denied("VAULT_AUDIT_OCCURRENCE_DUPLICATE")
    def literal(value: str) -> str:
        return "decode(unhex('" + value.encode().hex() + "'), 'UTF-8')"

    values = ", ".join("(" + literal(hk) + ", " + literal(grant["run_id"]) + ")"
                       for hk in occurrences)
    source_sql = ("SELECT c1 AS occurrence_hk, c2 AS execution_id FROM VALUES "
                  + values + " AS v(c1,c2)")
    table = f"{NAMESPACE}.r_load_event"
    join = "t.occurrence_hk=s.occurrence_hk AND t.execution_id=s.execution_id"
    precheck = (f"SELECT COUNT(*) AS mismatches FROM {table} AS t\n"
                f"JOIN ({source_sql}) AS s ON {join}\n"
                f"WHERE (NOT (t.event_kind <=> {literal(grant['event_kind'])}) "
                f"OR NOT (t.input_manifest_sha256 <=> "
                f"{literal(grant['input_manifest_sha256'])}))")
    merge = (f"MERGE INTO {table} AS t\nUSING ({source_sql}) AS s\nON {join}\n"
             "WHEN NOT MATCHED THEN INSERT "
             "(occurrence_hk, execution_id, load_dts, event_kind, statement_id, "
             "input_manifest_sha256) VALUES "
             f"(s.occurrence_hk, s.execution_id, current_timestamp(), "
             f"{literal(grant['event_kind'])}, NULL, "
             f"{literal(grant['input_manifest_sha256'])})")
    where = ("execution_id=" + literal(grant["run_id"])
             + " AND occurrence_hk IN (" + ", ".join(literal(hk) for hk in occurrences) + ")")
    readback = f"SELECT COUNT(*) FROM {table} WHERE {where}"
    return precheck, merge, readback, len(occurrences)


def execute(root: Path, base: Path, grant_path: Path) -> dict:
    """Serialize all Vault Dev writes at the protected namespace boundary."""
    _protected(root, base)
    lock = base / "ledger/namespace.lock"
    fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Denied("VAULT_NAMESPACE_WRITE_IN_PROGRESS") from exc
        return _execute_locked(root, base, grant_path)
    finally:
        os.close(fd)


def _execute_locked(root: Path, base: Path, grant_path: Path) -> dict:
    policy = _signed(root, base, "policy.signed.json")
    validate_standing_policy(policy, root=root)
    grant = load_run_grant(root, base, grant_path)
    if (grant["namespace"] != NAMESPACE or grant["tables"] != list(TABLES)
            or grant["revocation_id"] != policy["policy_id"]):
        raise Denied("VAULT_GRANT_SCOPE_CHANGED")
    receipt = _eligibility(root, base, grant["cohort_id"], policy)
    if (grant["workload_kind"] != receipt["workload_kind"]
            or grant["contract"] != receipt["contract"]
            or grant["mapping_rule"] != receipt["mapping_rule"]
            or grant["sources"] != receipt["sources"]
            or grant["input_manifest_sha256"] != receipt["input_manifest_sha256"]
            or grant["load_plan_sha256"] != receipt["load_plan_sha256"]):
        raise Denied("VAULT_COHORT_GRANT_DRIFT")
    plan_path = root / receipt["load_plan"]["path"]
    if file_digest(plan_path) != grant["load_plan_sha256"]:
        raise Denied("VAULT_LOAD_PLAN_CHANGED")
    plan = json.loads(plan_path.read_bytes())
    if plan.get("schema") != "EDP_VAULT_LOAD_PLAN_V2":
        raise Denied("VAULT_LOAD_PLAN_SCHEMA_INVALID")
    _ready(root, base, policy)
    run_ledger = base / "ledger" / grant["run_sha256"]
    run_ledger.mkdir(mode=0o700, exist_ok=True)
    budget = _budget(grant)
    for index, stage in enumerate(plan["stages"], 1):
        operation_id = f"{grant['run_sha256']}-{index:03d}"
        request = {**stage, "operation_id": operation_id,
                   "load_plan_sha256": grant["load_plan_sha256"]}
        authorize_stage(grant, request, used_statements=index - 1,
                        uncertain_operation_ids=set())
        record = run_ledger / (operation_id + ".json")
        if record.exists():
            prior = json.loads(record.read_bytes())
            if (prior.get("status") != "STAGE_READBACK_VERIFIED"
                    or prior.get("statement_sha256") != stage["statement_sha256"]):
                raise Denied("VAULT_UNCERTAIN_WRITE_REPLAY_DENIED")
            count, _ = scalar(root, base, f"SELECT COUNT(*) FROM {stage['table']}",
                              budget=budget)
            if int(count) != stage["expected_rows"]:
                raise Denied("VAULT_RESUME_READBACK_CHANGED")
            continue
        precheck = stage["precheck"]
        if (not isinstance(precheck, str)
                or not precheck.startswith(
                    f"SELECT COUNT(*) AS mismatches FROM {stage['table']} AS t\n")
                or ";" in precheck):
            raise Denied("VAULT_PRECHECK_OUT_OF_SCOPE")
        mismatches, precheck_id = scalar(root, base, precheck, budget=budget)
        if mismatches != "0":
            raise Denied("VAULT_IMMUTABLE_COMPONENT_DRIFT")
        _reserve(run_ledger, operation_id, request)
        write = statement(root, base, stage["statement"], budget=budget)
        count, readback_id = scalar(root, base,
                                    f"SELECT COUNT(*) FROM {stage['table']}", budget=budget)
        if int(count) != stage["expected_rows"]:
            raise Denied("VAULT_STAGE_READBACK_COUNT_MISMATCH")
        _save(record, {"status": "STAGE_READBACK_VERIFIED",
                       "statement_sha256": stage["statement_sha256"],
                       "precheck_statement_id": precheck_id,
                       "write_statement_id": write["statement_id"],
                       "readback_statement_id": readback_id,
                       "count": int(count)})
    precheck, merge, audit_readback, expected_audit = _audit_sql(plan, grant)
    audit_id = grant["run_sha256"] + "-audit"
    audit_record = run_ledger / (audit_id + ".json")
    if audit_record.exists():
        previous = json.loads(audit_record.read_bytes())
        if (previous.get("status") != "STAGE_READBACK_VERIFIED"
                or previous.get("statement_sha256") != hashlib.sha256(merge.encode()).hexdigest()):
            raise Denied("VAULT_UNCERTAIN_AUDIT_REPLAY_DENIED")
        count, _ = scalar(root, base, audit_readback, budget=budget)
        if int(count) != expected_audit:
            raise Denied("VAULT_AUDIT_REPLAY_COUNT_CHANGED")
    else:
        mismatches, precheck_id = scalar(root, base, precheck, budget=budget)
        if mismatches != "0":
            raise Denied("VAULT_AUDIT_PAYLOAD_DRIFT")
        _reserve(run_ledger, audit_id, {"run_sha256": grant["run_sha256"],
                                        "statement_sha256": hashlib.sha256(merge.encode()).hexdigest()})
        write = statement(root, base, merge, budget=budget)
        count, readback_id = scalar(root, base, audit_readback, budget=budget)
        if int(count) != expected_audit:
            raise Denied("VAULT_AUDIT_READBACK_COUNT_MISMATCH")
        _save(audit_record, {"status": "STAGE_READBACK_VERIFIED",
                             "statement_sha256": hashlib.sha256(merge.encode()).hexdigest(),
                             "precheck_statement_id": precheck_id,
                             "write_statement_id": write["statement_id"],
                             "readback_statement_id": readback_id,
                             "count": int(count)})
    response = subprocess.run(
        [str(base / "python/bin/python3.12"), "-m", "edp_lab.vault.verifier_v2",
         str(root), str(base), str(grant_path)],
        env={**os.environ, "PYTHONPATH": str(base / "runtime/src")},
        capture_output=True, text=True, timeout=grant["max_runtime_seconds"], check=False)
    if response.returncode:
        raise Denied("VAULT_INDEPENDENT_READBACK_FAILED")
    return json.loads(response.stdout)


def serve(root: Path, base: Path) -> None:
    _protected(root, base)
    socket_path = base / "executor.sock"
    _prepare_socket(socket_path)

    class Handler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            try:
                request = json.loads(self.rfile.readline(4096))
                if set(request) != {"action", "grant_path"} or request["action"] != "execute":
                    raise Denied("VAULT_EXECUTOR_ACTION_DENIED")
                result = execute(root, base, Path(request["grant_path"]))
            except (Denied, OSError, KeyError, TypeError, ValueError) as exc:
                result = {"status": "DENIED", "reason": str(exc)}
            self.wfile.write((json.dumps(result, sort_keys=True) + "\n").encode())

    with socketserver.UnixStreamServer(str(socket_path), Handler) as server:
        os.chown(socket_path, 0, grp.getgrnam("staff").gr_gid)
        os.chmod(socket_path, 0o660)
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("base", type=Path)
    args = parser.parse_args()
    serve(args.root, args.base)


if __name__ == "__main__":
    main()
