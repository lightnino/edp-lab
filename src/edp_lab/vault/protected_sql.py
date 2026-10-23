"""Protected Databricks SQL transport for the fixed Day 6 Vault policy.

Only the root-owned Vault service may use this transport. Agent-supplied SQL,
credentials, warehouse IDs and target names are never accepted.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from edp_lab.operating.authority import Denied


def _warehouse(base: Path) -> str:
    envelope = json.loads((base / "trust/policy.signed.json").read_bytes())
    warehouse = envelope["document"]["warehouse_id"]
    if not isinstance(warehouse, str) or len(warehouse) != 16 or not all(
            character in "0123456789abcdef" for character in warehouse):
        raise Denied("VAULT_WAREHOUSE_ID_INVALID")
    return warehouse


def _reserve_statement_budget(base: Path, budget: dict | None = None) -> None:
    envelope = json.loads((base / "trust/policy.signed.json").read_bytes())
    policy = envelope["document"]
    if policy.get("schema") == "EDP_VAULT_STANDING_POLICY_V2":
        if (not isinstance(budget, dict) or not isinstance(budget.get("run_sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", budget["run_sha256"]) is None
                or not isinstance(budget.get("max_statements"), int)
                or not 1 <= budget["max_statements"] <= policy["max_run_statements"]
                or not isinstance(budget.get("max_runtime_seconds"), int)
                or not 1 <= budget["max_runtime_seconds"] <= policy["max_run_runtime_seconds"]):
            raise Denied("VAULT_RUN_SQL_BUDGET_INVALID")
        maximum = budget["max_statements"]
        runtime = budget["max_runtime_seconds"]
        ledger = base / "ledger" / ("sql-" + budget["run_sha256"] + ".json")
        _reserve_total_sql_budget(base, policy["max_total_sql_statements"])
    else:
        maximum = policy["max_sql_statements"]
        runtime = policy["max_runtime_seconds"]
        ledger = base / "ledger/sql_statement_budget.json"
    if not isinstance(maximum, int) or maximum < 1 or maximum > 100:
        raise Denied("VAULT_SQL_BUDGET_INVALID")
    fd = os.open(ledger, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "r+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        content = stream.read()
        state = json.loads(content) if content else {"used": 0, "started_at_epoch": time.time()}
        used = state["used"]
        if time.time() - state["started_at_epoch"] > runtime:
            raise Denied("VAULT_RUNTIME_CAP_EXHAUSTED")
        if used >= maximum:
            raise Denied("VAULT_SQL_STATEMENT_CAP_EXHAUSTED")
        stream.seek(0)
        stream.truncate()
        json.dump({**state, "used": used + 1}, stream)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _reserve_total_sql_budget(base: Path, maximum: int) -> None:
    if not isinstance(maximum, int) or not 1 <= maximum <= 10_000:
        raise Denied("VAULT_TOTAL_SQL_BUDGET_INVALID")
    ledger = base / "ledger/total-sql-statements.json"
    fd = os.open(ledger, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "r+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        content = stream.read()
        used = json.loads(content)["used"] if content else 0
        if used >= maximum:
            raise Denied("VAULT_STANDING_SQL_CAP_EXHAUSTED")
        stream.seek(0)
        stream.truncate()
        json.dump({"used": used + 1}, stream)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def protected_environment(root: Path, base: Path) -> dict[str, str]:
    root, base = root.resolve(strict=True), base.resolve(strict=True)
    config = base / "private/databrickscfg"
    if (os.geteuid() != 0 or base.is_relative_to(root)
            or base.stat().st_uid != 0 or base.stat().st_mode & 0o022
            or config.stat().st_uid != 0 or config.stat().st_mode & 0o077):
        raise Denied("VAULT_PROTECTED_CREDENTIAL_BOUNDARY_REQUIRED")
    env = os.environ.copy()
    env["DATABRICKS_CONFIG_FILE"] = str(config)
    env["DATABRICKS_AUTH_STORAGE"] = "plaintext"
    return env


def _cli(root: Path, base: Path, *args: str, timeout: int = 180) -> dict:
    result = subprocess.run(["/opt/homebrew/bin/databricks", *args,
                             "-p", "vault-dev", "-o", "json"],
                            env=protected_environment(root, base),
                            capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise Denied("VAULT_DATABRICKS_REQUEST_FAILED")
    return json.loads(result.stdout)


def statement(root: Path, base: Path, sql: str, *, timeout: int = 300,
              budget: dict | None = None) -> dict:
    """Submit once, then poll read-only. Timeout/uncertainty never resubmits."""
    if not isinstance(sql, str) or not sql or len(sql.encode()) > 600_000:
        raise Denied("VAULT_SQL_SIZE_OR_EMPTY")
    _reserve_statement_budget(base, budget)
    request = {"warehouse_id": _warehouse(base), "statement": sql,
               "wait_timeout": "50s", "on_wait_timeout": "CONTINUE",
               "disposition": "INLINE"}
    with tempfile.TemporaryDirectory(dir=base / "private") as temporary:
        path = Path(temporary) / "request.json"
        path.write_text(json.dumps(request, sort_keys=True) + "\n")
        response = _cli(root, base, "api", "post", "/api/2.0/sql/statements",
                        "--json", "@" + str(path), timeout=timeout)
    statement_id = response.get("statement_id")
    if not isinstance(statement_id, str):
        raise Denied("VAULT_SQL_SUBMISSION_UNCERTAIN")
    deadline = time.monotonic() + timeout
    while response.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        if time.monotonic() >= deadline:
            raise Denied("VAULT_SQL_TERMINAL_TIMEOUT")
        time.sleep(3)
        response = _cli(root, base, "api", "get",
                        "/api/2.0/sql/statements/" + statement_id,
                        timeout=min(180, max(5, int(deadline - time.monotonic()))))
    if response.get("status", {}).get("state") != "SUCCEEDED":
        raise Denied("VAULT_SQL_FAILED")
    if response.get("manifest", {}).get("truncated"):
        raise Denied("VAULT_SQL_RESULT_TRUNCATED")
    return response


def scalar(root: Path, base: Path, sql: str, *, timeout: int = 300,
           budget: dict | None = None) -> tuple[str, str]:
    result = statement(root, base, sql, timeout=timeout, budget=budget)
    values = result.get("result", {}).get("data_array", [])
    if len(values) != 1 or len(values[0]) != 1:
        raise Denied("VAULT_SCALAR_READBACK_INVALID")
    return str(values[0][0]), result["statement_id"]
