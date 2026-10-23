"""Cohort-neutral, one-time Vault Dev 0A owner-terminal installer.

This is never invoked by Codex. The owner supplies a reviewed commit and
proposal SHA. It stops before resource creation when UC authority is absent.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import socket
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from owner_setup_day6_vault_0a import (
    ADMIN_USER,
    BASE,
    PLISTS,
    ROOT,
    _launch,
    _runtime,
    _schema_and_tables,
    admin_cli,
    digest,
    run,
)

from edp_lab.operating.authority import canonical, file_digest, verified_document
from edp_lab.vault.protected_readback import _sign
from edp_lab.vault.standing_v2 import validate_standing_policy

PROPOSAL = ROOT / "metadata/operating/vault_standing_policy_v2_proposal.json"
BROKER_LABEL = "org.edp-lab.vault-v2-broker"
EXECUTOR_LABEL = "org.edp-lab.vault-v2-executor"


def preflight(commit: str, policy_sha256: str) -> dict:
    if os.geteuid() != 0 or ROOT != Path(
            "/Users/lightnino/Projects/edp-lab-day6-vault-prototype"):
        raise RuntimeError("OWNER_ROOT_TERMINAL_AND_WORKTREE_REQUIRED")
    actual_commit = run("/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
                        "rev-parse", "HEAD").stdout.strip()
    if actual_commit != commit:
        raise RuntimeError("UNREVIEWED_COMMIT")
    if run("/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
           "status", "--porcelain", "--untracked-files=no").stdout.strip():
        raise RuntimeError("TRACKED_WORKTREE_CHANGED")
    if digest(PROPOSAL) != policy_sha256:
        raise RuntimeError("UNREVIEWED_POLICY_PROPOSAL")
    if BASE.exists() or any(Path("/Library/LaunchDaemons", label + ".plist").exists()
                            for label in (*PLISTS, BROKER_LABEL, EXECUTOR_LABEL)):
        raise RuntimeError("VAULT_0A_ALREADY_OR_PARTIALLY_INSTALLED")
    policy = json.loads(PROPOSAL.read_bytes())
    validate_standing_policy(policy, root=ROOT)
    principal = admin_cli("current-user", "me")
    if (principal.get("userName") != "chengzhu13@gmail.com"
            or "admins" not in {group.get("display") for group in principal.get("groups", [])}):
        raise RuntimeError("INDEPENDENT_ADMIN_PRINCIPAL_REQUIRED")
    grants = admin_cli("grants", "get-effective", "catalog", "workspace",
                       "--principal", principal["userName"])
    _require_schema_create(grants)
    existing = admin_cli("service-principals", "list", "--filter",
                         'displayName sw "edp-lab-vault-dev-v2"')
    if existing:
        raise RuntimeError("VAULT_SERVICE_PRINCIPAL_ALREADY_EXISTS")
    warehouses = admin_cli("warehouses", "list")
    candidates = warehouses if isinstance(warehouses, list) else warehouses.get("warehouses", [])
    if any(item.get("name") == "EDP Vault Dev V2" for item in candidates):
        raise RuntimeError("VAULT_WAREHOUSE_ALREADY_EXISTS")
    # An absent target is required; inspect the CLI result without swallowing other errors.
    probe = subprocess.run(
        ["/usr/bin/sudo", "-n", "-u", ADMIN_USER, "-H",
         "/opt/homebrew/bin/databricks", "schemas", "get",
         "workspace.edp_lab_day6_vault_proto", "-p", "edp-lab", "-o", "json"],
        capture_output=True, text=True, timeout=30, check=False)
    if probe.returncode == 0 or "does not exist" not in probe.stderr.lower():
        raise RuntimeError("VAULT_SCHEMA_ABSENCE_NOT_PROVEN")
    return policy


def _require_schema_create(grants: dict) -> None:
    effective = {item["privilege"] for assignment in grants.get("privilege_assignments", [])
                 for item in assignment.get("privileges", [])}
    if not {"USE_CATALOG", "CREATE_SCHEMA"} <= effective:
        raise RuntimeError("VAULT_SCHEMA_CREATE_PRIVILEGE_REQUIRED_FOR_OWNER_ADMIN")


def _directories() -> None:
    BASE.mkdir(mode=0o755)
    for name, mode in (("private", 0o700), ("trust", 0o755), ("grants", 0o755),
                       ("approvals", 0o700), ("eligibility", 0o700), ("receipts", 0o700),
                       ("ledger", 0o700), ("runtime", 0o755)):
        (BASE / name).mkdir(mode=mode)


def _warehouse_v2(application_id: str) -> str:
    response = admin_cli("warehouses", "create", "--name", "EDP Vault Dev V2",
                         "--cluster-size", "2X-Small", "--min-num-clusters", "1",
                         "--max-num-clusters", "1", "--auto-stop-mins", "10",
                         "--enable-serverless-compute", "--warehouse-type", "PRO",
                         "--no-wait")
    warehouse = response["id"]
    if re.fullmatch(r"[0-9a-f]{16}", warehouse) is None:
        raise RuntimeError("VAULT_WAREHOUSE_ID_INVALID")
    admin_cli("permissions", "update", "warehouses", warehouse,
              "--json", json.dumps({"access_control_list": [{
                  "service_principal_name": application_id, "permission_level": "CAN_USE"}]}))
    return warehouse


def _verify_service_principal_boundaries(application_id: str) -> None:
    for securable, name, forbidden in (
        ("catalog", "workspace", {"CREATE_SCHEMA", "ALL_PRIVILEGES", "MANAGE"}),
        ("schema", "workspace.edp_lab_day6_vault_proto",
         {"CREATE_TABLE", "CREATE_VOLUME", "ALL_PRIVILEGES", "MANAGE"}),
        ("schema", "workspace.edp_lab",
         {"CREATE_TABLE", "MODIFY", "ALL_PRIVILEGES", "MANAGE"}),
        ("volume", "workspace.edp_lab.raw",
         {"WRITE_VOLUME", "CREATE_VOLUME", "ALL_PRIVILEGES", "MANAGE"}),
    ):
        result = admin_cli("grants", "get-effective", securable, name,
                           "--principal", application_id)
        effective = {item["privilege"] for assignment in
                     result.get("privilege_assignments", [])
                     for item in assignment.get("privileges", [])}
        if effective & forbidden:
            raise RuntimeError("VAULT_SERVICE_PRINCIPAL_PROTECTED_ACCESS")


def _service_identity_v2() -> tuple[str, str]:
    created = admin_cli("service-principals", "create", "--display-name",
                        "edp-lab-vault-dev-v2")
    sp_id = str(created["id"])
    app_id = created["applicationId"]
    secret = admin_cli("service-principal-secrets-proxy", "create", sp_id,
                       "--lifetime", "604800")["secret"]
    config = BASE / "private/databrickscfg"
    from owner_setup_day6_vault_0a import HOST

    config.write_text(f"[vault-dev]\nhost = {HOST}\nclient_id = {app_id}\n"
                      f"client_secret = {secret}\n")
    config.chmod(0o600)
    return sp_id, app_id


def _keys_and_policy(policy: dict, warehouse: str) -> None:
    for role in ("owner", "broker", "verifier"):
        key = BASE / "private" / (role + ".pem")
        run("/opt/homebrew/bin/openssl", "genpkey", "-algorithm", "Ed25519",
            "-out", str(key))
        key.chmod(0o600)
        run("/opt/homebrew/bin/openssl", "pkey", "-in", str(key), "-pubout",
            "-out", str(BASE / "trust" / (role + "_ed25519_public.pem")))
    (BASE / "trust/revoked_grants.json").write_text("[]\n")
    policy["warehouse_id"] = warehouse
    policy["status"] = "OWNER_INSTALLED_STANDING_POLICY"
    message = BASE / "private/policy.payload"
    message.write_bytes(canonical(policy))
    signature = BASE / "private/policy.sig"
    run("/opt/homebrew/bin/openssl", "pkeyutl", "-sign", "-inkey",
        str(BASE / "private/owner.pem"), "-rawin", "-in", str(message),
        "-out", str(signature))
    envelope = {"document": policy,
                "signature_base64": base64.b64encode(signature.read_bytes()).decode()}
    (BASE / "trust/policy.signed.json").write_bytes(canonical(envelope))
    verified_document(ROOT, BASE / "trust/policy.signed.json", BASE / "trust")


def _rpc(path: Path, request: dict) -> dict:
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(30)
        client.connect(str(path))
        client.sendall((json.dumps(request) + "\n").encode())
        client.shutdown(socket.SHUT_WR)
        return json.loads(client.recv(8192))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    parser.add_argument("expected_policy_sha256")
    args = parser.parse_args()
    policy = preflight(args.expected_commit, args.expected_policy_sha256)
    _directories()
    _runtime()
    sp_id, app_id = _service_identity_v2()
    warehouse = _warehouse_v2(app_id)
    ddl_ids = _schema_and_tables(app_id)
    _verify_service_principal_boundaries(app_id)
    _keys_and_policy(policy, warehouse)
    (BASE / "private/service-principal.json").write_text(
        json.dumps({"service_principal_id": sp_id, "application_id": app_id}) + "\n")
    _launch(BROKER_LABEL, "edp_lab.vault.broker_v2", str(ROOT), str(BASE))
    _launch(EXECUTOR_LABEL, "edp_lab.vault.executor_v2", str(ROOT), str(BASE))
    for _ in range(30):
        if (BASE / "broker.sock").exists() and (BASE / "executor.sock").exists():
            break
        time.sleep(1)
    if (_rpc(BASE / "broker.sock", {"action": "unauthorized", "run_path": "x"}).get("status")
            != "DENIED" or _rpc(BASE / "executor.sock",
                            {"action": "execute", "grant_path": "/tmp/forged.json"}
                            ).get("status") != "DENIED"):
        raise RuntimeError("VAULT_NEGATIVE_SERVICE_TEST_FAILED")
    installation = {"schema": "EDP_VAULT_0A_INSTALL_RECEIPT_V2",
                    "authority": "protected-verifier-v1",
                    "status": "VAULT_0A_INSTALLED_AWAITING_ELIGIBLE_RUN",
                    "namespace": "workspace.edp_lab_day6_vault_proto",
                    "warehouse_id": warehouse, "service_principal_id": sp_id,
                    "ddl_statement_ids": ddl_ids,
                    "negative_broker_action_denied": True,
                    "negative_forged_executor_grant_denied": True,
                    "signed_policy_sha256": file_digest(BASE / "trust/policy.signed.json"),
                    "at_utc": datetime.now(UTC).isoformat()}
    output = BASE / "receipts/install-v2.signed.json"
    _sign(installation, BASE / "private/verifier.pem", output)
    verified_document(ROOT, output, BASE / "trust")
    print(json.dumps({"status": installation["status"],
                      "receipt_path": str(output), "receipt_sha256": file_digest(output),
                      "namespace": installation["namespace"],
                      "warehouse_id": warehouse, "service_principal_id": sp_id},
                     sort_keys=True))


if __name__ == "__main__":
    main()
