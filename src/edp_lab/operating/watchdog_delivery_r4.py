"""Owner-scheduled R4 watchdog with an independently configured alert command.

The protected owner writes the private configuration and installs the schedule.
This process observes status only; it cannot restart or replay the Supervisor.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from edp_lab.operating.authority import Denied
from edp_lab.operating.supervisor_health import watchdog


def load_config(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise Denied("WATCHDOG_CONFIG_UNTRUSTED")
    try:
        config = json.loads(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise Denied("WATCHDOG_CONFIG_INVALID") from exc
    if not isinstance(config, dict) or set(config) != {
            "schema", "state_dir", "heartbeat_seconds", "progress_seconds",
            "alert_argv", "operator_id"}:
        raise Denied("WATCHDOG_CONFIG_INVALID")
    argv = config["alert_argv"]
    if (config["schema"] != "EDP_WATCHDOG_INSTALL_V1"
            or not isinstance(config["state_dir"], str)
            or not Path(config["state_dir"]).is_absolute()
            or type(config["heartbeat_seconds"]) is not int
            or config["heartbeat_seconds"] < 1
            or type(config["progress_seconds"]) is not int
            or config["progress_seconds"] < 1
            or not isinstance(config["operator_id"], str)
            or not config["operator_id"]
            or not isinstance(argv, list) or not argv
            or any(not isinstance(arg, str) or not arg for arg in argv)
            or not Path(argv[0]).is_absolute()):
        raise Denied("WATCHDOG_CONFIG_INVALID")
    return config


def check_and_deliver(config: dict, *, run_alert=None) -> dict:
    try:
        report = watchdog(Path(config["state_dir"]),
                          max_heartbeat_seconds=config["heartbeat_seconds"],
                          max_progress_seconds=config["progress_seconds"])
    except (Denied, OSError):
        report = {"schema": "EDP_SUPERVISOR_WATCHDOG_V1", "state": "ALERT",
                  "reason_code": "WATCHDOG_CHECK_FAILED", "replay_authorized": False}
    result = {"state": report["state"], "reason_code": report["reason_code"],
              "replay_authorized": False, "delivered": False}
    if report["state"] != "ALERT":
        return result
    payload = json.dumps(report, sort_keys=True).encode() + b"\n"
    sender = run_alert or (lambda argv, data: subprocess.run(
        argv, input=data, capture_output=True, timeout=30, check=False))
    try:
        sent = sender(config["alert_argv"], payload)
        result["delivered"] = sent.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        pass
    result["alert_payload_sha256"] = hashlib.sha256(payload).hexdigest()
    result["operator_id_sha256"] = hashlib.sha256(
        config["operator_id"].encode()).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent owner-installed R4 watchdog")
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    try:
        outcome = check_and_deliver(load_config(args.config))
    except Denied:
        outcome = {"state": "ALERT", "reason_code": "WATCHDOG_CONFIG_UNTRUSTED",
                   "replay_authorized": False, "delivered": False}
    print(json.dumps(outcome, sort_keys=True))
    return 0 if outcome["state"] == "HEALTHY" else (3 if outcome["delivered"] else 4)


if __name__ == "__main__":
    raise SystemExit(main())
