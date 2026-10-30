"""Owner Terminal only: sign the already approved C2000 semantic document.

Never run from Codex. This script neither grants writes nor changes policy.
It uses the installed owner key only when the Owner invokes it as root.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from edp_lab.operating.authority import canonical, file_digest, verified_document

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/private/var/db/edp-lab-day6-vault")
UNSIGNED = ROOT / "metadata/authorizations/day6_c2000_full_semantics_owner_decision_v1.unsigned.json"
OUTPUT = BASE / "approvals/c2000-full-semantics-v1.signed.json"


def _exact_commit(expected: str) -> None:
    current = subprocess.run(["/usr/bin/git", "-c", f"safe.directory={ROOT}",
                              "-C", str(ROOT), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True, timeout=30).stdout.strip()
    if current != expected:
        raise RuntimeError("OWNER_UNREVIEWED_COMMIT")
    changed = subprocess.run(["/usr/bin/git", "-c", f"safe.directory={ROOT}",
                              "-C", str(ROOT), "status", "--porcelain",
                              "--untracked-files=no"],
                             capture_output=True, text=True, check=True, timeout=30).stdout.strip()
    if changed:
        raise RuntimeError("OWNER_TRACKED_WORKTREE_CHANGED")


def preflight(expected_commit: str, expected_payload_sha256: str) -> dict:
    if os.geteuid() != 0 or ROOT != Path(
            "/Users/lightnino/Projects/edp-lab-day6-vault-prototype"):
        raise RuntimeError("OWNER_ROOT_TERMINAL_REQUIRED")
    _exact_commit(expected_commit)
    if file_digest(UNSIGNED) != expected_payload_sha256:
        raise RuntimeError("OWNER_SEMANTIC_PAYLOAD_CHANGED")
    if OUTPUT.exists():
        raise RuntimeError("OWNER_SEMANTIC_DOCUMENT_ALREADY_SIGNED")
    request = json.loads(UNSIGNED.read_bytes())
    if (set(request) != {"schema", "signature_status", "document"}
            or request["signature_status"] != "PENDING_OWNER_CONTROLLED_SIGNATURE"
            or request["document"].get("decision_id") !=
                "DAY6_C2000_FULL_SOURCE_BUSINESS_SEMANTICS_2026_10_25_V1"
            or request["document"].get("cohort") != "C2000"
            or request["document"].get("status") != "APPROVED"):
        raise RuntimeError("OWNER_SEMANTIC_DOCUMENT_INVALID")
    for pin in request["document"]["contract_pins"]:
        if file_digest(ROOT / pin["path"]) != pin["sha256"]:
            raise RuntimeError("OWNER_CONTRACT_PIN_CHANGED:" + pin["version"])
    policy = verified_document(ROOT, BASE / "trust/policy.signed.json", BASE / "trust")
    if policy.get("schema") != "EDP_VAULT_STANDING_POLICY_V2":
        raise RuntimeError("OWNER_INSTALLED_ISSUER_UNVERIFIED")
    key = BASE / "private/owner.pem"
    if (key.is_symlink() or key.stat().st_uid != 0
            or key.stat().st_mode & 0o077):
        raise RuntimeError("OWNER_KEY_NOT_PROTECTED")
    return request["document"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected_commit")
    parser.add_argument("expected_payload_sha256")
    args = parser.parse_args()
    document = preflight(args.expected_commit, args.expected_payload_sha256)
    with tempfile.TemporaryDirectory(prefix="owner-semantic-", dir=BASE / "private") as folder:
        payload = Path(folder) / "document.payload"
        signature = Path(folder) / "document.sig"
        payload.write_bytes(canonical(document))
        subprocess.run(["/opt/homebrew/bin/openssl", "pkeyutl", "-sign", "-inkey",
                        str(BASE / "private/owner.pem"), "-rawin", "-in", str(payload),
                        "-out", str(signature)], check=True, timeout=30)
        envelope = {"document": document,
                    "signature_base64": base64.b64encode(signature.read_bytes()).decode()}
        fd = os.open(OUTPUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(canonical(envelope))
            stream.flush()
            os.fsync(stream.fileno())
    if verified_document(ROOT, OUTPUT, BASE / "trust") != document:
        raise RuntimeError("OWNER_SIGNED_DOCUMENT_READBACK_MISMATCH")
    print(json.dumps({"status": "SIGNED_OWNER_SEMANTICS_ONLY",
                      "signed_document_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
                      "path": str(OUTPUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
