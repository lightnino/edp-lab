"""Read-only Day 7 partial-install diagnosis. NEVER creates secrets.

Run as normal Owner (no sudo): uv run python scripts/diagnose_day7_secret.py
Prints principal/assignment and secret *metadata counts* only; never values.
"""

from __future__ import annotations

import json
import re
import subprocess

CLI = "/opt/homebrew/bin/databricks"
SP_ID = "78491734320299"
PROFILE = "edp-lab"


def safe_error(raw: str) -> str:
    """Avoid printing bearer tokens or secret fields from unexpected errors."""
    message = re.sub(r"(?i)(bearer\\s+)\\S+", r"\\1[REDACTED]", raw)
    message = re.sub(
        r"(?i)(client_secret|refresh_token|access_token|authorization|api_key|"
        r"password|secret)\\s*[:=]\\s*[^\\s,]+",
        r"\\1=[REDACTED]", message,
    )
    message = re.sub(r"[\\x00-\\x1f\\x7f]+", " ", message).strip()
    return message[:360] if message else "[CLI returned no error text]"


def read_only(*args: str) -> dict:
    result = subprocess.run(
        [CLI, *args, "-p", PROFILE, "-o", "json"],
        capture_output=True, text=True, check=False, timeout=60,
    )
    if result.returncode:
        return {"status": "ERROR", "exit": result.returncode,
                "message": safe_error(result.stderr)}
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"status": "UNEXPECTED_RESPONSE"}
    return {"status": "PASS", "data": parsed}


def diagnose() -> dict:
    principal = read_only("service-principals", "get", SP_ID)
    assignment = read_only(
        "api", "get", "/api/2.0/identity/workspace-assignments/" + SP_ID,
    )
    secrets = read_only("service-principal-secrets-proxy", "list", SP_ID)

    if principal["status"] == "PASS":
        identity = principal["data"]
        principal = {"status": "PASS", "id_matches":
                     str(identity.get("id")) == SP_ID,
                     "active": identity.get("active"),
                     "display_name_matches":
                     identity.get("displayName") == "edp-lab-day7-c3000-cohort"}
    if assignment["status"] == "PASS":
        item = assignment["data"]
        assignment = {"status": "PASS", "principal_id_matches":
                      str(item.get("principal_id")) == SP_ID,
                      "type": item.get("principal_type"),
                      "direct_entitlements": item.get("entitlements", []),
                      "effective_entitlements": item.get("effective_entitlements", [])}
    if secrets["status"] == "PASS":
        listing = secrets["data"]
        if isinstance(listing, list):
            rows = listing
            paginated = False
        elif isinstance(listing, dict):
            rows = listing.get("secrets")
            paginated = bool(listing.get("next_page_token"))
        else:
            rows = None
            paginated = False
        if not isinstance(rows, list):
            secrets = {"status": "UNEXPECTED_METADATA_SCHEMA"}
        else:
            secrets = {
                "status": "PASS", "returned_secret_metadata_count": len(rows),
                "metadata_statuses": [row.get("status") for row in rows
                                      if isinstance(row, dict)],
                "pagination_incomplete": paginated,
                "secret_values": "NEVER_READ_OR_PRINTED",
            }
    return {
        "status": "DAY7_PARTIAL_SECRET_READ_ONLY_DIAGNOSTIC",
        "service_principal_id": SP_ID,
        "principal": principal, "workspace_assignment": assignment,
        "secret_inventory": secrets,
        "protected_local_journal": "NOT_READ_NO_SUDO",
        "no_cloud_mutations": True,
    }


if __name__ == "__main__":
    print(json.dumps(diagnose(), sort_keys=True))
