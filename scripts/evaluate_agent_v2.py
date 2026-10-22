"""Reproduce the fixed bounded candidate evaluation without modifying artifacts."""
import hashlib
import json
import subprocess
from pathlib import Path

from edp_lab.agents.candidates_v2 import VERSION, propose, score, validate_candidate
from edp_lab.profiling.source_reader import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "metadata/evaluations/agent_v2"
TRUTH_COMMIT = "31fd869c697e3afd6611838794513a3fcf64e927"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    for name in ("inputs_v1.json", "ground_truth_v1.json"):
        relative = f"metadata/evaluations/agent_v2/{name}"
        original = subprocess.check_output(
            ["git", "show", f"{TRUTH_COMMIT}:{relative}"], cwd=ROOT
        )
        assert original == (BASE / name).read_bytes(), "Fixed evidence changed"
    inputs = json.loads((BASE / "inputs_v1.json").read_text())
    truth_bytes = (BASE / "ground_truth_v1.json").read_bytes()
    truth = json.loads(truth_bytes)
    assert digest((BASE / "inputs_v1.json").read_bytes()) == truth["inputs_sha256"]
    reports = [propose(case, inputs["witnesses"]) for case in inputs["cases"]]
    assert all(validate_candidate(report) for report in reports)
    results = {
        "agent_version": VERSION,
        "ground_truth_commit": TRUTH_COMMIT,
        "ground_truth_sha256": digest(truth_bytes),
        "inputs_sha256": truth["inputs_sha256"],
        "agent_code_sha256": digest(
            (ROOT / "src/edp_lab/agents/candidates_v2.py").read_bytes()
        ),
        "proposals": reports,
        "side_effects": [],
        "semantic_promotions": [],
    }
    results["result_fingerprint"] = canonical_hash(results)
    assert results == json.loads((BASE / "proposals_v1.json").read_text())
    evaluation = json.loads((BASE / "evaluation_v1.json").read_text())
    assert digest((BASE / "proposals_v1.json").read_bytes()) == evaluation["proposals_sha256"]
    assert score(reports, truth["cases"]) == evaluation["metrics"]
    print(json.dumps({"status": "REPRODUCED", "cases": len(reports),
                      "fingerprint": results["result_fingerprint"]}, sort_keys=True))


if __name__ == "__main__":
    main()
