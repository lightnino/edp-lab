"""Owner-terminal recovery of the exact Vault V2 secret-creation checkpoint.

This deliberately does not provision a second identity or repair an unknown
checkpoint. A failed secret request is never automatically retried.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from owner_setup_day6_vault_0a import ADMIN_USER, BASE, HOST, ROOT, admin_cli, digest, run
from owner_setup_vault_0a_v2 import (
    BROKER_LABEL,
    EXECUTOR_LABEL,
    PLISTS,
    PROPOSAL,
    _keys_and_policy,
    _launch,
    _require_schema_create,
    _schema_and_tables,
    _verify_service_principal_boundaries,
    _warehouse_v2,
)

from edp_lab.vault.standing_v2 import validate_standing_policy

ORIGINAL_COMMIT = "d841204782f21402d4cd8553a1a5b425cda68655"
PRINCIPAL_ID = "72304318628585"
APPLICATION_ID = "87df13c2-1bb7-4a0b-b84a-84e01bdc1764"
POLICY_SHA256 = "0deae5164d9276987d5beabad25afc86082a0ea72983588135a870440e53edc0"
NAME = "edp-lab-vault-dev-v2"
WAREHOUSE_NAME = "EDP Vault Dev V2"
NAMESPACE = "workspace.edp_lab_day6_vault_proto"


def _absent_schema() -> None:
    result = subprocess.run(
        ["/usr/bin/sudo", "-n", "-u", ADMIN_USER, "-H",
         "/opt/homebrew/bin/databricks", "schemas", "get", NAMESPACE,
         "-p", "edp-lab", "-o", "json"],
        capture_output=True, text=True, timeout=30, check=False)
    if result.returncode == 0 or "does not exist" not in result.stderr.lower():
        raise RuntimeError("VAULT_SCHEMA_ABSENCE_NOT_PROVEN")


def _remote_checkpoint() -> None:
    identity = admin_cli("service-principals", "get", PRINCIPAL_ID)
    if (identity.get("id") != PRINCIPAL_ID or identity.get("applicationId") != APPLICATION_ID
            or identity.get("displayName") != NAME or identity.get("active") is not True):
        raise RuntimeError("VAULT_EXISTING_PRINCIPAL_MISMATCH")
    matches = admin_cli("service-principals", "list", "--filter",
                        'displayName sw "edp-lab-vault-dev-v2"')
    if len(matches) != 1 or str(matches[0].get("id")) != PRINCIPAL_ID:
        raise RuntimeError("VAULT_DUPLICATE_OR_MISSING_PRINCIPAL")
    assignment = admin_cli("workspace-iam-v2", "get-workspace-assignment-proxy", PRINCIPAL_ID)
    access = admin_cli("workspace-iam-v2", "get-workspace-access-detail-local", PRINCIPAL_ID)
    if (str(assignment.get("principal_id")) != PRINCIPAL_ID
            or assignment.get("principal_type") != "SERVICE_PRINCIPAL"
            or access.get("status") != "ACTIVE"
            or access.get("access_type") != "DIRECT"):
        raise RuntimeError("VAULT_WORKSPACE_ASSIGNMENT_REQUIRED")
    if admin_cli("service-principal-secrets-proxy", "list", PRINCIPAL_ID):
        raise RuntimeError("VAULT_SECRET_EXISTS_VALUE_UNRECOVERABLE_NO_DUPLICATE")
    warehouses = admin_cli("warehouses", "list")
    candidates = warehouses if isinstance(warehouses, list) else warehouses.get("warehouses", [])
    if any(item.get("name") == WAREHOUSE_NAME for item in candidates):
        raise RuntimeError("VAULT_WAREHOUSE_CHECKPOINT_CHANGED")
    _absent_schema()


def _protected_checkpoint() -> None:
    if not BASE.is_dir() or BASE.is_symlink() or BASE.stat().st_uid != 0:
        raise RuntimeError("VAULT_PROTECTED_ROOT_MISMATCH")
    for name in ("private", "trust", "grants", "approvals", "eligibility",
                 "receipts", "ledger", "runtime"):
        path = BASE / name
        if not path.is_dir() or path.is_symlink() or path.stat().st_uid != 0:
            raise RuntimeError("VAULT_PROTECTED_DIRECTORY_MISMATCH: " + name)
    for name in ("private", "trust", "grants", "approvals", "eligibility",
                 "receipts", "ledger"):
        if any((BASE / name).iterdir()):
            raise RuntimeError("VAULT_PROTECTED_CHECKPOINT_CHANGED: " + name)
    if not (BASE / "runtime/src/edp_lab").is_dir() or not (BASE / "python/bin/python3.12").exists():
        raise RuntimeError("VAULT_RUNTIME_CHECKPOINT_MISMATCH")
    for label in (*PLISTS, BROKER_LABEL, EXECUTOR_LABEL):
        if (Path("/Library/LaunchDaemons") / (label + ".plist")).exists():
            raise RuntimeError("VAULT_SERVICE_CHECKPOINT_CHANGED")


def preflight(commit: str, policy_sha256: str) -> dict:
    if os.geteuid() != 0 or ROOT != Path(
            "/Users/lightnino/Projects/edp-lab-day6-vault-prototype"):
        raise RuntimeError("OWNER_ROOT_TERMINAL_AND_WORKTREE_REQUIRED")
    actual = run("/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
                 "rev-parse", "HEAD").stdout.strip()
    if actual != commit:
        raise RuntimeError("UNREVIEWED_RECOVERY_COMMIT")
    ancestor = subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
         "merge-base", "--is-ancestor", ORIGINAL_COMMIT, "HEAD"],
        capture_output=True, text=True, check=False)
    if ancestor.returncode:
        raise RuntimeError("ORIGINAL_INSTALL_COMMIT_NOT_PRESERVED")
    if run("/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
           "status", "--porcelain", "--untracked-files=no").stdout.strip():
        raise RuntimeError("TRACKED_WORKTREE_CHANGED")
    run("/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
        "ls-files", "--error-unmatch", "scripts/owner_recover_vault_0a_v2.py")
    if policy_sha256 != POLICY_SHA256 or digest(PROPOSAL) != POLICY_SHA256:
        raise RuntimeError("UNREVIEWED_POLICY_PROPOSAL")
    policy = json.loads(PROPOSAL.read_bytes())
    validate_standing_policy(policy, root=ROOT)
    user = admin_cli("current-user", "me")
    if (user.get("userName") != "chengzhu13@gmail.com"
            or "admins" not in {g.get("display") for g in user.get("groups", [])}):
        raise RuntimeError("INDEPENDENT_ADMIN_PRINCIPAL_REQUIRED")
    _require_schema_create(admin_cli("grants", "get-effective", "catalog", "workspace",
                                     "--principal", user["userName"]))
    _protected_checkpoint()
    _remote_checkpoint()
    return policy


def _create_single_secret() -> None:
    # Recheck directly at the mutation boundary. A timeout or ambiguous response
    # is not retried: the owner must inspect secret metadata again.
    if admin_cli("service-principal-secrets-proxy", "list", PRINCIPAL_ID):
        raise RuntimeError("VAULT_SECRET_ALREADY_EXISTS_NO_DUPLICATE")
    assignment = admin_cli("workspace-iam-v2", "get-workspace-assignment-proxy", PRINCIPAL_ID)
    if str(assignment.get("principal_id")) != PRINCIPAL_ID:
        raise RuntimeError("VAULT_WORKSPACE_ASSIGNMENT_REQUIRED")
    cmd = ["/usr/bin/sudo", "-n", "-u", ADMIN_USER, "-H",
           "/opt/homebrew/bin/databricks", "service-principal-secrets-proxy", "create",
           PRINCIPAL_ID, "--lifetime", "604800", "-p", "edp-lab", "-o", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    if result.returncode:
        # Databricks CLI errors contain endpoint details, not the OAuth value.
        raise RuntimeError("VAULT_SECRET_CREATE_FAILED: " + result.stderr.strip()[:2000])
    response = json.loads(result.stdout)
    secret = response.get("secret")
    if not isinstance(secret, str) or not secret:
        raise RuntimeError("VAULT_SECRET_CREATE_RESPONSE_INVALID_CHECK_METADATA")
    config = BASE / "private/databrickscfg"
    with config.open("x", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(f"[vault-dev]\nhost = {HOST}\nclient_id = {APPLICATION_ID}\n"
                     f"client_secret = {secret}\n")
    identity = BASE / "private/service-principal.json"
    with identity.open("x", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump({"service_principal_id": PRINCIPAL_ID,
                   "application_id": APPLICATION_ID}, stream)
        stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_recovery_commit")
    parser.add_argument("expected_policy_sha256")
    args = parser.parse_args()
    policy = preflight(args.expected_recovery_commit, args.expected_policy_sha256)
    _create_single_secret()
    # Each later operation is guarded by the checkpoint above. A failure after
    # this point stops without automatic replay or duplicate remote creation.
    warehouses = admin_cli("warehouses", "list")
    candidates = warehouses if isinstance(warehouses, list) else warehouses.get("warehouses", [])
    if any(item.get("name") == WAREHOUSE_NAME for item in candidates):
        raise RuntimeError("VAULT_WAREHOUSE_ALREADY_EXISTS_NO_DUPLICATE")
    warehouse = _warehouse_v2(APPLICATION_ID)
    _absent_schema()
    ddl_ids = _schema_and_tables(APPLICATION_ID)
    _verify_service_principal_boundaries(APPLICATION_ID)
    _keys_and_policy(policy, warehouse)
    _launch(BROKER_LABEL, "edp_lab.vault.broker_v2", str(ROOT), str(BASE))
    _launch(EXECUTOR_LABEL, "edp_lab.vault.executor_v2", str(ROOT), str(BASE))
    import time

    from owner_setup_vault_0a_v2 import _rpc
    for _ in range(30):
        if (BASE / "broker.sock").exists() and (BASE / "executor.sock").exists():
            break
        time.sleep(1)
    if (_rpc(BASE / "broker.sock", {"action": "unauthorized", "run_path": "x"}).get("status")
            != "DENIED" or _rpc(BASE / "executor.sock",
                            {"action": "execute", "grant_path": "/tmp/forged.json"}
                            ).get("status") != "DENIED"):
        raise RuntimeError("VAULT_NEGATIVE_SERVICE_TEST_FAILED")
    from datetime import UTC, datetime

    from edp_lab.operating.authority import file_digest, verified_document
    from edp_lab.vault.protected_readback import _sign
    installation = {"schema": "EDP_VAULT_0A_INSTALL_RECEIPT_V2",
                    "authority": "protected-verifier-v1",
                    "status": "VAULT_0A_INSTALLED_AWAITING_ELIGIBLE_RUN",
                    "namespace": NAMESPACE, "warehouse_id": warehouse,
                    "service_principal_id": PRINCIPAL_ID,
                    "service_principal_application_id": APPLICATION_ID,
                    "ddl_statement_ids": ddl_ids,
                    "negative_broker_action_denied": True,
                    "negative_forged_executor_grant_denied": True,
                    "signed_policy_sha256": file_digest(BASE / "trust/policy.signed.json"),
                    "recovered_from_commit": ORIGINAL_COMMIT,
                    "at_utc": datetime.now(UTC).isoformat()}
    output = BASE / "receipts/install-v2.signed.json"
    _sign(installation, BASE / "private/verifier.pem", output)
    verified_document(ROOT, output, BASE / "trust")
    print(json.dumps({"status": installation["status"], "receipt_path": str(output),
                      "receipt_sha256": file_digest(output), "namespace": NAMESPACE,
                      "warehouse_id": warehouse, "service_principal_id": PRINCIPAL_ID},
                     sort_keys=True))


if __name__ == "__main__":
    main()
