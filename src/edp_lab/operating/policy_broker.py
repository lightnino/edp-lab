"""Protected 0A policy broker: evaluate P5 and issue exact signed run grants.

Deploy this service outside the Agent's writable trust domain. Its key, policy,
socket and grant store must be owner controlled; this module is not an approval.
"""

import argparse
import base64
import grp
import json
import os
import re
import socket
import socketserver
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from edp_lab.operating.raw_ownership import (
    require_cohort_operation_readonly,
    require_cohort_readonly,
)
from edp_lab.operating.authority import (
    Denied,
    canonical,
    digest,
    file_digest,
    load_grant,
    verified_document,
)


def evaluate(root: Path, queue_path: Path, policy_path: Path, trust: Path) -> dict:
    """Evaluate an Agent-selected queue against the signed standing policy."""
    root = root.resolve()
    queue_path = queue_path.resolve(strict=True)
    if not queue_path.is_relative_to(root):
        raise Denied("QUEUE_OUTSIDE_REPO")
    if policy_path.resolve(strict=True).is_relative_to(root):
        raise Denied("POLICY_MUST_BE_PROTECTED")
    policy = verified_document(root, policy_path, trust)
    if policy.get("schema") != "EDP_STANDING_POLICY_V1":
        raise Denied("INVALID_STANDING_POLICY")
    now = datetime.now(UTC)
    if not (datetime.fromisoformat(policy["issued_at"]) <= now
            < datetime.fromisoformat(policy["expires_at"])):
        raise Denied("POLICY_NOT_CURRENT")
    if policy["policy_id"] in json.loads((trust / "revoked_grants.json").read_bytes()):
        raise Denied("POLICY_REVOKED")
    queue = json.loads(queue_path.read_bytes())
    if queue.get("schema") != "EDP_QUEUE_V1" or queue.get("simulation_only"):
        raise Denied("INVALID_LIVE_QUEUE")
    # A legacy broad 0A policy cannot grant RAW mutation to a Cohort.
    require_cohort_readonly(queue)
    if not re.fullmatch(policy["cohort_pattern"], queue["cohort"]):
        raise Denied("COHORT_OUT_OF_SCOPE")
    if queue.get("route") not in policy["routes"]:
        raise Denied("SEMANTIC_ROUTE_OUT_OF_POLICY")
    if not queue["output"].startswith(policy["output_prefix"]):
        raise Denied("OUTPUT_OUT_OF_SCOPE")
    prior = verified_document(root, Path(queue["prior_receipt"]), trust)
    if (prior.get("schema") != "EDP_PRIOR_COHORT_RECEIPT_V1"
            or prior.get("status") != "VERIFIED" or prior.get("live_readback") is not True
            or prior.get("cohort") != queue.get("previous_cohort")
            or not re.fullmatch(r"[a-f0-9]{64}", prior.get("result_freeze_sha256", ""))
            or prior.get("roster_sha256") != digest(canonical(prior.get("identities")))
            or not isinstance(prior.get("identities"), list)
            or len(prior["identities"]) != len(set(prior["identities"]))):
        raise Denied("PRIOR_COHORT_NOT_VERIFIED")
    universe_path = (root / policy["universe_path"]).resolve(strict=True)
    if (not universe_path.is_relative_to(root)
            or file_digest(universe_path) != policy["universe_sha256"]):
        raise Denied("UNIVERSE_PIN_CHANGED")
    members = {m["identity"]: m for m in json.loads(universe_path.read_bytes())["members"]}
    selected = queue.get("sources")
    if (not isinstance(selected, list) or not selected
            or len(selected) > policy["max_increment"]
            or len(selected) != len({s["identity"] for s in selected})
            or set(prior["identities"]) & {s["identity"] for s in selected}):
        raise Denied("INVALID_INCREMENT")
    if re.fullmatch(r"C\d+", queue["cohort"]) and int(queue["cohort"][1:]) != (
            len(prior["identities"]) + len(selected)):
        raise Denied("COHORT_SIZE_MISMATCH")
    if any(identity not in members or members[identity]["holdout"]
           for identity in prior["identities"]):
        raise Denied("PRIOR_COHORT_OUT_OF_UNIVERSE")
    sources = {identity: members[identity]["raw_sha256"] for identity in prior["identities"]}
    for source in selected:
        member = members.get(source["identity"])
        if (member is None or member["holdout"] or source["sha256"] != member["raw_sha256"]
                or source["path"] != member["raw_path"]):
            raise Denied("SOURCE_OUT_OF_UNIVERSE_OR_HOLDOUT")
        if file_digest(Path(source["path"])) != source["sha256"]:
            raise Denied("RAW_HASH_CHANGED")
        sources[source["identity"]] = source["sha256"]
    contracts = {"queue": {"version": "EDP_QUEUE_V1", "sha256": file_digest(queue_path)}}
    for name, pin in queue["contracts"].items():
        allowed = policy["contracts"].get(name)
        path = (root / pin["path"]).resolve(strict=True)
        if (allowed is None or not path.is_relative_to(root)
                or pin["version"] != allowed["version"]
                or file_digest(path) != allowed["sha256"]
                or pin.get("sha256", allowed["sha256"]) != allowed["sha256"]):
            raise Denied("CONTRACT_OUT_OF_POLICY")
        contracts[name] = allowed
    if not {"parser", "model", "rule", "registry"} <= set(contracts):
        raise Denied("MISSING_EXECUTION_CONTRACT")
    operations = set(policy["operations"])
    paths = set()
    tables = set()
    for task in queue["tasks"]:
        if task["kind"] not in operations:
            raise Denied("OPERATION_OUT_OF_POLICY")
        source = task.get("source")
        if source is not None:
            member = members.get(source["identity"])
            if (member is None or source["identity"] not in sources
                    or source["path"] != member["raw_path"]
                    or source["sha256"] != member["raw_sha256"]):
                raise Denied("TASK_SOURCE_OUT_OF_POLICY")
        path = task.get("databricks_path")
        table = task.get("databricks_table")
        if path is not None:
            components = path.removeprefix("dbfs:").split("/")
            if (not any(path.startswith(prefix)
                        for prefix in policy["databricks_path_prefixes"])
                    or any(part in {"", ".", ".."} for part in components[1:])):
                raise Denied("DATABRICKS_PATH_OUT_OF_POLICY")
            paths.add(path)
        if table is not None:
            if not any(table.startswith(prefix) for prefix in policy["databricks_table_prefixes"]):
                raise Denied("DATABRICKS_TABLE_OUT_OF_POLICY")
            tables.add(table)
        if task.get("git_operation") not in (None, *policy["git_operations"]):
            raise Denied("GIT_OPERATION_OUT_OF_POLICY")
        if task.get("branch") in policy["protected_branches"]:
            raise Denied("PROTECTED_BRANCH")
        if task["kind"] == "databricks_job_submit":
            name = task["deployment_contract"]
            if task["deployment_path"] != queue["contracts"][name]["path"]:
                raise Denied("DEPLOYMENT_CONTRACT_MISMATCH")
            deployment = json.loads((root / task["deployment_path"]).read_bytes())
            for item in deployment["files"]:
                uri = item["uri"]
                if not any(uri.startswith(prefix)
                           for prefix in policy["databricks_path_prefixes"]):
                    raise Denied("DEPLOYMENT_PATH_OUT_OF_POLICY")
                paths.add(uri)
    limits = policy["limits"]
    if len(queue["tasks"]) > limits["operations"] or sum(
            t.get("runtime_seconds", 0) for t in queue["tasks"]) > limits["runtime_seconds"]:
        raise Denied("BUDGET_EXCEEDED")
    return {"schema": "EDP_SIGNED_GRANT_V1",
            "grant_id": "broker-" + digest(queue_path.read_bytes())[:32],
            "authority": "policy-broker-v1", "issued_at": now.isoformat(),
            "expires_at": min(now + timedelta(hours=policy["grant_hours"]),
                              datetime.fromisoformat(policy["expires_at"])).isoformat(),
            "revocation_id": policy["policy_id"], "cohort": queue["cohort"],
            "sources": sources, "contracts": contracts,
            "operations": sorted({task["kind"] for task in queue["tasks"]}),
            "databricks_paths": sorted(paths), "databricks_tables": sorted(tables),
            "outputs": [queue["output"]],
            "git_operations": sorted({task["git_operation"] for task in queue["tasks"]
                                      if task.get("git_operation")}),
            "protected_branches": policy["protected_branches"], "limits": limits}


def issue(root: Path, queue: Path, policy: Path, trust: Path, key: Path,
          grant_store: Path) -> Path:
    """Protected service entrypoint; key and grant store are outside worktree."""
    if any(path.resolve().is_relative_to(root.resolve()) for path in (key, grant_store, trust)):
        raise Denied("BROKER_MUST_BE_PROTECTED")
    grant = evaluate(root, queue, policy, trust)
    target = grant_store / (grant["grant_id"] + ".json")
    grant_store.mkdir(parents=True, exist_ok=True)
    if target.exists():
        existing = json.loads(target.read_bytes())["grant"]
        scoped = set(grant) - {"issued_at", "expires_at"}
        if any(existing.get(field) != grant[field] for field in scoped):
            raise Denied("GRANT_POLICY_CHANGED")
        if datetime.fromisoformat(existing["expires_at"]) > datetime.now(UTC):
            return target
    with tempfile.TemporaryDirectory() as temporary:
        payload = Path(temporary) / "payload"
        signature = Path(temporary) / "signature"
        payload.write_bytes(canonical(grant))
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(key),
                        "-rawin", "-in", str(payload), "-out", str(signature)],
                       check=True, capture_output=True)
        envelope = {"grant": grant,
                    "signature_base64": base64.b64encode(signature.read_bytes()).decode()}
    staged = target.with_suffix(".next")
    fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical(envelope))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(staged, target)
    return target


def request(socket_path: Path, queue: Path) -> Path:
    """Agent-facing P5 request; the server makes the decision and retains the grant."""
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(30)
        client.connect(str(socket_path))
        client.sendall(canonical({"action": "issue", "queue": str(queue.resolve())}))
        client.shutdown(socket.SHUT_WR)
        response = json.loads(client.recv(8192))
    if response.get("status") != "ISSUED":
        raise Denied(response.get("reason", "BROKER_DENIED"))
    return Path(response["grant_path"])


def execute(socket_path: Path, grant_path: Path, operation: dict) -> dict:
    """Submit one exact operation to the protected credential and ledger holder."""
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(900)
        client.connect(str(socket_path))
        client.sendall(canonical({"action": "execute", "grant_path": str(grant_path),
                                  "operation": operation}))
        client.shutdown(socket.SHUT_WR)
        response = json.loads(client.recv(65536))
    if response.get("status") != "EXECUTED":
        raise Denied(response.get("reason", "PROTECTED_EXECUTION_DENIED"))
    return response["result"]


def serve(socket_path: Path, root: Path, policy: Path, trust: Path, key: Path,
          grant_store: Path) -> None:
    """Run under an independent service identity with protected credentials."""
    if socket_path.resolve().is_relative_to(root.resolve()):
        raise Denied("BROKER_SOCKET_MUST_BE_PROTECTED")
    if socket_path.exists():
        if not socket_path.is_socket() or socket_path.stat().st_uid != 0:
            raise Denied("BROKER_SOCKET_PATH_UNSAFE")
        with socket.socket(socket.AF_UNIX) as probe:
            try:
                probe.connect(str(socket_path))
            except OSError:
                socket_path.unlink()
            else:
                raise Denied("BROKER_ALREADY_RUNNING")
    class Handler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            try:
                query = json.loads(self.rfile.readline(8192))
                if query.get("action") == "issue":
                    path = issue(root, Path(query["queue"]), policy, trust, key, grant_store)
                    response = {"status": "ISSUED", "grant_path": str(path)}
                elif query.get("action") == "execute":
                    from edp_lab.operating.boundaries import databricks_write, git_write
                    from edp_lab.operating.cohort_admission import cohort_admit
                    from edp_lab.operating.databricks_jobs import databricks_job_submit

                    grant_path = Path(query["grant_path"]).resolve(strict=True)
                    if not grant_path.is_relative_to(grant_store.resolve()):
                        raise Denied("GRANT_NOT_IN_PROTECTED_STORE")
                    grant = load_grant(root, grant_path, trust)
                    if grant["authority"] != "policy-broker-v1":
                        raise Denied("BROKER_GRANT_REQUIRED")
                    operation = query["operation"]
                    require_cohort_operation_readonly(operation)
                    if operation.get("grant_path") != str(grant_path):
                        raise Denied("GRANT_PATH_MISMATCH")
                    adapters = {"databricks_write": databricks_write,
                                "databricks_job_submit": databricks_job_submit,
                                "git_write": git_write, "cohort_admit": cohort_admit}
                    adapter = adapters.get(operation.get("operation"))
                    if adapter is None:
                        raise Denied("PROTECTED_OPERATION_NOT_SUPPORTED")
                    result = adapter(root, grant, operation, trust.parent / "ledger",
                                     execute=True)
                    response = {"status": "EXECUTED", "result": result}
                else:
                    raise Denied("UNKNOWN_BROKER_ACTION")
            except (Denied, OSError, ValueError, KeyError) as exc:
                response = {"status": "DENIED", "reason": str(exc)}
            self.wfile.write(canonical(response))

    with socketserver.UnixStreamServer(str(socket_path), Handler) as server:
        os.chown(socket_path, -1, grp.getgrnam("staff").gr_gid)
        os.chmod(socket_path, 0o660)
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Protected standing-policy grant broker")
    for name in ("socket", "root", "policy", "trust", "key", "grant_store"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--databricks-user")
    parser.add_argument("--git-user")
    args = parser.parse_args()
    os.environ["EDP_OWNER_TRUST_DIR"] = str(args.trust)
    if args.databricks_user:
        os.environ["EDP_DATABRICKS_RUN_AS_USER"] = args.databricks_user
        os.environ["EDP_DATABRICKS_PROFILE"] = "edp-lab"
    if args.git_user:
        os.environ["EDP_GIT_RUN_AS_USER"] = args.git_user
    serve(args.socket, args.root, args.policy, args.trust, args.key, args.grant_store)


if __name__ == "__main__":
    main()
