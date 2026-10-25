"""ONE-TIME Owner repair for the precisely identified Day 7 partial install.

Existing protected install was created on c2c4c1e... and stopped during the
first OAuth service-principal-secrets-proxy create. Normal-user independent
diagnostics showed SP 78491734320299 + workspace assignment valid and
exactly zero secrets, before the Owner granted SP Manager permissions.

This command must run ONCE after Owner review from pinned clean Day 7 HEAD.
It does not create another principal, alter Day 5/6, stage RAW or select N1000.
It keeps the only newly minted OAuth secret exclusively in owner-only storage.

If the remote response is lost/uncertain or the secret inventory is nonzero,
STOP and reconcile manually. A second invocation cannot silently re-create.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from configparser import ConfigParser
from pathlib import Path

import owner_install_day7 as install

OLD_COMMIT = "c2c4c1e5ffb4f795d345ce95023287b174c13b28"
SP_ID = "78491734320299"
ALLOWED_CHANGES = {
    "scripts/owner_install_day7.py",
    "scripts/diagnose_day7_secret.py",
    "scripts/owner_recover_day7_secret_v1.py",
    "tests/operating/test_day7_secret_partial_diagnostic.py",
    "tests/operating/test_day7_secret_recovery.py",
}
ALLOWED_COMPLETED = {"protected_files", "workspace_assignment"}
RECOVERY_INTENT = install.BASE / "ledger/day7-secret-recovery-intent.json"
ORIGINAL_INTENT = install.BASE / "ledger/secret-creation-intent.json"
IDENTITY = install.BASE / "private/service-identity.json"
CONFIG = install.BASE / "private/databrickscfg"
CONFIG_TEMP = install.BASE / "private/databrickscfg.new"
REVOKED = install.BASE / "trust/revoked_grants.json"


def require(test: bool, reason: str) -> None:
    if not test:
        raise RuntimeError(reason)


def git(*args: str) -> str:
    return subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={install.ROOT}",
         "-C", str(install.ROOT), *args],
        capture_output=True, text=True, check=True, timeout=60,
    ).stdout.strip()


def _root_file(path: Path, *, mode: int | None = None) -> None:
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_uid == 0
            and not path.stat().st_mode & 0o022,
            "DAY7_PROTECTED_FILE_CHANGED:" + path.name)
    if mode is not None:
        require(stat.S_IMODE(path.stat().st_mode) == mode,
                "DAY7_PROTECTED_FILE_MODE_CHANGED:" + path.name)


def _secret_metadata() -> list[dict]:
    """Strictly read metadata; never request or print secret values."""
    response = install.admin("service-principal-secrets-proxy", "list", SP_ID)
    if isinstance(response, list):
        return response
    require(isinstance(response, dict),
            "DAY7_SECRET_METADATA_RESPONSE_INVALID")
    require(not response.get("next_page_token"),
            "DAY7_SECRET_INVENTORY_PAGINATION_UNVERIFIED")
    items = response.get("secrets", [])
    require(isinstance(items, list), "DAY7_SECRET_METADATA_RESPONSE_INVALID")
    return items


def _safe_error(value: str) -> str:
    text = re.sub(r"(?i)Bearer\s+\S+", "Bearer [REDACTED]", value)
    text = re.sub(
        r"(?i)(client_secret|access_token|refresh_token|password|api_key|"
        r"authorization)\s*[:=]\s*[^\s,]+", r"\1=[REDACTED]", text)
    return re.sub(r"[\x00-\x1f\x7f]+", " ", text).strip()[:300]


def _confirmed_before_mutation(expected_commit: str) -> tuple[dict, dict]:
    require(os.geteuid() == 0, "DAY7_OWNER_ROOT_REQUIRED")
    require(len(expected_commit) == 40
            and git("rev-parse", "HEAD") == expected_commit,
            "DAY7_REVIEWED_COMMIT_CHANGED")
    require(not git("status", "--porcelain"),
            "DAY7_TRACKED_OR_UNTRACKED_WORKTREE_CHANGED")
    changes = set(git("diff", "--name-only", OLD_COMMIT, expected_commit).splitlines())
    require({"scripts/owner_install_day7.py",
             "scripts/owner_recover_day7_secret_v1.py"} <= changes <= ALLOWED_CHANGES,
            "DAY7_RECOVERY_CODE_SCOPE_CHANGED")
    require(install.file_digest(install.POLICY) == install.POLICY_SHA
            and install.file_digest(install.SOURCE_INDEX) == install.SOURCE_INDEX_SHA
            and install.file_digest(
                install.ROOT / "metadata/source_universes/approved/manifest.json")
            == install.MANIFEST_SHA,
            "DAY7_CANONICAL_PINS_CHANGED")
    require(install.BASE.is_dir() and not install.BASE.is_symlink()
            and install.BASE.stat().st_uid == 0,
            "DAY7_EXPECTED_PROTECTED_BASE_MISSING")
    _root_file(install.JOURNAL, mode=0o600)
    _root_file(IDENTITY, mode=0o600)
    _root_file(ORIGINAL_INTENT, mode=0o600)
    _root_file(REVOKED)
    require(not CONFIG.exists() and not CONFIG.is_symlink()
            and not CONFIG_TEMP.exists() and not CONFIG_TEMP.is_symlink()
            and not RECOVERY_INTENT.exists(),
            "DAY7_SECRET_RECOVERY_ALREADY_ATTEMPTED_OR_CONFIG_PRESENT")
    require(not (install.BASE / "receipts/day7-deployment.json").exists(),
            "DAY7_DEPLOYMENT_ALREADY_SUBMITTED")
    require(not (install.BASE / "ledger/canary-submit-intent.json").exists(),
            "DAY7_CANARY_ALREADY_SUBMITTED")
    require(not install.PLIST.exists(), "DAY7_BROKER_ALREADY_INSTALLED")
    journal = install._read_json(install.JOURNAL)
    expected = {**install._install_intent(OLD_COMMIT)}
    require({k: v for k, v in journal.items() if k != "completed"} == expected
            and isinstance(journal.get("completed"), dict)
            and "protected_files" in journal["completed"]
            and set(journal["completed"]) <= ALLOWED_COMPLETED,
            "DAY7_ORIGINAL_INSTALL_JOURNAL_CHANGED")
    identity = install._read_json(IDENTITY)
    require(str(identity.get("service_principal_id")) == SP_ID
            and isinstance(identity.get("application_id"), str)
            and identity["application_id"],
            "DAY7_OLD_SP_IDENTITY_CHANGED")
    require(install._read_json(ORIGINAL_INTENT) == identity,
            "DAY7_ORIGINAL_SECRET_INTENT_CHANGED")
    # Preserve original protected signatures and immutable source evidence.
    sys.path.insert(0, str(install.ROOT / "src"))
    from edp_lab.operating.authority import verified_document
    signed_policy = verified_document(
        install.ROOT,
        install.BASE / "trust/policy.signed.json",
        install.BASE / "trust",
    )
    require(signed_policy == install._read_json(install.POLICY)
            and install.file_digest(
                install.BASE / "source_evidence_index.json") == install.SOURCE_INDEX_SHA,
            "DAY7_OWNER_SIGNED_POLICY_OR_INDEX_CHANGED")
    # The original git-archived broker code is unchanged across the repair;
    # only the Owner installer, diagnostics and tests differ.
    module = "src/edp_lab/operating/policy_broker.py"
    require(
        (install.BASE / "runtime" / module).read_bytes()
        == subprocess.run(
            ["/usr/bin/git", "-c", f"safe.directory={install.ROOT}",
             "-C", str(install.ROOT), "show", f"{OLD_COMMIT}:{module}"],
            capture_output=True, check=True, timeout=30,
        ).stdout,
        "DAY7_ORIGINAL_BROKER_CODE_CHANGED",
    )
    # The old installer mistakenly wrote literal backslash-n to revoked JSON.
    require(REVOKED.read_bytes() in (b"[]\\n", b"[]\n"),
            "DAY7_REVOKED_GRANTS_UNEXPECTED")
    require(not any((install.BASE / "grants").iterdir()),
            "DAY7_EXISTING_GRANTS_UNEXPECTED")
    principal = install.admin("service-principals", "get", SP_ID)
    require(str(principal.get("id")) == SP_ID
            and principal.get("active", True) is True
            and principal.get("displayName") == install.SP_NAME
            and principal.get("applicationId") == identity["application_id"],
            "DAY7_SERVICE_PRINCIPAL_CHANGED")
    matches = install._find_exact_service_principals()
    require(len(matches) == 1 and str(matches[0]["id"]) == SP_ID,
            "DAY7_SERVICE_PRINCIPAL_NOT_UNIQUE")
    assignment = install.admin(
        "api", "get", "/api/2.0/identity/workspace-assignments/" + SP_ID)
    effective = set(assignment.get("effective_entitlements", []))
    require(str(assignment.get("principal_id")) == SP_ID
            and assignment.get("principal_type") == "SERVICE_PRINCIPAL"
            and {"WORKSPACE_ACCESS", "DATABRICKS_SQL_ACCESS"} <= effective
            and "WORKSPACE_ADMIN" not in effective,
            "DAY7_SERVICE_WORKSPACE_ENTITLEMENTS_CHANGED")
    require(len(_secret_metadata()) == 0,
            "DAY7_SECRET_ALREADY_EXISTS_RECONCILE_DO_NOT_CREATE")
    install.verify_canary_raw_read_only()
    return journal, identity


def _store_oauth_profile(identity: dict, response: dict) -> None:
    secret = response.get("secret")
    require(isinstance(secret, str) and len(secret) >= 12,
            "DAY7_SECRET_CREATED_BUT_VALUE_UNAVAILABLE_MANUAL_RECONCILIATION")
    require(isinstance(response.get("id"), str) and response["id"],
            "DAY7_SECRET_CREATED_BUT_ID_MISSING_MANUAL_RECONCILIATION")
    require(not CONFIG.exists() and not CONFIG_TEMP.exists(),
            "DAY7_SECRET_DESTINATION_ALREADY_EXISTS")
    config_text = (
        "[edp-lab]\n"
        f"host = {install.HOST}\n"
        "auth_type = oauth-m2m\n"
        f"client_id = {identity['application_id']}\n"
        f"client_secret = {secret}\n"
    )
    # O_EXCL and 0600 at creation, rather than chmod after writing secrets.
    fd = os.open(CONFIG_TEMP, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(config_text)
        stream.flush()
        os.fsync(stream.fileno())
    CONFIG_TEMP.chmod(0o600)
    parser = ConfigParser(interpolation=None)
    parser.read(CONFIG_TEMP)
    require(
        parser.get("edp-lab", "auth_type", fallback="") == "oauth-m2m"
        and parser.get("edp-lab", "host", fallback="") == install.HOST
        and parser.get("edp-lab", "client_id", fallback="")
        == identity["application_id"]
        and parser.get("edp-lab", "client_secret", fallback="") == secret,
        "DAY7_STORED_M2M_PROFILE_INVALID",
    )
    os.replace(CONFIG_TEMP, CONFIG)


def recover(expected_commit: str) -> dict:
    journal, identity = _confirmed_before_mutation(expected_commit)
    # Durable one-use intent prevents a second create after uncertain HTTP
    # submission, even if a caller blindly re-executes this script.
    install._save_json(RECOVERY_INTENT, {
        "schema": "EDP_DAY7_SECRET_RECOVERY_ATTEMPT_V1",
        "old_install_commit": OLD_COMMIT,
        "repair_commit": expected_commit,
        "service_principal_id": SP_ID,
        "application_id": identity["application_id"],
        "prior_request_independently_found_zero_secrets": True,
    })
    command = [
        "/usr/bin/sudo", "-n", "-u", "lightnino", "-H",
        install.CLI, "service-principal-secrets-proxy", "create", SP_ID,
        "--lifetime", "7776000", "-p", "edp-lab", "-o", "json",
    ]
    result = subprocess.run(
        command, capture_output=True, text=True, check=False, timeout=120,
    )
    if result.returncode:
        try:
            remaining = len(_secret_metadata())
        except (OSError, ValueError, subprocess.CalledProcessError):
            remaining = "UNKNOWN"
        raise RuntimeError(
            "DAY7_CONTROLLED_SECRET_CREATE_BLOCKED:"
            + _safe_error(result.stderr)
            + f":remote_secret_count={remaining}:NO_AUTOMATIC_RETRY"
        )
    try:
        value = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError(
            "DAY7_SECRET_CREATE_RESPONSE_INVALID_NO_RETRY"
        ) from exc
    _store_oauth_profile(identity, value)

    # Authenticate BEFORE migrating the journal pin or doing UC/Job writes.
    observed = install.service("current-user", "me")
    require(str(observed.get("id")) == SP_ID,
            "DAY7_M2M_AUTHENTICATED_PRINCIPAL_CHANGED")
    # Verify the newly issued secret is actually present without printing it.
    require(len(_secret_metadata()) == 1,
            "DAY7_SECRET_CREATION_REMOTE_READBACK_UNVERIFIED")

    # Repair only the known old malformed trust JSON and leave signed policy
    # and historic receipts unchanged.
    if REVOKED.read_bytes() == b"[]\\n":
        normalized = REVOKED.with_name("revoked_grants.json.recovery-temp")
        require(not normalized.exists(), "DAY7_REVOKED_RECOVERY_ALREADY_STARTED")
        fd = os.open(normalized, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(b"[]\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(normalized, REVOKED)

    journal["reviewed_commit"] = expected_commit
    journal["completed"]["secret_recovery"] = {
        "from_commit": OLD_COMMIT,
        "service_principal_id": SP_ID,
        "m2m_verified": True,
    }
    install._save_json(install.JOURNAL, journal)
    # Resume remaining original checkpoints in this one Owner invocation.
    # The new installer verifies actual remote effects for every subsequent
    # stage and preserves the existing SP, source evidence and C2000 freeze.
    sys.argv = [str(install.ROOT / "scripts/owner_install_day7.py"),
                expected_commit]
    install.main()
    return {
        "status": "DAY7_PARTIAL_INSTALL_RECOVERED",
        "service_principal_id": SP_ID,
        "reviewed_commit": expected_commit,
        "secret_value": "NEVER_PRINTED",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    args = parser.parse_args()
    print(json.dumps(recover(args.expected_commit), sort_keys=True))


if __name__ == "__main__":
    main()
