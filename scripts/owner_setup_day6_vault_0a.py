"""One-time owner-Terminal installer for isolated Day 6 Vault Dev 0A.

Never invoke through Codex. The owner reviews the pinned commit and policy
before running this script as root. It creates no Day 5 paths or services.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import socket
import subprocess
import tarfile
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/private/var/db/edp-lab-day6-vault")
ADMIN_USER = "lightnino"
ADMIN_WAREHOUSE = "589e80595c7c8cb8"
HOST = "https://dbc-23e7784b-bb6e.cloud.databricks.com"
PYTHON_SOURCE = Path("/Users/lightnino/.local/share/uv/python/cpython-3.12-macos-aarch64-none")
PLISTS = ("org.edp-lab.day6-vault-broker", "org.edp-lab.day6-vault-executor")
TABLES = ("h_filing", "h_concept", "l_fact_slot", "r_source_occurrence",
          "s_fact_assertion", "s_num_m2_value", "r_load_event",
          "vault_reject_quarantine")
REMOTE = "dbfs:/Volumes/workspace/edp_lab/raw/c300-verified-v1/"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(*args: str, admin: bool = False, capture: bool = True) -> subprocess.CompletedProcess:
    argv = (["/usr/bin/sudo", "-n", "-u", ADMIN_USER, "-H"] if admin else []) + list(args)
    return subprocess.run(argv, capture_output=capture, text=True, check=True, timeout=900)


def admin_cli(*args: str) -> dict:
    result = run("/opt/homebrew/bin/databricks", *args, "-p", "edp-lab", "-o", "json",
                 admin=True)
    return json.loads(result.stdout)


def admin_sql(sql: str) -> dict:
    request = {"warehouse_id": ADMIN_WAREHOUSE, "statement": sql,
               "wait_timeout": "50s", "on_wait_timeout": "CONTINUE",
               "disposition": "INLINE"}
    result = admin_cli("api", "post", "/api/2.0/sql/statements",
                       "--json", json.dumps(request))
    deadline = time.monotonic() + 600
    while result.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        if time.monotonic() > deadline:
            raise RuntimeError("OWNER_DDL_TIMEOUT_NO_REPLAY")
        time.sleep(4)
        result = admin_cli("api", "get", "/api/2.0/sql/statements/" + result["statement_id"])
    if result.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError("OWNER_DDL_FAILED: " + result["statement_id"])
    return result


def preflight(expected_commit: str, expected_policy_sha: str) -> dict:
    if os.geteuid() != 0:
        raise RuntimeError("OWNER_ROOT_TERMINAL_REQUIRED")
    if ROOT != Path("/Users/lightnino/Projects/edp-lab-day6-vault-prototype"):
        raise RuntimeError("WRONG_WORKTREE")
    if run("/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
           "rev-parse", "HEAD").stdout.strip() != expected_commit:
        raise RuntimeError("UNREVIEWED_COMMIT")
    if run("/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
           "status", "--porcelain", "--untracked-files=no").stdout.strip():
        raise RuntimeError("TRACKED_WORKTREE_CHANGED")
    proposal = ROOT / "metadata/operating/day6_vault_dev_policy_proposal_v1.json"
    if digest(proposal) != expected_policy_sha:
        raise RuntimeError("UNREVIEWED_POLICY")
    if BASE.exists() or any(Path("/Library/LaunchDaemons", label + ".plist").exists()
                            for label in PLISTS):
        raise RuntimeError("VAULT_0A_ALREADY_OR_PARTIALLY_INSTALLED")
    from edp_lab.vault.standing_authority import validate_policy

    policy = json.loads(proposal.read_bytes())
    validate_policy(ROOT, policy,
                    ROOT / "runs/day6-vault-prototype/sample-manifest.json",
                    ROOT / "runs/day6-vault-prototype/projected-manifest.json",
                    ROOT / "runs/day6-vault-prototype/load-plan.json")
    principal = admin_cli("current-user", "me")
    if (principal.get("userName") != "chengzhu13@gmail.com"
            or "admins" not in {group.get("display") for group in principal.get("groups", [])}):
        raise RuntimeError("INDEPENDENT_ADMIN_PRINCIPAL_REQUIRED")
    catalog_grants = admin_cli("grants", "get-effective", "catalog", "workspace",
                               "--principal", principal["userName"])
    catalog_privileges = {entry["privilege"] for assignment in
                          catalog_grants.get("privilege_assignments", [])
                          for entry in assignment.get("privileges", [])}
    if not {"USE_CATALOG", "CREATE_SCHEMA"} <= catalog_privileges:
        raise RuntimeError("VAULT_SCHEMA_CREATE_PRIVILEGE_REQUIRED_FOR_OWNER_ADMIN")
    if admin_cli("service-principals", "list", "--filter",
                 'displayName sw "edp-lab-day6-vault-dev"'):
        raise RuntimeError("VAULT_SERVICE_PRINCIPAL_ALREADY_EXISTS")
    warehouses = admin_cli("warehouses", "list")
    candidates = warehouses if isinstance(warehouses, list) else warehouses.get("warehouses", [])
    if any(w.get("name") == "EDP Day6 Vault Dev V1" for w in candidates):
        raise RuntimeError("VAULT_WAREHOUSE_ALREADY_EXISTS")
    present = subprocess.run(
        ["/usr/bin/sudo", "-n", "-u", ADMIN_USER, "-H",
         "/opt/homebrew/bin/databricks", "schemas", "get",
         "workspace.edp_lab_day6_vault_proto", "-p", "edp-lab", "-o", "json"],
        capture_output=True, text=True, check=False, timeout=30)
    if present.returncode == 0:
        raise RuntimeError("VAULT_SCHEMA_ALREADY_EXISTS")
    if "does not exist" not in present.stderr.lower():
        raise RuntimeError("VAULT_SCHEMA_ABSENCE_NOT_PROVEN")
    return policy


def _protected_directories() -> None:
    BASE.mkdir(mode=0o755)
    for name, mode in (("private", 0o700), ("trust", 0o755), ("grants", 0o755),
                       ("receipts", 0o700), ("ledger", 0o700), ("runtime", 0o755),
                       ("raw", 0o700)):
        (BASE / name).mkdir(mode=mode)


def _service_identity() -> tuple[str, str]:
    created = admin_cli("service-principals", "create",
                        "--display-name", "edp-lab-day6-vault-dev")
    sp_id = str(created["id"])
    app_id = created["applicationId"]
    secret = admin_cli("service-principal-secrets-proxy", "create", sp_id,
                       "--lifetime", "604800")["secret"]
    config = BASE / "private/databrickscfg"
    config.write_text(f"[vault-dev]\nhost = {HOST}\nclient_id = {app_id}\n"
                      f"client_secret = {secret}\n")
    config.chmod(0o600)
    return sp_id, app_id


def _warehouse(app_id: str) -> str:
    response = admin_cli("warehouses", "create", "--name", "EDP Day6 Vault Dev V1",
                         "--cluster-size", "2X-Small", "--min-num-clusters", "1",
                         "--max-num-clusters", "1", "--auto-stop-mins", "10",
                         "--enable-serverless-compute", "--warehouse-type", "PRO",
                         "--no-wait")
    warehouse = response["id"]
    admin_cli("permissions", "update", "warehouses", warehouse,
              "--json", json.dumps({"access_control_list": [{
                  "service_principal_name": app_id, "permission_level": "CAN_USE"}]}))
    return warehouse


def _schema_and_tables(app_id: str) -> list[str]:
    sql = (ROOT / "sql/vault/day6_proto_v1.sql").read_text()
    sql = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    statements = [part.strip().replace("{{SCHEMA}}", "workspace.edp_lab_day6_vault_proto")
                  .replace(" IF NOT EXISTS", "") for part in sql.split(";") if part.strip()]
    if (len(statements) != 9 or not statements[0].startswith(
            "CREATE SCHEMA workspace.edp_lab_day6_vault_proto")
            or any(not statement.startswith(
                f"CREATE TABLE workspace.edp_lab_day6_vault_proto.{table} ")
                for statement, table in zip(statements[1:], TABLES, strict=True))):
        raise RuntimeError("MIGRATION_SCOPE_CHANGED")
    ids = [admin_sql(statement)["statement_id"] for statement in statements]
    admin_sql(f"GRANT USE CATALOG ON CATALOG workspace TO `{app_id}`")
    admin_sql("GRANT USE SCHEMA ON SCHEMA workspace.edp_lab_day6_vault_proto "
              f"TO `{app_id}`")
    for table in TABLES:
        admin_sql("GRANT SELECT, MODIFY ON TABLE "
                  f"workspace.edp_lab_day6_vault_proto.{table} TO `{app_id}`")
        effective = admin_cli("grants", "get-effective", "table",
                              f"workspace.edp_lab_day6_vault_proto.{table}",
                              "--principal", app_id)
        privileges = {entry.get("privilege", entry) for assignment in
                      effective.get("privilege_assignments", []) for entry in
                      assignment.get("privileges", [])}
        if not {"SELECT", "MODIFY"} <= privileges:
            raise RuntimeError("VAULT_TABLE_EFFECTIVE_GRANTS_INCOMPLETE")
    protected = admin_cli("grants", "get-effective", "schema", "workspace.edp_lab",
                          "--principal", app_id)
    inherited = {entry.get("privilege", entry) for assignment in
                 protected.get("privilege_assignments", []) for entry in
                 assignment.get("privileges", [])}
    if inherited & {"CREATE_TABLE", "MODIFY", "ALL_PRIVILEGES", "MANAGE"}:
        raise RuntimeError("VAULT_SP_CAN_WRITE_PROTECTED_SCHEMA")
    return ids


def _raw_copy_and_verify(policy: dict) -> dict:
    sample = json.loads((ROOT / "runs/day6-vault-prototype/sample-manifest.json").read_bytes())
    by_source = {r["source_instance_id"]: r for r in sample["rows"]}
    for sid in policy["source_ids"]:
        row = by_source[sid]
        relative = Path(row["raw_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("RAW_PATH_OUT_OF_SCOPE")
        target = BASE / "raw" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            result = subprocess.run(
                ["/usr/bin/sudo", "-n", "-u", ADMIN_USER, "-H",
                 "/opt/homebrew/bin/databricks", "fs", "cat",
                 REMOTE + str(relative), "-p", "edp-lab"],
                stdout=stream, stderr=subprocess.PIPE, timeout=900, check=False)
        if result.returncode:
            raise RuntimeError("VERIFIED_REMOTE_RAW_COPY_FAILED")
        target.chmod(0o400)
    from edp_lab.vault.raw_verify import verify_selected

    return verify_selected(BASE / "raw", sample["rows"])


def _keys_and_policy(policy: dict, warehouse: str) -> None:
    for role in ("owner", "broker", "verifier"):
        key = BASE / "private" / (role + ".pem")
        run("/opt/homebrew/bin/openssl", "genpkey", "-algorithm", "Ed25519",
            "-out", str(key))
        key.chmod(0o600)
        public = BASE / "trust" / (role + "_ed25519_public.pem")
        run("/opt/homebrew/bin/openssl", "pkey", "-in", str(key),
            "-pubout", "-out", str(public))
    (BASE / "trust/revoked_grants.json").write_text("[]\n")
    policy["warehouse_id"] = warehouse
    payload = (json.dumps(policy, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False) + "\n").encode()
    source = BASE / "private/policy.payload"
    source.write_bytes(payload)
    signature = BASE / "private/policy.sig"
    run("/opt/homebrew/bin/openssl", "pkeyutl", "-sign", "-inkey",
        str(BASE / "private/owner.pem"), "-rawin", "-in", str(source),
        "-out", str(signature))
    envelope = {"document": policy,
                "signature_base64": base64.b64encode(signature.read_bytes()).decode()}
    (BASE / "trust/policy.signed.json").write_text(
        json.dumps(envelope, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False) + "\n")


def _runtime() -> None:
    run("/usr/bin/ditto", str(PYTHON_SOURCE), str(BASE / "python"))
    archive = subprocess.run(["/usr/bin/git", "-c", f"safe.directory={ROOT}",
                              "-C", str(ROOT), "archive", "HEAD", "src/edp_lab"],
                             stdout=subprocess.PIPE, check=True, timeout=60)
    with tarfile.open(fileobj=BytesIO(archive.stdout), mode="r:") as tar:
        tar.extractall(BASE / "runtime", filter="data")
    for path in (BASE / "runtime").rglob("*"):
        if path.is_file():
            path.chmod(path.stat().st_mode & ~0o022)


def _launch(label: str, module: str, *arguments: str) -> None:
    plist = Path("/Library/LaunchDaemons") / (label + ".plist")
    args = [str(BASE / "python/bin/python3.12"), "-m", module, *arguments]
    from xml.sax.saxutils import escape

    arguments_xml = "".join(f"<string>{escape(arg)}</string>" for arg in args)
    xml = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
           "<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" "
           "\"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n"
           "<plist version=\"1.0\"><dict><key>Label</key>"
           f"<string>{label}</string><key>ProgramArguments</key><array>{arguments_xml}</array>"
           "<key>EnvironmentVariables</key><dict><key>PYTHONPATH</key>"
           f"<string>{BASE}/runtime/src</string><key>PATH</key>"
           "<string>/opt/homebrew/bin:/usr/bin:/bin</string></dict>"
           "<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>"
           f"<key>StandardOutPath</key><string>{BASE}/{label}.stdout.log</string>"
           f"<key>StandardErrorPath</key><string>{BASE}/{label}.stderr.log</string>"
           "</dict></plist>\n")
    plist.write_text(xml)
    plist.chmod(0o644)
    run("/bin/launchctl", "bootstrap", "system", str(plist))


def _rpc(path: Path, request: dict) -> dict:
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(600)
        client.connect(str(path))
        client.sendall((json.dumps(request, sort_keys=True) + "\n").encode())
        client.shutdown(socket.SHUT_WR)
        return json.loads(client.recv(8192))


def main() -> None:
    raise RuntimeError("C1500_SPECIFIC_INSTALLER_PAUSED_USE_REUSABLE_VAULT_0A")
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    parser.add_argument("expected_policy_sha256")
    args = parser.parse_args()
    policy = preflight(args.expected_commit, args.expected_policy_sha256)
    _protected_directories()
    _runtime()
    sp_id, app_id = _service_identity()
    warehouse = _warehouse(app_id)
    ddl_ids = _schema_and_tables(app_id)
    raw = _raw_copy_and_verify(policy)
    _keys_and_policy(policy, warehouse)
    from edp_lab.operating.authority import Denied
    from edp_lab.vault.protected_sql import scalar
    from edp_lab.vault.standing_authority import validate_policy

    for table in TABLES:
        count, _ = scalar(ROOT, BASE, "SELECT COUNT(*) FROM "
                          f"workspace.edp_lab_day6_vault_proto.{table} WHERE 1=0")
        if count != "0":
            raise RuntimeError("VAULT_SERVICE_PRINCIPAL_TABLE_READ_DENIED")
    # Installer preflight is outside the future bounded load clock/statement budget.
    (BASE / "ledger/sql_statement_budget.json").unlink()
    for change in ({"namespace": "workspace.edp_lab"},
                   {"tables": [*TABLES, "day5_protected"]},
                   {"sample_rows_sha256": "0" * 64}):
        mutation = copy.deepcopy(policy)
        mutation.update(change)
        try:
            validate_policy(ROOT, mutation,
                            ROOT / "runs/day6-vault-prototype/sample-manifest.json",
                            ROOT / "runs/day6-vault-prototype/projected-manifest.json",
                            ROOT / "runs/day6-vault-prototype/load-plan.json")
        except Denied:
            pass
        else:
            raise RuntimeError("NEGATIVE_POLICY_TEST_FAILED")
    _launch(PLISTS[0], "edp_lab.vault.standing_authority", str(ROOT), str(BASE),
            str(BASE / "raw"))
    _launch(PLISTS[1], "edp_lab.vault.protected_executor", str(ROOT), str(BASE))
    for _ in range(30):
        if (BASE / "broker.sock").exists() and (BASE / "executor.sock").exists():
            break
        time.sleep(1)
    denied = _rpc(BASE / "broker.sock", {"action": "unauthorized"})
    if denied.get("status") != "DENIED":
        raise RuntimeError("NEGATIVE_BROKER_TEST_FAILED")
    grant = _rpc(BASE / "broker.sock", {"action": "grant"})
    if grant.get("status") != "ISSUED":
        raise RuntimeError("VAULT_GRANT_NOT_ISSUED")
    from edp_lab.operating.authority import load_grant

    verified = load_grant(ROOT, Path(grant["grant_path"]), BASE / "trust")
    denied_write = _rpc(BASE / "executor.sock",
                        {"action": "execute", "grant_path": "/tmp/forged.json"})
    if denied_write.get("status") != "DENIED":
        raise RuntimeError("NEGATIVE_EXECUTOR_TEST_FAILED")
    receipt = {"schema": "EDP_VAULT_0A_INSTALL_EVIDENCE_V1",
               "authority": "protected-verifier-v1",
               "status": "VAULT_0A_INFRA_OPERATIONAL", "at_utc": datetime.now(UTC).isoformat(),
               "grant_id": verified["grant_id"], "grant_sha256": digest(Path(grant["grant_path"])),
               "dedicated_warehouse_id": warehouse, "service_principal_id": sp_id,
               "namespace": "workspace.edp_lab_day6_vault_proto", "ddl_statement_ids": ddl_ids,
               "raw_verification": raw,
               "broker_negative_denied": True, "executor_negative_denied": True}
    from edp_lab.vault.protected_readback import _sign

    output = BASE / "receipts/infra-operational.signed.json"
    _sign(receipt, BASE / "private/verifier.pem", output)
    print(json.dumps({"status": receipt["status"], "receipt_path": str(output),
                      "receipt_sha256": digest(output), "grant_path": grant["grant_path"],
                      "warehouse_id": warehouse}, sort_keys=True))


if __name__ == "__main__":
    main()
