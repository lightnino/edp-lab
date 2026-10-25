"""Pin reusable historical source and locator evidence without asserting U10."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from edp_lab.operating.authority import canonical, file_digest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "metadata/source_universes/approved/source_evidence_index_v1.json"
MANIFEST = ROOT / "metadata/source_universes/approved/manifest.json"
UNIVERSE_SHA = "dcc63767c88ae712eab8f5ba29d52a206b4262710740e591a4b233d9c04c699b"
DECISION_SHA = "416efc5f7ab18b2570ba9beab26bba33210c5e0a75ec813a92ccac953af36d74"
PARENT = "/Users/lightnino/Projects/edp-lab/runs/whole_lab/layout-v2/whole_lab_inventory_v2.csv"
RECEIPT_DIRS = {
    "N450": "/Users/lightnino/Projects/edp-lab-day3/runs/n450/upload-v1/receipts",
    "N750": "/Users/lightnino/Projects/edp-lab-day4/runs/n750/upload-v1/receipts",
    "N500": "/Users/lightnino/Projects/edp-lab-day5/runs/n500/upload-v1/receipts",
}


def prepare() -> dict:
    if file_digest(MANIFEST) != UNIVERSE_SHA:
        raise ValueError("Active Universe digest changed")
    manifest = json.loads(MANIFEST.read_bytes())
    c2000 = json.loads((ROOT / "metadata/freezes/C2000_v1/C2000.bindings.json").read_bytes())
    prior_ids = {row["source_identity"] for row in c2000}
    eligible = [row for row in manifest["members"]
                if not row["holdout"] and row["identity"] not in prior_ids]
    originals = [row for row in eligible if "remote_raw_path" not in row]
    if len(eligible) != 1780 or len(originals) != 980:
        raise ValueError("Unexpected Day 7 source population")
    inventory_path = Path(PARENT)
    if file_digest(inventory_path) != manifest["inventory_sha256"]:
        raise ValueError("Pinned original inventory changed")
    with inventory_path.open(newline="") as stream:
        inventory = {row["inventory_id"]: row for row in csv.DictReader(stream)}
    original_rows = []
    for member in originals:
        row = inventory.get(member["identity"])
        if (row is None or row["final_path"] != member["raw_path"]
                or row["sha256"] != member["raw_sha256"]):
            raise ValueError("Original identity not bound by pinned inventory")
        byte_count = int(row["bytes"])
        if Path(member["raw_path"]).stat().st_size != byte_count:
            raise ValueError("Original local bytes changed")
        receipt = Path(row["evidence"])
        receipt_doc = json.loads(receipt.read_bytes())
        datasets = receipt_doc.get("datasets", [])
        dataset = next((item for item in datasets
                        if item.get("dataset_id") == member["identity"]), None)
        representations = [] if dataset is None else [item for item in dataset.get("representations", [])
                                                       if item.get("path") == member["raw_path"]]
        representation = representations[0] if len(representations) == 1 else {}
        aggregate_ok = (receipt_doc.get("status") == "COMPLETE"
                        and receipt_doc.get("sha256") == member["raw_sha256"]
                        and receipt_doc.get("bytes") == byte_count)
        inventory_ok = (dataset is not None
                        and dataset.get("status") in {"EXISTING_GOLD_ADMISSION_UNCHANGED",
                                                       "EXISTING_UNADMITTED_CANDIDATE"}
                        and representation.get("availability") == "VERIFIED"
                        and representation.get("sha256") == member["raw_sha256"]
                        and representation.get("bytes") == byte_count)
        if not (aggregate_ok or inventory_ok):
            raise ValueError("Original acquisition receipt mismatch")
        original_rows.append({
            "physical_identity": member["identity"],
            "source_instance_id": row["source_instance_id"] or None,
            "publisher": row["publisher"], "family": row["family"],
            "raw_path": member["raw_path"],
            "raw_sha256": member["raw_sha256"],
            "raw_bytes": byte_count,
            "source_inventory_receipt_path": str(receipt),
            "source_inventory_receipt_sha256": file_digest(receipt),
            "delivery_identity_source": "inventory_source_instance_id" if row["source_instance_id"] else "physical_identity_fallback",
            "remote_locator_status": "UNRESOLVED_PENDING_PROTECTED_DISCOVERY",
        })

    remote_receipts = []
    for cohort, directory in RECEIPT_DIRS.items():
        base = Path(directory)
        for path in sorted(base.glob("*.json")):
            receipt = json.loads(path.read_bytes())
            if receipt.get("status") != "REMOTE_READBACK_SHA256_PASS":
                raise ValueError(f"Unverified historical receipt: {path}")
            remote_receipts.append({
                "cohort": cohort,
                "source_instance_id": receipt["source_instance_id"],
                "sha256": receipt["sha256"], "bytes": receipt["bytes"],
                "remote_path": receipt["remote"],
                "receipt_path": str(path),
                "receipt_sha256": file_digest(path),
            })
    if len(remote_receipts) != 1700:
        raise ValueError("Historical remote receipt index coverage changed")
    publisher_counts = Counter(row["publisher"] for row in original_rows)
    if publisher_counts != {"SEC": 977, "NASDAQ": 3}:
        raise ValueError(f"Original publisher inventory changed: {publisher_counts}")
    receipts_by_identity = {(row["source_instance_id"], row["sha256"], row["bytes"])
                            for row in remote_receipts}
    exact_receipt_matches = sum(
        1 for row in original_rows
        if ((row["source_instance_id"] or row["physical_identity"],
             row["raw_sha256"], row["raw_bytes"]) in receipts_by_identity))

    identity_doc = Path("/Users/lightnino/Projects/edp-lab/docs/source_instance_identity.md")
    native_doc = Path("/Users/lightnino/Projects/edp-lab-incident/docs/native_databricks_execution.md")
    nasdaq = next(row for row in original_rows
                  if row["physical_identity"] == "SRC000002")
    if ("SRC000002" not in identity_doc.read_text()
            or "edp-native-v1/nasdaqlisted.txt" not in native_doc.read_text()):
        raise ValueError("Historical SRC000002 locator provenance changed")
    locator_evidence = [{
        "physical_identity": "SRC000002",
        "source_instance_id": "SRC000002",
        "sha256": nasdaq["raw_sha256"], "bytes": nasdaq["raw_bytes"],
        "remote_path": "dbfs:/Volumes/workspace/edp_lab/raw/edp-native-v1/nasdaqlisted.txt",
        "locator_reference_paths": [str(identity_doc), str(native_doc)],
        "locator_reference_sha256": [file_digest(identity_doc), file_digest(native_doc)],
        "status": "LOCATOR_FOUND_REQUIRES_PROTECTED_U10_READBACK",
    }]
    document = {
        "schema": "EDP_DAY7_SOURCE_EVIDENCE_INDEX_V1",
        "status": "PINNED_DISCOVERY_INPUTS_NOT_U10_VERIFIED",
        "universe_sha256": UNIVERSE_SHA, "owner_decision_sha256": DECISION_SHA,
        "prior_cohort": "C2000", "prior_bindings_sha256": file_digest(
            ROOT / "metadata/freezes/C2000_v1/C2000.bindings.json"),
        "eligible_count": 1780, "original_universe_eligible_count": 980,
        "original_inventory_path": str(inventory_path),
        "original_inventory_sha256": file_digest(inventory_path),
        "original_sources": original_rows,
        "historical_remote_receipts": remote_receipts,
        "historical_locator_roots": [{
            "path": "dbfs:/Volumes/workspace/edp_lab/raw",
            "lookup": "bounded_metadata_walk_exact_identity_or_basename_then_full_readback",
            "max_depth": 5, "max_entries": 10000,
            "provenance_path": "/Users/lightnino/Projects/edp-lab/runs/c300-m1/final-freeze-review-v1/raw-hash-verification.json",
            "provenance_sha256": file_digest(Path(
                "/Users/lightnino/Projects/edp-lab/runs/c300-m1/final-freeze-review-v1/raw-hash-verification.json")),
        }],
        "known_original_locators": locator_evidence,
        "source_receipt_match_count_by_identity_sha_and_bytes": exact_receipt_matches,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(canonical(document))
    return {"path": str(OUTPUT), "sha256": file_digest(OUTPUT),
            "original_sources": len(original_rows),
            "historical_remote_receipts": len(remote_receipts),
            "known_original_locators": len(locator_evidence)}


if __name__ == "__main__":
    print(json.dumps(prepare(), sort_keys=True))
