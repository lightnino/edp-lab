"""New Cohort cannot stage RAW; Acquisition has a separate signed entrypoint."""

import base64
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from edp_lab.operating.acquisition_executor import execute_acquisition_stage
from edp_lab.operating.authority import Denied, canonical, digest
from edp_lab.operating.raw_ownership import (
    acquisition_remediation_request,
    require_cohort_operation_readonly,
    require_cohort_readonly,
)


def sign(target, private, payload, *, kind="document"):
    data = target.with_suffix(".canonical")
    sig = target.with_suffix(".sig")
    data.write_bytes(canonical(payload))
    subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(private),
                    "-rawin", "-in", str(data), "-out", str(sig)], check=True)
    target.write_bytes(canonical({
        kind: payload,
        "signature_base64": base64.b64encode(sig.read_bytes()).decode(),
    }))


def acquisition_fixture(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    trust = tmp_path / "trust"
    trust.mkdir()
    for label in ("owner", "verifier"):
        private = trust / f"{label}.pem"
        subprocess.run(["openssl", "genpkey", "-algorithm", "Ed25519",
                        "-out", str(private)], check=True)
        subprocess.run(["openssl", "pkey", "-in", str(private), "-pubout",
                        "-out", str(trust / f"{label}_ed25519_public.pem")], check=True)
    (trust / "revoked_grants.json").write_text("[]")
    raw = root / "raw.txt"
    raw.write_bytes(b"single source approved acquisition\n")
    source = {"identity": "a" * 64, "sha256": digest(raw.read_bytes()),
              "path": str(raw), "byte_size": raw.stat().st_size}
    uri = f"dbfs:/Volumes/workspace/edp_lab/raw/acquisition-v1/{source['identity']}/raw.txt"
    receipt = trust / "discovery.json"
    discovery = {
        "schema": "EDP_ACQUISITION_DISCOVERY_V1",
        "authority": "protected-verifier-v1",
        "status": "STAGE_NEW_AFTER_DISCOVERY",
        "discovery_scope": "CROSS_HISTORICAL_LOCATORS",
        "reusable_raw_found": False,
        "source_identity": source["identity"],
        "raw_sha256": source["sha256"],
        "byte_size": source["byte_size"],
        "destination": uri,
    }
    sign(receipt, trust / "verifier.pem", discovery)
    plan = root / "acquisition-plan.json"
    plan.write_bytes(canonical({
        "schema": "EDP_ACQUISITION_RAW_PLAN_V1",
        "decision": "STAGE_NEW",
        "operation_id": "acq-exact-source-001",
        "output": "acquisition.raw",
        "source": source,
        "remote_path": uri,
        "discovery_receipt": str(receipt),
    }))
    now = datetime.now(UTC)
    pin = digest(b"legacy mandatory field")
    grant = {
        "schema": "EDP_SIGNED_GRANT_V1",
        "grant_id": "acquisition-exact-001",
        "authority": "owner-acquisition-v1",
        "issued_at": (now - timedelta(hours=1)).isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "revocation_id": "acquisition-rev-001",
        "cohort": "ACQUISITION",
        "sources": {source["identity"]: source["sha256"]},
        "contracts": {
            **{name: {"version": "V1", "sha256": pin}
               for name in ("queue", "parser", "model", "rule", "registry")},
            "acquisition_plan": {
                "version": "ACQUISITION_RAW_PLAN_V1",
                "sha256": digest(plan.read_bytes()),
            },
        },
        "operations": ["raw_stage"],
        "databricks_paths": [uri],
        "databricks_tables": [],
        "outputs": ["acquisition.raw"],
        "git_operations": [],
        "protected_branches": ["main"],
        "limits": {
            "runtime_seconds": 60, "compute_units": 1, "token_count": 1,
            "retries": 0, "operations": 1,
        },
    }
    grant_path = trust / "acquisition-grant.json"
    sign(grant_path, trust / "owner.pem", grant, kind="grant")
    return root, trust, grant_path, plan, receipt, source


@pytest.mark.parametrize("kind", [
    "raw_stage", "raw_upload", "raw_copy", "raw_move", "raw_restage",
    "raw_overwrite", "raw_delete", "raw_mkdir",
])
def test_cohort_denies_any_raw_write_name_before_grant(kind):
    queue = {"tasks": [{"id": "P8", "kind": kind}]}
    with pytest.raises(Denied, match="COHORT_RAW_MUTATION_FORBIDDEN"):
        require_cohort_readonly(queue)
    with pytest.raises(Denied, match="COHORT_RAW_MUTATION_FORBIDDEN"):
        require_cohort_operation_readonly({"operation": kind})


def test_acquisition_remediation_is_unprivileged_packet():
    packet = acquisition_remediation_request(
        identity="source-1", raw_sha256="a" * 64, byte_size=100,
        reason_code="RAW_RECEIPT_MISSING", cohort="C2000")
    assert packet["status"] == "RAW_HANDOFF_BLOCKED"
    assert packet["target_actor"] == "ACQUISITION"
    assert packet["operations_authorized"] == []
    assert not packet["write_authorized"]
    assert packet["resume_requires"] == "INDEPENDENTLY_VERIFIED_RAW_HANDOFF"


def test_acquisition_stage_requires_independent_signed_discovery(
        tmp_path, monkeypatch):
    root, trust, grant, plan, receipt, source = acquisition_fixture(tmp_path)
    monkeypatch.setenv("EDP_OWNER_TRUST_DIR", str(trust))
    ledger = tmp_path / "ledger"
    before = source["sha256"]
    result = execute_acquisition_stage(root, grant, plan, ledger, execute=False)
    assert result == {"status": "AUTHORIZED_DRY_RUN"}
    assert digest((root / "raw.txt").read_bytes()) == before
    assert not ledger.exists()

    discovery = json.loads(receipt.read_bytes())["document"]
    discovery["reusable_raw_found"] = True
    sign(receipt, trust / "verifier.pem", discovery)
    with pytest.raises(Denied, match="ACQUISITION_DISCOVERY_UNVERIFIED"):
        execute_acquisition_stage(root, grant, plan, ledger, execute=False)
    assert not ledger.exists()


def test_acquisition_fails_closed_on_changed_plan_or_missing_signature(
        tmp_path, monkeypatch):
    root, trust, grant, plan, receipt, _source = acquisition_fixture(tmp_path)
    monkeypatch.setenv("EDP_OWNER_TRUST_DIR", str(trust))
    plan.write_bytes(plan.read_bytes() + b" ")
    with pytest.raises(Denied, match="ACQUISITION_PLAN_NOT_PINNED"):
        execute_acquisition_stage(root, grant, plan, tmp_path / "ledger")
    assert not (tmp_path / "ledger").exists()

    plan.write_bytes(plan.read_bytes()[:-1])
    receipt.unlink()
    with pytest.raises((Denied, OSError)):
        execute_acquisition_stage(root, grant, plan, tmp_path / "ledger")
