"""Signed-grant checks at operation boundaries.

The trust directory is supplied by the owner and must be outside the worktree.
Only the owner holds the Ed25519 private key. An editable approval string is never
authority. This module deliberately has no grant creation or signing function.
"""

import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path


class Denied(Exception):
    """Fail-closed authorization or integrity outcome."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise Denied("TIMEZONE_REQUIRED")
    return parsed.astimezone(UTC)


def _trusted_path(root: Path, path: Path) -> Path:
    resolved = path.resolve(strict=True)
    if not path.is_absolute() or resolved.is_relative_to(root.resolve()):
        raise Denied("TRUST_MUST_BE_OUTSIDE_WORKTREE")
    if not resolved.is_file():
        raise Denied("TRUST_FILE_MISSING")
    return resolved


def _verify_signature(payload: bytes, signature: bytes, public_key: Path) -> None:
    with tempfile.TemporaryDirectory() as temp:
        message = Path(temp) / "message"
        sig = Path(temp) / "signature"
        message.write_bytes(payload)
        sig.write_bytes(signature)
        result = subprocess.run(
            ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key),
             "-rawin", "-in", str(message), "-sigfile", str(sig)],
            capture_output=True, check=False, timeout=15,
        )
    if result.returncode:
        raise Denied("INVALID_SIGNATURE")


def load_grant(root: Path, envelope_path: Path, trust_dir: Path, now: datetime | None = None) -> dict:
    """Verify an Ed25519 envelope and externally protected revocation list."""
    root = root.resolve()
    trust = trust_dir.resolve(strict=True)
    if trust.is_relative_to(root):
        raise Denied("TRUST_MUST_BE_OUTSIDE_WORKTREE")
    key = _trusted_path(root, trust / "owner_ed25519_public.pem")
    revoked = _trusted_path(root, trust / "revoked_grants.json")
    try:
        envelope = json.loads(envelope_path.read_bytes())
        if set(envelope) != {"grant", "signature_base64"}:
            raise Denied("INVALID_ENVELOPE")
        signature = base64.b64decode(envelope["signature_base64"], validate=True)
        grant = envelope["grant"]
        _verify_signature(canonical(grant), signature, key)
        required = {"schema", "grant_id", "authority", "issued_at", "expires_at",
                    "cohort", "sources", "contracts", "operations", "databricks_paths",
                    "databricks_tables", "outputs", "git_operations", "protected_branches",
                    "limits", "revocation_id"}
        if set(grant) != required or grant["schema"] != "EDP_SIGNED_GRANT_V1":
            raise Denied("INVALID_GRANT_SCHEMA")
        if not {"queue", "parser", "model", "rule", "registry"} <= set(grant["contracts"]):
            raise Denied("MISSING_EXECUTION_CONTRACT")
        for entry in grant["contracts"].values():
            if (not isinstance(entry.get("version"), str)
                    or not re.fullmatch(r"[a-f0-9]{64}", entry.get("sha256", ""))):
                raise Denied("INVALID_CONTRACT_PIN")
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{8,120}", grant["grant_id"]):
            raise Denied("INVALID_GRANT_ID")
        instant = now or datetime.now(UTC)
        if not _time(grant["issued_at"]) <= instant < _time(grant["expires_at"]):
            raise Denied("GRANT_NOT_CURRENT")
        revoked_ids = json.loads(revoked.read_bytes())
        if not isinstance(revoked_ids, list) or grant["grant_id"] in revoked_ids or grant["revocation_id"] in revoked_ids:
            raise Denied("GRANT_REVOKED")
        return grant
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        raise Denied("INVALID_GRANT_EVIDENCE") from exc


def verified_document(root: Path, envelope_path: Path, trust_dir: Path) -> dict:
    """Verify a separately signed result receipt against the owner trust anchor."""
    key = _trusted_path(root.resolve(), trust_dir / "owner_ed25519_public.pem")
    try:
        envelope = json.loads(envelope_path.read_bytes())
        if set(envelope) != {"document", "signature_base64"}:
            raise Denied("INVALID_SIGNED_DOCUMENT")
        document = envelope["document"]
        signature = base64.b64decode(envelope["signature_base64"], validate=True)
        _verify_signature(canonical(document), signature, key)
        return document
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise Denied("INVALID_SIGNED_DOCUMENT") from exc


def authorize(grant: dict, request: dict, *, root: Path, used: dict | None = None) -> None:
    """Check one exact operation immediately before the caller performs it."""
    used = used or {}
    if request["operation"] not in grant["operations"]:
        raise Denied("OPERATION_OUT_OF_SCOPE")
    if request["cohort"] != grant["cohort"]:
        raise Denied("COHORT_OUT_OF_SCOPE")
    if request["operation"] in {"databricks_write", "databricks_job_submit",
                                "codex_task", "validate_controls", "freeze_verify"} and not {"parser", "model", "rule"} <= set(
                                    request.get("contracts", {})):
        raise Denied("EXECUTION_CONTRACT_NOT_PRESENTED")
    source = request.get("source")
    if source is not None:
        expected = grant["sources"].get(source["identity"])
        if expected is None or expected != source["sha256"]:
            raise Denied("SOURCE_OUT_OF_SCOPE")
        raw = Path(source["path"]).resolve(strict=True)
        if file_digest(raw) != expected:
            raise Denied("RAW_HASH_CHANGED")
    for name, supplied in request.get("contracts", {}).items():
        expected = grant["contracts"].get(name)
        if expected is None or expected["version"] != supplied["version"]:
            raise Denied("CONTRACT_OUT_OF_SCOPE")
        path = (root / supplied["path"]).resolve(strict=True)
        if not path.is_relative_to(root.resolve()) or file_digest(path) != expected["sha256"]:
            raise Denied("CONTRACT_HASH_CHANGED")
    if request.get("databricks_path") not in (None, *grant["databricks_paths"]):
        raise Denied("DATABRICKS_PATH_OUT_OF_SCOPE")
    if request.get("databricks_table") not in (None, *grant["databricks_tables"]):
        raise Denied("DATABRICKS_TABLE_OUT_OF_SCOPE")
    if request.get("output") not in (None, *grant["outputs"]):
        raise Denied("OUTPUT_OUT_OF_SCOPE")
    if request.get("git_operation") is not None:
        if request["git_operation"] not in grant["git_operations"]:
            raise Denied("GIT_OPERATION_OUT_OF_SCOPE")
        if request.get("branch") in grant["protected_branches"]:
            raise Denied("PROTECTED_BRANCH")
    limits = grant["limits"]
    for metric in ("runtime_seconds", "compute_units", "token_count", "retries", "operations"):
        if used.get(metric, 0) + request.get("budget", {}).get(metric, 0) > limits[metric]:
            raise Denied("BUDGET_EXCEEDED")


def protected_trust_dir(root: Path) -> Path:
    value = os.environ.get("EDP_OWNER_TRUST_DIR")
    if not value:
        raise Denied("TRUST_DIRECTORY_REQUIRED")
    trust = Path(value)
    if not trust.is_absolute() or trust.resolve().is_relative_to(root.resolve()):
        raise Denied("TRUST_MUST_BE_OUTSIDE_WORKTREE")
    return trust
