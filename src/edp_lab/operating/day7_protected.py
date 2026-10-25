"""Protected Day 7 publication, C2000 bridge and retained-RAW U10 readback.

Only the installed broker/verifier identity may call these functions with the
owner-signed successor policy and root-owned verifier key. No RAW write exists.
"""

from __future__ import annotations

import csv
import json
import subprocess
from functools import lru_cache
from pathlib import Path

from edp_lab.ingestion.universe import ACTIVE_AUTHORITY_PATH, UniverseGate
from edp_lab.operating.authority import (
    Denied,
    canonical,
    digest,
    file_digest,
    verified_document,
)
from edp_lab.operating.protected_cli import databricks_argv
from edp_lab.operating.protected_verifier import _remote_json, _sign

MANIFEST_SHA = "dcc63767c88ae712eab8f5ba29d52a206b4262710740e591a4b233d9c04c699b"
DECISION_SHA = "416efc5f7ab18b2570ba9beab26bba33210c5e0a75ec813a92ccac953af36d74"
PARENT_SHA = "2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c"
C2000_FREEZE_SHA = "324ca5e416adabc443d18d8066fbccdf137f4cb50aa20934e645615f4ee77ff3"
C2000_BINDINGS_SHA = "2a72b8f8483e2181a3112a26b5d68d702b92308def6e74978838b155cfd85312"
C2000_RESULT_SHA = "942fa887ceea8cf5c9bc64c603c2044e1b643b01fcbc29909ce264c024b69374"
C2000_RECEIPT_SHA = "e1023289fedb3b682e0afe33bc350997e5d84c5aa27e9d00bf34bc760fe93830"
C2000_OUTPUT = "workspace.edp_lab.o_c2000_m2_result_frozen_day5_v1"
C2000_UC_ID = "a9b7d2ab-4d9d-462a-b046-7f04bf144773"


def _protected(root: Path, trust: Path, key: Path | None = None) -> None:
    root = root.resolve()
    for path in (trust, key):
        if path is not None and path.resolve().is_relative_to(root):
            raise Denied("DAY7_TRUST_MUST_BE_PROTECTED")
    if key is not None and (not key.is_file() or key.stat().st_uid != 0
                            or key.stat().st_mode & 0o077):
        raise Denied("DAY7_VERIFIER_KEY_NOT_PROTECTED")


def _policy(root: Path, policy_path: Path, trust: Path) -> dict:
    _protected(root, trust)
    if policy_path.resolve().is_relative_to(root.resolve()):
        raise Denied("DAY7_POLICY_NOT_PROTECTED")
    policy = verified_document(root, policy_path, trust)
    if (policy.get("schema") != "EDP_STANDING_POLICY_V1"
            or policy.get("policy_id") != "edp-lab-standing-day7-c3000-v1"
            or policy.get("universe_path") != str(ACTIVE_AUTHORITY_PATH)
            or policy.get("universe_sha256") != MANIFEST_SHA
            or policy.get("contracts", {}).get("universe_approval", {}).get("sha256") != DECISION_SHA
            or policy.get("cohort_pattern") != "C3000"
            or policy.get("max_increment") != 1000
            or "raw_stage" in policy.get("operations", [])
            or any("/raw/" in prefix.lower() for prefix in policy.get("databricks_path_prefixes", []))):
        raise Denied("DAY7_POLICY_SCOPE_INVALID")
    index_pin = policy.get("contracts", {}).get("source_evidence_index", {})
    index_path = trust.parent / "source_evidence_index.json"
    if (index_pin.get("version") != "EDP_DAY7_SOURCE_EVIDENCE_INDEX_V1"
            or not index_path.is_file()
            or file_digest(index_path) != index_pin.get("sha256")):
        raise Denied("DAY7_SOURCE_EVIDENCE_INDEX_NOT_PINNED")
    return policy


def _source_index(policy: dict, trust: Path) -> tuple[dict, str]:
    path = trust.parent / "source_evidence_index.json"
    expected = policy["contracts"]["source_evidence_index"]["sha256"]
    if file_digest(path) != expected:
        raise Denied("DAY7_SOURCE_EVIDENCE_INDEX_NOT_PINNED")
    index = json.loads(path.read_bytes())
    if (index.get("schema") != "EDP_DAY7_SOURCE_EVIDENCE_INDEX_V1"
            or index.get("status") != "PINNED_DISCOVERY_INPUTS_NOT_U10_VERIFIED"
            or index.get("universe_sha256") != MANIFEST_SHA
            or index.get("owner_decision_sha256") != DECISION_SHA):
        raise Denied("DAY7_SOURCE_EVIDENCE_INDEX_SCOPE_INVALID")
    return index, expected


def _active(root: Path, policy: dict) -> dict:
    gate = UniverseGate.load_active(root, manifest_sha256=policy["universe_sha256"],
                                    approval_sha256=policy["contracts"]["universe_approval"]["sha256"])
    document = gate.document()
    parent = json.loads((root / "metadata/source_universes/approved_v1/manifest.json").read_bytes())
    parent_holdouts = {row["identity"] for row in parent["members"] if row["holdout"]}
    active_holdouts = {row["identity"] for row in document["members"] if row["holdout"]}
    if (document.get("parent_manifest_sha256") != PARENT_SHA
            or document.get("member_count") != 3821
            or document.get("universe_version") != "2"
            or sum(row["holdout"] for row in document["members"]) != 41
            or active_holdouts != parent_holdouts
            or file_digest(root / "metadata/source_universes/approved_v1/manifest.json") != PARENT_SHA):
        raise Denied("DAY7_UNIVERSE_BASELINE_CHANGED")
    return document


def _source_evidence(document: dict) -> tuple[dict[str, dict], str]:
    expansion = document["expansion"]
    rows = [m for m in document["members"] if "remote_raw_path" in m]
    if len(rows) != expansion["new_member_count"] or len(rows) != 800:
        raise Denied("DAY7_DELTA_COUNT_INVALID")
    evidence = Path("/Users/lightnino/Projects/edp-lab-incident/docs/incidents/evidence/800_remote_verification/objects.csv")
    if file_digest(evidence) != expansion["independent_remote_readback_sha256"]:
        raise Denied("DAY7_HISTORICAL_READBACK_CHANGED")
    with evidence.open(newline="") as stream:
        audit = list(csv.DictReader(stream))
    indexed = {row["source_instance_id"]: row for row in audit}
    if len(indexed) != len(audit) or len(audit) != 800:
        raise Denied("DAY7_READBACK_COVERAGE_INVALID")
    for member in rows:
        sid = member["source_instance_id"]
        observed = indexed.get(sid)
        if observed is None:
            raise Denied("DAY7_READBACK_SOURCE_MISSING")
        for path_key, sha_key in (("acquisition_receipt_path", "acquisition_receipt_sha256"),
                                  ("remote_receipt_path", "remote_receipt_sha256")):
            if file_digest(Path(member[path_key])) != member[sha_key]:
                raise Denied("DAY7_SOURCE_RECEIPT_CHANGED")
        acquisition = json.loads(Path(member["acquisition_receipt_path"]).read_bytes())
        receipt = json.loads(Path(member["remote_receipt_path"]).read_bytes())
        if ((acquisition.get("status"), acquisition.get("sha256"), acquisition.get("bytes"))
                != ("COMPLETE", member["raw_sha256"], member["raw_bytes"])
                or (receipt.get("status"), receipt.get("source_instance_id"),
                    receipt.get("remote"), receipt.get("sha256"), receipt.get("bytes"))
                != ("REMOTE_READBACK_SHA256_PASS", sid, member["remote_raw_path"],
                    member["raw_sha256"], member["raw_bytes"])
                or (observed.get("presence"), int(observed["listed_bytes"]),
                    observed.get("size_match"),
                    observed.get("read_size_match"), observed.get("hash_status"),
                    observed.get("current_sha256"), int(observed["read_bytes"]),
                    observed.get("error"))
                != ("PRESENT", member["raw_bytes"], "True", "True", "HASH_MATCH",
                    member["raw_sha256"], member["raw_bytes"], "")):
            raise Denied("DAY7_SOURCE_EVIDENCE_MISMATCH")
    return {m["identity"]: m for m in rows}, file_digest(evidence)


def _receipt(root: Path, trust: Path, key: Path, output: Path, document: dict) -> dict:
    _protected(root, trust, key)
    if output.parent.resolve() != (trust.parent / "receipts").resolve():
        raise Denied("DAY7_RECEIPT_OUTSIDE_PROTECTED_STORE")
    if output.exists():
        old = verified_document(root, output, trust)
        if old != document:
            raise Denied("DAY7_RECEIPT_ALREADY_DIFFERS")
    else:
        _sign(document, key, output)
    return {"status": document["status"], "receipt": str(output),
            "receipt_sha256": file_digest(output)}


def attest_universe(root: Path, policy_path: Path, trust: Path, key: Path,
                    output: Path) -> dict:
    policy = _policy(root, policy_path, trust)
    document = _active(root, policy)
    additions, evidence_sha = _source_evidence(document)
    old = json.loads((root / "metadata/freezes/C2000_v1/C2000.bindings.json").read_bytes())
    old_ids = {row["source_identity"] for row in old}
    if (file_digest(root / "metadata/freezes/C2000_v1/C2000.bindings.json") != C2000_BINDINGS_SHA
            or len(old) != len(old_ids) or len(old) != 2000
            or old_ids & set(additions)
            or len({m["identity"] for m in document["members"] if not m["holdout"]} - old_ids) != 1780):
        raise Denied("DAY7_PRIOR_MEMBERSHIP_CHANGED")
    signed = {"schema": "EDP_DAY7_UNIVERSE_PUBLICATION_RECEIPT_V1",
              "authority": "protected-verifier-v1", "status": "UNIVERSE_PUBLISHED_AND_VERIFIED",
              "manifest_sha256": MANIFEST_SHA, "owner_decision_sha256": DECISION_SHA,
              "parent_manifest_sha256": PARENT_SHA, "historical_raw_readback_sha256": evidence_sha,
              "members": 3821, "holdouts": 41, "additions": 800,
              "c2000_members": 2000, "eligible_after_c2000": 1780, "raw_uploads": 0}
    return _receipt(root, trust, key, output, signed)


def attest_prior(root: Path, policy_path: Path, trust: Path, key: Path,
                 output: Path) -> dict:
    policy = _policy(root, policy_path, trust)
    _active(root, policy)
    freeze_path = root / "metadata/freezes/C2000_v1/freeze.json"
    roster_path = root / "metadata/freezes/C2000_v1/C2000.bindings.json"
    result_path = root / "metadata/freezes/O_C2000_M2_v1/databricks_result_freeze_v1.json"
    receipt_path = root / "metadata/freezes/O_C2000_M2_v1/receipts/c2000-result-freeze.json"
    if tuple(map(file_digest, (freeze_path, roster_path, result_path, receipt_path))) != (
            C2000_FREEZE_SHA, C2000_BINDINGS_SHA, C2000_RESULT_SHA, C2000_RECEIPT_SHA):
        raise Denied("DAY7_C2000_PIN_CHANGED")
    freeze = json.loads(freeze_path.read_bytes())
    result = json.loads(result_path.read_bytes())
    prior = verified_document(root, receipt_path, trust)
    if (freeze.get("status") != "FROZEN_INPUT_NOT_RESULT"
            or freeze["files_sha256"]["C2000.bindings.json"] != C2000_BINDINGS_SHA
            or result.get("status") != "FROZEN_IN_DATABRICKS_SOURCE_PRESERVING"
            or result.get("input_freeze_sha256") != C2000_FREEZE_SHA
            or result.get("live_freeze_receipt_sha256") != C2000_RECEIPT_SHA
            or prior.get("status") != "C2000_RESULT_FROZEN"
            or prior.get("live_readback") != "VERIFIED"
            or prior.get("result_uc_table_id") != C2000_UC_ID
            or prior.get("input_freeze_sha256") != C2000_FREEZE_SHA):
        raise Denied("DAY7_C2000_ACCEPTANCE_INVALID")
    bindings = json.loads(roster_path.read_bytes())
    identities = [row["source_identity"] for row in bindings]
    delivery = [row["source_instance_id"] for row in bindings]
    if (len(identities) != len(set(identities)) or len(identities) != 2000
            or len(set(delivery)) != 2000):
        raise Denied("DAY7_C2000_ROSTER_INVALID")
    active = {m["identity"] for m in json.loads((root / ACTIVE_AUTHORITY_PATH).read_bytes())["members"]}
    if not set(identities) <= active:
        raise Denied("DAY7_C2000_OUTSIDE_UNIVERSE")
    uc = _remote_json("/api/2.1/unity-catalog/tables/" + C2000_OUTPUT, 180)
    if uc.get("full_name") != C2000_OUTPUT or uc.get("table_id") != C2000_UC_ID:
        raise Denied("DAY7_C2000_LIVE_UC_CHANGED")
    signed = {"schema": "EDP_PRIOR_COHORT_RECEIPT_V1",
              "authority": "protected-verifier-v1", "cohort": "C2000",
              "identities": identities, "roster_sha256": digest(canonical(identities)),
              "result_freeze_sha256": C2000_RESULT_SHA,
              "input_freeze_sha256": C2000_FREEZE_SHA,
              "accepted_result_receipt_sha256": C2000_RECEIPT_SHA,
              "live_uc_table_id": C2000_UC_ID,
              "live_uc_response_sha256": digest(canonical(uc)),
              "live_readback": True, "status": "VERIFIED"}
    return _receipt(root, trust, key, output, signed)


def _current_remote_bytes(remote: str) -> bytes:
    command = databricks_argv("fs", "cat", remote, "-p", "edp-lab")
    try:
        response = subprocess.run(command, capture_output=True, timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Denied("RAW_HANDOFF_INCOMPLETE: remote RAW readback unavailable") from exc
    if response.returncode:
        raise Denied("RAW_HANDOFF_INCOMPLETE: remote RAW readback unavailable")
    return response.stdout


@lru_cache(maxsize=10000)
def _remote_listing(remote: str) -> tuple[dict, ...]:
    command = databricks_argv("fs", "ls", remote, "-p", "edp-lab", "-o", "json")
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ()
    if result.returncode:
        return ()
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ()
    if isinstance(parsed, list):
        return tuple(row for row in parsed if isinstance(row, dict))
    if isinstance(parsed, dict) and isinstance(parsed.get("files"), list):
        return tuple(row for row in parsed["files"] if isinstance(row, dict))
    return ()


@lru_cache(maxsize=16)
def _historical_file_index(root_path: str, max_depth: int,
                           max_entries: int) -> dict[str, tuple[str, ...]]:
    pending = [(root_path.rstrip("/"), 0)]
    visited: set[str] = set()
    files: dict[str, list[str]] = {}
    entry_count = 0
    while pending and entry_count < max_entries:
        directory, depth = pending.pop(0)
        if directory in visited or depth > max_depth:
            continue
        visited.add(directory)
        for entry in _remote_listing(directory):
            entry_count += 1
            path = entry.get("path") or entry.get("name")
            if not isinstance(path, str):
                continue
            if not path.startswith("dbfs:"):
                path = directory.rstrip("/") + "/" + path.lstrip("/")
            if entry.get("is_dir", entry.get("directory", False)):
                if depth < max_depth:
                    pending.append((path, depth + 1))
            else:
                files.setdefault(Path(path.rstrip("/")).name, []).append(path)
    return {name: tuple(paths) for name, paths in files.items()}


def _candidate_original_locators(index: dict, source: dict) -> list[tuple[str, str]]:
    identity = source["physical_identity"]
    source_id = source.get("source_instance_id") or identity
    candidates: list[tuple[str, str]] = []
    for item in index.get("known_original_locators", []):
        if (item.get("physical_identity") == identity
                and item.get("sha256") == source["raw_sha256"]
                and item.get("bytes") == source["raw_bytes"]):
            candidates.append((item["remote_path"], "PINNED_HISTORICAL_LOCATOR"))
    for item in index.get("historical_remote_receipts", []):
        if (item.get("source_instance_id") == source_id
                and item.get("sha256") == source["raw_sha256"]
                and item.get("bytes") == source["raw_bytes"]):
            candidates.append((item["remote_path"], "PINNED_HISTORICAL_RECEIPT"))
    basename = Path(source["raw_path"]).name
    for root in index.get("historical_locator_roots", []):
        max_depth, max_entries = int(root.get("max_depth", 5)), int(root.get("max_entries", 10000))
        files = _historical_file_index(root["path"], max_depth, max_entries)
        for name in (identity, source_id, basename):
            candidates.extend((path, "BOUNDED_HISTORICAL_IDENTITY_SHA_BYTE_SEARCH")
                              for path in files.get(name, ()))
    return list(dict.fromkeys(candidates))


def attest_handoff(root: Path, policy_path: Path, trust: Path, key: Path,
                   identity: str, *, live_canary: bool = False) -> dict:
    policy = _policy(root, policy_path, trust)
    document = _active(root, policy)
    additions, historical_readback_sha = _source_evidence(document)
    index, index_sha = _source_index(policy, trust)
    member = additions.get(identity)
    source = next((item for item in index.get("original_sources", [])
                   if item.get("physical_identity") == identity), None)
    provenance = "APPROVED_EXPANSION_RECEIPT"
    if member is not None:
        locators = [(member["remote_raw_path"],
                     "CURRENT_FULL_HASH" if live_canary else "PINNED_HISTORICAL_FULL_HASH")]
        source = {"physical_identity": identity,
                  "source_instance_id": member["source_instance_id"],
                  "raw_sha256": member["raw_sha256"], "raw_bytes": member["raw_bytes"]}
    elif source is not None:
        if (source.get("raw_sha256") != next(
                (row["raw_sha256"] for row in document["members"]
                 if row.get("identity") == identity), None)
                or source.get("raw_path") != next(
                    (row["raw_path"] for row in document["members"]
                     if row.get("identity") == identity), None)):
            raise Denied("DAY7_SOURCE_EVIDENCE_INDEX_MEMBER_MISMATCH")
        locators = _candidate_original_locators(index, source)
        provenance = "PINNED_SOURCE_EVIDENCE_INDEX"
    else:
        raise Denied("RAW_HANDOFF_INCOMPLETE: identity absent from pinned evidence index; Acquisition-only remediation")
    verified: list[tuple[str, bytes, str]] = []
    for locator, locator_source in locators:
        try:
            raw = _current_remote_bytes(locator)
        except Denied:
            continue
        if len(raw) == source["raw_bytes"] and digest(raw) == source["raw_sha256"]:
            verified.append((locator, raw, locator_source))
    if not verified:
        raise Denied("RAW_HANDOFF_INCOMPLETE: no locator independently read back with exact SHA-256 and bytes; Acquisition-only remediation")
    remote, _, locator_source = verified[0]
    if any(item[0] != remote for item in verified):
        raise Denied("RAW_HANDOFF_AMBIGUOUS: multiple exact locators require independent reconciliation")
    member_receipt_sha = member.get("remote_receipt_sha256") if member else None
    signed = {"schema": "EDP_U10_RAW_HANDOFF_RECEIPT_V1",
              "authority": "protected-verifier-v1", "status": "VERIFIED",
              "live_readback": True, "physical_identity": identity,
              "source_instance_id": source.get("source_instance_id") or identity,
              "remote_sha256": source["raw_sha256"], "remote_bytes": source["raw_bytes"],
              "remote_path": remote,
              "manifest_sha256": MANIFEST_SHA,
              "source_evidence_index_sha256": index_sha,
              "historical_independent_readback_sha256": historical_readback_sha,
              "remote_receipt_sha256": member_receipt_sha,
              "locator_provenance": locator_source,
              "evidence_provenance": provenance,
              "readback_mode": "CURRENT_FULL_HASH"}
    output = trust.parent / "receipts" / f"day7-u10-{identity}.json"
    result = _receipt(root, trust, key, output, signed)
    result.update({"physical_identity": identity,
                   "source_instance_id": signed["source_instance_id"],
                   "raw_sha256": signed["remote_sha256"],
                   "raw_bytes": signed["remote_bytes"],
                   "remote_raw_path": signed["remote_path"]})
    return result


def verify_handoff_receipt(root: Path, trust: Path, member: dict,
                           source: dict, manifest: dict,
                           source_evidence_index_sha256: str) -> str:
    """Verify the exact protected U10 receipt used at P5 and admission."""
    identity = member["identity"]
    path = Path(source["raw_handoff_receipt_path"])
    expected = trust.parent / "receipts" / f"day7-u10-{identity}.json"
    if (path.resolve() != expected.resolve()
            or not path.is_file()
            or file_digest(path) != source["raw_handoff_receipt_sha256"]):
        raise Denied("RAW_HANDOFF_RECEIPT_NOT_PINNED")
    proof = verified_document(root, path, trust)
    mode = proof.get("readback_mode")
    index_path = trust.parent / "source_evidence_index.json"
    index_sha = file_digest(index_path) if index_path.is_file() else None
    index_document = json.loads(index_path.read_bytes()) if index_path.is_file() else {}
    original = next((row for row in index_document.get("original_sources", [])
                     if row.get("physical_identity") == identity), None)
    expected_delivery = (member.get("source_instance_id")
                         or (original.get("source_instance_id") if original else None)
                         or identity)
    expected_expansion_sha = manifest.get("expansion", {}).get(
        "independent_remote_readback_sha256")
    if (proof.get("schema") != "EDP_U10_RAW_HANDOFF_RECEIPT_V1"
            or proof.get("authority") != "protected-verifier-v1"
            or proof.get("status") != "VERIFIED"
            or mode != "CURRENT_FULL_HASH"
            or proof.get("live_readback") is not True
            or proof.get("physical_identity") != identity
            or proof.get("source_instance_id") != expected_delivery
            or proof.get("remote_sha256") != member["raw_sha256"]
            or proof.get("remote_bytes") != (member.get("raw_bytes")
                                               or (original or {}).get("raw_bytes"))
            or proof.get("remote_path") != source["remote_raw_path"]
            or proof.get("manifest_sha256") != file_digest(root / ACTIVE_AUTHORITY_PATH)
            or index_sha != source_evidence_index_sha256
            or proof.get("source_evidence_index_sha256") != source_evidence_index_sha256
            or ("remote_raw_path" in member
                and (proof.get("remote_path") != member["remote_raw_path"]
                     or proof.get("remote_receipt_sha256") != member["remote_receipt_sha256"]
                     or proof.get("historical_independent_readback_sha256")
                     != expected_expansion_sha))
            or ("remote_raw_path" not in member
                and proof.get("evidence_provenance") != "PINNED_SOURCE_EVIDENCE_INDEX")):
        raise Denied("RAW_HANDOFF_EVIDENCE_INVALID")
    return file_digest(path)
