"""Verify retained evidence and prepare the bounded native execution contract (offline)."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/databricks-native-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open("x") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    verified = {}
    for version in (1, 2):
        ref_path = ROOT / f"metadata/section_2_6_checkpoint_v{version}.json"
        ref = json.loads(ref_path.read_bytes())
        checkpoint = ROOT / ref["checkpoint_path"]
        assert sha(checkpoint) == ref["checkpoint_sha256"]
        verified[str(ref_path.relative_to(ROOT))] = sha(ref_path)
        verified[ref["checkpoint_path"]] = sha(checkpoint)
        for rel, expected in json.loads(checkpoint.read_bytes())["artifact_sha256"].items():
            assert sha(ROOT / rel) == expected, rel
            verified[rel] = expected
    gold = ROOT / "runs/section-2-6/gold-v4/checkpoint.json"
    selected = []
    for table in json.loads(gold.read_bytes())["tables"]:
        path = gold.parent / table["evidence"]
        assert sha(path) == table["evidence_sha256"]
        evidence = json.loads(path.read_bytes())
        report = evidence["report"]
        assert evidence["evaluation"]["status"] == report["execution_status"] == "PASS"
        assert evidence["evaluation"]["agent_replay_equal"]
        assert report["trace"] and "errors" in report and report["result_fingerprint"]
        assert report["semantic_promotions"] == []
        for trace in report["trace"]:
            refs = trace["response"]["evidence_refs"]
            assert refs["source"] and refs["config"] and refs["provenance"]
        selected.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path),
                         "binding": report["binding"],
                         "result_fingerprint": report["result_fingerprint"]})
    save("evidence-closeout.json", {"section_2_7": "COMPLETE", "profiling_rerun": False,
                                    "verified_artifacts": verified, "observations": selected})
    registry = list(csv.DictReader((ROOT / "metadata/gold_set_logical_tables_v2.csv").open()))
    binding = next(r for r in registry if r["source_instance_id"] == "SRC000002")
    assert binding["logical_table_name"] == "nasdaqlisted.txt"
    raw = ROOT / binding["raw_path"]
    assert sha(raw) == binding["raw_sha256"]
    evidence = json.loads((gold.parent / "SRC000002_nasdaqlisted.txt.json").read_bytes())
    trace = evidence["report"]["trace"]
    config = trace[0]["response"]["evidence_refs"]["config"]
    assert sha(ROOT / config["freeze_ref"]) == config["freeze_sha256"]
    save("contract.json", {"binding": binding, "config": config,
                            "expected_rows": trace[0]["response"]["result"]["row_count"]["value"],
                            "expected_duplicate_groups": 0,
                            "gold_evidence_sha256": sha(gold.parent / "SRC000002_nasdaqlisted.txt.json"),
                            "raw_size": raw.stat().st_size})
    print(f"2.7 COMPLETE: {len(selected)} observations; {len(verified)} sealed artifacts verified")
    print(f"RAW SHA-256 verified: {sha(raw)}")


if __name__ == "__main__":
    main()
