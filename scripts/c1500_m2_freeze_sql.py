"""Execute one explicitly named Databricks SQL statement with retained receipts.

The SQL file is the reviewed input. A label is write-once: a changed statement or
result cannot silently replace a prior receipt. This helper never modifies RAW or
builds a data table; DDL is supplied only by the separately reviewed freeze SQL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/c1500-m2-databricks-freeze/v1"
WAREHOUSE = "589e80595c7c8cb8"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"Existing receipt differs: {path}")
        return
    path.write_bytes(data)


def cli(*args: str) -> dict:
    process = subprocess.run(
        ["databricks", *args, "-p", "edp-lab", "-o", "json"],
        capture_output=True, text=True, check=False, timeout=1800,
    )
    if process.returncode:
        raise RuntimeError(process.stderr.strip())
    return json.loads(process.stdout)


def encoded(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def run(label: str, sql_file: Path) -> dict:
    if not label.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Label must contain only letters, digits, dashes or underscores")
    sql = sql_file.read_text()
    request = {"warehouse_id": WAREHOUSE, "statement": sql,
               "wait_timeout": "50s", "on_wait_timeout": "CONTINUE",
               "disposition": "INLINE"}
    request_path = OUT / f"{label}-request.json"
    result_path = OUT / f"{label}-result.json"
    save_new(request_path, encoded(request))
    if result_path.exists():
        result = json.loads(result_path.read_bytes())
        if result.get("status", {}).get("state") != "SUCCEEDED":
            raise RuntimeError(f"Existing SQL failed: {label}: {result.get('status')}")
    else:
        result = cli("api", "post", "/api/2.0/sql/statements", "--json",
                     "@" + str(request_path))
        save_new(OUT / f"{label}-submitted.json", encoded(result))
        while result.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
            time.sleep(5)
            result = cli("api", "get", "/api/2.0/sql/statements/" + result["statement_id"])
        save_new(result_path, encoded(result))
        if result.get("status", {}).get("state") != "SUCCEEDED":
            raise RuntimeError(f"SQL failed: {label}: {result.get('status')}")
    return {"label": label, "statement_id": result["statement_id"],
            "state": result["status"]["state"], "request_sha256": sha(request_path.read_bytes()),
            "response_sha256": sha(result_path.read_bytes()),
            "rows": result.get("result", {}).get("data_array", []),
            "columns": [c["name"] for c in result.get("manifest", {}).get(
                "schema", {}).get("columns", [])]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    parser.add_argument("sql_file", type=Path)
    args = parser.parse_args()
    result = run(args.label, args.sql_file)
    print(json.dumps({k: value for k, value in result.items() if k != "rows"}
                     | {"row_count": len(result["rows"])}, sort_keys=True))


if __name__ == "__main__":
    main()
