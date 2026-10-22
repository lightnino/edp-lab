"""Read-only current identity/version/count check of Step 8 Delta and views."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from publish_n750_step8 import OUT, PUB, TABLES, VIEWS, count, rows, save, sql

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    report = json.loads((PUB / "delta-readback.json").read_bytes())
    queryable = json.loads((PUB / "queryable.json").read_bytes())
    validation = json.loads((OUT / "validation.json").read_bytes())
    assert report["status"] == queryable["status"] == "PASS"
    assert validation["status"] == "STEP8_COMPLETE_WITH_ECONOMIC_BOUNDARY"
    found = {}
    for key, name in TABLES.items():
        detail_response = sql("live-detail-" + key, f"DESCRIBE DETAIL {name}")
        columns = [c["name"] for c in detail_response["manifest"]["schema"]["columns"]]
        detail = dict(zip(columns, rows(detail_response)[0], strict=True))
        history = rows(sql("live-history-" + key, f"DESCRIBE HISTORY {name} LIMIT 1"))
        latest = int(history[0][0])
        observed = count("live-count-" + key, f"SELECT COUNT(*) FROM {name} VERSION AS OF 0")
        pinned = validation["output_tables"][key]
        assert detail["id"] == pinned["delta_id"] and latest == pinned["delta_version"] == 0
        assert observed == pinned["row_count"]
        found[key] = {"table": name, "delta_id": detail["id"], "latest_version": latest,
                      "read_version": 0, "rows": observed}
    view_definitions = {}
    for key, name in VIEWS.items():
        definition = rows(sql("live-view-definition-" + key, f"SHOW CREATE TABLE {name}"))[0][0]
        assert TABLES[key].lower() in definition.lower() and "VERSION AS OF 0" in definition.upper()
        observed = count("live-view-count-" + key, f"SELECT COUNT(*) FROM {name}")
        assert observed == queryable["counts"][key]
        view_definitions[key] = {"view": name, "definition_sha256": hashlib.sha256(
            definition.encode()).hexdigest(), "rows": observed}
    evidence = {"status": "PASS", "checked_at_utc": datetime.now(UTC).isoformat(),
                "tables": found, "views": view_definitions,
                "input_evidence_sha256": {
                    "validation": sha(OUT / "validation.json"),
                    "delta_readback": sha(PUB / "delta-readback.json"),
                    "queryable": sha(PUB / "queryable.json"),
                    "raw_completion": sha(OUT / "raw/completion.json"),
                    "clean_completion": sha(OUT / "clean/completion.json"),
                }}
    save(OUT / "live-verify-v1.json", evidence)
    print(json.dumps({"status": "PASS", "tables": found, "views": view_definitions}))


if __name__ == "__main__":
    main()
