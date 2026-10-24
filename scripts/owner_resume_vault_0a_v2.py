"""Owner-only continuation from the verified post-secret, pre-warehouse checkpoint."""
from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import subprocess
import tarfile
from io import BytesIO
from pathlib import Path

from owner_recover_vault_0a_v2 import (
    APPLICATION_ID,
    NAME,
    ORIGINAL_COMMIT,
    PRINCIPAL_ID,
    _absent_schema,
    complete_after_warehouse,
)
from owner_setup_day6_vault_0a import BASE, HOST, ROOT, admin_cli, digest, run
from owner_setup_vault_0a_v2 import (
    BROKER_LABEL,
    EXECUTOR_LABEL,
    PLISTS,
    PROPOSAL,
    _require_schema_create,
    _warehouse_v2,
)

from edp_lab.vault.standing_v2 import validate_standing_policy

POLICY_SHA256 = "7200b417a3321580147c8d135eef99868c5fb79dbe78ae236f54266240fa3316"


def _root_owned(path: Path) -> bool:
    return path.stat().st_uid == 0


def _protected_checkpoint() -> None:
    if not BASE.is_dir() or BASE.is_symlink() or not _root_owned(BASE):
        raise RuntimeError("VAULT_PROTECTED_ROOT_MISMATCH")
    for name in ("private", "trust", "grants", "approvals", "eligibility",
                 "receipts", "ledger", "runtime"):
        path = BASE / name
        if not path.is_dir() or path.is_symlink() or not _root_owned(path):
            raise RuntimeError("VAULT_PROTECTED_DIRECTORY_MISMATCH: " + name)
    for name in ("trust", "grants", "approvals", "eligibility", "receipts", "ledger"):
        if any((BASE / name).iterdir()):
            raise RuntimeError("VAULT_PROTECTED_CHECKPOINT_CHANGED: " + name)
    private = BASE / "private"
    if {p.name for p in private.iterdir()} != {"databrickscfg", "service-principal.json"}:
        raise RuntimeError("VAULT_PRIVATE_CHECKPOINT_CHANGED")
    for path in private.iterdir():
        if (not path.is_file() or path.is_symlink() or not _root_owned(path)
                or path.stat().st_mode & 0o077):
            raise RuntimeError("VAULT_PROTECTED_CREDENTIAL_PERMISSIONS")
    identity = json.loads((private / "service-principal.json").read_text())
    if identity != {"service_principal_id": PRINCIPAL_ID,
                    "application_id": APPLICATION_ID}:
        raise RuntimeError("VAULT_PROTECTED_IDENTITY_MISMATCH")
    config = configparser.ConfigParser(interpolation=None)
    config.read(private / "databrickscfg")
    if (config.sections() != ["vault-dev"]
            or set(config["vault-dev"]) != {"host", "client_id", "client_secret"}
            or config["vault-dev"]["host"] != HOST
            or config["vault-dev"]["client_id"] != APPLICATION_ID
            or not config["vault-dev"]["client_secret"].strip()):
        raise RuntimeError("VAULT_PROTECTED_CONFIG_MISMATCH")
    if (not (BASE / "runtime/src/edp_lab").is_dir()
            or not (BASE / "runtime/src/edp_lab-original-d841204").is_dir()
            or not (BASE / "python/bin/python3.12").exists()
            or (BASE / "runtime-next").exists()):
        raise RuntimeError("VAULT_RUNTIME_CHECKPOINT_MISMATCH")
    for label in (*PLISTS, BROKER_LABEL, EXECUTOR_LABEL):
        if (Path("/Library/LaunchDaemons") / (label + ".plist")).exists():
            raise RuntimeError("VAULT_SERVICE_CHECKPOINT_CHANGED")


def _remote_checkpoint() -> None:
    identity = admin_cli("service-principals", "get", PRINCIPAL_ID)
    if (str(identity.get("id")) != PRINCIPAL_ID
            or identity.get("applicationId") != APPLICATION_ID
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
            or access.get("status") != "ACTIVE" or access.get("access_type") != "DIRECT"):
        raise RuntimeError("VAULT_WORKSPACE_ASSIGNMENT_REQUIRED")
    secrets = admin_cli("service-principal-secrets-proxy", "list", PRINCIPAL_ID)
    if not isinstance(secrets, list) or len(secrets) != 1:
        raise RuntimeError("VAULT_SECRET_METADATA_COUNT_CHANGED")
    from owner_setup_vault_0a_v2 import _verify_shared_warehouse

    _verify_shared_warehouse()
    _absent_schema()
    result = subprocess.run(
        ["/opt/homebrew/bin/databricks", "current-user", "me", "-p", "vault-dev", "-o", "json"],
        env={**{key: value for key, value in os.environ.items()
                if not key.startswith("DATABRICKS_")},
             "DATABRICKS_CONFIG_FILE": str(BASE / "private/databrickscfg")},
        capture_output=True, text=True, timeout=30, check=False)
    if result.returncode:
        raise RuntimeError("VAULT_PROTECTED_CREDENTIAL_AUTH_FAILED")
    principal = json.loads(result.stdout)
    if str(principal.get("id")) != PRINCIPAL_ID:
        raise RuntimeError("VAULT_PROTECTED_CREDENTIAL_IDENTITY_MISMATCH")


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
        "ls-files", "--error-unmatch", "scripts/owner_resume_vault_0a_v2.py")
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


def _sanitized_cli_error(exc: subprocess.CalledProcessError) -> str:
    stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    line = next((line.strip() for line in stderr.splitlines()
                 if line.strip().lower().startswith("error:")), "")
    config = configparser.ConfigParser(interpolation=None)
    config.read(BASE / "private/databrickscfg")
    secret = config.get("vault-dev", "client_secret", fallback="")
    if secret:
        line = line.replace(secret, "[REDACTED]")
    line = re.sub(r"(?i)(bearer|token|secret|password|authorization)\s*[:=]\s*\S+",
                  r"\1=[REDACTED]", line)
    line = re.sub(r"https?://\S+", "[URL REDACTED]", line)
    return line[:1000] if line else f"CLI_EXIT_{exc.returncode}_NO_ERROR_LINE"


def _refresh_reviewed_runtime() -> None:
    """Replace only the protected runtime copy with reviewed HEAD code."""
    current = BASE / "runtime/src/edp_lab"
    staged = BASE / "runtime-next"
    if staged.exists() or not current.is_dir():
        raise RuntimeError("VAULT_RUNTIME_REFRESH_CHECKPOINT_CHANGED")
    archive = subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
         "archive", "HEAD", "src/edp_lab"], capture_output=True, check=True, timeout=60)
    staged.mkdir(mode=0o700)
    with tarfile.open(fileobj=BytesIO(archive.stdout), mode="r:") as tar:
        tar.extractall(staged, filter="data")
    incoming = staged / "src/edp_lab"
    if not (incoming / "vault/standing_v2.py").is_file():
        raise RuntimeError("VAULT_REVIEWED_RUNTIME_MISSING")
    for path in staged.rglob("*"):
        if path.is_file():
            path.chmod(path.stat().st_mode & ~0o022)
    backup = BASE / "runtime/src/edp_lab-pre-shared-compute"
    if backup.exists():
        raise RuntimeError("VAULT_RUNTIME_REFRESH_CHECKPOINT_CHANGED")
    current.rename(backup)
    incoming.rename(current)
    (staged / "src").rmdir()
    staged.rmdir()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_recovery_commit")
    parser.add_argument("expected_policy_sha256")
    args = parser.parse_args()
    policy = preflight(args.expected_recovery_commit, args.expected_policy_sha256)
    # The owner invokes this command once from the post-secret checkpoint.
    _refresh_reviewed_runtime()
    try:
        warehouse = _warehouse_v2(APPLICATION_ID)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("VAULT_SHARED_WAREHOUSE_VERIFY_OR_PERMISSION_FAILED: "
                           + _sanitized_cli_error(exc)) from None
    except subprocess.TimeoutExpired:
        raise RuntimeError("VAULT_SHARED_WAREHOUSE_TIMEOUT_NO_RETRY") from None
    complete_after_warehouse(policy, warehouse)


if __name__ == "__main__":
    main()
