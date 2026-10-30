"""Render exact V3 target DDL/insert-only SQL without executing it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from edp_lab.vault.v3_ddl import plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_bytes())
    result = plan(request["new_v3_table_allowlist"])
    if args.output.exists() and json.loads(args.output.read_bytes()) != result:
        raise ValueError("V3_DDL_CHANGED")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"table_count": len(result["tables"]), "write_kind": "INSERT_ONLY"}))


if __name__ == "__main__":
    main()
