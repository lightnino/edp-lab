"""Separate owner-authorized Acquisition RAW staging (not a Cohort task).

This is an *independent* execution surface. It deliberately requires an
owner-signed Acquisition-only V1 grant and independently signed discovery
disposition BEFORE any RAW mutation. It does not silently restage when an old
locator or receipt cannot be found. No owner credentials live in this module.
"""

import argparse
import json
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    file_digest,
    load_grant,
    protected_trust_dir,
    verified_document,
)
from edp_lab.operating.boundaries import raw_stage


def execute_acquisition_stage(
    root: Path, grant_path: Path, plan_path: Path, ledger: Path,
    *, execute: bool = False,
) -> dict:
    root = root.resolve()
    trust = protected_trust_dir(root)
    grant = load_grant(root, grant_path, trust)
    if (grant.get("authority") != "owner-acquisition-v1"
            or grant.get("cohort") != "ACQUISITION"
            or set(grant["operations"]) != {"raw_stage"}):
        raise Denied("ACQUISITION_GRANT_REQUIRED")
    plan_path = plan_path.resolve(strict=True)
    if not plan_path.is_relative_to(root):
        raise Denied("ACQUISITION_PLAN_OUTSIDE_REPO")
    pinned = grant["contracts"].get("acquisition_plan")
    if (not pinned or pinned.get("version") != "ACQUISITION_RAW_PLAN_V1"
            or pinned.get("sha256") != file_digest(plan_path)):
        raise Denied("ACQUISITION_PLAN_NOT_PINNED")
    try:
        plan = json.loads(plan_path.read_bytes())
    except (ValueError, OSError) as exc:
        raise Denied("ACQUISITION_PLAN_INVALID") from exc
    if (not isinstance(plan, dict)
            or plan.get("schema") != "EDP_ACQUISITION_RAW_PLAN_V1"
            or plan.get("decision") != "STAGE_NEW"
            or plan.get("operation_id") is None
            or plan.get("output") not in grant["outputs"]
            or plan.get("remote_path") not in grant["databricks_paths"]):
        raise Denied("ACQUISITION_PLAN_INVALID")
    source = plan.get("source")
    if (not isinstance(source, dict)
            or set(source) != {"identity", "path", "sha256", "byte_size"}
            or type(source["byte_size"]) is not int
            or source["byte_size"] < 0):
        raise Denied("ACQUISITION_SOURCE_INVALID")
    path = Path(source["path"]).resolve(strict=True)
    if (path.stat().st_size != source["byte_size"]
            or file_digest(path) != source["sha256"]
            or grant["sources"].get(source["identity"]) != source["sha256"]):
        raise Denied("ACQUISITION_SOURCE_CHANGED")
    discovery_path = Path(plan.get("discovery_receipt", ""))
    if (not discovery_path.is_absolute()
            or discovery_path.resolve().is_relative_to(root)):
        raise Denied("ACQUISITION_DISCOVERY_NOT_PROTECTED")
    discovery = verified_document(root, discovery_path, trust)
    if (discovery.get("schema") != "EDP_ACQUISITION_DISCOVERY_V1"
            or discovery.get("authority") != "protected-verifier-v1"
            or discovery.get("status") != "STAGE_NEW_AFTER_DISCOVERY"
            or discovery.get("source_identity") != source["identity"]
            or discovery.get("raw_sha256") != source["sha256"]
            or discovery.get("byte_size") != source["byte_size"]
            or discovery.get("destination") != plan["remote_path"]
            or discovery.get("discovery_scope") != "CROSS_HISTORICAL_LOCATORS"
            or discovery.get("reusable_raw_found") is not False):
        raise Denied("ACQUISITION_DISCOVERY_UNVERIFIED")
    request = {
        "operation": "raw_stage", "cohort": "ACQUISITION",
        "output": plan["output"],
        "source": {k: source[k] for k in ("identity", "path", "sha256")},
        "databricks_path": plan["remote_path"],
        "operation_id": plan["operation_id"],
        "grant_path": str(grant_path),
        "contracts": {"acquisition_plan": {
            "version": "ACQUISITION_RAW_PLAN_V1",
            "path": str(plan_path.relative_to(root))}},
        "budget": {"operations": 1},
    }
    return raw_stage(root, grant, request, ledger, execute=execute)


def main() -> int:
    parser = argparse.ArgumentParser(description="Protected Acquisition-only RAW stage")
    for name in ("root", "grant", "plan", "ledger"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        outcome = execute_acquisition_stage(
            args.root, args.grant, args.plan, args.ledger, execute=args.execute)
    except Denied as exc:
        print(json.dumps({"status": "BLOCKED", "reason_code": str(exc),
                          "write_authorized": False}, sort_keys=True))
        return 2
    print(json.dumps(outcome, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
