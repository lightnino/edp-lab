"""R8 owner-terminal READ-ONLY installed CLI smoke; never a recovery installer.

Use explicitly configured protected CLI identity, only after owner review.
Prints sanitized identifiers/hashes, never original CLI stdout/stderr/credentials.
A successful smoke DOES NOT prove no remote effects or authorize resubmission.
"""

import argparse
import json

from edp_lab.operating.authority import Denied
from edp_lab.operating.cli_preflight_r8 import inspect_readonly


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", default="/opt/homebrew/bin/databricks")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--expected-user", required=True)
    parser.add_argument("--table", required=True)
    parser.add_argument("--start-ms", type=int, required=True)
    parser.add_argument("--end-ms", type=int, required=True)
    args = parser.parse_args()
    try:
        result = inspect_readonly(
            cli=args.cli, profile=args.profile, expected_user=args.expected_user,
            table=args.table, start_ms=args.start_ms, end_ms=args.end_ms)
    except (Denied, OSError, TimeoutError):
        print(json.dumps({"status": "BLOCKED_PREFLIGHT_UNVERIFIED",
                          "write_or_recovery_authorized": False}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
