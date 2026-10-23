"""Root-owned fixed-plan Vault Dev executor with durable no-replay ledger."""
from __future__ import annotations

import argparse
import grp
import json
import os
import socketserver
import subprocess
import time
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    authorize,
    file_digest,
    load_grant,
    verified_document,
)
from edp_lab.operating.boundaries import _reserve
from edp_lab.vault.load_plan import NAMESPACE, TABLES
from edp_lab.vault.protected_sql import _cli, scalar, statement
from edp_lab.vault.standing_authority import signed_policy, validate_policy

EXPECTED_COUNTS = (20, 24, 76, 127, 127, 127, 127, 254, 6)


def _save(path: Path, document: dict) -> None:
    staged = path.with_suffix(".next")
    fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(document, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(staged, path)


def _request(root: Path, base: Path, grant_path: Path, grant: dict,
             stage: dict, index: int) -> dict:
    contracts = {name: {"version": grant["contracts"][name]["version"], "path": path}
                 for name, path in (
                     ("parser", "scripts/day6_vault_contract_v1.py"),
                     ("model", "src/edp_lab/vault/prototype.py"),
                     ("rule", "docs/vault_load_contract_v1.md"),
                 )}
    return {"operation": "databricks_write", "cohort": "C1500",
            "operation_id": f"vault-c1500-{index:02d}-{stage['id']}",
            "grant_path": str(grant_path), "databricks_table": stage["table"],
            "output": NAMESPACE, "contracts": contracts,
            "budget": {"operations": 1}}


def _tables_ready(root: Path, base: Path, policy: dict) -> None:
    warehouse = _cli(root, base, "warehouses", "get", policy["warehouse_id"])
    if (warehouse.get("name") != policy["warehouse_name"]
            or warehouse.get("cluster_size") != "2X-Small"
            or warehouse.get("max_num_clusters") != 1):
        raise Denied("VAULT_DEDICATED_COMPUTE_CHANGED")
    for name in TABLES:
        full = f"{NAMESPACE}.{name}"
        value, _ = scalar(root, base,
                          f"SELECT COUNT(*) FROM {full} WHERE 1=0")
        if value != "0":
            raise Denied("VAULT_TABLE_NOT_READABLE")


def execute(root: Path, base: Path, grant_path: Path) -> dict:
    """Run only the signed, regenerated plan. Uncertain writes remain isolated."""
    root, base = root.resolve(strict=True), base.resolve(strict=True)
    if base.is_relative_to(root) or grant_path.resolve().parent != (base / "grants").resolve():
        raise Denied("VAULT_EXECUTION_BOUNDARY_INVALID")
    policy = signed_policy(root, base / "trust/policy.signed.json", base / "trust")
    sample = root / "runs/day6-vault-prototype/sample-manifest.json"
    projected = root / "runs/day6-vault-prototype/projected-manifest.json"
    plan_path = root / "runs/day6-vault-prototype/load-plan.json"
    _selected, plan = validate_policy(root, policy, sample, projected, plan_path)
    grant = load_grant(root, grant_path, base / "trust")
    if (grant.get("authority") != "policy-broker-v1"
            or grant.get("cohort") != "C1500"
            or grant["contracts"]["queue"]["sha256"] != file_digest(plan_path)
            or set(grant["databricks_tables"]) != {f"{NAMESPACE}.{name}" for name in TABLES}):
        raise Denied("VAULT_GRANT_SCOPE_MISMATCH")
    completed = base / "receipts/vault-c1500-final-v1.signed.json"
    if completed.exists():
        final = verified_document(root, completed, base / "trust")
        if (final.get("schema") != "EDP_VAULT_PROTOTYPE_READBACK_RECEIPT_V1"
                or final.get("status") != "VERIFIED"
                or final.get("plan_file_sha256") != file_digest(plan_path)
                or final.get("namespace") != NAMESPACE):
            raise Denied("VAULT_FINAL_RECEIPT_INVALID")
        return {"status": "VAULT_PROTOTYPE_READBACK_VERIFIED",
                "receipt_path": str(completed),
                "receipt_sha256": file_digest(completed)}
    _tables_ready(root, base, policy)
    ledger = base / "ledger"
    ledger.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    for index, (stage, expected) in enumerate(zip(plan["stages"], EXPECTED_COUNTS, strict=True), 1):
        if time.monotonic() - start > policy["max_runtime_seconds"]:
            raise Denied("VAULT_RUNTIME_CAP_EXHAUSTED")
        request = _request(root, base, grant_path, grant, stage, index)
        authorize(grant, request, root=root, used={"operations": index - 1})
        record = ledger / (request["operation_id"] + ".json")
        if record.exists():
            old = json.loads(record.read_bytes())
            if old.get("status") != "STAGE_READBACK_VERIFIED" or old.get(
                    "statement_sha256") != stage["statement_sha256"]:
                raise Denied("VAULT_UNCERTAIN_STAGE_REQUIRES_DISPOSITION")
            count, _ = scalar(root, base, f"SELECT COUNT(*) FROM {stage['table']}")
            allowed_counts = {127, 254} if stage["id"] == "event-admitted" else {expected}
            if int(count) not in allowed_counts:
                raise Denied("VAULT_RESUME_COUNT_CHANGED")
            continue
        mismatches, precheck_id = scalar(root, base, stage["precheck"])
        if mismatches != "0":
            raise Denied("VAULT_IMMUTABLE_COMPONENT_DRIFT")
        _reserve(ledger, request["operation_id"], request)
        result = statement(root, base, stage["statement"])
        # Successful DML submission is not itself persistence evidence.
        count, readback_id = scalar(root, base,
                                    f"SELECT COUNT(*) FROM {stage['table']}")
        if int(count) != expected:
            raise Denied("VAULT_STAGE_READBACK_COUNT_MISMATCH")
        _save(record, {"status": "STAGE_READBACK_VERIFIED",
                       "plan_sha256": file_digest(plan_path),
                       "statement_sha256": stage["statement_sha256"],
                       "precheck_statement_id": precheck_id,
                       "write_statement_id": result["statement_id"],
                       "readback_statement_id": readback_id,
                       "count": expected})
    # A different module and signing key performs the final exact-row readback.
    response = subprocess.run(
        [str(base / "python/bin/python3.12"), "-m",
         "edp_lab.vault.protected_readback", str(root), str(base), str(grant_path)],
        env={**os.environ, "PYTHONPATH": str(base / "runtime/src")},
        capture_output=True, text=True, timeout=policy["max_runtime_seconds"], check=False)
    if response.returncode:
        raise Denied("VAULT_INDEPENDENT_READBACK_FAILED")
    return json.loads(response.stdout)


def serve(root: Path, base: Path) -> None:
    root, base = root.resolve(strict=True), base.resolve(strict=True)
    if base.is_relative_to(root):
        raise Denied("VAULT_EXECUTOR_NOT_PROTECTED")
    socket = base / "executor.sock"
    if socket.exists():
        raise Denied("VAULT_EXECUTOR_SOCKET_ALREADY_EXISTS")

    class Handler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            try:
                query = json.loads(self.rfile.readline(4096))
                if set(query) != {"action", "grant_path"} or query["action"] != "execute":
                    raise Denied("VAULT_EXECUTOR_ACTION_OUT_OF_SCOPE")
                response = execute(root, base, Path(query["grant_path"]))
            except (Denied, OSError, ValueError, KeyError, TypeError) as exc:
                response = {"status": "DENIED", "reason": str(exc)}
            self.wfile.write((json.dumps(response, sort_keys=True) + "\n").encode())

    with socketserver.UnixStreamServer(str(socket), Handler) as server:
        os.chown(socket, 0, grp.getgrnam("staff").gr_gid)
        os.chmod(socket, 0o660)
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("base", type=Path)
    args = parser.parse_args()
    serve(args.root, args.base)


if __name__ == "__main__":
    main()
