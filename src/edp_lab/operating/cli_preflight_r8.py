"""R8: fail-closed, read-only installed CLI preflight; NEVER a write grant.

The one-time Day 5 owner recovery installer is historical and must not be rerun.
This module emits only sanitized findings and hashes; it does not declare
pre-submission/no-effect proof or issue authorization.
"""

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from edp_lab.operating.authority import Denied


@dataclass(frozen=True)
class CliResponse:
    returncode: int
    stdout: bytes
    stderr: bytes


class ProtectedResponseStore:
    """Append-only raw CLI evidence in an existing owner-only root directory."""

    def __init__(self, directory: Path) -> None:
        if (directory.is_symlink() or not directory.is_dir()
                or directory.resolve().is_relative_to(Path.cwd().resolve())):
            raise Denied("PREFLIGHT_EVIDENCE_DIR_UNTRUSTED")
        info = directory.stat()
        if info.st_uid != 0 or info.st_mode & 0o077:
            raise Denied("PREFLIGHT_EVIDENCE_DIR_UNTRUSTED")
        self.directory = directory

    def __call__(self, label: str, response: CliResponse) -> None:
        if not re.fullmatch(r"[a-z0-9-]{1,40}", label):
            raise Denied("PREFLIGHT_EVIDENCE_LABEL_INVALID")
        for suffix, data in (("stdout", response.stdout), ("stderr", response.stderr)):
            path = self.directory / f"{label}.{suffix}.bin"
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError as exc:
                raise Denied("PREFLIGHT_EVIDENCE_WRITE_FAILED") from exc


def _text(value: bytes) -> str:
    try:
        return value.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise Denied("PREFLIGHT_INVALID_UTF8") from exc


def _json(value: bytes) -> dict:
    try:
        parsed = json.loads(_text(value))
    except (ValueError, TypeError) as exc:
        raise Denied("PREFLIGHT_INVALID_JSON") from exc
    if not isinstance(parsed, dict):
        raise Denied("PREFLIGHT_INVALID_RESPONSE_SHAPE")
    return parsed


def verify_identity(response: CliResponse, *, expected_user: str) -> dict:
    """Authenticated current-user me response, not a fabricated profile label."""
    if response.returncode != 0 or response.stderr.strip():
        raise Denied("PREFLIGHT_IDENTITY_FAILED")
    identity = _json(response.stdout)
    user = identity.get("userName", identity.get("user_name"))
    if not isinstance(user, str) or user != expected_user:
        raise Denied("PREFLIGHT_IDENTITY_MISMATCH")
    return {"status": "IDENTITY_VERIFIED", "identity_sha256": hashlib.sha256(
        user.encode("utf-8")).hexdigest()}


def exact_uc_missing(response: CliResponse, *, table: str) -> bool:
    """Only target-bound documented CLI/UC not-found formats qualify."""
    if response.returncode != 1 or (response.stderr.strip() and response.stdout.strip()):
        return False
    try:
        message = _text(response.stderr or response.stdout)
    except Denied:
        return False
    expected = f"Table '{table}' does not exist."
    if message == "Error: " + expected:
        return True
    message = message.removeprefix("Error: ")
    try:
        body = json.loads(message)
    except ValueError:
        return False
    return (isinstance(body, dict)
            and body.get("error_code") == "TABLE_DOES_NOT_EXIST"
            and body.get("message") == expected)


def exact_uc_present(response: CliResponse, *, table: str) -> dict:
    """Require a successful UC response naming the requested physical table."""
    if response.returncode != 0 or response.stderr.strip():
        raise Denied("PREFLIGHT_TARGET_PRESENT_UNVERIFIED")
    body = _json(response.stdout)
    catalog, schema, name = table.split(".")
    if (body.get("full_name") != table or body.get("catalog_name") != catalog
            or body.get("schema_name") != schema or body.get("name") != name
            or not isinstance(body.get("table_id"), str)
            or not body["table_id"]):
        raise Denied("PREFLIGHT_TARGET_IDENTITY_MISMATCH")
    return {"table_id_sha256": hashlib.sha256(body["table_id"].encode()).hexdigest()}


def inspect_history_page(response: CliResponse) -> tuple[int, str | None]:
    """Return visible result count and the exact next token; no effect inference."""
    if response.returncode != 0 or response.stderr.strip():
        raise Denied("PREFLIGHT_HISTORY_CLI_FAILED")
    page = _json(response.stdout)
    groups = [page[key] for key in ("res", "queries", "results") if key in page]
    if (len(groups) > 1 or any(not isinstance(items, list) for items in groups)):
        raise Denied("PREFLIGHT_HISTORY_SHAPE_UNRECOGNIZED")
    more = page.get("has_next_page")
    if type(more) is not bool:
        raise Denied("PREFLIGHT_HISTORY_PAGINATION_UNKNOWN")
    token = page.get("next_page_token")
    # The installed CLI emits {"has_next_page": false} for an empty window.
    if not groups and (more or token is not None or set(page) != {"has_next_page"}):
        raise Denied("PREFLIGHT_HISTORY_SHAPE_UNRECOGNIZED")
    if more and (not isinstance(token, str) or not token):
        raise Denied("PREFLIGHT_HISTORY_NEXT_PAGE_MISSING")
    if not more and token:
        raise Denied("PREFLIGHT_HISTORY_CONTRADICTORY_PAGINATION")
    return len(groups[0]) if groups else 0, token if more else None


def check_profile(profile: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", profile):
        raise Denied("PREFLIGHT_PROFILE_INVALID")
    return profile


def inspect_readonly(
    *, cli: str, profile: str, expected_user: str, table: str,
    start_ms: int, end_ms: int, expected_uc_state: str,
    max_pages: int = 10,
    invoke=None, raw_response_store=None,
) -> dict:
    """Owner-terminal read-only inspection; never proves no external effects.

    The effective CLI profile and expected identity must be owner specified.
    Responses stay in protected memory; only digests and sanitized reason codes
    are emitted. A positive result is READONLY_EVIDENCE_ONLY, not permission
    for a new operation or proof an old statement never arrived.
    """
    check_profile(profile)
    if (not isinstance(expected_user, str) or not expected_user
            or not re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+){2,}", table)
            or type(start_ms) is not int or type(end_ms) is not int
            or start_ms <= 0 or end_ms <= start_ms
            or expected_uc_state not in {"PRESENT", "ABSENT"}
            or type(max_pages) is not int or not 1 <= max_pages <= 100):
        raise Denied("PREFLIGHT_SCOPE_INVALID")
    if invoke is None:
        def invoke(*parts):
            result = subprocess.run([cli, *parts], capture_output=True, timeout=60,
                                    check=False)
            return CliResponse(result.returncode, result.stdout, result.stderr)

    def call(*args):
        result = invoke(*args)
        if not isinstance(result, CliResponse):
            raise Denied("PREFLIGHT_INVALID_COMMAND_RESULT")
        return result

    identity_response = call("current-user", "me", "-p", profile, "-o", "json")
    if raw_response_store is not None:
        raw_response_store("identity", identity_response)
    identity = verify_identity(identity_response,
                               expected_user=expected_user)
    window = ("/api/2.0/sql/history/queries?"
              f"filter_by.query_start_time_range.start_time_ms={start_ms}&"
              f"filter_by.query_start_time_range.end_time_ms={end_ms}&max_results=100")
    tokens = set()
    seen = 0
    pages = 0
    history_hashes = []
    history_stderr_hashes = []
    next_token = None
    while pages < max_pages:
        path = window if next_token is None else window + "&page_token=" + quote(
            next_token, safe="")
        page = call("api", "get", path, "-p", profile, "-o", "json")
        if raw_response_store is not None:
            raw_response_store(f"history-{pages:03d}", page)
        num, next_token = inspect_history_page(page)
        history_hashes.append(hashlib.sha256(page.stdout).hexdigest())
        history_stderr_hashes.append(hashlib.sha256(page.stderr).hexdigest())
        pages += 1
        seen += num
        if next_token is None:
            break
        if next_token in tokens:
            raise Denied("PREFLIGHT_HISTORY_PAGINATION_CYCLE")
        tokens.add(next_token)
    else:
        raise Denied("PREFLIGHT_HISTORY_PAGE_LIMIT")

    uc = call("api", "get", "/api/2.1/unity-catalog/tables/" + table,
              "-p", profile, "-o", "json")
    if raw_response_store is not None:
        raw_response_store("uc-target", uc)
    if expected_uc_state == "ABSENT":
        if not exact_uc_missing(uc, table=table):
            raise Denied("PREFLIGHT_TARGET_ABSENCE_UNVERIFIED")
        uc_identity = {}
    else:
        uc_identity = exact_uc_present(uc, table=table)
    return {
        "schema": "EDP_READONLY_CLI_PREFLIGHT_V2",
        "status": "READONLY_EVIDENCE_ONLY",
        "profile": profile,
        "identity_sha256": identity["identity_sha256"],
        "identity_stdout_sha256": hashlib.sha256(identity_response.stdout).hexdigest(),
        "identity_stderr_sha256": hashlib.sha256(identity_response.stderr).hexdigest(),
        "history_stdout_sha256": history_hashes,
        "history_stderr_sha256": history_stderr_hashes,
        "raw_responses_preserved_in_protected_store": raw_response_store is not None,
        "pages_checked": pages,
        "visible_queries": seen,
        "target": table,
        "expected_uc_state": expected_uc_state,
        "observed_uc_state": expected_uc_state,
        **uc_identity,
        "uncertain_external_effects_resolved": False,
        "write_or_recovery_authorized": False,
        "uc_stdout_sha256": hashlib.sha256(uc.stdout).hexdigest(),
        "uc_stderr_sha256": hashlib.sha256(uc.stderr).hexdigest(),
    }
