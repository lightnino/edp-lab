"""Protected cohort-neutral Vault broker; owner installation is required."""
from __future__ import annotations

import argparse
import base64
import fcntl
import grp
import json
import os
import socket
import socketserver
import stat
import subprocess
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.operating.authority import Denied, _verify_signature, canonical, verified_document
from edp_lab.vault.standing_v2 import (
    NAMESPACE,
    TABLES,
    authorize_stage,
    grant_for_run,
    validate_cohort_receipt,
    validate_run,
    validate_standing_policy,
)


def _protected(root: Path, base: Path) -> None:
    root, base = root.resolve(strict=True), base.resolve(strict=True)
    if (os.geteuid() != 0 or base.is_relative_to(root)
            or base.stat().st_uid != 0 or base.stat().st_mode & 0o022):
        raise Denied("VAULT_0A_PROTECTED_ROOT_REQUIRED")
    for name in ("trust", "private", "approvals", "eligibility", "grants",
                 "ledger", "receipts"):
        path = base / name
        if (path.stat().st_uid != 0 or path.stat().st_mode & 0o022):
            raise Denied("VAULT_0A_PROTECTED_DIRECTORY_REQUIRED")


def _signed(root: Path, base: Path, name: str) -> dict:
    path = base / "trust" / name
    if path.stat().st_uid != 0 or path.stat().st_mode & 0o022:
        raise Denied("VAULT_0A_SIGNED_POLICY_UNPROTECTED")
    return verified_document(root, path, base / "trust")


def _eligibility(root: Path, base: Path, cohort_id: str, policy: dict) -> dict:
    if not cohort_id or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:-"
                            for character in cohort_id):
        raise Denied("VAULT_COHORT_ID_INVALID")
    path = base / "eligibility" / (cohort_id + ".signed.json")
    if path.stat().st_uid != 0 or path.stat().st_mode & 0o022:
        raise Denied("VAULT_COHORT_RECEIPT_UNPROTECTED")
    receipt = verified_document(root, path, base / "trust")
    validate_cohort_receipt(policy, receipt, root)
    return receipt


def _run_file(root: Path, relative: str) -> dict:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or path.suffix != ".json":
        raise Denied("VAULT_RUN_PATH_INVALID")
    resolved = (root / path).resolve(strict=True)
    if not resolved.is_relative_to(root.resolve()):
        raise Denied("VAULT_RUN_OUTSIDE_WORKTREE")
    if resolved.stat().st_size > 100_000:
        raise Denied("VAULT_RUN_REQUEST_TOO_LARGE")
    return json.loads(resolved.read_bytes())


def _plan(root: Path, receipt: dict, run: dict) -> None:
    """Check every SQL stage against the independently signed plan pin."""
    relative = receipt["load_plan"]["path"]
    plan = json.loads((root / relative).read_bytes())
    if (plan.get("schema") != "EDP_VAULT_LOAD_PLAN_V2"
            or plan.get("cohort_id") != run["cohort_id"]
            or plan.get("input_manifest_sha256") != run["input_manifest_sha256"]
            or plan.get("data_occurrences") != run["data_occurrences"]
            or plan.get("synthetic_rows") != run["synthetic_rows"]
            or not isinstance(plan.get("stages"), list)
            or not 1 <= len(plan["stages"])
            or 3 * len(plan["stages"]) + 11 > run["max_statements"]):
        raise Denied("VAULT_PINNED_PLAN_INVALID")
    expected_tables = plan.get("expected_tables")
    if not isinstance(expected_tables, dict) or set(expected_tables) != set(TABLES):
        raise Denied("VAULT_PLAN_EXPECTED_ROWS_INVALID")
    occurrence_table = expected_tables["r_source_occurrence"]
    event_table = expected_tables["r_load_event"]
    if (not isinstance(occurrence_table, dict) or not isinstance(event_table, dict)
            or not isinstance(occurrence_table.get("rows"), list)
            or len(occurrence_table["rows"]) != run["data_occurrences"]):
        raise Denied("VAULT_PLAN_EXPECTED_ROWS_INVALID")
    if event_table.get("rows") != []:
        raise Denied("VAULT_RUN_AUDIT_MUST_BE_PROTECTED_GENERATED")
    from edp_lab.vault.verifier_v2 import _expected

    _expected(plan)
    stage_scope = {"max_statements": run["max_statements"],
                   "load_plan_sha256": run["load_plan_sha256"]}
    for index, stage in enumerate(plan["stages"], 1):
        request = {**stage, "operation_id": f"{run['run_id']}-{index:03d}",
                   "load_plan_sha256": run["load_plan_sha256"]}
        authorize_stage(stage_scope, request, used_statements=index - 1,
                        uncertain_operation_ids=set())
        if (stage.get("table") not in {f"{NAMESPACE}.{name}" for name in TABLES}
                or stage.get("kind") != "MERGE_INSERT_ONLY"
                or stage["table"] == f"{NAMESPACE}.r_load_event"
                or not isinstance(stage.get("precheck"), str)
                or not stage["precheck"].startswith(
                    f"SELECT COUNT(*) AS mismatches FROM {stage['table']} AS t\n")
                or ";" in stage["precheck"]
                or len(stage["precheck"].encode()) > 600_000
                or len(stage["statement"].encode()) > 600_000
                or not isinstance(stage.get("expected_rows"), int)
                or stage["expected_rows"] < 0):
            raise Denied("VAULT_PLAN_READBACK_BOUND_INVALID")


def _sign(grant: dict, key: Path) -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        message = Path(directory) / "message"
        signature = Path(directory) / "signature"
        message.write_bytes(canonical(grant))
        subprocess.run(["/opt/homebrew/bin/openssl", "pkeyutl", "-sign", "-inkey",
                        str(key), "-rawin", "-in", str(message), "-out", str(signature)],
                       check=True, capture_output=True, timeout=15)
        return signature.read_bytes()


def _reserve_grant_budget(base: Path, maximum: int) -> None:
    """Reserve one issuance durably; a crash consumes capacity, never expands it."""
    ledger = base / "ledger/grant-issuance.json"
    fd = os.open(ledger, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "r+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        content = stream.read()
        used = json.loads(content)["used"] if content else 0
        if used >= maximum:
            raise Denied("VAULT_STANDING_GRANT_CAP_EXHAUSTED")
        stream.seek(0)
        stream.truncate()
        json.dump({"used": used + 1}, stream)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def load_run_grant(root: Path, base: Path, path: Path,
                   *, now: datetime | None = None) -> dict:
    """Verify protected broker signature, current time and revocation."""
    _protected(root, base)
    if (path.resolve().parent != (base / "grants").resolve()
            or path.stat().st_uid != 0 or path.stat().st_mode & 0o022):
        raise Denied("VAULT_GRANT_NOT_PROTECTED")
    envelope = json.loads(path.read_bytes())
    revoked = json.loads((base / "trust/revoked_grants.json").read_bytes())
    return verify_grant_envelope(envelope, base / "trust/broker_ed25519_public.pem",
                                 revoked, now=now)


def verify_grant_envelope(envelope: dict, public_key: Path, revoked: list[str],
                          *, now: datetime | None = None) -> dict:
    """Pure boundary around the signature verifier for negative tests."""
    if set(envelope) != {"grant", "signature_base64"}:
        raise Denied("VAULT_GRANT_ENVELOPE_INVALID")
    grant = envelope["grant"]
    signature = base64.b64decode(envelope["signature_base64"], validate=True)
    _verify_signature(canonical(grant), signature, public_key)
    current = now or datetime.now(UTC)
    if (grant.get("schema") != "EDP_VAULT_RUN_GRANT_V1"
            or grant.get("authority") != "vault-policy-broker-v2"
            or not datetime.fromisoformat(grant["issued_at"]) <= current
            < datetime.fromisoformat(grant["expires_at"])):
        raise Denied("VAULT_GRANT_EXPIRED_OR_INVALID")
    if grant["grant_id"] in revoked or grant["revocation_id"] in revoked:
        raise Denied("VAULT_GRANT_REVOKED")
    return grant


def issue(root: Path, base: Path, run_relative: str) -> Path:
    _protected(root, base)
    policy = _signed(root, base, "policy.signed.json")
    validate_standing_policy(policy, root=root)
    run = _run_file(root, run_relative)
    receipt = _eligibility(root, base, run["cohort_id"], policy)
    validate_run(policy, receipt, run)
    _plan(root, receipt, run)
    grant = grant_for_run(policy, receipt, run)
    grant["grant_id"] += "-" + uuid.uuid4().hex
    key = base / "private/broker.pem"
    if key.stat().st_uid != 0 or key.stat().st_mode & 0o077:
        raise Denied("VAULT_BROKER_KEY_UNPROTECTED")
    _reserve_grant_budget(base, policy["max_total_grants"])
    envelope = {"grant": grant,
                "signature_base64": base64.b64encode(_sign(grant, key)).decode()}
    target = base / "grants" / (grant["grant_id"] + ".json")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical(envelope))
        stream.flush()
        os.fsync(stream.fileno())
    load_run_grant(root, base, target)
    return target


def serve(root: Path, base: Path) -> None:
    _protected(root, base)
    socket_path = base / "broker.sock"
    _prepare_socket(socket_path)

    class Handler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            try:
                request = json.loads(self.rfile.readline(4096))
                if set(request) != {"action", "run_path"} or request["action"] != "grant":
                    raise Denied("VAULT_BROKER_ACTION_DENIED")
                path = issue(root, base, request["run_path"])
                response = {"status": "ISSUED", "grant_path": str(path)}
            except (Denied, OSError, KeyError, TypeError, ValueError) as exc:
                response = {"status": "DENIED", "reason": str(exc)}
            self.wfile.write(canonical(response))

    with socketserver.UnixStreamServer(str(socket_path), Handler) as server:
        os.chown(socket_path, 0, grp.getgrnam("staff").gr_gid)
        os.chmod(socket_path, 0o660)
        server.serve_forever()


def _prepare_socket(socket_path: Path, *, owner_uid: int = 0) -> None:
    """Remove only a root-owned stale socket after an interrupted restart."""
    if socket_path.exists():
        entry = socket_path.lstat()
        if not stat.S_ISSOCK(entry.st_mode) or entry.st_uid != owner_uid:
            raise Denied("VAULT_BROKER_SOCKET_UNTRUSTED")
        with socket.socket(socket.AF_UNIX) as probe:
            probe.settimeout(2)
            try:
                probe.connect(str(socket_path))
            except ConnectionRefusedError:
                socket_path.unlink()
            else:
                raise Denied("VAULT_BROKER_ALREADY_RUNNING")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("base", type=Path)
    args = parser.parse_args()
    serve(args.root, args.base)


if __name__ == "__main__":
    main()
