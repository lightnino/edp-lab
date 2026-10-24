"""R8 owner-terminal READ-ONLY installed CLI smoke; never a recovery installer.

Use explicitly configured protected CLI identity, only after owner review.
Prints sanitized identifiers/hashes, never original CLI stdout/stderr/credentials.
A successful smoke DOES NOT prove no remote effects or authorize resubmission.
"""

import argparse
import json
import re
from pathlib import Path

from edp_lab.operating.authority import Denied
from edp_lab.operating.cli_preflight_r8 import ProtectedResponseStore, inspect_readonly


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", default="/opt/homebrew/bin/databricks")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--expected-user", required=True)
    parser.add_argument("--table", required=True)
    parser.add_argument("--expected-uc-state", required=True,
                        choices=("PRESENT", "ABSENT"))
    parser.add_argument("--start-ms", type=int, required=True)
    parser.add_argument("--end-ms", type=int, required=True)
    parser.add_argument("--protected-evidence-dir", type=Path)
    args = parser.parse_args()
    try:
        store = (ProtectedResponseStore(args.protected_evidence_dir)
                 if args.protected_evidence_dir else None)
        result = inspect_readonly(
            cli=args.cli, profile=args.profile, expected_user=args.expected_user,
            table=args.table, start_ms=args.start_ms, end_ms=args.end_ms,
            expected_uc_state=args.expected_uc_state, raw_response_store=store)
    except (Denied, OSError, TimeoutError) as exc:
        code = str(exc) if isinstance(exc, Denied) else "PREFLIGHT_COMMAND_FAILED"
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", code):
            code = "PREFLIGHT_UNCLASSIFIED_FAILURE"
        print(json.dumps({"status": "BLOCKED_PREFLIGHT_UNVERIFIED",
                          "reason_code": code,
                          "write_or_recovery_authorized": False}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
