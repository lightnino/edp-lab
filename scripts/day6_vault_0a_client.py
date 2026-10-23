"""Agent-facing client for the separately owner-installed Vault Dev 0A service."""
from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

from edp_lab.operating.authority import Denied, load_grant

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/private/var/db/edp-lab-day6-vault")


def _call(path: Path, request: dict, *, timeout: int = 600) -> dict:
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
    raise Denied("C1500_PROTOTYPE_EXECUTION_PAUSED_PENDING_REUSABLE_VAULT_0A")
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("grant", "execute"))
    args = parser.parse_args()
    grant_response = _call(BASE / "broker.sock", {"action": "grant"})
    if grant_response.get("status") != "ISSUED":
        raise Denied("VAULT_GRANT_NOT_ISSUED")
    path = Path(grant_response["grant_path"])
    grant = load_grant(ROOT, path, BASE / "trust")
    if (grant.get("cohort") != "C1500"
            or grant.get("authority") != "policy-broker-v1"):
        raise Denied("VAULT_GRANT_NOT_EXACT")
    if args.command == "grant":
        print(json.dumps({"status": "VAULT_GRANT_VERIFIED", "grant_path": str(path),
                          "grant_id": grant["grant_id"]}, sort_keys=True))
    else:
        print(json.dumps(_call(BASE / "executor.sock",
                               {"action": "execute", "grant_path": str(path)},
                               timeout=3700),
                         sort_keys=True))


if __name__ == "__main__":
    main()
