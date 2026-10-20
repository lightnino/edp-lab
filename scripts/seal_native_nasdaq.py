"""Seal completed native results and their reproducible local evidence references."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/databricks-native-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    native = json.loads((OUT / "native-results.json").read_bytes())
    run = json.loads((OUT / "run-v3.json").read_bytes())
    sql = json.loads((OUT / "warehouse-sql-v2.json").read_bytes())
    assert run["state"]["result_state"] == "SUCCESS"
    assert native["status"] == "TESTED"
    assert sql["status"]["state"] == "SUCCEEDED"
    assert sql["result"]["data_array"] == [["5629", "5629", "1", "SRC000002"]]
    assert native["notebook_sha256"] == sha(ROOT / "notebooks/bronze_nasdaq_listed.py")
    assert native["contract_sha256"] == sha(OUT / "contract.json")
    contract = json.loads((OUT / "contract.json").read_bytes())
    assert native["reconstructed_raw_sha256"] == contract["binding"]["raw_sha256"]
    assert all(native["integrity"].values())
    metrics = {
        "native_notebook_attempts": 3, "failed_attempts": 2, "successful_attempts": 1,
        "final_run_duration_ms": run["run_duration"],
        "final_task_execution_duration_ms": run["tasks"][0]["execution_duration"],
        "human_semantic_interventions": 0, "profiling_reruns": 0,
        "resource_usage": {"status": "NOT_COMPUTED",
                           "reason": "Jobs API evidence exposes duration, not CPU/memory usage"},
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    checks = {}
    commands = {
        "pytest": [".venv/bin/python", "-m", "pytest", "-q", "tests/agents",
                   "tests/tool_adapters", "tests/governance",
                   "tests/corpus_invariants/test_gold_v2_registration.py"],
        "ruff": [".venv/bin/ruff", "check", "."],
        "whitespace": ["git", "diff", "--check"],
    }
    for name, command in commands.items():
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        (OUT / f"final-{name}.log").write_text(result.stdout + result.stderr)
        checks[name] = {"command": command, "exit_code": result.returncode}
        assert result.returncode == 0, name
    # git diff ignores new files; validate whitespace on all untracked deliverables too.
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    diagnostics = []
    for rel in filter(None, untracked):
        for number, line in enumerate((ROOT / rel).read_text().splitlines(), 1):
            if line.rstrip() != line:
                diagnostics.append(f"{rel}:{number}: trailing whitespace")
    assert not diagnostics, diagnostics
    checks["untracked_whitespace"] = {"diagnostics": diagnostics}
    (OUT / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    source_paths = [ROOT / "notebooks/bronze_nasdaq_listed.py",
                    ROOT / "scripts/prepare_native_nasdaq.py", Path(__file__).resolve(),
                    ROOT / "docs/native_databricks_execution.md", ROOT / "AGENTS.md"]
    artifacts = {str(p.relative_to(ROOT)): sha(p) for p in sorted(OUT.iterdir())
                 if p.is_file() and p.name != "checkpoint.json"}
    artifacts.update({str(p.relative_to(ROOT)): sha(p) for p in source_paths})
    checkpoint = {
        "version": "NATIVE_NASDAQ_CHECKPOINT_V1", "section_2_7": "COMPLETE",
        "section_2_8": "TESTED", "primary_platform": "Databricks",
        "artifact_sha256": artifacts, "run_id": run["run_id"],
        "run_url": run["run_page_url"], "table": native["table"],
        "source": contract["binding"], "checks": checks,
        "native_integrity": native["integrity"], "runtime": native["runtime"],
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT).decode(),
        "blockers": [], "ready_to_merge": True,
        "failed_attempts": ["failed-attempt-1.json", "failed-attempt-2.json",
                            "warehouse-sql.json"],
        "limitation": "One registered snapshot only; source NULL semantics unresolved. "
                      "No actual source blanks or duplicate groups; separate SQL blank/NULL probe.",
    }
    checkpoint["fingerprint"] = hashlib.sha256(json.dumps(
        checkpoint, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    with (OUT / "checkpoint.json").open("x") as stream:
        stream.write(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    reference = {k: checkpoint[k] for k in ("version", "section_2_7", "section_2_8", "fingerprint")}
    reference.update({"checkpoint_path": str((OUT / "checkpoint.json").relative_to(ROOT)),
                      "checkpoint_sha256": sha(OUT / "checkpoint.json"),
                      "operational_artifacts": "gitignored runs/; do not commit results or RAW"})
    with (ROOT / "metadata/native_nasdaq_checkpoint_v1.json").open("x") as stream:
        stream.write(json.dumps(reference, indent=2, sort_keys=True) + "\n")
    print(json.dumps(reference, indent=2))
    print((OUT / "final-pytest.log").read_text())


if __name__ == "__main__":
    main()
