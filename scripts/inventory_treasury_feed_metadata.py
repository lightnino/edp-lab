"""Read five hash-pinned Treasury RAW feeds only for source-declared metadata."""
from __future__ import annotations

import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "runs/c1500-m2-stability/v1"
ATOM = "{http://www.w3.org/2005/Atom}"


def main() -> None:
    receipts = json.loads((ROOT / "runs/n750/step8-v1/raw/completion.json").read_bytes())
    selected = [r for r in receipts["receipts"] if r["source_instance_id"] in {
        "SRC010451", "SRC010452", "SRC010453", "SRC010454", "SRC010455"}]
    assert len(selected) == 5
    results = []
    for receipt in sorted(selected, key=lambda x: x["source_instance_id"]):
        target = BASE / "source-metadata-raw" / receipt["source_instance_id"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            subprocess.run(["databricks", "fs", "cp", receipt["remote"], str(target),
                            "-p", "edp-lab"], check=True, timeout=300)
        raw = target.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        assert actual == receipt["actual_sha256"] == receipt["expected_sha256"]
        root = ET.fromstring(raw)
        assert root.tag == ATOM + "feed"
        feed = {tag: [x.text for x in root.findall(ATOM + tag)]
                for tag in ("title", "subtitle", "id", "updated", "rights", "category")}
        results.append({"source_instance_id": receipt["source_instance_id"],
                        "raw_sha256": actual, "remote": receipt["remote"],
                        "feed_metadata": feed, "entries": len(root.findall(ATOM + "entry"))})
    path = BASE / "treasury-feed-metadata.json"
    path.write_text(json.dumps({"status": "PASS", "sources": results}, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "sources": results}))


if __name__ == "__main__":
    main()
