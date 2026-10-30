"""Owner-only code repair for a Workspace-path/UC-table audit routing bug.

The installed 6c4324b V3 service already passed 12/13 read-only capability
checks, with attempt 1 ready. No change to credentials, trust, receipts, grants,
ledgers, Jobs, Databricks objects, or the standing policy is permitted here.
Only the fixed v3_service module and exact installed code pin are replaced.
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
PIN = BASE / "trust/day6-v3-installed-commit.txt"
SOCKET = BASE / "day6-v3.sock"
LABEL = "system/org.edp-lab.day6-v3-standing"
OLD_SHA = "6c4324b08ea8393525fd41604029e9b5c1d2f250"
MODULE = "src/edp_lab/vault/v3_service.py"
ALLOWED = {
    MODULE,
    "scripts/owner_repair_day6_v3_workspace_audit.py",
    "tests/vault/test_v3_unattended_role_boundaries.py",
}


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)


def git(*argv: str) -> bytes:
    return subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={ROOT}",
         "-C", str(ROOT), *argv],
        check=True, capture_output=True, timeout=60,
    ).stdout


def request(action: str) -> dict:
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(600 if action == "audit" else 120)
        client.connect(str(SOCKET))
        client.sendall((json.dumps({"action": action}) + "\n").encode())
        client.shutdown(socket.SHUT_WR)
        result = bytearray()
        while data := client.recv(8192):
            result.extend(data)
            require(len(result) <= 100_000, "SERVICE_RESPONSE_TOO_LARGE")
    return json.loads(result)


def repair(expected_commit: str) -> dict:
    require(os.geteuid() == 0, "OWNER_ROOT_REQUIRED")
    require(len(expected_commit) == 40
            and git("rev-parse", "HEAD").decode().strip() == expected_commit,
            "REVIEWED_COMMIT_CHANGED")
    require(not git("status", "--porcelain", "--untracked-files=no").strip(),
            "TRACKED_WORKTREE_CHANGED")
    require(PIN.is_file() and not PIN.is_symlink()
            and PIN.stat().st_uid == 0 and not PIN.stat().st_mode & 0o022
            and PIN.read_text().strip() == OLD_SHA,
            "NOT_EXPECTED_INSTALLED_COMMIT")
    changed = set(git("diff", "--name-only", OLD_SHA, expected_commit)
                  .decode().splitlines())
    require(MODULE in changed and changed <= ALLOWED,
            "UNRELATED_RUNTIME_CHANGE")
    installed = RUNTIME / MODULE
    require(installed.is_file() and not installed.is_symlink()
            and installed.stat().st_uid == 0
            and installed.read_bytes() == git("show", f"{OLD_SHA}:{MODULE}"),
            "INSTALLED_MODULE_CHANGED")
    config = BASE / "private/databrickscfg"
    require(config.is_file() and not config.is_symlink()
            and config.stat().st_uid == 0 and not config.stat().st_mode & 0o077,
            "PROTECTED_M2M_CONFIG_CHANGED")

    before = request("status")
    require(before.get("status") == "READY_FOR_DISTINCT_ATTEMPT"
            and before.get("next_attempt") == 1,
            "V3_CHECKPOINT_CHANGED")

    # Do not invoke old probe as an installation prerequisite. The pinned
    # module bytes, protected commit, checkpoint, and review define the scope.
    module_tmp = installed.with_name(installed.name + ".workspace-audit-tmp")
    pin_tmp = PIN.with_name(PIN.name + ".workspace-audit-tmp")
    require(not module_tmp.exists() and not pin_tmp.exists(),
            "PARTIAL_WORKSPACE_AUDIT_REPAIR_DETECTED")
    module_tmp.write_bytes((ROOT / MODULE).read_bytes())
    module_tmp.chmod(0o644)
    module_tmp.replace(installed)
    pin_tmp.write_text(expected_commit + "\n")
    pin_tmp.chmod(0o644)
    pin_tmp.replace(PIN)
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

    return {"status": result.get("status"), "installed_commit": expected_commit,
            "attempt_number": 1, "checks": result.get("checks", {}),
            "checks_passed": result.get("checks_passed"),
            "checks_total": result.get("checks_total"),
            "write_capabilities": "NOT_TESTED_NO_MUTATION",
            "standing_sha256": after["standing_sha256"],
            "e2e_sha256": after["e2e_sha256"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    args = parser.parse_args()
    print(json.dumps(repair(args.expected_commit), sort_keys=True))


if __name__ == "__main__":
    main()
