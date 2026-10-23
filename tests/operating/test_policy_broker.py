"""Standing 0A policy authorizes a selected cohort without a per-run owner signature."""

import base64
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied, canonical, digest, load_grant
from edp_lab.operating.policy_broker import issue
from edp_lab.operating.runner import run


def signed(path, key, document):
    payload = path.with_suffix(".payload")
    signature = path.with_suffix(".sig")
    payload.write_bytes(canonical(document))
    subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(key),
                    "-rawin", "-in", str(payload), "-out", str(signature)], check=True)
    path.write_bytes(canonical({"document": document,
                                "signature_base64": base64.b64encode(
                                    signature.read_bytes()).decode()}))
    return path


def setup(tmp_path, *, prior_count=1, increment=1):
    root = tmp_path / "repo"
    root.mkdir()
    trust = tmp_path / "protected"
    trust.mkdir()
    for role in ("owner", "broker", "verifier"):
        secret = trust / (role + ".pem")
        subprocess.run(["openssl", "genpkey", "-algorithm", "Ed25519",
                        "-out", str(secret)], check=True)
        subprocess.run(["openssl", "pkey", "-in", str(secret), "-pubout",
                        "-out", str(trust / (role + "_ed25519_public.pem"))], check=True)
    (trust / "revoked_grants.json").write_text("[]\n")
    members = []
    for index in range(prior_count + increment + 1):
        raw = root / f"raw-{index}.txt"
        raw.write_text(f"source {index}\n")
        members.append({"identity": f"source-{index}", "raw_path": str(raw),
                        "raw_sha256": digest(raw.read_bytes()),
                        "holdout": index == prior_count + increment})
    universe = root / "universe.json"
    universe.write_bytes(canonical({"members": members}))
    registry = root / "registry.json"
    registry.write_bytes(canonical({"schema": "EDP_VALIDATION_REGISTRY_V1", "version": 1,
                                    "controls": []}))
    contract = root / "contract.txt"
    contract.write_text("approved contract\n")
    contracts = {name: {"version": "V1", "path": "contract.txt"}
                 for name in ("parser", "model", "rule")}
    contracts["registry"] = {"version": "V1", "path": "registry.json"}
    queue = {"schema": "EDP_QUEUE_V1", "cohort": f"C{prior_count + increment}",
             "previous_cohort": f"C{prior_count}",
             "prior_receipt": str(trust / "prior.json"), "route": "CORPUS_ONLY",
             "sources": [{"identity": member["identity"], "path": member["raw_path"],
                          "sha256": member["raw_sha256"]}
                         for member in members[prior_count:prior_count + increment]],
             "output": f"workspace.edp_lab.c{prior_count + increment}",
             "tags": [], "contracts": contracts,
             "tasks": [{"id": "hash", "kind": "verify_file", "depends_on": [],
                        "source": {"identity": members[prior_count]["identity"],
                                   "path": members[prior_count]["raw_path"],
                                   "sha256": members[prior_count]["raw_sha256"]}},
                       {"id": "P5", "kind": "stage_gate", "stage": "P5",
                        "depends_on": ["hash"]},
                       {"id": "freeze", "kind": "freeze_verify", "depends_on": ["hash", "P5"],
                        "simulated_receipt": True}]}
    queue_path = root / "queue.json"
    queue_path.write_bytes(canonical(queue))
    now = datetime.now(UTC)
    prior = {"schema": "EDP_PRIOR_COHORT_RECEIPT_V1",
             "authority": "protected-verifier-v1", "cohort": f"C{prior_count}",
             "identities": [m["identity"] for m in members[:prior_count]],
             "result_freeze_sha256": "a" * 64, "status": "VERIFIED",
             "live_readback": True}
    prior["roster_sha256"] = digest(canonical(prior["identities"]))
    signed(trust / "prior.json", trust / "verifier.pem", prior)
    policy = {"schema": "EDP_STANDING_POLICY_V1", "policy_id": "standing-test-v1",
              "issued_at": (now - timedelta(hours=1)).isoformat(),
              "expires_at": (now + timedelta(days=1)).isoformat(),
              "cohort_pattern": "C[0-9]+", "routes": ["CORPUS_ONLY"],
              "max_increment": increment, "universe_path": "universe.json",
              "universe_sha256": digest(universe.read_bytes()),
              "output_prefix": "workspace.edp_lab.",
              "contracts": {name: {"version": pin["version"],
                                   "sha256": digest((root / pin["path"]).read_bytes())}
                            for name, pin in contracts.items()},
              "operations": ["verify_file", "stage_gate", "freeze_verify"],
              "databricks_path_prefixes": ["/Volumes/workspace/edp_lab/"],
              "databricks_table_prefixes": ["workspace.edp_lab."],
              "git_operations": ["push"], "protected_branches": ["main"],
              "grant_hours": 1,
              "limits": {"runtime_seconds": 30, "compute_units": 10, "token_count": 1000,
                         "retries": 2, "operations": 4}}
    policy_path = signed(trust / "policy.json", trust / "owner.pem", policy)
    return root, trust, queue_path, policy_path, members


def test_broker_issues_run_grant_without_new_owner_signature(tmp_path, monkeypatch):
    root, trust, queue, policy, _members = setup(tmp_path)
    grants = trust / "grants"
    issued = issue(root, queue, policy, trust, trust / "broker.pem", grants)
    grant = load_grant(root, issued, trust)
    assert grant["authority"] == "policy-broker-v1"
    assert grant["cohort"] == "C2" and len(grant["sources"]) == 2
    monkeypatch.setenv("EDP_OWNER_TRUST_DIR", str(trust))
    monkeypatch.setenv("EDP_POLICY_BROKER_SOCKET", str(trust / "broker.sock"))
    monkeypatch.setattr("edp_lab.operating.runner.request_policy_grant",
                        lambda _socket, _queue: issued)
    state = run(root, queue, Path("auto"), tmp_path / "state", dry_run=True)
    assert state["summary"]["simulation_complete"]
    assert state["tasks"]["P5"]["status"] == "COMPLETE"
    assert issue(root, queue, policy, trust, trust / "broker.pem", grants) == issued


def test_c1500_to_c2000_p5_authorization(tmp_path, monkeypatch):
    root, trust, queue, policy, _members = setup(tmp_path, prior_count=1500, increment=500)
    issued = issue(root, queue, policy, trust, trust / "broker.pem", trust / "grants")
    grant = load_grant(root, issued, trust)
    assert grant["cohort"] == "C2000" and len(grant["sources"]) == 2000
    monkeypatch.setenv("EDP_OWNER_TRUST_DIR", str(trust))
    monkeypatch.setenv("EDP_POLICY_BROKER_SOCKET", str(trust / "broker.sock"))
    monkeypatch.setattr("edp_lab.operating.runner.request_policy_grant",
                        lambda _socket, _queue: issued)
    state = run(root, queue, Path("auto"), tmp_path / "state", dry_run=True)
    assert state["tasks"]["P5"]["status"] == "COMPLETE"


def test_policy_tamper_and_revocation_fail_closed(tmp_path):
    root, trust, queue, policy, _members = setup(tmp_path)
    envelope = json.loads(policy.read_bytes())
    envelope["document"]["max_increment"] = 99
    policy.write_bytes(canonical(envelope))
    with pytest.raises(Denied, match="INVALID_SIGNATURE"):
        issue(root, queue, policy, trust, trust / "broker.pem", trust / "grants")
    signed(policy, trust / "owner.pem", envelope["document"])
    (trust / "revoked_grants.json").write_text('["standing-test-v1"]\n')
    with pytest.raises(Denied, match="POLICY_REVOKED"):
        issue(root, queue, policy, trust, trust / "broker.pem", trust / "grants")


@pytest.mark.parametrize("change,reason", [
    ("holdout", "SOURCE_OUT_OF_UNIVERSE_OR_HOLDOUT"),
    ("semantic", "SEMANTIC_ROUTE_OUT_OF_POLICY"),
    ("write", "OPERATION_OUT_OF_POLICY"),
    ("contract", "CONTRACT_OUT_OF_POLICY"),
])
def test_broker_fails_closed(tmp_path, change, reason):
    root, trust, queue_path, policy, members = setup(tmp_path)
    queue = json.loads(queue_path.read_bytes())
    if change == "holdout":
        queue["sources"] = [{"identity": members[2]["identity"],
                             "path": members[2]["raw_path"],
                             "sha256": members[2]["raw_sha256"]}]
    elif change == "semantic":
        queue["route"] = "CORRECTIVE"
    elif change == "write":
        queue["tasks"].insert(1, {"id": "unsafe", "kind": "databricks_write",
                                  "depends_on": ["hash"]})
    else:
        (root / "contract.txt").write_text("unapproved change\n")
    queue_path.write_bytes(canonical(queue))
    with pytest.raises(Denied, match=reason):
        issue(root, queue_path, policy, trust, trust / "broker.pem", trust / "grants")
