"""Fixed-action client for an owner-installed reusable Vault 0A V2 service."""
from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

from edp_lab.operating.authority import Denied

BASE = Path("/private/var/db/edp-lab-day6-vault")


def _call(path: Path, request: dict, *, timeout: int) -> dict:
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(timeout)
        client.connect(str(path))
        client.sendall((json.dumps(request, sort_keys=True) + "\n").encode())
        client.shutdown(socket.SHUT_WR)
        response = json.loads(client.recv(8192))
    if response.get("status") == "DENIED":
        raise Denied(response.get("reason", "VAULT_SERVICE_DENIED"))
    return response


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("grant", "execute"))
    parser.add_argument("run_path", help="Repo-relative V2 run request JSON path")
    args = parser.parse_args()
    relative = Path(args.run_path)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".json":
        raise Denied("VAULT_RUN_PATH_INVALID")
    response = _call(BASE / "broker.sock",
                     {"action": "grant", "run_path": str(relative)}, timeout=600)
    if response.get("status") != "ISSUED":
        raise Denied("VAULT_GRANT_NOT_ISSUED")
    grant_path = Path(response["grant_path"])
    if grant_path.parent != BASE / "grants" or grant_path.suffix != ".json":
        raise Denied("VAULT_GRANT_PATH_OUT_OF_SCOPE")
    if args.command == "grant":
        print(json.dumps({"status": "VAULT_GRANT_ISSUED",
                          "grant_path": str(grant_path)}, sort_keys=True))
    else:
        result = _call(BASE / "executor.sock",
                       {"action": "execute", "grant_path": str(grant_path)},
                       timeout=3700)
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
