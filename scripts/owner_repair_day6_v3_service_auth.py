"""Owner terminal: switch the existing Day 6 V3 daemon to protected M2M CLI.

This updates only three installed Python modules and the reviewed commit pin.
It preserves every signed V0A/attempt receipt, grant, ledger and Delta table.
The daemon's fixed probe verifies its own authentication and admission reads.
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
FILES = (
    "scripts/owner_setup_day6_vault_0a.py",
    "scripts/owner_day6_v3_one_shot.py",
    "src/edp_lab/vault/v3_service.py",
)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(reason)


def git(*args: str) -> bytes:
    return subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT), *args],
        capture_output=True, check=True, timeout=60).stdout


def request(action: str) -> dict:
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(120)
        client.connect(str(SOCKET))
        client.sendall((json.dumps({"action": action}) + "\n").encode())
        client.shutdown(socket.SHUT_WR)
        return json.loads(client.recv(8192))


def repair(expected_commit: str) -> dict:
    require(os.geteuid() == 0, "OWNER_ROOT_REQUIRED")
    require(git("rev-parse", "HEAD").decode().strip() == expected_commit,
            "REVIEWED_COMMIT_CHANGED")
    require(not git("status", "--porcelain", "--untracked-files=no").strip(),
            "TRACKED_WORKTREE_CHANGED")
    old_commit = COMMIT.read_text().strip()
    require(len(old_commit) == 40 and old_commit != expected_commit,
            "INSTALLED_COMMIT_INVALID_OR_ALREADY_UPDATED")
    changed = set(git("diff", "--name-only", old_commit, expected_commit).decode().splitlines())
    require(set(FILES) <= changed <= set(FILES) | {
        "scripts/day6_v3_service_client.py",
        "scripts/owner_repair_day6_v3_service_auth.py",
        "tests/vault/test_owner_admin_cli.py",
        "tests/vault/test_day6_v3_service.py",
    }, "UNRELATED_RUNTIME_CHANGE")
    require(request("status").get("status") == "READY_FOR_DISTINCT_ATTEMPT",
            "V3_CHECKPOINT_CHANGED")
    for name in FILES:
        path = RUNTIME / name
        require(path.is_file() and path.stat().st_uid == 0,
                "INSTALLED_RUNTIME_FILE_MISSING:" + name)
        require(path.read_bytes() == git("show", f"{old_commit}:{name}"),
                "INSTALLED_RUNTIME_FILE_CHANGED:" + name)
    config = BASE / "private/databrickscfg"
    require(config.is_file() and not config.is_symlink()
            and config.stat().st_uid == 0 and not config.stat().st_mode & 0o077,
            "PROTECTED_M2M_CONFIG_REQUIRED")
    # No installed receipt or ledger is edited. File replacement is atomic.
    for name in FILES:
        path = RUNTIME / name
        temporary = path.with_name(path.name + ".auth-repair-tmp")
        require(not temporary.exists(), "RUNTIME_UPDATE_ALREADY_PARTIAL")
        temporary.write_bytes((ROOT / name).read_bytes())
        temporary.chmod(0o644)
        temporary.replace(path)
    temporary = COMMIT.with_name(COMMIT.name + ".auth-repair-tmp")
    require(not temporary.exists(), "COMMIT_UPDATE_ALREADY_PARTIAL")
    temporary.write_text(expected_commit + "\n")
    temporary.chmod(0o644)
    temporary.replace(COMMIT)
    subprocess.run(["/bin/launchctl", "kickstart", "-k", LABEL],
                   check=True, capture_output=True, timeout=30)
    last = None
    for _ in range(30):
        try:
            last = request("probe")
            if last.get("status") != "BLOCKED":
                break
        except (OSError, ValueError):
            pass
        time.sleep(1)
    require(last is not None, "V3_DAEMON_RESTART_UNVERIFIED")
    return last


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    args = parser.parse_args()
    print(json.dumps(repair(args.expected_commit), sort_keys=True))


if __name__ == "__main__":
    main()
