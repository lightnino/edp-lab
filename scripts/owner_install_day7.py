"""One reviewed root action for the isolated Day 7 Cohort successor.

Run only in the Owner's Terminal from a clean, pinned commit. The script never
touches Day 5 or Vault runtime state. A partial install stops for reconciliation
instead of replaying a potentially uncertain external write.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import time
from io import BytesIO
from pathlib import Path

ROOT = Path("/Users/lightnino/Projects/edp-lab-day7-universe")
BASE = Path("/private/var/db/edp-lab-day7")
DAY5 = Path("/private/var/db/edp-lab")
POLICY = ROOT / "metadata/operating/day7_c3000_standing_policy_unsigned_v1.json"
SOURCE_INDEX = ROOT / "metadata/source_universes/approved/source_evidence_index_v1.json"
JOURNAL = BASE / "ledger/day7-install.json"
POLICY_SHA = "add8ec782742bea6ed2d8dfaf1fb7281706e6b47cdc9390abe76892c5e235d33"
SOURCE_INDEX_SHA = "981207077b3710e3f60c3d669a27dcd84b74cf6aafb341354737ed74e2f645fc"
MANIFEST_SHA = "dcc63767c88ae712eab8f5ba29d52a206b4262710740e591a4b233d9c04c699b"
DECISION_SHA = "416efc5f7ab18b2570ba9beab26bba33210c5e0a75ec813a92ccac953af36d74"
HOST = "https://dbc-23e7784b-bb6e.cloud.databricks.com"
WAREHOUSE = "589e80595c7c8cb8"
SP_NAME = "edp-lab-day7-c3000-cohort"
SCHEMA = "workspace.edp_lab_day7_c3000"
NOTEBOOK = "/Shared/edp-lab-day7-c3000/pr80-protected-canary"
CANARY_TABLE = SCHEMA + ".canary_pr80_v1"
CANARY_SOURCE = ROOT / "notebooks/day7_c3000_protected_canary_v1.py"
LABEL = "org.edp-lab.day7-policy-broker"
PLIST = Path("/Library/LaunchDaemons") / (LABEL + ".plist")
CLI = "/opt/homebrew/bin/databricks"
PYTHON = DAY5 / "python/bin/python3.12"


def file_digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def run(*argv: str, env: dict | None = None) -> str:
    result = subprocess.run(argv, env=env, text=True, capture_output=True,
                            check=True, timeout=900)
    return result.stdout


def admin(*args: str) -> dict:
    value = run("/usr/bin/sudo", "-n", "-u", "lightnino", "-H", CLI,
                *args, "-p", "edp-lab", "-o", "json")
    return json.loads(value) if value.strip() else {}


def service(*args: str) -> dict:
    # Do not allow inherited Owner/U2M OAuth or PAT variables to supersede
    # the protected M2M profile. Databricks env config takes precedence.
    env = {k: v for k, v in os.environ.items() if not k.startswith("DATABRICKS_")}
    env.update(EDP_DAY7_PROTECTED="1",
               DATABRICKS_CONFIG_FILE=str(BASE / "private/databrickscfg"),
               HOME=str(BASE / "private"))
    return json.loads(run(CLI, *args, "-p", "edp-lab", "-o", "json", env=env))


def admin_sql(statement: str) -> dict:
    request = {"warehouse_id": WAREHOUSE, "statement": statement,
               "wait_timeout": "50s", "on_wait_timeout": "CONTINUE",
               "disposition": "INLINE"}
    result = admin("api", "post", "/api/2.0/sql/statements",
                   "--json", json.dumps(request))
    deadline = time.monotonic() + 600
    while result.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        if time.monotonic() > deadline:
            raise RuntimeError("UNCERTAIN_ADMIN_SQL_CHECK_STATEMENT_ID_" + result["statement_id"])
        time.sleep(4)
        result = admin("api", "get", "/api/2.0/sql/statements/" + result["statement_id"])
    if result.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError("ADMIN_SQL_FAILED_" + result["statement_id"])
    return result



def _save_json(path: Path, obj: dict) -> None:
    """Durable replace; never write credentials or volatile tokens to Git."""
    tmp = path.with_name(path.name + ".new")
    if tmp.exists():
        raise RuntimeError("DAY7_PARTIAL_JOURNAL_WRITE_NEEDS_RECONCILIATION")
    with tmp.open("x") as stream:
        json.dump(obj, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_bytes())


def _install_intent(expected_commit: str) -> dict:
    return {
        "schema": "EDP_DAY7_OWNER_INSTALL_JOURNAL_V1",
        "reviewed_commit": expected_commit,
        "universe_sha256": MANIFEST_SHA,
        "source_evidence_sha256": SOURCE_INDEX_SHA,
        "policy_sha256": POLICY_SHA,
    }


def _mark(name: str, detail: dict | None = None) -> None:
    journal = _read_json(JOURNAL)
    value = detail or {"status": "VERIFIED"}
    existing = journal.setdefault("completed", {}).get(name)
    if existing is not None and existing != value:
        raise RuntimeError("DAY7_INSTALLED_STAGE_EVIDENCE_CHANGED:" + name)
    if existing is None:
        journal["completed"][name] = value
        _save_json(JOURNAL, journal)


def _completed(name: str) -> bool:
    return name in _read_json(JOURNAL).get("completed", {})


def verify_canary_raw_read_only() -> dict:
    """Prove SRC000002 original RAW exists before ANY protected or cloud write.

    The Owner's existing interactive identity is used exclusively for this
    pre-deployment read; the deployed broker must independently re-verify via
    its protected M2M identity before a U10 receipt is signed.
    """
    index = _read_json(SOURCE_INDEX)
    sources = [row for row in index["original_sources"]
               if row.get("physical_identity") == "SRC000002"]
    if len(sources) != 1:
        raise RuntimeError("DAY7_CANARY_IDENTITY_NOT_UNIQUE")
    source = sources[0]
    locators = [row for row in index.get("known_original_locators", [])
                if (row.get("physical_identity") == "SRC000002"
                    and row.get("sha256") == source["raw_sha256"]
                    and row.get("bytes") == source["raw_bytes"])]
    if len(locators) != 1:
        raise RuntimeError("DAY7_CANARY_LOCATOR_NOT_PINNED")
    locator = locators[0]["remote_path"]
    if (not isinstance(locator, str)
            or not locator.startswith("dbfs:/Volumes/workspace/edp_lab/raw/")
            or ".." in locator.split("/")):
        raise RuntimeError("DAY7_CANARY_REMOTE_PATH_INVALID")
    result = subprocess.run(
        ["/usr/bin/sudo", "-n", "-u", "lightnino", "-H",
         CLI, "fs", "cat", locator, "-p", "edp-lab"],
        capture_output=True, check=False, timeout=180,
    )
    if (result.returncode != 0
            or len(result.stdout) != source["raw_bytes"]
            or hashlib.sha256(result.stdout).hexdigest() != source["raw_sha256"]):
        raise RuntimeError("DAY7_CANARY_REMOTE_FULL_HASH_READBACK_FAILED")
    return {"physical_identity": "SRC000002", "remote_path": locator,
            "raw_sha256": source["raw_sha256"], "raw_bytes": source["raw_bytes"]}


def preflight(expected_commit: str) -> None:
    if os.geteuid() != 0 or Path(__file__).resolve().parents[1] != ROOT:
        raise RuntimeError("OWNER_ROOT_TERMINAL_AND_DAY7_WORKTREE_REQUIRED")
    if run("/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
           "rev-parse", "HEAD").strip() != expected_commit:
        raise RuntimeError("UNREVIEWED_DAY7_COMMIT")
    if run("/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
           "status", "--porcelain").strip():
        raise RuntimeError("DAY7_WORKTREE_NOT_CLEAN")
    pins = ((POLICY, POLICY_SHA),
            (ROOT / "metadata/source_universes/approved/manifest.json", MANIFEST_SHA),
            (ROOT / "metadata/source_universes/approved/source_evidence_index_v1.json",
             SOURCE_INDEX_SHA),
            (ROOT / "metadata/authorizations/day7_universe_expansion_800_owner_decision.json",
             DECISION_SHA))
    if any(file_digest(path) != sha for path, sha in pins):
        raise RuntimeError("REVIEWED_DAY7_PIN_CHANGED")
    manifest = json.loads((ROOT / "metadata/source_universes/approved/manifest.json").read_bytes())
    old = {row["source_identity"] for row in json.loads(
        (ROOT / "metadata/freezes/C2000_v1/C2000.bindings.json").read_bytes())}
    eligible = [row for row in manifest["members"]
                if not row["holdout"] and row["identity"] not in old]
    if len(eligible) != 1780:
        raise RuntimeError("DAY7_ELIGIBLE_UNIVERSE_COUNT_CHANGED")
    if not PYTHON.is_file() or not all((DAY5 / "private" / (role + ".pem")).is_file()
                                       for role in ("owner", "broker", "verifier")):
        raise RuntimeError("EXISTING_COHORT_PROTECTED_INFRASTRUCTURE_REQUIRED")
    recovering = BASE.exists()
    if recovering:
        if (PLIST.exists() and (PLIST.is_symlink() or PLIST.stat().st_uid != 0)):
            raise RuntimeError("DAY7_UNOWNED_LAUNCHDAEMON_CHANGED")
        if (BASE.is_symlink() or BASE.stat().st_uid != 0
                or BASE.stat().st_mode & 0o077
                or not JOURNAL.is_file() or JOURNAL.is_symlink()
                or JOURNAL.stat().st_uid != 0
                or {k: v for k, v in _read_json(JOURNAL).items()
                    if k != "completed"} != _install_intent(expected_commit)
                or not isinstance(_read_json(JOURNAL).get("completed"), dict)):
            raise RuntimeError("DAY7_EXISTING_INSTALL_JOURNAL_PIN_MISMATCH")
    elif PLIST.exists():
        raise RuntimeError("DAY7_UNOWNED_LAUNCHDAEMON_EXISTS")
    principal = admin("current-user", "me")
    if (principal.get("userName") != "chengzhu13@gmail.com"
            or "admins" not in {group.get("display") for group in principal.get("groups", [])}):
        raise RuntimeError("OWNER_ADMIN_IDENTITY_REQUIRED")
    existing = _find_exact_service_principals()
    if existing and not recovering:
        raise RuntimeError("DAY7_SERVICE_PRINCIPAL_ALREADY_EXISTS")
    if len(existing) > 1:
        raise RuntimeError("DAY7_SERVICE_PRINCIPAL_DUPLICATE_UNSAFE")
    present = subprocess.run(["/usr/bin/sudo", "-n", "-u", "lightnino", "-H",
                              CLI, "schemas", "get", SCHEMA, "-p", "edp-lab",
                              "-o", "json"], capture_output=True, text=True,
                             check=False, timeout=30)
    if present.returncode == 0 and not recovering:
        raise RuntimeError("DAY7_TARGET_SCHEMA_ALREADY_EXISTS")
    if present.returncode != 0 and "does not exist" not in present.stderr.lower():
        raise RuntimeError("DAY7_TARGET_SCHEMA_ABSENCE_NOT_PROVEN")
    if not recovering:
        notebook = subprocess.run(
            ["/usr/bin/sudo", "-n", "-u", "lightnino", "-H",
             CLI, "workspace", "get-status", NOTEBOOK,
             "-p", "edp-lab", "-o", "json"],
            capture_output=True, text=True, check=False, timeout=30)
        if notebook.returncode == 0:
            raise RuntimeError("DAY7_CANARY_NOTEBOOK_ALREADY_OWNED")
        error = notebook.stderr.upper()
        if not any(term in error for term in
                   ("RESOURCE_DOES_NOT_EXIST", "PATH_NOT_FOUND", "DOESN'T EXIST",
                    "DOES NOT EXIST")):
            raise RuntimeError("DAY7_CANARY_NOTEBOOK_ABSENCE_UNVERIFIED")
    # This must run before protected_files, SP creation, UC grants or any Job.
    # The installer cannot assume that a documented legacy locator still exists.
    verify_canary_raw_read_only()



def _find_exact_service_principals() -> list[dict]:
    found = admin("service-principals", "list", "--filter",
                  f'displayName sw "{SP_NAME}"')
    rows = found if isinstance(found, list) else found.get(
        "Resources", found.get("service_principals", []))
    return [item for item in rows if item.get("displayName") == SP_NAME]


def protected_files(expected_commit: str) -> None:
    from edp_lab.operating.authority import verified_document
    from edp_lab.operating.protected_verifier import _sign

    BASE.mkdir(mode=0o700, exist_ok=True)
    for name, mode in (("private", 0o700), ("trust", 0o700),
                       ("receipts", 0o700), ("grants", 0o700),
                       ("ledger", 0o700), ("runtime", 0o700)):
        (BASE / name).mkdir(mode=mode, exist_ok=True)
    if not JOURNAL.exists():
        _save_json(JOURNAL, {**_install_intent(expected_commit), "completed": {}})
        JOURNAL.chmod(0o600)
    elif {k: v for k, v in _read_json(JOURNAL).items() if k != "completed"} != (
            _install_intent(expected_commit)):
        raise RuntimeError("DAY7_INSTALL_JOURNAL_PIN_MISMATCH")

    if _completed("protected_files"):
        verified_document(ROOT, BASE / "trust/policy.signed.json", BASE / "trust")
        if file_digest(BASE / "source_evidence_index.json") != SOURCE_INDEX_SHA:
            raise RuntimeError("DAY7_PROTECTED_INDEX_CHANGED")
        return
    for role in ("owner", "broker", "verifier"):
        dest = BASE / "trust" / (role + "_ed25519_public.pem")
        src = DAY5 / "trust" / (role + "_ed25519_public.pem")
        if dest.exists() and dest.read_bytes() != src.read_bytes():
            raise RuntimeError("DAY7_TRUST_KEY_CHANGED")
        shutil.copyfile(src, dest)
    revoked = BASE / "trust/revoked_grants.json"
    if revoked.exists() and revoked.read_text() != "[]\\n":
        raise RuntimeError("DAY7_REVOKED_GRANTS_CHANGED")
    if not revoked.exists():
        revoked.write_text("[]\\n")
    index_dest = BASE / "source_evidence_index.json"
    if index_dest.exists() and file_digest(index_dest) != SOURCE_INDEX_SHA:
        raise RuntimeError("DAY7_PROTECTED_INDEX_CHANGED")
    shutil.copyfile(SOURCE_INDEX, index_dest)
    index_dest.chmod(0o444)
    archive = subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={ROOT}",
         "-C", str(ROOT), "archive", expected_commit, "src/edp_lab"],
        capture_output=True, check=True, timeout=60,
    ).stdout
    with tarfile.open(fileobj=BytesIO(archive)) as tar:
        tar.extractall(BASE / "runtime", filter="data")
    for item in (BASE / "runtime").rglob("*"):
        item.chmod(item.stat().st_mode & ~0o022)
    signed = BASE / "trust/policy.signed.json"
    if signed.exists():
        prior = verified_document(ROOT, signed, BASE / "trust")
        if prior != _read_json(POLICY):
            raise RuntimeError("DAY7_PROTECTED_POLICY_CHANGED")
    else:
        _sign(_read_json(POLICY), DAY5 / "private/owner.pem", signed)
    verified_document(ROOT, signed, BASE / "trust")
    _mark("protected_files")


def service_identity() -> tuple[str, str]:
    """Reconcile a uniquely named SP; do not regenerate lost OAuth secrets."""
    matches = _find_exact_service_principals()
    if len(matches) > 1:
        raise RuntimeError("DAY7_DUPLICATE_SERVICE_PRINCIPAL")
    if matches:
        created = matches[0]
    else:
        created = admin("service-principals", "create", "--display-name", SP_NAME)
    sp_id, app_id = str(created["id"]), created["applicationId"]
    if not sp_id.isdecimal() or not app_id:
        raise RuntimeError("DAY7_SP_IDENTITY_INVALID")
    observed = admin("service-principals", "get", sp_id)
    if (str(observed.get("id")) != sp_id
            or observed.get("applicationId") != app_id
            or observed.get("displayName") != SP_NAME):
        raise RuntimeError("DAY7_SP_OWNER_IDENTITY_MISMATCH")
    identity = BASE / "private/service-identity.json"
    pinned = {"service_principal_id": sp_id, "application_id": app_id}
    if identity.exists():
        if _read_json(identity) != pinned:
            raise RuntimeError("DAY7_SP_IDENTITY_CHANGED")
    else:
        _save_json(identity, pinned)
        identity.chmod(0o600)
    config = BASE / "private/databrickscfg"
    if not config.exists():
        # If OAuth secret creation returned but credentials were not durably
        # stored, the secret cannot be retrieved. Stop instead of issuing a
        # second orphan credential or silently escalating permissions.
        intent = BASE / "ledger/secret-creation-intent.json"
        if intent.exists():
            raise RuntimeError("DAY7_SECRET_UNCERTAIN_MANUAL_RECONCILIATION")
        _save_json(intent, pinned)
        secret = admin("service-principal-secrets-proxy", "create", sp_id,
                       "--lifetime", "7776000")["secret"]
        temp = config.with_name("databrickscfg.new")
        with temp.open("x") as stream:
            stream.write("[edp-lab]\\n" + f"host = {HOST}\\n"
                         + "auth_type = oauth-m2m\\n"
                         + f"client_id = {app_id}\\nclient_secret = {secret}\\n")
            stream.flush()
            os.fsync(stream.fileno())
        temp.chmod(0o600)
        os.replace(temp, config)
    if config.is_symlink() or config.stat().st_uid != 0 or config.stat().st_mode & 0o077:
        raise RuntimeError("DAY7_M2M_CONFIG_NOT_PROTECTED")
    _mark("service_identity", pinned)
    return sp_id, app_id


def ensure_workspace_access(sp_id: str) -> None:
    """Owner-only IAM; never grant WORKSPACE_ADMIN to the execution SP."""
    expected = {"WORKSPACE_ACCESS", "DATABRICKS_SQL_ACCESS"}
    try:
        assignment = admin("workspace-iam-v2", "get-workspace-assignment-proxy", sp_id)
    except subprocess.CalledProcessError as exc:
        # Fail closed unless the response specifically proves the principal
        # is not yet workspace-assigned; do not conflate forbidden and missing.
        message = (exc.stderr or "").upper()
        if not any(token in message for token in
                   ("RESOURCE_DOES_NOT_EXIST", "NOT_FOUND", "404")):
            raise
        admin("api", "post", "/api/2.0/identity/workspace-assignments",
              "--json", json.dumps({"principal_id": int(sp_id),
                                     "entitlements": sorted(expected)}))
        assignment = admin("workspace-iam-v2", "get-workspace-assignment-proxy", sp_id)
    if (str(assignment.get("principal_id")) != sp_id
            or assignment.get("principal_type") != "SERVICE_PRINCIPAL"):
        raise RuntimeError("DAY7_SP_WORKSPACE_ASSIGNMENT_ID_MISMATCH")
    direct = set(assignment.get("entitlements", []))
    effective = set(assignment.get("effective_entitlements", []))
    if any(value in effective | direct for value in
           ("WORKSPACE_ADMIN", "ALLOW_CLUSTER_CREATE", "ALLOW_INSTANCE_POOL_CREATE")):
        raise RuntimeError("DAY7_SP_UNEXPECTED_ADMIN_OR_COMPUTE_ENTITLEMENT")
    if not expected <= effective:
        if direct - expected:
            raise RuntimeError("DAY7_SP_ENTITLEMENT_SCOPE_CHANGE_REQUIRES_OWNER")
        admin("workspace-iam-v2", "update-workspace-assignment-proxy",
              sp_id, "entitlements", "--json",
              json.dumps({"principal_id": int(sp_id),
                          "entitlements": sorted(direct | expected)}))
    after = admin("workspace-iam-v2", "get-workspace-assignment-proxy", sp_id)
    if (str(after.get("principal_id")) != sp_id
            or not expected <= set(after.get("effective_entitlements", []))
            or "WORKSPACE_ADMIN" in after.get("effective_entitlements", [])):
        raise RuntimeError("DAY7_SP_WORKSPACE_ENTITLEMENT_NOT_VERIFIED")
    _mark("workspace_assignment",
          {"principal_id": sp_id, "entitlements": sorted(expected)})


def verify_service_identity(sp_id: str, app_id: str) -> None:
    """CLI current-user is a SCIM resource with id, not applicationId."""
    principal = service("current-user", "me")
    if (str(principal.get("id")) != sp_id
            or principal.get("active", True) is not True):
        raise RuntimeError("DAY7_M2M_IDENTITY_MISMATCH")
    # Application ID is verified independently against the Owner-scoped SP.
    registered = admin("service-principals", "get", sp_id)
    if (str(registered.get("id")) != sp_id
            or registered.get("applicationId") != app_id):
        raise RuntimeError("DAY7_M2M_APP_ID_MISMATCH")
    _mark("service_auth", {"service_principal_id": sp_id,
                          "application_id": app_id})


def permissions(app_id: str) -> None:
    admin_sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    admin_sql(f"CREATE VOLUME IF NOT EXISTS {SCHEMA}.artifacts")
    admin_sql(f"GRANT USE CATALOG ON CATALOG workspace TO `{app_id}`")
    admin_sql(f"GRANT USE SCHEMA, CREATE TABLE ON SCHEMA {SCHEMA} TO `{app_id}`")
    admin_sql(f"GRANT READ VOLUME, WRITE VOLUME ON VOLUME {SCHEMA}.artifacts "
              f"TO `{app_id}`")
    admin_sql(f"GRANT USE SCHEMA ON SCHEMA workspace.edp_lab TO `{app_id}`")
    admin_sql(f"GRANT READ VOLUME ON VOLUME workspace.edp_lab.raw TO `{app_id}`")
    admin_sql("GRANT SELECT ON TABLE workspace.edp_lab."
              f"o_c2000_m2_result_frozen_day5_v1 TO `{app_id}`")
    def merge_acl(resource: str, resource_id: str, subject: str,
                  permission: str) -> None:
        existing = admin("api", "get", f"/api/2.0/permissions/{resource}/{resource_id}")
        acl = existing.get("access_control_list", [])
        retained = [item for item in acl
                    if item.get("service_principal_name") != subject]
        retained.append({"service_principal_name": subject,
                         "permission_level": permission})
        admin("permissions", "update", resource, resource_id, "--json",
              json.dumps({"access_control_list": retained}))

    merge_acl("warehouses", WAREHOUSE, app_id, "CAN_USE")
    raw = admin("grants", "get-effective", "volume", "workspace.edp_lab.raw",
                "--principal", app_id)
    old = admin("grants", "get-effective", "table",
                "workspace.edp_lab.o_c2000_m2_result_frozen_day5_v1",
                "--principal", app_id)

    def privileges(response: dict) -> set[str]:
        # Databricks returns privilege names as strings, not objects.
        result: set[str] = set()
        for assignment in response.get("privilege_assignments", []):
            for item in assignment.get("privileges", []):
                if isinstance(item, str):
                    result.add(item)
                elif isinstance(item, dict) and isinstance(item.get("privilege"), str):
                    result.add(item["privilege"])
                else:
                    raise RuntimeError("DAY7_GRANT_READBACK_SCHEMA_INVALID")
        return result

    if ("READ_VOLUME" not in privileges(raw)
            or privileges(raw) & {"WRITE_VOLUME", "ALL_PRIVILEGES", "MANAGE"}
            or "SELECT" not in privileges(old)
            or privileges(old) & {"MODIFY", "ALL_PRIVILEGES", "MANAGE"}):
        raise RuntimeError("DAY7_SERVICE_RAW_OR_PRIOR_PRIVILEGE_INVALID")


def submit_canary_once(payload: dict, source_sha256: str) -> str:
    """Submit with a durable intent and Databricks idempotency token."""
    checkpoint = BASE / "ledger/canary-submit-intent.json"
    intent = {"payload": payload, "source_sha256": source_sha256}
    if checkpoint.exists():
        if json.loads(checkpoint.read_bytes()) != intent:
            raise RuntimeError("DAY7_CANARY_RESTART_INTENT_CHANGED")
    else:
        with checkpoint.open("x") as stream:
            stream.write(json.dumps(intent, sort_keys=True))
            stream.flush()
            os.fsync(stream.fileno())
    run_checkpoint = BASE / "ledger/canary-run-id"
    if run_checkpoint.exists():
        run_id = run_checkpoint.read_text().strip()
        if not run_id.isdecimal():
            raise RuntimeError("DAY7_CANARY_RUN_CHECKPOINT_INVALID")
        return run_id
    result = service("jobs", "submit", "--json", json.dumps(payload), "--no-wait")
    run_id = str(result["run_id"])
    with run_checkpoint.open("x") as stream:
        stream.write(run_id + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return run_id


def _check_current_identity_before_writes(sp_id: str) -> None:
    # Exercise non-admin M2M identity before granting the new SP UC rights.
    observed = service("current-user", "me")
    if str(observed.get("id")) != sp_id:
        raise RuntimeError("DAY7_SERVICE_PRINCIPAL_NOT_CURRENT_USER")


def publication() -> tuple[dict, dict, dict]:
    from edp_lab.operating.day7_protected import (
        attest_handoff,
        attest_prior,
        attest_universe,
    )

    trust = BASE / "trust"
    policy = trust / "policy.signed.json"
    key = DAY5 / "private/verifier.pem"
    os.environ.update(EDP_DAY7_PROTECTED="1",
                      DATABRICKS_CONFIG_FILE=str(BASE / "private/databrickscfg"),
                      HOME=str(BASE / "private"))
    universe = attest_universe(ROOT, policy, trust, key,
                               BASE / "receipts/day7-universe.json")
    prior = attest_prior(ROOT, policy, trust, key,
                         BASE / "receipts/c2000-prior.json")
    from edp_lab.ingestion.universe import UniverseGate

    member = next(row for row in UniverseGate.load(ROOT).document()["members"]
                  if row.get("identity") == "SRC000002")
    handoff = attest_handoff(ROOT, policy, trust, key,
                             member["identity"], live_canary=True)
    return universe, prior, handoff


def canary(expected_commit: str) -> dict:
    admin("workspace", "mkdirs", str(Path(NOTEBOOK).parent))
    # This notebook path is exclusive to the pinned Day 7 installer. On
    # restart, upload exactly the same immutable source; never overwrite a
    # pre-existing path from an unowned fresh installation.
    admin("workspace", "import", NOTEBOOK, "--file", str(CANARY_SOURCE),
          "--format", "SOURCE", "--language", "PYTHON", "--overwrite")
    notebook = admin("workspace", "get-status", NOTEBOOK)
    if notebook.get("object_type") != "NOTEBOOK" or not notebook.get("object_id"):
        raise RuntimeError("DAY7_CANARY_NOTEBOOK_IMPORT_UNVERIFIED")
    app_id = json.loads((BASE / "private/service-identity.json").read_bytes())["application_id"]
    existing_acl = admin("api", "get",
                         f"/api/2.0/permissions/notebooks/{notebook['object_id']}")
    acl = [item for item in existing_acl.get("access_control_list", [])
           if item.get("service_principal_name") != app_id]
    acl.append({"service_principal_name": app_id, "permission_level": "CAN_READ"})
    admin("permissions", "update", "notebooks", str(notebook["object_id"]),
          "--json", json.dumps({"access_control_list": acl}))
    payload = {"idempotency_token": "day7-pr80-canary-" + expected_commit[:32],
               "run_name": "day7-pr80-protected-canary",
               "timeout_seconds": 1800,
               "tasks": [{"task_key": "canary", "timeout_seconds": 1800,
                          "max_retries": 0,
                          "notebook_task": {"notebook_path": NOTEBOOK,
                                            "source": "WORKSPACE"}}]}
    # The stable token reconciles an uncertain submit to the same Databricks run.
    run_id = submit_canary_once(payload, file_digest(CANARY_SOURCE))
    deadline = time.monotonic() + 1800
    while True:
        run_state = service("jobs", "get-run", run_id)
        state = run_state["state"]
        if state.get("life_cycle_state") in {"TERMINATED", "SKIPPED", "INTERNAL_ERROR"}:
            break
        if time.monotonic() > deadline:
            raise RuntimeError("UNCERTAIN_DAY7_CANARY_RUN_" + run_id)
        time.sleep(10)
    if state.get("result_state") != "SUCCESS":
        raise RuntimeError("DAY7_CANARY_JOB_FAILED_" + run_id)
    task = run_state["tasks"][0]
    output = service("jobs", "get-run-output", str(task["run_id"]))
    if output.get("notebook_output", {}).get("result") != "DAY7_PROTECTED_CANARY_PASS":
        raise RuntimeError("DAY7_CANARY_NOTEBOOK_RESULT_INVALID")
    table = service("tables", "get", CANARY_TABLE)
    if table.get("full_name") != CANARY_TABLE or not table.get("table_id"):
        raise RuntimeError("DAY7_CANARY_REMOTE_TABLE_UNVERIFIED")
    # Independently read the remote Delta payload as Owner, not solely via
    # the SP-owned Job's notebook exit string.
    readback = admin_sql(
        "SELECT universe_sha256, owner_decision_sha256 FROM " + CANARY_TABLE)
    rows = readback.get("result", {}).get("data_array")
    if rows != [[MANIFEST_SHA, DECISION_SHA]]:
        raise RuntimeError("DAY7_CANARY_OWNER_SQL_READBACK_MISMATCH")
    return {"job_run_id": run_id, "task_run_id": str(task["run_id"]),
            "table": CANARY_TABLE, "table_id": table["table_id"],
            "notebook_sha256": file_digest(CANARY_SOURCE),
            "result": "DAY7_PROTECTED_CANARY_PASS",
            "independent_readback": "OWNER_SQL_EXACT_ONE_ROW"}


def install_broker() -> None:
    from xml.sax.saxutils import escape

    args = [str(PYTHON), "-m", "edp_lab.operating.policy_broker",
            str(BASE / "broker.sock"), str(ROOT),
            str(BASE / "trust/policy.signed.json"), str(BASE / "trust"),
            str(DAY5 / "private/broker.pem"), str(BASE / "grants")]
    values = "".join(f"<string>{escape(arg)}</string>" for arg in args)
    env = {"PYTHONPATH": str(BASE / "runtime/src"),
           "EDP_DAY7_PROTECTED": "1",
           "EDP_DAY7_VERIFIER_KEY": str(DAY5 / "private/verifier.pem"),
           "DATABRICKS_CONFIG_FILE": str(BASE / "private/databrickscfg"),
           "HOME": str(BASE / "private"),
           "PATH": "/opt/homebrew/bin:/usr/bin:/bin"}
    environment = "".join(f"<key>{key}</key><string>{escape(value)}</string>"
                          for key, value in env.items())
    xml = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
           "<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" "
           "\"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n"
           f"<plist version=\"1.0\"><dict><key>Label</key><string>{LABEL}</string>"
           f"<key>ProgramArguments</key><array>{values}</array>"
           f"<key>EnvironmentVariables</key><dict>{environment}</dict>"
           "<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>"
           f"<key>StandardOutPath</key><string>{BASE}/broker.stdout.log</string>"
           f"<key>StandardErrorPath</key><string>{BASE}/broker.stderr.log</string>"
           "</dict></plist>\n")
    if PLIST.exists():
        if PLIST.read_text() != xml:
            raise RuntimeError("DAY7_EXISTING_LAUNCHDAEMON_CHANGED")
    else:
        PLIST.write_text(xml)
        PLIST.chmod(0o644)
    existing = subprocess.run(
        ["/bin/launchctl", "print", "system/" + LABEL],
        capture_output=True, text=True, check=False, timeout=30)
    if existing.returncode != 0:
        run("/bin/launchctl", "bootstrap", "system", str(PLIST))
    run("/bin/launchctl", "print", "system/" + LABEL)
    # Real request through the installed LaunchDaemon, not only a root
    # installer subprocess. The broker must resolve/sign the pinned canary
    # under its own protected OAuth profile.
    from edp_lab.operating.policy_broker import resolve_handoff
    receipt = None
    for _ in range(30):
        try:
            receipt = resolve_handoff(BASE / "broker.sock", "SRC000002")
            break
        except (ConnectionError, FileNotFoundError):
            time.sleep(1)
    if (receipt is None or receipt.get("physical_identity") != "SRC000002"
            or not receipt.get("receipt_sha256")):
        raise RuntimeError("DAY7_BROKER_LIVE_U10_READBACK_INVALID")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    args = parser.parse_args()

    # All feasible fixed-source checks and real RAW readback run BEFORE any
    # protected directory, secret, IAM mutation, Job or remote write.
    preflight(args.expected_commit)
    from edp_lab.operating.authority import verified_document
    from edp_lab.operating.protected_verifier import _sign

    protected_files(args.expected_commit)
    sp_id, app_id = service_identity()
    ensure_workspace_access(sp_id)
    verify_service_identity(sp_id, app_id)

    # UC GRANT/CREATE are scoped and idempotent. Reconcile exact remote
    # state after uncertain failures; never create another SP or secret.
    if not _completed("permissions"):
        permissions(app_id)
        _mark("permissions", {"service_principal_id": sp_id, "verified": True})
    universe, prior, handoff = publication()
    _mark("publication",
          {"universe_receipt_sha256": universe["receipt_sha256"],
           "prior_receipt_sha256": prior["receipt_sha256"],
           "u10_canary_sha256": handoff["receipt_sha256"]})
    job = canary(args.expected_commit)
    _mark("job_canary",
          {"run_id": job["job_run_id"], "table_id": job["table_id"],
           "readback": job["independent_readback"]})
    install_broker()
    _mark("broker", {"launchd_label": LABEL, "live_m2m_u10": True})

    receipt = {"schema": "EDP_DAY7_DEPLOYMENT_RECEIPT_V1",
               "authority": "protected-verifier-v1",
               "status": "RUNNER_DEPLOYED_AND_VERIFIED",
               "commit": args.expected_commit,
               "policy_sha256": file_digest(BASE / "trust/policy.signed.json"),
               "source_evidence_index_sha256": SOURCE_INDEX_SHA,
               "service_principal_id": sp_id, "service_application_id": app_id,
               "service_auth": "OAUTH_M2M",
               "service_workspace_access": "OWNER_VERIFIED_AND_M2M_PROBED",
               "raw_write_volume_privilege": False,
               "prior_modify_privilege": False,
               "universe": universe, "prior": prior,
               "u10_canary": handoff, "job_canary": job}
    path = BASE / "receipts/day7-deployment.json"
    if path.exists():
        prior_receipt = verified_document(ROOT, path, BASE / "trust")
        if prior_receipt != receipt:
            raise RuntimeError("DAY7_DEPLOYMENT_RECEIPT_CHANGED")
    else:
        _sign(receipt, DAY5 / "private/verifier.pem", path)
    verified_document(ROOT, path, BASE / "trust")
    _mark("deployment", {"receipt_sha256": file_digest(path)})

    print(json.dumps({
        "status": receipt["status"],
        "deployment_receipt_sha256": file_digest(path),
        "universe_receipt_sha256": universe["receipt_sha256"],
        "prior_receipt_sha256": prior["receipt_sha256"],
        "u10_canary_receipt_sha256": handoff["receipt_sha256"],
        "service_application_id": app_id,
        "canary_run_id": job["job_run_id"],
        "day7_autonomous_ready": "NOT_ASSERTED_C3000_U10_GATE_PENDING",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
