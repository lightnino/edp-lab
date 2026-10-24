"""Rebaseline the retained FSDS NUM sample on the accepted C2000 freeze.

This is a local, read-only input preparation step. It grants no Vault authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from edp_lab.vault.load_plan import render_v2
from edp_lab.vault.protected_readback import _expected
from edp_lab.vault.prototype import project, validate_batch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/day6-vault-c2000-v1"
OLD = ROOT / "runs/day6-vault-prototype"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name: str, value: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return path


def main() -> None:
    cohort_dir = ROOT / "metadata/freezes/C2000_v1"
    cohort = json.loads((cohort_dir / "freeze.json").read_bytes())
    assert cohort["cohort"] == "C2000" and cohort["status"] == "FROZEN_INPUT_NOT_RESULT"
    for name, expected_sha in cohort["files_sha256"].items():
        assert digest(cohort_dir / name) == expected_sha
    result_path = ROOT / "metadata/freezes/O_C2000_M2_v1/databricks_result_freeze_v1.json"
    result = json.loads(result_path.read_bytes())
    assert result["status"] == "FROZEN_IN_DATABRICKS_SOURCE_PRESERVING"
    assert result["input_freeze_sha256"] == digest(cohort_dir / "freeze.json")
    assert result["accepted_tasks"] == result["expected_tasks"] == 513
    if (OLD / "sample-manifest.json").exists():
        old_sample = json.loads((OLD / "sample-manifest.json").read_bytes())
        old_projection = json.loads((OLD / "projected-manifest.json").read_bytes())
    else:
        # The original read-only packet is ignored locally. Tracked, pinned
        # copies keep later CI and review reproducible without requerying data.
        retained = json.loads((OUT / "input_manifest.json").read_bytes())
        old_sample = {"rows": retained["rows"],
                      "rows_sha256": retained["historical_rows_sha256"],
                      "warehouse_statement_id": retained["historical_read_statement_id"]}
        old_projection = json.loads((OUT / "projected_manifest.json").read_bytes())
    roster = {item["source_instance_id"]: item for item in
              json.loads((cohort_dir / "C2000.bindings.json").read_bytes())}
    rows = old_sample["rows"]
    encoded = json.dumps(rows, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode()
    assert hashlib.sha256(encoded).hexdigest() == old_sample["rows_sha256"]
    ids = sorted({row["source_instance_id"] for row in rows})
    assert ids == ["SRC000005", "SRC000054", "SRC000064"] and len(rows) == 127
    for row in rows:
        source = roster[row["source_instance_id"]]
        assert row["raw_path"] == source["raw_path"]
        assert row["raw_sha256"] == source["raw_sha256"]
        assert row["archive_member"] == "num.txt"
    projected = [project(row, old_projection["approved_bindings"]) for row in rows]
    validate_batch(projected)
    assert projected == old_projection["rows"]
    input_path = save("input_manifest.json", {
        "schema": "DAY6_C2000_VAULT_INPUT_MANIFEST_V1",
        "cohort_id": "C2000", "source_ids": ids,
        "cohort_freeze_sha256": digest(cohort_dir / "freeze.json"),
        "result_freeze_sha256": digest(result_path),
        "historical_read_statement_id": old_sample["warehouse_statement_id"],
        "historical_rows_sha256": old_sample["rows_sha256"],
        "data_occurrences": len(rows), "rows": rows,
    })
    projected_path = save("projected_manifest.json", {
        "schema": "DAY6_C2000_VAULT_PROJECTED_MANIFEST_V1",
        "cohort_id": "C2000", "input_manifest_sha256": digest(input_path),
        "approved_bindings": old_projection["approved_bindings"], "rows": projected,
    })
    expected = _expected(projected, include_events=False,
                         include_negatives=True,
                         negative_execution_id="vault-negative-C2000")
    counts = {name: len(values) for name, values in expected.items()}
    plan = render_v2(projected, cohort_id="C2000",
                     input_manifest_sha256=digest(input_path),
                     expected_table_counts=counts, synthetic_negatives=True)
    plan_path = save("load_plan.json", plan)
    print(json.dumps({"cohort": "C2000", "source_ids": ids,
                      "data_occurrences": len(rows), "synthetic_rows": plan["synthetic_rows"],
                      "stages": len(plan["stages"]), "expected_table_counts": counts,
                      "input_manifest_sha256": digest(input_path),
                      "projected_manifest_sha256": digest(projected_path),
                      "load_plan_sha256": digest(plan_path)}, sort_keys=True))


if __name__ == "__main__":
    main()
