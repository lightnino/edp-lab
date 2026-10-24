"""Standing 0A policy authorizes a selected cohort without a per-run owner signature."""

import base64
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied, canonical, digest, load_grant
from edp_lab.operating.policy_broker import issue
from edp_lab.operating.protected_verifier import attest_sql
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


def test_broker_rejects_cohort_raw_stage_even_if_standing_policy_allows(
        tmp_path, monkeypatch):
    root, trust, queue_path, policy_path, _members = setup(tmp_path)
    queue = json.loads(queue_path.read_bytes())
    queue["tasks"].insert(2, {"id": "stage", "kind": "raw_stage",
                               "depends_on": ["P5"],
                               "operation_id": "cohort-raw-forbidden",
                               "source": queue["sources"][0],
                               "databricks_path": "dbfs:/Volumes/workspace/edp_lab/raw/"
                                                  "day5/source-1/raw-1.txt"})
    queue_path.write_bytes(canonical(queue))
    envelope = json.loads(policy_path.read_bytes())
    policy = envelope["document"]
    policy["operations"].append("raw_stage")
    policy["databricks_path_prefixes"].append("dbfs:/Volumes/workspace/edp_lab/raw/")
    signed(policy_path, trust / "owner.pem", policy)
    grants = trust / "grants"
    with pytest.raises(Denied, match="COHORT_RAW_MUTATION_FORBIDDEN"):
        issue(root, queue_path, policy_path, trust, trust / "broker.pem", grants)
    assert not grants.exists()
    monkeypatch.setenv("EDP_OWNER_TRUST_DIR", str(trust))
    monkeypatch.setenv("EDP_POLICY_BROKER_SOCKET", str(trust / "broker.sock"))
    with pytest.raises(Denied, match="COHORT_RAW_MUTATION_FORBIDDEN"):
        run(root, queue_path, Path("auto"), tmp_path / "state", dry_run=True)
    assert not (tmp_path / "state").exists()


def test_protected_sql_readback_matches_exact_statement(tmp_path, monkeypatch):
    root, trust, queue_path, policy_path, _members = setup(tmp_path)
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    statement = root / "roster-sql.json"
    sql = "CREATE TABLE workspace.edp_lab.c2_roster USING DELTA AS SELECT 1"
    statement.write_bytes(canonical({"warehouse_id": "test", "statement": sql}))
    queue = json.loads(queue_path.read_bytes())
    queue["contracts"]["statement_roster"] = {"version": "V1", "path": statement.name}
    queue["tasks"].insert(2, {"id": "roster", "kind": "databricks_write",
                              "depends_on": ["P5"], "operation_id": "create-c2-roster",
                              "statement_path": statement.name,
                              "statement_contract": "statement_roster",
                              "databricks_table": "workspace.edp_lab.c2_roster",
                              "external_receipt": str(receipts / "roster.json")})
    queue["tasks"][-1]["depends_on"].append("roster")
    queue["tasks"][-1]["receipt"] = str(receipts / "freeze.json")
    queue_path.write_bytes(canonical(queue))
    policy = json.loads(policy_path.read_bytes())["document"]
    policy["contracts"]["statement_roster"] = {
        "version": "V1", "sha256": digest(statement.read_bytes())}
    policy["operations"].append("databricks_write")
    signed(policy_path, trust / "owner.pem", policy)
    grant_path = issue(root, queue_path, policy_path, trust, trust / "broker.pem",
                       trust / "grants")
    monkeypatch.setenv("EDP_OWNER_TRUST_DIR", str(trust))
    monkeypatch.setenv("EDP_POLICY_BROKER_SOCKET", str(trust / "broker.sock"))
    monkeypatch.setattr("edp_lab.operating.runner.request_policy_grant",
                        lambda _socket, _queue: grant_path)
    monkeypatch.setattr("edp_lab.operating.runner.protected_execute",
                        lambda *_args: {"status": "SUBMITTED_REQUIRES_READBACK",
                                        "statement_id": "statement-c2",
                                        "submitted_at_utc": datetime.now(UTC).isoformat()})
    first = run(root, queue_path, Path("auto"), tmp_path / "state")
    assert first["tasks"]["roster"]["status"] == "VALIDATING"

    def live(path, _timeout):
        if path.startswith("/api/2.0/sql/statements/"):
            return {"statement_id": "statement-c2", "statement": sql,
                    "status": {"state": "SUCCEEDED"}}
        return {"full_name": "workspace.edp_lab.c2_roster", "table_id": "uc-c2"}

    monkeypatch.setattr("edp_lab.operating.protected_verifier._remote_json", live)
    assert attest_sql(root, queue_path, grant_path, tmp_path / "state/checkpoint.json",
                      "roster", trust, trust / "verifier.pem")["status"] == "VERIFIED"
    resumed = run(root, queue_path, Path("auto"), tmp_path / "state")
    assert resumed["tasks"]["roster"]["status"] == "COMPLETE"


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


def test_future_day6_cohort_requires_signed_u10_handoff(tmp_path):
    """Synthetic Day 6-like cohort: consume trusted RAW, never stage it."""
    root, trust, queue_path, policy_path, _members = setup(tmp_path)
    queue = json.loads(queue_path.read_bytes())
    policy = json.loads(policy_path.read_bytes())["document"]
    policy["require_verified_raw_handoff"] = True
    signed(policy_path, trust / "owner.pem", policy)

    # A signed standing policy cannot be bypassed by an agent omitting the
    # newly required Acquisition/U10 handoff field from an otherwise valid Queue.
    with pytest.raises(Denied, match="RAW_HANDOFF_BLOCKED"):
        issue(root, queue_path, policy_path, trust, trust / "broker-empty")

    sources = queue["sources"]
    receipt = trust / "u10-handoff.json"
    document = {
        "schema": "EDP_U10_RAW_HANDOFF_V1",
        "authority": "protected-verifier-v1",
        "status": "VERIFIED", "live_remote_readback": True,
        "cohort": queue["cohort"],
        "sources": [{
            "identity": row["identity"], "sha256": row["sha256"],
            "byte_size": Path(row["path"]).stat().st_size,
            "remote_raw_path": f"dbfs:/Volumes/workspace/edp_lab/raw/reused/{row['identity']}/original.txt",
            "remote_readback_sha256": row["sha256"],
            "readback_receipt_sha256": digest(row["sha256"].encode()),
        } for row in sources],
    }
    signed(receipt, trust / "verifier.pem", document)
    queue["raw_handoff"] = {
        "path": str(receipt), "sha256": digest(receipt.read_bytes())}
    queue_path.write_bytes(canonical(queue))
    issued = issue(root, queue_path, policy_path, trust, trust / "broker-verified")
    assert load_grant(root, issued, trust)["operations"] == [
        "freeze_verify", "stage_gate", "verify_file"]

    # A remote-hash mismatch remains blocked even when signed by a verifier:
    # signature alone cannot substitute for verified source bytes.
    document["sources"][0]["remote_readback_sha256"] = "f" * 64
    signed(receipt, trust / "verifier.pem", document)
    queue["raw_handoff"]["sha256"] = digest(receipt.read_bytes())
    queue_path.write_bytes(canonical(queue))
    with pytest.raises(Denied, match="RAW_HANDOFF_BLOCKED"):
        issue(root, queue_path, policy_path, trust, trust / "broker-mismatch")


def test_future_day6_missing_raw_handoff_routes_upstream_not_upload(tmp_path):
    root, trust, queue_path, policy_path, _members = setup(tmp_path)
    policy = json.loads(policy_path.read_bytes())["document"]
    policy["require_verified_raw_handoff"] = True
    signed(policy_path, trust / "owner.pem", policy)
    with pytest.raises(Denied, match="RAW_HANDOFF_BLOCKED"):
        issue(root, queue_path, policy_path, trust, trust / "broker")
    from edp_lab.operating.raw_ownership import acquisition_remediation_request

    source = json.loads(queue_path.read_bytes())["sources"][0]
    packet = acquisition_remediation_request(
        identity=source["identity"], raw_sha256=source["sha256"],
        byte_size=Path(source["path"]).stat().st_size,
        reason_code="RAW_RECEIPT_MISSING", cohort="C2")
    assert packet["target_actor"] == "ACQUISITION"
    assert packet["operations_authorized"] == []
    assert packet["write_authorized"] is False
