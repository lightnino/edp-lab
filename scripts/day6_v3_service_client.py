"""Agent-facing, fixed-action client for the protected Day 6 V3/V9 service."""

from __future__ import annotations

import argparse
import json
import socket

SOCKET = "/private/var/db/edp-lab-day6-vault/day6-v3.sock"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("status", "probe", "audit", "evidence", "run", "reconcile", "freeze"))
    args = parser.parse_args()
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(3600 if args.action in {"reconcile", "freeze"}
                          else 600 if args.action in {"probe", "audit"} else 120)
        client.connect(SOCKET)
        client.sendall((json.dumps({"action": args.action}) + "\n").encode())
        client.shutdown(socket.SHUT_WR)
        payload = bytearray()
        while chunk := client.recv(8192):
            payload.extend(chunk)
            if len(payload) > 100000:
                raise RuntimeError("V3_SERVICE_RESPONSE_TOO_LARGE")
    print(json.dumps(json.loads(payload), sort_keys=True))


if __name__ == "__main__":
    main()
