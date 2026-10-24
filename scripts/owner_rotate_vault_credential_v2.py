"""Rotate only the isolated Vault service-principal secret in owner terminal."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from owner_setup_day6_vault_0a import BASE, ROOT, admin_cli

from edp_lab.vault.credential_rotation import rotate_config


def main() -> None:
    if os.geteuid() != 0 or not BASE.is_dir() or BASE.is_relative_to(ROOT):
        raise RuntimeError("PROTECTED_VAULT_INSTALL_REQUIRED")
    identity = json.loads((BASE / "private/service-principal.json").read_bytes())
    policy = json.loads((BASE / "trust/policy.signed.json").read_bytes())["document"]
    if policy.get("schema") != "EDP_VAULT_STANDING_POLICY_V2":
        raise RuntimeError("REUSABLE_VAULT_POLICY_REQUIRED")
    config = BASE / "private/databrickscfg"
    old_hash = hashlib.sha256(config.read_bytes()).hexdigest()
    response = admin_cli("service-principal-secrets-proxy", "create",
                         identity["service_principal_id"],
                         "--json", '{"lifetime":"604800s"}')
    secret = response["secret"]
    from owner_setup_day6_vault_0a import HOST

    replacement = (f"[vault-dev]\nhost = {HOST}\n"
                   f"client_id = {identity['application_id']}\n"
                   f"client_secret = {secret}\n")

    def probe(staged: Path) -> bool:
        env = {**os.environ, "DATABRICKS_CONFIG_FILE": str(staged)}
        result = subprocess.run(
            ["/opt/homebrew/bin/databricks", "warehouses", "get",
             policy["warehouse_id"], "-p", "vault-dev", "-o", "json"],
            env=env, capture_output=True, text=True, timeout=120, check=False)
        if result.returncode:
            return False
        warehouse = json.loads(result.stdout)
        return warehouse.get("id") == policy["warehouse_id"]

    rotate_config(config, replacement, probe)
    receipt = {"schema": "EDP_VAULT_CREDENTIAL_ROTATION_V1",
               "status": "PROBED_AND_ATOMICALLY_SWAPPED",
               "service_principal_id": identity["service_principal_id"],
               "warehouse_id": policy["warehouse_id"],
               "old_config_sha256": old_hash,
               "new_config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
               "rotated_at_utc": datetime.now(UTC).isoformat()}
    from edp_lab.vault.protected_readback import _sign

    output = BASE / "receipts" / ("credential-rotation-" + datetime.now(UTC).strftime(
        "%Y%m%d%H%M%S") + ".signed.json")
    _sign({**receipt, "authority": "protected-verifier-v1"},
          BASE / "private/verifier.pem", output)
    print(json.dumps({"status": receipt["status"], "receipt_path": str(output)},
                     sort_keys=True))


if __name__ == "__main__":
    main()
