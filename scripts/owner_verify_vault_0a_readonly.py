"""Read-only protected Vault 0A acceptance probe for the Owner Terminal.

Prints no credentials, private keys, signed envelopes, or arbitrary RPC payloads.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import tarfile
from io import BytesIO
from pathlib import Path

from owner_setup_vault_0a_v2 import _rpc

from edp_lab.operating.authority import file_digest, verified_document
from edp_lab.vault.standing_v2 import validate_standing_policy

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/private/var/db/edp-lab-day6-vault")
COMMIT = "4485030d23faee7a993cd07969dc1db6dfa2aea9"
RECEIPT_SHA256 = "04b555202469cd1aa9423da7d6f7639900202693c986859e1b229f3d1427c7b2"
PROPOSAL_SHA256 = "7200b417a3321580147c8d135eef99868c5fb79dbe78ae236f54266240fa3316"


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)


def executor_negative_probe(base: Path, impossible: Path) -> dict:
    lock = base / "ledger/namespace.lock"
    try:
        metadata = lock.lstat()
    except FileNotFoundError:
        raise RuntimeError("NAMESPACE_LOCK_MISSING_OR_INVALID") from None
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == 0,
            "NAMESPACE_LOCK_MISSING_OR_INVALID")
    return _rpc(base / "executor.sock",
                {"action": "execute", "grant_path": str(impossible)})


def runtime_matches_commit() -> int:
    archive = subprocess.run(
        ["/usr/bin/git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
         "archive", COMMIT, "src/edp_lab"],
        capture_output=True, check=True, timeout=30).stdout
    installed = BASE / "runtime/src/edp_lab"
    require(installed.is_dir() and not installed.is_symlink(), "RUNTIME_MISSING")
    expected: set[Path] = set()
    with tarfile.open(fileobj=BytesIO(archive), mode="r:") as tar:
        for member in tar:
            if not member.isfile():
                continue
            relative = Path(member.name).relative_to("src/edp_lab")
            expected.add(relative)
            actual = installed / relative
            require(actual.is_file() and not actual.is_symlink(), "RUNTIME_FILE_MISSING")
            source = tar.extractfile(member)
            require(source is not None, "ARCHIVE_FILE_MISSING")
            require(hashlib.sha256(source.read()).hexdigest() == file_digest(actual),
                    "RUNTIME_FILE_MISMATCH")
    extras = {p.relative_to(installed) for p in installed.rglob("*") if p.is_file()
              and "__pycache__" not in p.parts and p.suffix != ".pyc"} - expected
    require(not extras, "RUNTIME_EXTRA_SOURCE_FILE")
    return len(expected)


def main() -> None:
    require(os.geteuid() == 0, "OWNER_ROOT_TERMINAL_REQUIRED")
    require(BASE.is_dir() and BASE.stat().st_uid == 0, "PROTECTED_ROOT_MISSING")
    proposal_path = ROOT / "metadata/operating/vault_standing_policy_v2_proposal.json"
    require(file_digest(proposal_path) == PROPOSAL_SHA256, "PROPOSAL_HASH_MISMATCH")
    proposal = json.loads(proposal_path.read_bytes())
    signed_policy_path = BASE / "trust/policy.signed.json"
    policy = verified_document(ROOT, signed_policy_path, BASE / "trust")
    require(policy == {**proposal, "status": "OWNER_INSTALLED_STANDING_POLICY"},
            "SIGNED_POLICY_MISMATCH")
    validate_standing_policy(policy, root=ROOT)

    receipt_path = BASE / "receipts/install-v2.signed.json"
    require(file_digest(receipt_path) == RECEIPT_SHA256, "INSTALL_RECEIPT_HASH_MISMATCH")
    receipt = verified_document(ROOT, receipt_path, BASE / "trust")
    require(receipt.get("schema") == "EDP_VAULT_0A_INSTALL_RECEIPT_V2"
            and receipt.get("status") == "VAULT_0A_INSTALLED_AWAITING_ELIGIBLE_RUN"
            and receipt.get("authority") == "protected-verifier-v1"
            and receipt.get("namespace") == policy["namespace"]
            and receipt.get("warehouse_id") == policy["warehouse_id"]
            and receipt.get("warehouse_name") == policy["warehouse_name"]
            and receipt.get("warehouse_mode") == policy["warehouse_mode"]
            and receipt.get("warehouse_service_principal_permission") == "CAN_USE"
            and str(receipt.get("service_principal_id")) == "72304318628585"
            and len(receipt.get("ddl_statement_ids", [])) == 9
            and receipt.get("signed_policy_sha256") == file_digest(signed_policy_path),
            "INSTALL_RECEIPT_CONTENT_MISMATCH")
    files = runtime_matches_commit()

    grants_dir = BASE / "grants"
    ledger_dir = BASE / "ledger"
    before = (sorted(p.name for p in grants_dir.iterdir()),
              sorted(p.name for p in ledger_dir.iterdir()))
    impossible = Path("/private/var/db/edp-lab-day6-vault/never-issued-acceptance-grant.json")
    require(not impossible.exists(), "NEGATIVE_GRANT_PATH_EXISTS")
    broker = _rpc(BASE / "broker.sock", {"action": "unauthorized", "run_path": "x"})
    executor = executor_negative_probe(BASE, impossible)
    after = (sorted(p.name for p in grants_dir.iterdir()),
             sorted(p.name for p in ledger_dir.iterdir()))
    require(broker.get("status") == executor.get("status") == "DENIED"
            and before == after, "NEGATIVE_SERVICE_CHECK_FAILED")
    print(json.dumps({
        "status": "PASS_READ_ONLY_PROTECTED_ACCEPTANCE",
        "receipt_sha256": RECEIPT_SHA256,
        "receipt_signature": "PASS",
        "signed_policy_sha256": file_digest(signed_policy_path),
        "policy_signature_and_scope": "PASS",
        "runtime_commit": COMMIT,
        "runtime_files_verified": files,
        "broker_negative_denied": True,
        "executor_forged_grant_denied": True,
        "grant_and_ledger_names_unchanged": True,
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError, TypeError,
            subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "FAIL_READ_ONLY_PROTECTED_ACCEPTANCE",
                          "reason": str(exc)[:180]}, sort_keys=True))
        raise SystemExit(1) from None
