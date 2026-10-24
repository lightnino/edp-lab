"""Protected one-time C1500 prior-cohort attestation from live Databricks readback.

Run only from a root-owned deployment with a private verifier key inaccessible
to the Agent. It signs observations it obtains itself, never an Agent document.
"""

import argparse
import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path

from edp_lab.operating.authority import Denied, canonical, digest, file_digest

VIEW = "workspace.edp_lab.o_c1500_m2_result_frozen_v1"
WAREHOUSE = "589e80595c7c8cb8"
PROFILE = "edp-lab"
EXPECTED_VIEW_ID = "43e16098-b123-4689-83d5-4d942bbe4dfc"
EXPECTED_ROSTER_SHA = "810c6898df0cb5e5c478305f71c190ffe4a7c7a2bb40133efa79a16de630e703"
EXPECTED_FREEZE_SHA = "8917847746d7a4a5d848d4a605e908ed3fe3b6d2b631346ad49dfd66f519fd72"


def _databricks(user: str, *args: str) -> dict:
    command = ["/usr/bin/sudo", "-n", "-u", user, "-H", "/opt/homebrew/bin/databricks",
               "api", *args, "-p", PROFILE, "-o", "json"]
    result = subprocess.run(command, capture_output=True, check=False, timeout=180, text=True)
    if result.returncode:
        raise Denied("LIVE_DATABRICKS_READBACK_FAILED")
    return json.loads(result.stdout)


def _statement(user: str, sql: str) -> dict:
    result = _databricks(user, "post", "/api/2.0/sql/statements", "--json", json.dumps({
        "warehouse_id": WAREHOUSE, "statement": sql, "wait_timeout": "50s",
        "on_wait_timeout": "CONTINUE", "disposition": "INLINE", "row_limit": 2000}))
    for _ in range(20):
        if result.get("status", {}).get("state") not in {"PENDING", "RUNNING"}:
            return result
        result = _databricks(user, "get", "/api/2.0/sql/statements/" + result[
            "statement_id"] + "?wait_timeout=50s")
    raise Denied("LIVE_PRIOR_QUERY_LIMIT")


def attest(root: Path, trust: Path, key: Path, output: Path, user: str) -> dict:
    root = root.resolve()
    if any(path.resolve().is_relative_to(root) for path in (trust, key, output)):
        raise Denied("VERIFIER_MUST_BE_PROTECTED")
    frozen = root / "metadata/freezes/C1500_v1/C1500.bindings.json"
    freeze = root / "metadata/freezes/O_C1500_M2_v1/databricks_result_freeze_v2.json"
    if file_digest(frozen) != EXPECTED_ROSTER_SHA or file_digest(freeze) != EXPECTED_FREEZE_SHA:
        raise Denied("PRIOR_FREEZE_PIN_CHANGED")
    bindings = json.loads(frozen.read_bytes())
    identities = [row["source_identity"] for row in bindings]
    source_ids = {row["source_instance_id"] for row in bindings}
    if len(identities) != 1500 or len(set(identities)) != 1500 or len(source_ids) != 1500:
        raise Denied("PRIOR_MEMBERSHIP_INVALID")
    uc = _databricks(user, "get", "/api/2.1/unity-catalog/tables/" + VIEW)
    props = uc.get("properties", {})
    if (uc.get("full_name") != VIEW or uc.get("table_type") != "VIEW"
            or uc.get("table_id") != EXPECTED_VIEW_ID
            or props.get("edp.freeze.status") != "SOURCE_PRESERVING_VERIFIED"
            or props.get("edp.freeze.source_roster_sha256") != EXPECTED_ROSTER_SHA
            or props.get("edp.freeze.physical_sources") != "1500"
            or props.get("edp.freeze.version") != "O_C1500_M2_DATABRICKS_V2"):
        raise Denied("LIVE_PRIOR_FREEZE_MISMATCH")
    sql = f"SELECT DISTINCT source_instance_id FROM {VIEW}"
    live = _statement(user, sql)
    if live.get("status", {}).get("state") != "SUCCEEDED":
        raise Denied("LIVE_PRIOR_QUERY_NOT_SUCCEEDED")
    members = live.get("result", {}).get("data_array", [])
    if (live.get("manifest", {}).get("truncated")
            or len(members) != 1500 or any(len(row) != 1 for row in members)
            or {row[0] for row in members} != source_ids):
        raise Denied("LIVE_PRIOR_MEMBERSHIP_MISMATCH")
    document = {
        "schema": "EDP_PRIOR_COHORT_RECEIPT_V1",
        "authority": "protected-verifier-v1", "cohort": "C1500",
        "identities": identities, "roster_sha256": digest(canonical(identities)),
        "result_freeze_sha256": EXPECTED_FREEZE_SHA,
        "live_uc_table_id": EXPECTED_VIEW_ID,
        "live_statement_id": live["statement_id"],
        "live_membership_sha256": digest(canonical(sorted(source_ids))),
        "live_readback": True, "status": "VERIFIED",
    }
    with tempfile.TemporaryDirectory() as temporary:
        payload = Path(temporary) / "payload"
        signature = Path(temporary) / "signature"
        payload.write_bytes(canonical(document))
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(key),
                        "-rawin", "-in", str(payload), "-out", str(signature)],
                       check=True, capture_output=True)
        envelope = {"document": document,
                    "signature_base64": base64.b64encode(signature.read_bytes()).decode()}
    output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical(envelope))
        stream.flush()
        os.fsync(stream.fileno())
    return {"status": "VERIFIED", "receipt": str(output),
            "receipt_sha256": file_digest(output), "statement_id": live["statement_id"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("root", "trust", "key", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--databricks-user", required=True)
    args = parser.parse_args()
    print(json.dumps(attest(args.root, args.trust, args.key, args.output,
                            args.databricks_user), sort_keys=True))


if __name__ == "__main__":
    main()
