"""Host-pinned N450/C750 preflight. Proposal evidence never grants execution.

Installing an owner grant requires a separately reviewed host deployment. No caller
can supply a pin or approval path. Existing historical consumers remain excluded.
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path

from edp_lab.ingestion.universe import ScopeDenied, UniverseGate, sha

PACKET = Path("proposals/n450-v1")
PINS = {
    "roster.json": "1567d32bb1db1fedfcf5bafb4538cbbdf4bba06af460c3eb6cb075f590a5a08b",
    "qualification.json": "656a27c1fc994cb340b9b818ed9eb2adfd2527be79fadda1c2f8ede67949c084",
    "c750-proposed.json": "f7994d3a4db77c3d16f8f3c805f57bd23755b165b120740b153d97b0d523eee6",
    "remote-live.json": "8b46ce38d970be771ad56bbfd1a86d8eb60438852f3e9b5fe98fa57ac10f844b",
}
# Deliberately absent. Agent-generated files cannot activate these actions.
OWNER_GRANT_SHA256 = "de242d3754688288cb174fbfde2f8cbc6594fc80b36a8d6281726ca9479322e7"
OWNER_GRANT_PATH = Path("metadata/authorizations/n450_processing_v6.json")
ACTIONS = {"admission", "freeze", "upload", "processing", "remote_processing"}
# Trusted installation path; never taken from a request or environment override.
HISTORICAL_RAW_ROOT = Path("/Users/lightnino/Projects/edp-lab/data/raw")


def _require(condition, reason):
    if not condition:
        raise ScopeDenied(reason)


def validate_packet(root, *, _verified_gate=None):
    """Read-only evidence validation, without RAW reads or execution authority."""
    root = Path(root)
    gate = UniverseGate.load(root) if _verified_gate is None else _verified_gate
    gate.verify_inventory(root)
    try:
        docs = {}
        for name, expected in PINS.items():
            raw = (root / PACKET / name).read_bytes()
            _require(sha(raw) == expected, "COHORT_PACKET_PIN_MISMATCH")
            docs[name] = json.loads(raw)
        roster = docs["roster.json"]
        qualification = docs["qualification.json"]
        union = docs["c750-proposed.json"]
        _require(len(roster) == 450 and len(union) == 750, "COHORT_COUNT_MISMATCH")
        side = json.loads(gate.bindings)
        historical = {b["delivery_identity"]: b for b in side["bindings"]
                      if b["identity"] in side["cohorts"]["C300"]["identities"]}
        _require(len(historical) == 300, "C300_COUNT_MISMATCH")
        _require(set(qualification["excluded_c300"]) == set(historical), "C300_MISMATCH")
        old_rows = list(csv.DictReader((root / "metadata/corpus_manifest_v3.csv").open()))
        old_hashes = {r["raw_sha256"] for r in old_rows}
        for field in ("source_identity", "raw_path", "raw_sha256"):
            _require(len({r[field] for r in roster}) == 450, "DUPLICATE_COHORT_BINDING")
        for row in roster:
            identity = row["source_identity"]
            gate.check(identity, row["raw_sha256"], row["raw_path"])
            _require(identity not in historical, "C300_OVERLAP")
            _require(identity not in qualification["excluded_holdouts"], "HOLDOUT_OVERLAP")
            _require(identity not in qualification["excluded_outside_ids"], "EXCLUDED_SOURCE")
            _require(row["raw_sha256"] not in old_hashes, "HISTORICAL_HASH_OVERLAP")
        expected = {i: b["raw_sha256"] for i, b in historical.items()}
        expected.update({r["source_identity"]: r["raw_sha256"] for r in roster})
        _require(len(expected) == 750, "COHORT_OVERLAP")
        _require(len({r["source_identity"] for r in union}) == 750, "DUPLICATE_UNION")
        _require({r["source_identity"]: r["raw_sha256"] for r in union} == expected,
                 "C750_UNION_MISMATCH")
        objects = docs["remote-live.json"]["objects"]
        indexed = {r["source_identity"]: r for r in objects}
        _require(len(objects) == len(indexed) == 450, "REMOTE_ROSTER_MISMATCH")
        _require(len({r["remote"] for r in objects}) == 450, "DUPLICATE_REMOTE_PATH")
        for row in roster:
            obj = indexed[row["source_identity"]]
            _require(obj["expected_sha256"] == obj["actual_sha256"] == row["raw_sha256"]
                     and obj["bytes"] == row["bytes"]
                     and obj["remote_status"] == "EXACT_REMOTE_BYTES_PASS",
                     "REMOTE_EVIDENCE_MISMATCH")
        return {"status": "VALIDATED_NOT_AUTHORIZED", "n450": 450, "c750": 750,
                "universe": gate.scope_reference(), "packet_sha256": dict(PINS)}
    except (OSError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, ScopeDenied):
            raise
        raise ScopeDenied("INVALID_COHORT_EVIDENCE") from None


def authorize(root, action, bindings, *, cohort="N450"):
    """Guard every new admission/freeze/transfer/local or remote processing boundary.

    Phase A intentionally has no installed execution grant. This function never
    dispatches a consumer, discovers a directory, submits a job or publishes output.
    """
    _require(action in ACTIONS and cohort in {"N450", "C750"}, "INVALID_COHORT_ACTION")
    if action in {"processing", "remote_processing"} and cohort == "C750":
        from edp_lab.materialization.n450_runtime import authorize_processing
        return authorize_processing(Path(root), action, bindings)
    validate_packet(root)
    _require(OWNER_GRANT_SHA256 is not None, "OWNER_EXECUTION_GRANT_NOT_INSTALLED")
    try:
        raw = (Path(root) / OWNER_GRANT_PATH).read_bytes()
        _require(sha(raw) == OWNER_GRANT_SHA256, "OWNER_GRANT_PIN_MISMATCH")
        grant = json.loads(raw)
        _require(grant["status"] == "OWNER_APPROVED", "INVALID_OWNER_GRANT")
        _require(grant["packet_sha256"] == PINS, "GRANT_PACKET_MISMATCH")
        _require(grant["universe"] == UniverseGate.load(Path(root)).scope_reference(),
                 "GRANT_UNIVERSE_MISMATCH")
        scope = grant["scopes"].get(action)
        _require(scope is not None and cohort == scope["cohort"], "ACTION_NOT_AUTHORIZED")
        _require(bindings == scope["bindings"], "EXACT_INPUT_SET_REQUIRED")
        roster = json.loads((Path(root) / PACKET / "roster.json").read_bytes())
        # C750 execution also needs a reviewed complete historical parser/binding
        # contract; Phase A does not manufacture one from the proposal.
        _require(cohort == "N450" or action == "freeze", "C750_PROCESSING_NOT_INSTALLED")
        if cohort == "N450":
            expected = [{"source_instance_id": r["source_identity"],
                         "raw_path": r["raw_path"], "raw_sha256": r["raw_sha256"]}
                        for r in roster]
        else:
            expected = json.loads((Path(root) / PACKET / "c750-proposed.json").read_bytes())
        _require(bindings == expected, "EXACT_INPUT_SET_REQUIRED")
        if action in {"upload", "processing", "remote_processing"}:
            # These actions remain blocked until remote object/immutable snapshot
            # and independently pinned parser approval adapters are installed.
            raise ScopeDenied("STORAGE_OR_PARSER_INTEGRATION_NOT_INSTALLED")
        verify_local_bytes(root)
        if action == "freeze":
            verify_historical_bytes(root)
        return {"status": "AUTHORIZED_PREFLIGHT_ONLY", "grant": grant, "action": action,
                "cohort": cohort, "owner_grant_sha256": sha(raw)}
    except (OSError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, ScopeDenied):
            raise
        raise ScopeDenied("INVALID_OWNER_GRANT") from None


def verify_local_bytes(root):
    """Read-only integrity check, separately callable; never processes payloads."""
    result = validate_packet(root)
    roster = json.loads((Path(root) / PACKET / "roster.json").read_bytes())
    for row in roster:
        path = Path(row["raw_path"])
        _require(path.is_file() and not path.is_symlink(), "MISSING_OR_LINKED_RAW")
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        _require(actual == row["raw_sha256"] and path.stat().st_size == row["bytes"],
                 "RAW_INTEGRITY_MISMATCH")
    return result


def verify_historical_bytes(root):
    """Resolve exact pinned physical inputs while preserving registry-relative aliases."""
    root = Path(root)
    gate = UniverseGate.load(root)
    try:
        doc = gate.document()
        side = json.loads(gate.bindings)
        rows = [b for b in side["bindings"]
                if b["identity"] in side["cohorts"]["C300"]["identities"]]
        _require(len(rows) == len({b["identity"] for b in rows}) == 300,
                 "C300_COUNT_MISMATCH")
        members = {m["identity"]: m for m in doc["members"]}
        inventory_raw = (root / doc["inventory_reference"]).read_bytes()
        _require(sha(inventory_raw) == doc["inventory_sha256"], "INVENTORY_HASH_MISMATCH")
        inventory_rows = list(csv.DictReader(io.StringIO(inventory_raw.decode())))
        inventory = {r["inventory_id"]: r for r in inventory_rows}
        _require(len(inventory) == len(inventory_rows), "DUPLICATE_INVENTORY_IDENTITY")
        checked = []
        # Check all identities and locators before reading any RAW bytes.
        for row in rows:
            relative = Path(row["raw_path"])
            _require(not relative.is_absolute() and ".." not in relative.parts
                     and str(relative) == row["raw_path"]
                     and relative.parts[:2] == ("data", "raw"), "UNSAFE_C300_REGISTRY_PATH")
            suffix = relative.relative_to("data/raw")
            member = members[row["delivery_identity"]]
            path = Path(member["raw_path"])
            _require(path.is_absolute() and path == HISTORICAL_RAW_ROOT / suffix
                     and str(path) == member["raw_path"], "C300_PHYSICAL_PATH_MISMATCH")
            resolved = path.resolve(strict=True)
            _require(resolved.is_relative_to(HISTORICAL_RAW_ROOT.resolve(strict=True))
                     and resolved == HISTORICAL_RAW_ROOT.resolve(strict=True) / suffix
                     and not path.is_symlink() and path.is_file(), "UNSAFE_C300_PHYSICAL_PATH")
            gate.check(row["identity"], row["raw_sha256"], row["raw_path"], cohort="C300")
            gate.check(row["delivery_identity"], row["raw_sha256"], str(path))
            physical = inventory[row["delivery_identity"]]
            _require(physical["final_path"] == str(path)
                     and physical["sha256"] == row["raw_sha256"], "C300_INVENTORY_BINDING_MISMATCH")
            size = int(physical["bytes"])
            _require(size >= 0, "INVALID_C300_SIZE")
            checked.append((path, row["raw_sha256"], size))
        total = 0
        for path, expected, size in checked:
            with path.open("rb") as stream:
                before = os.fstat(stream.fileno())
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
                after = os.fstat(stream.fileno())
            _require(before.st_size == after.st_size == size and actual == expected
                     and (before.st_ino, before.st_mtime_ns, before.st_ctime_ns) ==
                         (after.st_ino, after.st_mtime_ns, after.st_ctime_ns),
                     "C300_RAW_INTEGRITY_MISMATCH")
            total += size
        return {"verified_sources": len(checked), "verified_bytes": total,
                "universe": gate.scope_reference()}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, ScopeDenied):
            raise
        raise ScopeDenied("INVALID_OR_MISSING_C300_RAW_EVIDENCE") from None
