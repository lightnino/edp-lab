"""One-time Owner repair: replace only V3 service and runtime admission roles.

The previous Owner repair has already installed M2M auth and patched probe
shadowing. Its installed commit is 1c4913d. This update removes administrator-
only workspace IAM and UC introspection from service-principal execution,
replacing it with signed historical Owner evidence and scoped live readbacks.
It does not modify V0A evidence, previous grants, run reservations or Delta.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path("/Users/lightnino/Projects/edp-lab-day6-vault-prototype")
BASE = Path("/private/var/db/edp-lab-day6-vault")
RUNTIME = BASE / "runtime-v3"
COMMIT = BASE / "trust/day6-v3-installed-commit.txt"
SOCKET = BASE / "day6-v3.sock"
LABEL = "system/org.edp-lab.day6-v3-standing"
OLD_SHA = "1c4913d6d56ddad692673e9c5abdecf7ffff32d8"
FILES = (
    "scripts/owner_day6_v3_one_shot.py",
    "src/edp_lab/vault/v3_service.py",
)
UNCHANGED = ("scripts/owner_setup_day6_vault_0a.py",)
ALLOWED = set(FILES) | {
    "scripts/day6_v3_service_client.py",
    "scripts/owner_repair_day6_v3_service_roles.py",
    "tests/vault/test_v3_unattended_role_boundaries.py",
}


def require(test: bool, reason: str) -> None:
    if not test:
        raise RuntimeError(reason)


def git(*args: str) -> bytes:
    return subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={ROOT}",
         "-C", str(ROOT), *args],
        capture_output=True, check=True, timeout=60,
    ).stdout


def request(action: str) -> dict:
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(600 if action in {"probe", "audit"} else 120)
        client.connect(str(SOCKET))
        client.sendall((json.dumps({"action": action}) + "\n").encode())
        client.shutdown(socket.SHUT_WR)
        response = bytearray()
        while part := client.recv(8192):
            response.extend(part)
            require(len(response) <= 100_000, "SERVICE_RESPONSE_TOO_LARGE")
        return json.loads(response)


def repair(expected_commit: str) -> dict:
    require(os.geteuid() == 0, "OWNER_ROOT_REQUIRED")
    require(len(expected_commit) == 40
            and git("rev-parse", "HEAD").decode().strip() == expected_commit,
            "REVIEWED_COMMIT_CHANGED")
    require(not git("status", "--porcelain", "--untracked-files=no").strip(),
            "TRACKED_WORKTREE_CHANGED")
    require(COMMIT.is_file() and COMMIT.stat().st_uid == 0
            and not COMMIT.stat().st_mode & 0o022
            and COMMIT.read_text().strip() == OLD_SHA,
            "NOT_EXPECTED_PARTIALLY_INSTALLED_COMMIT")
    changed = set(git("diff", "--name-only", OLD_SHA, expected_commit).decode().splitlines())
    require(set(FILES) <= changed <= ALLOWED, "UNRELATED_RUNTIME_CHANGE")
    for name in (*FILES, *UNCHANGED):
        installed = RUNTIME / name
        require(installed.is_file() and not installed.is_symlink()
                and installed.stat().st_uid == 0
                and installed.read_bytes() == git("show", f"{OLD_SHA}:{name}"),
                "INSTALLED_M2M_MODULE_CHANGED:" + name)
    config = BASE / "private/databrickscfg"
    require(config.is_file() and not config.is_symlink()
            and config.stat().st_uid == 0
            and not config.stat().st_mode & 0o077,
            "PROTECTED_M2M_CREDENTIAL_BOUNDARY_CHANGED")

    before = request("status")
    require(before.get("status") == "READY_FOR_DISTINCT_ATTEMPT"
            and before.get("next_attempt") == 1,
            "V3_CHECKPOINT_CHANGED")
    # The original probe-shadow repair already wrote root-owned files.
    # Confirm the reported next blocker, rather than repeating that repair.
    old_probe = request("probe")
    require(old_probe.get("status") == "BLOCKED"
            and "This API is disabled for users without admin status"
            in old_probe.get("reason", ""),
            "V3_UNEXPECTED_PRE_REPAIR_PROBE_STATE")

    # No signed receipts, Data/Delta, grants or ledgers are touched.
    for name in FILES:
        dest = RUNTIME / name
        tmp = dest.with_name(dest.name + ".role-repair-tmp")
        require(not tmp.exists(), "PARTIAL_ROLE_REPAIR_DETECTED")
        tmp.write_bytes((ROOT / name).read_bytes())
        tmp.chmod(0o644)
        tmp.replace(dest)
    new_pin = COMMIT.with_name(COMMIT.name + ".role-repair-tmp")
    require(not new_pin.exists(), "PARTIAL_COMMIT_REPAIR_DETECTED")
    new_pin.write_text(expected_commit + "\n")
    new_pin.chmod(0o644)
    new_pin.replace(COMMIT)
    subprocess.run(["/bin/launchctl", "kickstart", "-k", LABEL],
                   check=True, capture_output=True, timeout=30)

    result = None
    for _ in range(30):
        try:
            result = request("audit")
            break
        except (OSError, ValueError):
            time.sleep(1)
    require(result is not None, "V3_DAEMON_RESTART_UNVERIFIED")
    after = request("status")
    require(after.get("status") == "READY_FOR_DISTINCT_ATTEMPT"
            and after.get("next_attempt") == 1
            and after.get("standing_sha256") == before.get("standing_sha256")
            and after.get("e2e_sha256") == before.get("e2e_sha256"),
            "V3_SIGNED_CHECKPOINT_CHANGED")

    return {"status": result.get("status"),
            "checks": result.get("checks", {}),
            "checks_passed": result.get("checks_passed"),
            "checks_total": result.get("checks_total"),
            "write_capabilities": "NOT_TESTED_NO_MUTATION",
            "attempt_number": 1, "installed_commit": expected_commit,
            "standing_sha256": after["standing_sha256"],
            "e2e_sha256": after["e2e_sha256"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    arguments = parser.parse_args()
    print(json.dumps(repair(arguments.expected_commit), sort_keys=True))


if __name__ == "__main__":
    main()
