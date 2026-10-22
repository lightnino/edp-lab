"""Reusable, exact-scope cohort admission and input freeze.

This is an additive successor to the historical N450/C750 implementation. The old
publisher and frozen Day 2/3 artifacts are intentionally not rewritten. The trusted
caller supplies the independently installed owner-grant digest; there is no CLI
option that can promote a proposed grant into an approved one.
"""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

from edp_lab.ingestion.c300_admission import csv_bytes, encoded
from edp_lab.ingestion.gold_set import HEADERS
from edp_lab.ingestion.universe import ScopeDenied, UniverseGate, sha

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"SRC[0-9]{6}\Z")


def require(condition, reason):
    if not condition:
        raise ScopeDenied(reason)


def inside(root, raw, prefix="metadata/"):
    """Resolve a reviewed, relative metadata destination without escaping root."""
    require(isinstance(raw, str) and raw.startswith(prefix), "UNSAFE_COHORT_PATH")
    relative = Path(raw)
    require(not relative.is_absolute() and ".." not in relative.parts
            and str(relative) == raw, "UNSAFE_COHORT_PATH")
    root = Path(root).resolve()
    path = root / relative
    require(path.resolve().is_relative_to(root), "UNSAFE_COHORT_PATH")
    require(not any(p.is_symlink() for p in (path, *path.parents) if p != root),
            "UNSAFE_COHORT_PATH")
    return path


def read_csv(raw):
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))


def read_frozen(root, plan):
    paths = {key: inside(root, plan[key]) for key in
             ("baseline_roster", "baseline_bindings", "baseline_manifest",
              "baseline_freeze")}
    raw = {key: path.read_bytes() for key, path in paths.items()}
    hashes = plan["baseline_sha256"]
    require(set(hashes) == set(raw) and
            all(_SHA.fullmatch(hashes[k]) and sha(v) == hashes[k]
                for k, v in raw.items()), "BASELINE_HASH_MISMATCH")
    freeze = json.loads(raw["baseline_freeze"])
    require(freeze["status"] == "FROZEN", "BASELINE_NOT_FROZEN")
    return raw


def prepare(root, plan):
    """Read-only, deterministic output planner for any approved increment."""
    root = Path(root).resolve()
    require(plan["version"] == "COHORT_ADDITIVE_V1", "INVALID_COHORT_PLAN")
    previous, increment, combined = (plan[key] for key in
                                     ("baseline", "increment", "combined"))
    require(all(re.fullmatch(r"[CN][0-9]+", c) for c in
                (previous, increment, combined)), "INVALID_COHORT_ID")
    baseline = read_frozen(root, plan)
    old_roster = read_csv(baseline["baseline_roster"])
    old_bindings = json.loads(baseline["baseline_bindings"])
    old_manifest = read_csv(baseline["baseline_manifest"])
    require(len(old_roster) == plan["baseline_count"] and
            len({r["source_instance_id"] for r in old_roster}) == len(old_roster),
            "BASELINE_ROSTER_MISMATCH")
    require(len(old_bindings) >= len(old_roster) and
            len({r["source_identity"] for r in old_bindings}) == len(old_bindings),
            "BASELINE_BINDINGS_INVALID")
    selected = plan["selected"]
    require(len(selected) == plan["increment_count"] and
            len(old_roster) + len(selected) == plan["combined_count"],
            "COHORT_COUNT_MISMATCH")
    require(len({r["source_instance_id"] for r in old_manifest}) == len(old_manifest),
            "HISTORICAL_MANIFEST_DUPLICATES")
    gate = UniverseGate.load(root)
    gate.verify_inventory(root)
    original_ids = {r["source_instance_id"] for r in old_manifest}
    physical = {r["source_identity"] for r in old_bindings}
    known_sha = {r["raw_sha256"] for r in old_manifest}
    selected_ids, selected_physical, new_rows, new_bindings = set(), set(), [], []
    for r in selected:
        identity, registered, digest = (r[k] for k in
                                        ("source_identity", "source_instance_id",
                                         "raw_sha256"))
        require(_ID.fullmatch(registered) and _SHA.fullmatch(digest),
                "INVALID_NEW_REGISTRATION")
        require(registered not in original_ids | selected_ids and
                identity not in physical | selected_physical and
                digest not in known_sha, "COHORT_OVERLAP")
        checked = gate.check(identity, digest, r["physical_raw_path"])
        require(checked["physical_identity"] == identity, "PHYSICAL_IDENTITY_MISMATCH")
        require(r["raw_path"].startswith("data/raw/") and
                ".." not in Path(r["raw_path"]).parts, "UNSAFE_REGISTERED_RAW_PATH")
        require(r["family"] and r["raw_path"], "INVALID_NEW_SOURCE")
        selected_ids.add(registered)
        selected_physical.add(identity)
        known_sha.add(digest)
        new_rows.append(dict(zip(HEADERS, (
            registered, r["family"], plan["admitted_at_utc"], increment,
            r["raw_path"], digest, "REAL", "", "", "FALSE", "", "ADMITTED"
        ), strict=True)))
        new_bindings.append({"source_identity": identity,
                             "source_instance_id": registered,
                             "raw_path": r["raw_path"],
                             "raw_sha256": digest})
    require(len(selected_ids) == len(selected_physical) == len(selected),
            "DUPLICATE_SELECTED_SOURCE")
    require(set(plan["baseline_sha256"]) ==
            {"baseline_roster", "baseline_bindings", "baseline_manifest", "baseline_freeze"},
            "BASELINE_SHA_SCOPE_MISMATCH")
    require(re.fullmatch(rf"metadata/admissions/{increment}_v[1-9][0-9]*",
                         plan["admission_path"]) and
            re.fullmatch(rf"metadata/freezes/{combined}_v[1-9][0-9]*",
                         plan["freeze_path"]), "COHORT_DESTINATION_MISMATCH")
    require(plan["manifest_version"] >= 4 and
            isinstance(plan["manifest_version"], int), "INVALID_MANIFEST_VERSION")
    all_rows = old_manifest + new_rows
    require(len({r["raw_path"] for r in all_rows}) == len(all_rows), "RAW_PATH_COLLISION")
    admitted = {
        f"corpus_manifest_v{plan['manifest_version']}.original.csv":
            baseline["baseline_manifest"],
        f"corpus_manifest_v{plan['manifest_version'] + 1}.csv":
            csv_bytes(HEADERS, all_rows),
        f"{increment}.csv": csv_bytes(("source_instance_id",), [
            {"source_instance_id": r["source_instance_id"]} for r in new_rows]),
        "bindings.json": encoded(new_bindings),
    }
    admitted["admission.json"] = encoded({
        "schema": "INCREMENT_ADMISSION_V1", "cohort": increment,
        "status": "ADMITTED", "universe": gate.scope_reference(),
        "files_sha256": {k: sha(v) for k, v in admitted.items()},
    })
    all_cohort_ids = [*old_roster, *[
        {"source_instance_id": r["source_instance_id"]} for r in new_rows]]
    require(len({r["source_instance_id"] for r in all_cohort_ids}) ==
            plan["combined_count"], "COMBINED_ROSTER_COLLISION")
    combined_files = {
        f"{combined}.csv": csv_bytes(("source_instance_id",), all_cohort_ids),
        f"{combined}.bindings.json": encoded([*old_bindings, *new_bindings]),
        f"{previous}.original.csv": baseline["baseline_roster"],
    }
    combined_files["freeze.json"] = encoded({
        "schema": "COMBINED_COHORT_FREEZE_V1", "status": "FROZEN",
        "cohort": combined, "baseline": previous, "increment": increment,
        "universe": gate.scope_reference(),
        "admission_files_sha256": {k: sha(v) for k, v in admitted.items()},
        "files_sha256": {k: sha(v) for k, v in combined_files.items()},
        "processing_authorization": "NOT_GRANTED",
        "output_freeze": "NOT_RESULT_FREEZE",
    })
    return {"admission": admitted, "freeze": combined_files}


def authorize(plan_raw, grant_raw, trusted_grant_sha256):
    """Require a digest independently installed by the trusted owner/operator.

    The digest cannot be derived from an agent-generated plan or record. A
    proposal's internal OWNER_APPROVED label alone does not confer authority.
    """
    require(isinstance(trusted_grant_sha256, str) and
            _SHA.fullmatch(trusted_grant_sha256), "TRUSTED_GRANT_NOT_INSTALLED")
    require(sha(grant_raw) == trusted_grant_sha256, "OWNER_GRANT_PIN_MISMATCH")
    grant = json.loads(grant_raw)
    require(grant.get("status") == "OWNER_APPROVED" and
            grant.get("plan_sha256") == sha(plan_raw),
            "OWNER_SCOPE_MISMATCH")
    return grant


def publish(root, plan_raw, grant_raw, trusted_grant_sha256, action):
    """Exclusive, scope-pinned publication; this function never grants itself access."""
    require(action in ("admission", "freeze"), "INVALID_COHORT_ACTION")
    grant = authorize(plan_raw, grant_raw, trusted_grant_sha256)
    plan = json.loads(plan_raw)
    files = prepare(root, plan)
    scope = grant.get("scopes", {}).get(action)
    target = plan["admission_path" if action == "admission" else "freeze_path"]
    require(scope is not None and scope.get("destination") == target and
            scope.get("cohort") == plan["increment" if action == "admission"
                                         else "combined"] and
            scope.get("files_sha256") ==
            {k: sha(v) for k, v in files[action].items()},
            "ACTION_NOT_AUTHORIZED")
    path = inside(root, target)
    require(not path.exists(), "PUBLICATION_ALREADY_EXISTS")
    if action == "freeze":
        admitted = inside(root, plan["admission_path"])
        require(admitted.is_dir() and not admitted.is_symlink(), "ADMISSION_NOT_PUBLISHED")
        require({p.name for p in admitted.iterdir()} == set(files["admission"]),
                "ADMISSION_FILE_SET_MISMATCH")
        require(all((admitted / k).is_file() and not (admitted / k).is_symlink()
                    and (admitted / k).read_bytes() == v
                    for k, v in files["admission"].items()),
                "ADMISSION_BYTES_CHANGED")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir()
    for name, data in files[action].items():
        with (path / name).open("xb") as out:
            out.write(data)
    require(all((path / name).read_bytes() == data
                for name, data in files[action].items()), "PUBLICATION_READBACK_FAILED")
    return {"status": "PUBLISHED", "cohort": scope["cohort"],
            "path": target, "files_sha256": scope["files_sha256"]}
