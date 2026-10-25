"""One reviewed root action for the isolated Day 7 Cohort successor.

Run only in the Owner's Terminal from a clean, pinned commit. The script never
touches Day 5 or Vault runtime state. A partial install stops for reconciliation
instead of replaying a potentially uncertain external write.
"""

from __future__ import annotations

import argparse
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
POLICY_SHA = "a3ebfc053ce87914d7335e404b7baa9a1e265e61066088bcb7515e5ec18c4a6b"
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
    env = dict(os.environ, EDP_DAY7_PROTECTED="1",
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
            (ROOT / "metadata/authorizations/day7_universe_expansion_800_owner_decision.json",
             DECISION_SHA))
    if any(file_digest(path) != sha for path, sha in pins):
        raise RuntimeError("REVIEWED_DAY7_PIN_CHANGED")
    manifest = json.loads((ROOT / "metadata/source_universes/approved/manifest.json").read_bytes())
    old = {row["source_identity"] for row in json.loads(
        (ROOT / "metadata/freezes/C2000_v1/C2000.bindings.json").read_bytes())}
    eligible = [row for row in manifest["members"]
                if not row["holdout"] and row["identity"] not in old]
    remote_bound = [row for row in eligible
                    if all(key in row for key in
                           ("remote_raw_path", "remote_receipt_path",
                            "remote_receipt_sha256", "raw_bytes"))]
    if len(eligible) != 1780 or len(remote_bound) < 1000:
        raise RuntimeError("DAY7_N1000_HANDOFF_COVERAGE_INSUFFICIENT_"
                           f"{len(remote_bound)}_OF_1000")
    if not PYTHON.is_file() or not all((DAY5 / "private" / (role + ".pem")).is_file()
                                       for role in ("owner", "broker", "verifier")):
        raise RuntimeError("EXISTING_COHORT_PROTECTED_INFRASTRUCTURE_REQUIRED")
    if PLIST.exists() or BASE.exists():
        raise RuntimeError("PARTIAL_OR_EXISTING_DAY7_INSTALL_RECONCILE_BEFORE_RETRY")
    principal = admin("current-user", "me")
    if (principal.get("userName") != "chengzhu13@gmail.com"
            or "admins" not in {group.get("display") for group in principal.get("groups", [])}):
        raise RuntimeError("OWNER_ADMIN_IDENTITY_REQUIRED")
    existing = admin("service-principals", "list", "--filter",
                     f'displayName sw "{SP_NAME}"')
    if existing and (existing if isinstance(existing, list)
                     else existing.get("Resources", existing.get("service_principals", []))):
        raise RuntimeError("DAY7_SERVICE_PRINCIPAL_ALREADY_EXISTS")
    present = subprocess.run(["/usr/bin/sudo", "-n", "-u", "lightnino", "-H",
                              CLI, "schemas", "get", SCHEMA, "-p", "edp-lab",
                              "-o", "json"], capture_output=True, text=True,
                             check=False, timeout=30)
    if present.returncode == 0:
        raise RuntimeError("DAY7_TARGET_SCHEMA_ALREADY_EXISTS")
    if "does not exist" not in present.stderr.lower():
        raise RuntimeError("DAY7_TARGET_SCHEMA_ABSENCE_NOT_PROVEN")


def protected_files(expected_commit: str) -> None:
    from edp_lab.operating.authority import verified_document
    from edp_lab.operating.protected_verifier import _sign

    BASE.mkdir(mode=0o755)
    for name, mode in (("private", 0o700), ("trust", 0o755),
                       ("receipts", 0o700), ("grants", 0o700),
                       ("ledger", 0o700), ("runtime", 0o755)):
        (BASE / name).mkdir(mode=mode)
    for role in ("owner", "broker", "verifier"):
        shutil.copyfile(DAY5 / "trust" / (role + "_ed25519_public.pem"),
                        BASE / "trust" / (role + "_ed25519_public.pem"))
    (BASE / "trust/revoked_grants.json").write_text("[]\n")
    archive = subprocess.run(["/usr/bin/git", "-c", f"safe.directory={ROOT}",
                              "-C", str(ROOT), "archive", expected_commit,
                              "src/edp_lab"], capture_output=True, check=True,
                             timeout=60).stdout
    with tarfile.open(fileobj=BytesIO(archive)) as tar:
        tar.extractall(BASE / "runtime", filter="data")
    for path in (BASE / "runtime").rglob("*"):
        path.chmod(path.stat().st_mode & ~0o022)
    policy = json.loads(POLICY.read_bytes())
    _sign(policy, DAY5 / "private/owner.pem", BASE / "trust/policy.signed.json")
    verified_document(ROOT, BASE / "trust/policy.signed.json", BASE / "trust")


def service_identity() -> tuple[str, str]:
    created = admin("service-principals", "create", "--display-name", SP_NAME)
    sp_id, app_id = str(created["id"]), created["applicationId"]
    # The secret is never printed or stored in the repository. A partial
    # failure requires protected reconciliation, never a blind second create.
    secret = admin("service-principal-secrets-proxy", "create", sp_id,
                   "--lifetime", "7776000")["secret"]
    config = BASE / "private/databrickscfg"
    config.write_text("[edp-lab]\n" + f"host = {HOST}\n"
                      + "auth_type = oauth-m2m\n"
                      + f"client_id = {app_id}\nclient_secret = {secret}\n")
    config.chmod(0o600)
    principal = service("current-user", "me")
    if principal.get("applicationId") != app_id:
        raise RuntimeError("DAY7_M2M_IDENTITY_MISMATCH")
    identity = BASE / "private/service-identity.json"
    identity.write_text(json.dumps({"service_principal_id": sp_id,
                                    "application_id": app_id}, sort_keys=True))
    identity.chmod(0o600)
    return sp_id, app_id


def permissions(app_id: str) -> None:
    admin_sql(f"CREATE SCHEMA {SCHEMA}")
    admin_sql(f"CREATE VOLUME {SCHEMA}.artifacts")
    admin_sql(f"GRANT USE CATALOG ON CATALOG workspace TO `{app_id}`")
    admin_sql(f"GRANT USE SCHEMA, CREATE TABLE ON SCHEMA {SCHEMA} TO `{app_id}`")
    admin_sql(f"GRANT READ VOLUME, WRITE VOLUME ON VOLUME {SCHEMA}.artifacts "
              f"TO `{app_id}`")
    admin_sql(f"GRANT USE SCHEMA ON SCHEMA workspace.edp_lab TO `{app_id}`")
    admin_sql(f"GRANT READ VOLUME ON VOLUME workspace.edp_lab.raw TO `{app_id}`")
    admin_sql("GRANT SELECT ON TABLE workspace.edp_lab."
              f"o_c2000_m2_result_frozen_day5_v1 TO `{app_id}`")
    admin("permissions", "update", "warehouses", WAREHOUSE, "--json",
          json.dumps({"access_control_list": [{"service_principal_name": app_id,
                                                 "permission_level": "CAN_USE"}]}))
    raw = admin("grants", "get-effective", "volume", "workspace.edp_lab.raw",
                "--principal", app_id)
    old = admin("grants", "get-effective", "table",
                "workspace.edp_lab.o_c2000_m2_result_frozen_day5_v1",
                "--principal", app_id)

    def privileges(response: dict) -> set[str]:
        return {item.get("privilege", item) for assignment in
                response.get("privilege_assignments", [])
                for item in assignment.get("privileges", [])}

    if ("READ_VOLUME" not in privileges(raw)
            or privileges(raw) & {"WRITE_VOLUME", "ALL_PRIVILEGES", "MANAGE"}
            or "SELECT" not in privileges(old)
            or privileges(old) & {"MODIFY", "ALL_PRIVILEGES", "MANAGE"}):
        raise RuntimeError("DAY7_SERVICE_RAW_OR_PRIOR_PRIVILEGE_INVALID")


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
                  if "remote_raw_path" in row)
    handoff = attest_handoff(ROOT, policy, trust, key,
                             member["identity"], live_canary=True)
    return universe, prior, handoff


def canary(expected_commit: str) -> dict:
    admin("workspace", "mkdirs", str(Path(NOTEBOOK).parent))
    admin("workspace", "import", NOTEBOOK, "--file", str(CANARY_SOURCE),
          "--format", "SOURCE", "--language", "PYTHON")
    notebook = admin("workspace", "get-status", NOTEBOOK)
    if notebook.get("object_type") != "NOTEBOOK" or not notebook.get("object_id"):
        raise RuntimeError("DAY7_CANARY_NOTEBOOK_IMPORT_UNVERIFIED")
    app_id = json.loads((BASE / "private/service-identity.json").read_bytes())["application_id"]
    admin("permissions", "update", "notebooks", str(notebook["object_id"]),
          "--json", json.dumps({"access_control_list": [{
              "service_principal_name": app_id, "permission_level": "CAN_READ"}]}))
    payload = {"idempotency_token": "day7-pr80-canary-" + expected_commit[:32],
               "run_name": "day7-pr80-protected-canary",
               "timeout_seconds": 1800,
               "tasks": [{"task_key": "canary", "timeout_seconds": 1800,
                          "max_retries": 0,
                          "notebook_task": {"notebook_path": NOTEBOOK,
                                            "source": "WORKSPACE"}}]}
    checkpoint = BASE / "ledger/canary-submit-intent.json"
    checkpoint.write_text(json.dumps({"payload": payload,
                                      "source_sha256": file_digest(CANARY_SOURCE)}))
    result = service("jobs", "submit", "--json", json.dumps(payload), "--no-wait")
    run_id = str(result["run_id"])
    (BASE / "ledger/canary-run-id").write_text(run_id)
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
    return {"job_run_id": run_id, "task_run_id": str(task["run_id"]),
            "table": CANARY_TABLE, "table_id": table["table_id"],
            "notebook_sha256": file_digest(CANARY_SOURCE),
            "result": "DAY7_PROTECTED_CANARY_PASS"}


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
    PLIST.write_text(xml)
    PLIST.chmod(0o644)
    run("/bin/launchctl", "bootstrap", "system", str(PLIST))
    run("/bin/launchctl", "print", "system/" + LABEL)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    args = parser.parse_args()
    preflight(args.expected_commit)
    from edp_lab.operating.authority import verified_document
    from edp_lab.operating.protected_verifier import _sign

    protected_files(args.expected_commit)
    sp_id, app_id = service_identity()
    permissions(app_id)
    universe, prior, handoff = publication()
    job = canary(args.expected_commit)
    install_broker()
    receipt = {"schema": "EDP_DAY7_DEPLOYMENT_RECEIPT_V1",
               "authority": "protected-verifier-v1", "status": "RUNNER_DEPLOYED_AND_VERIFIED",
               "commit": args.expected_commit,
               "policy_sha256": file_digest(BASE / "trust/policy.signed.json"),
               "service_principal_id": sp_id, "service_application_id": app_id,
               "service_auth": "OAUTH_M2M", "raw_write_volume_privilege": False,
               "prior_modify_privilege": False, "universe": universe,
               "prior": prior, "u10_canary": handoff, "job_canary": job}
    _sign(receipt, DAY5 / "private/verifier.pem",
          BASE / "receipts/day7-deployment.json")
    verified_document(ROOT, BASE / "receipts/day7-deployment.json", BASE / "trust")
    print(json.dumps({"status": receipt["status"],
                      "deployment_receipt_sha256": file_digest(
                          BASE / "receipts/day7-deployment.json"),
                      "universe_receipt_sha256": universe["receipt_sha256"],
                      "prior_receipt_sha256": prior["receipt_sha256"],
                      "u10_canary_receipt_sha256": handoff["receipt_sha256"],
                      "service_application_id": app_id,
                      "canary_run_id": job["job_run_id"]}, sort_keys=True))


if __name__ == "__main__":
    main()
