"""Owner-only repair for the *partially installed* Day 6 authentication change.

Prior owner_repair_day6_v3_service_auth.py completed its root file replacement
and restart but its probe failed due to a local socket variable shadowing the
probe function. This one-time successor changes ONLY the root-owned service
module and its installed commit pin. Never reinstall V0A or resubmit V3 here.
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
OLD_SHA = "17e88890166b46cbb9d562eef176038dd424f92a"
SERVICE = "src/edp_lab/vault/v3_service.py"
ALLOWED = {
    SERVICE,
    "scripts/owner_repair_day6_v3_probe_shadow.py",
    "tests/vault/test_day6_v3_probe_shadow.py",
}


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(reason)


def git(*args: str) -> bytes:
    return subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={ROOT}",
         "-C", str(ROOT), *args],
        capture_output=True, check=True, timeout=60,
    ).stdout


def request(action: str) -> dict:
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(120)
        client.connect(str(SOCKET))
        client.sendall((json.dumps({"action": action}) + "\n").encode())
        client.shutdown(socket.SHUT_WR)
        return json.loads(client.recv(8192))


def repair(expected_commit: str) -> dict:
    require(os.geteuid() == 0, "OWNER_ROOT_REQUIRED")
    require(len(expected_commit) == 40
            and git("rev-parse", "HEAD").decode().strip() == expected_commit,
            "REVIEWED_COMMIT_CHANGED")
    require(not git("status", "--porcelain", "--untracked-files=no").strip(),
            "TRACKED_WORKTREE_CHANGED")
    require(COMMIT.is_file() and COMMIT.stat().st_uid == 0
            and COMMIT.read_text().strip() == OLD_SHA,
            "NOT_THE_EXPECTED_PARTIALLY_INSTALLED_COMMIT")
    changed = set(git("diff", "--name-only", OLD_SHA, expected_commit).decode().splitlines())
    require(SERVICE in changed and changed <= ALLOWED,
            "UNRELATED_RUNTIME_CHANGE")
    require(git("show", f"{OLD_SHA}:{SERVICE}") != (ROOT / SERVICE).read_bytes(),
            "SERVICE_FIX_NOT_PRESENT")

    # The original command already installed the 3 M2M-enabled modules. Check
    # these exact bytes, never reinstall or repair a different checkpoint.
    for name in ("scripts/owner_setup_day6_vault_0a.py",
                 "scripts/owner_day6_v3_one_shot.py", SERVICE):
        installed = RUNTIME / name
        require(installed.is_file() and installed.stat().st_uid == 0
                and installed.read_bytes() == git("show", f"{OLD_SHA}:{name}"),
                "INSTALLED_M2M_MODULE_CHANGED:" + name)

    protected = BASE / "private/databrickscfg"
    require(protected.is_file() and not protected.is_symlink()
            and protected.stat().st_uid == 0
            and not protected.stat().st_mode & 0o077,
            "PROTECTED_M2M_CONFIG_CHANGED")
    before = request("status")
    require(before.get("status") == "READY_FOR_DISTINCT_ATTEMPT"
            and before.get("next_attempt") == 1,
            "V3_CHECKPOINT_CHANGED")
    failed_probe = request("probe")
    require(failed_probe.get("status") == "BLOCKED"
            and failed_probe.get("reason") == "'socket' object is not callable",
            "NOT_THE_EXPECTED_PROBE_SHADOW_ERROR")

    # Durable receipts, signed 0A grants, ledger, jobs and Delta remain untouched.
    target = RUNTIME / SERVICE
    temp = target.with_name(target.name + ".probe-shadow-tmp")
    require(not temp.exists(), "PARTIAL_SERVICE_REPAIR_DETECTED")
    temp.write_bytes((ROOT / SERVICE).read_bytes())
    temp.chmod(0o644)
    temp.replace(target)
    pin = COMMIT.with_name(COMMIT.name + ".probe-shadow-tmp")
    require(not pin.exists(), "PARTIAL_COMMIT_REPAIR_DETECTED")
    pin.write_text(expected_commit + "\n")
    pin.chmod(0o644)
    pin.replace(COMMIT)
    subprocess.run(["/bin/launchctl", "kickstart", "-k", LABEL],
                   check=True, capture_output=True, timeout=30)

    last = None
    for _ in range(30):
        try:
            last = request("probe")
            if last.get("status") == "V3_UNATTENDED_ADMISSION_READS_VERIFIED":
                break
        except (OSError, ValueError):
            pass
        time.sleep(1)
    require(last is not None, "V3_DAEMON_RESTART_UNVERIFIED")
    if last.get("status") != "V3_UNATTENDED_ADMISSION_READS_VERIFIED":
        return last  # A real auth/admission error; no auto-retry of root repair.
    after = request("status")
    require(after.get("status") == "READY_FOR_DISTINCT_ATTEMPT"
            and after.get("next_attempt") == 1
            and after.get("e2e_sha256") == before.get("e2e_sha256")
            and after.get("standing_sha256") == before.get("standing_sha256"),
            "V3_SIGNED_CHECKPOINT_CHANGED")
    return {"status": "V3_UNATTENDED_ADMISSION_READS_VERIFIED",
            "attempt_number": 1, "installed_commit": expected_commit,
            "standing_sha256": after["standing_sha256"],
            "e2e_sha256": after["e2e_sha256"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    args = parser.parse_args()
    print(json.dumps(repair(args.expected_commit), sort_keys=True))


if __name__ == "__main__":
    main()
