"""Resolve frozen N750 RAW locations, upload missing originals, and hash readback.

The installed Step 8 owner pin and frozen inputs are checked before effects.
Evidence is written only under ignored runs/. No existing remote object is overwritten.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.ingestion.n750_step8_authorization import authorize

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/n750/step8-v1/raw"
BASE = "dbfs:/Volumes/workspace/edp_lab/raw"
NEW = BASE + "/n750-step8-raw-v1-5ae18d7d2ee7"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cli(*args):
    result = subprocess.run(["databricks", *args, "-p", "edp-lab", "-o", "json"],
                            check=False, capture_output=True, text=True, timeout=1800)
    if result.returncode:
        raise RuntimeError(f"Databricks {args[:2]} failed: {result.stderr.strip()}")
    return result.stdout


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def verified_receipt(path, binding):
    if not path.exists():
        return None
    value = json.loads(path.read_bytes())
    assert value["source_instance_id"] == binding["source_instance_id"]
    assert value["expected_sha256"] == binding["raw_sha256"]
    assert value["actual_sha256"] == binding["raw_sha256"]
    assert value["status"] == "EXACT_REMOTE_BYTES_PASS"
    return value


def main():
    started = time.monotonic()
    bindings = json.loads((ROOT / "metadata/admissions/N750_v1/bindings.json").read_bytes())
    plan = json.loads((ROOT / "proposals/n750-step1-v3/plan.json").read_bytes())
    qualification = json.loads((ROOT / "proposals/n750-step1-v3/qualification.json").read_bytes())
    assert len(bindings) == len(plan["selected"]) == 750
    assert all({k: p[k] for k in b} == b for b, p in zip(bindings, plan["selected"], strict=True))
    by_identity = {b["source_identity"]: b for b in bindings}
    reused = {r["source_identity"]: r for r in qualification["remote_reuse"]}
    missing = [b for b in bindings if b["source_identity"] not in reused]
    assert len(reused) == 450 and len(missing) == 300
    authority = authorize(ROOT, "remote_raw_resolution", [b["source_instance_id"] for b in missing])
    authorize(ROOT, "processing", [b["source_instance_id"] for b in bindings])
    OUT.mkdir(parents=True, exist_ok=True)

    # Every historically known RAW prefix is inventoried before interpreting a
    # missing receipt as an absent object. Unknown objects fail closed.
    completions = qualification["remote_evidence_sha256"]
    inventories = {}
    for name, expected in completions.items():
        path = Path(name)
        assert sha(path) == expected, name
        completion = json.loads(path.read_bytes())
        prefix = completion["prefix"]
        assert prefix.startswith(BASE + "/") and prefix != NEW
        actual = json.loads(cli("fs", "ls", prefix))
        known = {r["name"]: r["bytes"] for r in completion["receipts"]}
        assert len(actual) == len(known) and {x["name"]: x["size"] for x in actual} == known
        inventories[prefix] = {"count": len(actual), "completion_sha256": expected}
    assert all(r["source_identity"] in by_identity and
               r["raw_sha256"] == by_identity[r["source_identity"]]["raw_sha256"]
               for r in reused.values())
    save(OUT / "preflight.json", {"status": "PASS", "owner_grant_sha256": authority["owner_grant_sha256"],
         "existing_prefixes": inventories, "historical_located": 450, "new_upload_scope": 300,
         "destination": NEW, "started_at_utc": datetime.now(UTC).isoformat()})

    # Local originals are sealed before staging. All 300 are a single authorized
    # complement; never select by basename or infer identity from an SRC number.
    selected = {p["source_identity"]: p for p in plan["selected"]}
    with tempfile.TemporaryDirectory(prefix="n750-step8-stage-", dir=OUT) as temp:
        staging = Path(temp) / "stage"
        staging.mkdir()
        for binding in missing:
            item = selected[binding["source_identity"]]
            local = Path(item["physical_raw_path"])
            assert local.is_file() and not local.is_symlink()
            assert sha(local) == binding["raw_sha256"]
            staged = staging / (binding["source_instance_id"] + "__" + local.name)
            shutil.copyfile(local, staged)
            assert sha(staged) == binding["raw_sha256"]
        # A newly versioned destination must be absent. Listing failures are not
        # interpreted as absence; inspect the parent inventory instead.
        parent = json.loads(cli("fs", "ls", BASE))
        assert NEW.rsplit("/", 1)[-1] not in {x["name"] for x in parent}
        cli("fs", "mkdir", NEW)
        assert json.loads(cli("fs", "ls", NEW)) == []
        cli("fs", "cp", str(staging), NEW, "--recursive", "--concurrency", "2")
    uploaded = json.loads(cli("fs", "ls", NEW))
    names = {b["source_instance_id"] + "__" + Path(selected[b["source_identity"]]["physical_raw_path"]).name
             for b in missing}
    assert len(uploaded) == 300 and {x["name"] for x in uploaded} == names
    assert all(not x["is_directory"] for x in uploaded)

    locations = {by_identity[identity]["source_instance_id"]: row["remote"]
                 for identity, row in reused.items()}
    locations.update({b["source_instance_id"]: NEW + "/" + b["source_instance_id"] + "__" +
                      Path(selected[b["source_identity"]]["physical_raw_path"]).name for b in missing})
    receipts = OUT / "receipts"
    receipts.mkdir(exist_ok=True)

    def readback(binding):
        sid = binding["source_instance_id"]
        prior = verified_receipt(receipts / (sid + ".json"), binding)
        if prior:
            return prior
        with tempfile.TemporaryDirectory(prefix="n750-readback-") as temp:
            target = Path(temp) / "original"
            cli("fs", "cp", locations[sid], str(target))
            digest = sha(target)
            assert digest == binding["raw_sha256"], sid
            value = {"source_instance_id": sid, "source_identity": binding["source_identity"],
                     "remote": locations[sid], "expected_sha256": binding["raw_sha256"],
                     "actual_sha256": digest, "bytes": target.stat().st_size,
                     "status": "EXACT_REMOTE_BYTES_PASS", "verified_at_utc": datetime.now(UTC).isoformat(),
                     "disposition": "UPLOADED_NEW" if binding in missing else "EXISTING_REUSED"}
            save(receipts / (sid + ".json"), value)
            return value

    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for result in pool.map(readback, bindings):
            results.append(result)
            if len(results) % 50 == 0:
                print(f"remote SHA verified {len(results)}/750", flush=True)
    assert len(results) == 750 and len({r["source_instance_id"] for r in results}) == 750
    save(OUT / "completion.json", {"status": "PASS", "owner_grant_sha256": authority["owner_grant_sha256"],
         "verified_sources": 750, "reused": 450, "uploaded": 300,
         "verified_bytes": sum(r["bytes"] for r in results),
         "uploaded_bytes": sum(r["bytes"] for r in results if r["disposition"] == "UPLOADED_NEW"),
         "elapsed_seconds": round(time.monotonic() - started, 3), "receipts": results})
    print(json.dumps({"status": "PASS", "verified_sources": 750, "uploaded": 300,
                      "elapsed_seconds": round(time.monotonic() - started, 3)}), flush=True)


if __name__ == "__main__":
    main()
