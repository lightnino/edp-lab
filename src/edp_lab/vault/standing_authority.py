"""Isolated Day 6 Vault 0A policy checks and broker grant issuance.

Only an owner-installed, protected service may call ``issue`` with its private
broker key. Repository files and this module are proposals until installed.
"""
from __future__ import annotations

import argparse
import base64
import grp
import json
import os
import re
import socketserver
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    canonical,
    digest,
    file_digest,
    verified_document,
)
from edp_lab.vault.load_plan import NAMESPACE, TABLES, render
from edp_lab.vault.raw_verify import verify_selected

EXPECTED_IDS = ("SRC000005", "SRC000054", "SRC000064")
EXPECTED_STAGES = (
    "load-h_filing", "load-h_concept", "load-l_fact_slot",
    "load-r_source_occurrence", "load-s_fact_assertion", "load-s_num_m2_value",
    "event-admitted", "event-replay", "synthetic-negative-quarantine",
)
PINS = {
    "contract": ("contract_path", "contract_sha256"),
    "exception": ("exception_path", "exception_sha256"),
    "cohort_freeze": ("cohort_freeze_path", "cohort_freeze_sha256"),
    "result_freeze": ("result_freeze_path", "result_freeze_sha256"),
}


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root.resolve()):
        raise Denied("PIN_OUTSIDE_REPOSITORY")
    return path


def validate_policy(root: Path, policy: dict, sample: Path, projected: Path,
                    plan_path: Path) -> tuple[dict, dict]:
    """Compare signed scope with frozen files and regenerate every SQL stage."""
    if (policy.get("schema") != "EDP_VAULT_DEV_STANDING_POLICY_V1"
            or policy.get("policy_id") != "DAY6_VAULT_DEV_C1500_ONCE_V1"
            or policy.get("namespace") != NAMESPACE
            or policy.get("tables") != list(TABLES)
            or policy.get("source_ids") != list(EXPECTED_IDS)
            or policy.get("raw_remote_prefix") != "dbfs:/Volumes/workspace/edp_lab/raw/c300-verified-v1/"
            or policy.get("warehouse_name") != "EDP Day6 Vault Dev V1"
            or policy.get("warehouse_max_cluster_size") != "2X-Small"
            or policy.get("max_data_occurrences") != 127
            or policy.get("max_synthetic_negative_rows") != 6
            or not isinstance(policy.get("max_sql_statements"), int)
            or not 1 <= policy["max_sql_statements"] <= 60
            or not isinstance(policy.get("max_runtime_seconds"), int)
            or not 1 <= policy["max_runtime_seconds"] <= 3600
            or policy.get("max_retries_per_statement") != 0
            or policy.get("allowed_sql_kinds") != ["READBACK", "MERGE_INSERT_ONLY"]
            or policy.get("denied_sql_kinds") != ["DROP", "DELETE", "UPDATE", "TRUNCATE", "REPLACE", "OVERWRITE"]
            or policy.get("day5_resources_allowed") is not False
            or policy.get("c2000_integration_allowed") is not False
            or policy.get("requires_protected_service_principal") is not True
            or policy.get("requires_independent_readback_receipts") is not True):
        raise Denied("VAULT_POLICY_SCOPE_CHANGED")
    for relative, expected in PINS.values():
        if file_digest(_inside(root, policy[relative])) != policy[expected]:
            raise Denied("VAULT_CONTRACT_OR_FREEZE_PIN_CHANGED")
    for path, name in ((sample, "sample_file_sha256"),
                       (projected, "projected_file_sha256"),
                       (plan_path, "load_plan_file_sha256")):
        if file_digest(path) != policy[name]:
            raise Denied("VAULT_INPUT_OR_PLAN_CHANGED")
    selected = json.loads(sample.read_bytes())
    if (selected.get("selected_data_occurrences") != 127
            or selected.get("rows_sha256") != policy["sample_rows_sha256"]
            or {r["source_instance_id"] for r in selected["rows"]} != set(EXPECTED_IDS)):
        raise Denied("VAULT_SAMPLE_SCOPE_CHANGED")
    projected_rows = json.loads(projected.read_bytes())["rows"]
    regenerated = render(projected_rows)
    retained = json.loads(plan_path.read_bytes())
    if (retained != regenerated
            or retained["stages_sha256"] != policy["load_plan_stages_sha256"]
            or [s["id"] for s in retained["stages"]] != list(EXPECTED_STAGES)):
        raise Denied("VAULT_PLAN_REGENERATION_MISMATCH")
    for stage in retained["stages"]:
        target = stage["table"]
        if (target not in {f"{NAMESPACE}.{table}" for table in TABLES}
                or stage["kind"] != "MERGE_INSERT_ONLY"
                or not stage["statement"].startswith(f"MERGE INTO {target} AS t\n")
                or not stage["precheck"].startswith("SELECT COUNT(*) AS mismatches FROM ")
                or ";" in stage["statement"] or ";" in stage["precheck"]
                or re.search(r"\b(DROP|DELETE|UPDATE|TRUNCATE|REPLACE|OVERWRITE)\b",
                             stage["statement"], re.IGNORECASE)):
            raise Denied("VAULT_SQL_OUT_OF_SCOPE")
    return selected, retained


def signed_policy(root: Path, policy_path: Path, trust: Path) -> dict:
    if (policy_path.resolve().is_relative_to(root.resolve())
            or trust.resolve().is_relative_to(root.resolve())):
        raise Denied("VAULT_POLICY_NOT_PROTECTED")
    if (os.geteuid() != 0 or trust.stat().st_uid != 0
            or trust.stat().st_mode & 0o022
            or policy_path.stat().st_uid != 0
            or policy_path.stat().st_mode & 0o022):
        raise Denied("VAULT_OWNER_CONTROL_NOT_ESTABLISHED")
    document = verified_document(root, policy_path, trust)
    if document.get("authority") != "requesting-owner-vault-dev-v1":
        raise Denied("VAULT_POLICY_NOT_OWNER_SIGNED")
    if not re.fullmatch(r"[0-9a-f]{16}", document.get("warehouse_id", "")):
        raise Denied("VAULT_DEDICATED_WAREHOUSE_NOT_INSTALLED")
    issued, expires = (datetime.fromisoformat(document[name]).astimezone(UTC)
                       for name in ("issued_at", "expires_at"))
    if not issued <= datetime.now(UTC) < expires:
        raise Denied("VAULT_POLICY_EXPIRED")
    return document


def grant_document(policy: dict, root: Path, plan_path: Path,
                   selected: dict) -> dict:
    now = datetime.now(UTC)
    paths = {
        "parser": ("scripts/day6_vault_contract_v1.py", "VAULT_LOAD_CONTRACT_V1_SERIALIZER"),
        "model": ("src/edp_lab/vault/prototype.py", "DAY6_VAULT_PROJECTION_V1"),
        "rule": (policy["contract_path"], "VAULT_LOAD_CONTRACT_V1"),
        "registry": (policy["exception_path"], "C1500_PROTOTYPE_EXCEPTION_V1"),
        "statement": (str(plan_path.relative_to(root)), "DAY6_VAULT_BOUNDED_LOAD_PLAN_V1"),
    }
    contracts = {name: {"version": version, "sha256": file_digest(_inside(root, path))}
                 for name, (path, version) in paths.items()}
    contracts["queue"] = {"version": "DAY6_VAULT_BOUNDED_LOAD_PLAN_V1",
                          "sha256": file_digest(plan_path)}
    return {"schema": "EDP_SIGNED_GRANT_V1",
            "grant_id": "vault-" + digest(plan_path.read_bytes())[:20]
            + "-" + now.strftime("%Y%m%d%H%M%S"),
            "authority": "policy-broker-v1", "issued_at": now.isoformat(),
            "expires_at": min(now + timedelta(hours=8),
                              datetime.fromisoformat(policy["expires_at"])).isoformat(),
            "revocation_id": policy["policy_id"], "cohort": "C1500",
            "sources": {r["source_instance_id"]: r["raw_sha256"] for r in selected["rows"]},
            "contracts": contracts, "operations": ["databricks_write"],
            "databricks_paths": [],
            "databricks_tables": [f"{NAMESPACE}.{name}" for name in TABLES],
            "outputs": [NAMESPACE], "git_operations": [],
            "protected_branches": ["main"],
            "limits": {"runtime_seconds": policy["max_runtime_seconds"],
                       "compute_units": 20, "token_count": 0, "retries": 0,
                       "operations": policy["max_sql_statements"]}}


def issue(root: Path, policy_path: Path, trust: Path, broker_key: Path,
          grant_store: Path, sample: Path, projected: Path, plan: Path,
          raw_root: Path) -> Path:
    """Protected issuer; full source-byte verification precedes the grant."""
    root = root.resolve()
    if any(path.resolve().is_relative_to(root) for path in
           (trust, broker_key, grant_store, raw_root)):
        raise Denied("VAULT_PROTECTED_BOUNDARY_REQUIRED")
    if (os.geteuid() != 0 or broker_key.stat().st_uid != 0
            or broker_key.stat().st_mode & 0o077
            or grant_store.stat().st_uid != 0
            or grant_store.stat().st_mode & 0o022
            or raw_root.stat().st_uid != 0
            or raw_root.stat().st_mode & 0o077):
        raise Denied("VAULT_PROTECTED_ISSUER_NOT_INSTALLED")
    policy = signed_policy(root, policy_path, trust)
    selected, _ = validate_policy(root, policy, sample, projected, plan)
    verify_selected(raw_root, selected["rows"])
    grant = grant_document(policy, root, plan, selected)
    grant_store.mkdir(parents=True, exist_ok=True)
    target = grant_store / (grant["grant_id"] + ".json")
    if target.exists():
        from edp_lab.operating.authority import load_grant

        existing = load_grant(root, target, trust)
        if existing["expires_at"] > datetime.now(UTC).isoformat():
            return target
    with tempfile.TemporaryDirectory() as temporary:
        message, signature = (Path(temporary) / name for name in ("message", "signature"))
        message.write_bytes(canonical(grant))
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(broker_key),
                        "-rawin", "-in", str(message), "-out", str(signature)],
                       check=True, capture_output=True, timeout=15)
        envelope = {"grant": grant,
                    "signature_base64": base64.b64encode(signature.read_bytes()).decode()}
    staged = target.with_suffix(".next")
    fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical(envelope))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(staged, target)
    return target


def serve(root: Path, base: Path, raw_root: Path) -> None:
    """Owner-installed fixed-input broker; requests cannot select new scope."""
    root, base = root.resolve(strict=True), base.resolve(strict=True)
    if base.is_relative_to(root) or raw_root.resolve().is_relative_to(root):
        raise Denied("VAULT_SERVICE_NOT_PROTECTED")
    socket = base / "broker.sock"
    if socket.exists():
        raise Denied("VAULT_BROKER_SOCKET_ALREADY_EXISTS")

    class Handler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            try:
                query = json.loads(self.rfile.readline(4096))
                if query != {"action": "grant"}:
                    raise Denied("VAULT_BROKER_ACTION_OUT_OF_SCOPE")
                path = issue(root, base / "trust/policy.signed.json", base / "trust",
                             base / "private/broker.pem", base / "grants",
                             root / "runs/day6-vault-prototype/sample-manifest.json",
                             root / "runs/day6-vault-prototype/projected-manifest.json",
                             root / "runs/day6-vault-prototype/load-plan.json", raw_root)
                response = {"status": "ISSUED", "grant_path": str(path)}
            except (Denied, OSError, ValueError, KeyError, TypeError) as exc:
                response = {"status": "DENIED", "reason": str(exc)}
            self.wfile.write(canonical(response))

    with socketserver.UnixStreamServer(str(socket), Handler) as server:
        os.chown(socket, 0, grp.getgrnam("staff").gr_gid)
        os.chmod(socket, 0o660)
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("base", type=Path)
    parser.add_argument("raw_root", type=Path)
    args = parser.parse_args()
    serve(args.root, args.base, args.raw_root)


if __name__ == "__main__":
    main()
