"""Owner-controlled read-only projection of protected Supervisor status."""

import argparse
import json
from pathlib import Path

from edp_lab.operating.authority import Denied
from edp_lab.operating.supervisor_health import sanitized_status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state_dir", type=Path)
    args = parser.parse_args()
    try:
        report = sanitized_status(args.state_dir)
    except (Denied, OSError):
        report = {"status": "UNAVAILABLE", "reason_code": "STATUS_READ_FAILED",
                  "replay_authorized": False}
        print(json.dumps(report, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
