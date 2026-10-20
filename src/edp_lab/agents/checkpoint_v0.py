"""Explicit offline host execution and independent evaluation for Study Notes §2.6."""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from edp_lab.agents.analyst_v0 import observe, validate_report
from edp_lab.ingestion.gold_set import file_sha256
from edp_lab.parsers.c300_v1 import (
    VERSION,
    require_activation,
    roster,
    run_directory,
    save_new,
    verify_binding,
)
from edp_lab.profiling import tools
from edp_lab.profiling.source_reader import (
    FREEZE,
    canonical_hash,
    execution_provenance,
    read_registered,
)
from edp_lab.tool_adapters import ProfilingAdapters


def evaluate(host, report, table):
    """Dispatch underlying tools independently of the agent plan/adapter dispatch.

    Complete dictionary equality checks statistics, witnesses, provenance and hashes.
    Replay also verifies the complete tool response, including authority and errors.
    """
    validate_report(report)
    evaluations = []
    for step in report["trace"]:
        request, response = step["request"], step["response"]
        expected = getattr(tools, request["tool"])(table, **request["parameters"])
        replay = host.invoke(request).to_dict()
        evaluations.append({"sequence": step["sequence"], "tool": request["tool"],
                            "independent_result_equal": expected == response["result"],
                            "response_replay_equal": canonical_hash(replay) ==
                            canonical_hash(response),
                            "expected_result_sha256": expected["result_sha256"]})
    return {"status": "PASS" if all(e["independent_result_equal"] and
            e["response_replay_equal"] for e in evaluations) else "FAILED",
            "checks": evaluations}


def run_gold(root: Path, output: Path):
    output = run_directory(root, output)
    provenance = execution_provenance(root)
    freeze = json.loads((root / FREEZE).read_bytes())
    results = []
    for binding in freeze["effective_configuration"]["tables"]:
        name = f"{binding['source_instance_id']}/{binding['logical_table_name']}"
        table = read_registered(root, binding["source_instance_id"], binding["logical_table_name"],
                                provenance=provenance)
        host = ProfilingAdapters({name: table}, {"local_user": {name}})
        report = observe(host, name, "local_user", table.columns)
        evaluation = evaluate(host, report, table)
        replay = observe(host, name, "local_user", table.columns)
        evaluation["agent_replay_equal"] = report == replay
        filename = name.replace("/", "_") + ".json"
        save_new(output / filename, {"report": report, "evaluation": evaluation})
        result = {"binding": name, "execution": report["execution_status"],
                  "evaluation": evaluation["status"], "agent_replay_equal": report == replay,
                  "rows": len(table.rows), "column_profiles": len(table.columns),
                  "tool_statuses": report["tool_statuses"], "evidence": filename,
                  "evidence_sha256": file_sha256(output / filename),
                  "report_fingerprint": report["result_fingerprint"]}
        results.append(result)
        print(json.dumps(result), flush=True)
    save_new(output / "checkpoint.json", {"version": "SECTION_2_6_GOLD_CHECKPOINT_V1",
             "provenance": provenance, "tables": results,
             "freeze_sha256": file_sha256(root / FREEZE),
             "fingerprint": canonical_hash(results)})
    return results


def validate_c300(root: Path, registry_path: Path, output: Path):
    output = run_directory(root, output)
    registry = json.loads(registry_path.read_bytes())
    if registry["version"] != VERSION or registry["parser_code_sha256"] != file_sha256(
            root / "src/edp_lab/parsers/c300_v1.py"):
        raise ValueError("PARSER_VERSION_OR_CODE_MISMATCH")
    manifest = {r["source_instance_id"]: r for r in roster(root)}
    tables = []
    for binding in registry["bindings"]:
        result = {"source_instance_id": binding["source_instance_id"],
                  "logical_table_name": binding["logical_table_name"], "source": binding,
                  "activation": "BLOCKED", "agent_execution": "BLOCKED",
                  "reason": "SCOPED_HUMAN_PARSER_APPROVAL_REQUIRED"}
        try:
            row = manifest[binding["source_instance_id"]]
            if any(row[k] != binding[k] for k in ("raw_path", "raw_sha256", "source_family")):
                raise ValueError("FROZEN_SOURCE_BINDING_MISMATCH")
            validation = verify_binding(root, binding)
            result.update(validation=validation["validation"], inspection=validation)
        except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError) as exc:
            result.update(validation="FAILED", errors=[str(exc)])
        tables.append(result)
        print(f"{result['source_instance_id']} {result['logical_table_name']} "
              f"{result['validation']} activation BLOCKED", flush=True)
    instances = []
    for sid, row in manifest.items():
        covered = [t for t in tables if t["source_instance_id"] == sid]
        instances.append({"source_instance_id": sid, "family": row["source_family"],
                          "logical_tables": len(covered), "activation": "BLOCKED",
                          "validation": "BLOCKED" if not covered else "PASS" if all(
                              t["validation"] == "PASS" for t in covered) else "FAILED"})
    packet = {"version": "C300_LEXICAL_APPROVAL_PACKET_V1",
              "registry_path": str(registry_path.relative_to(root)),
              "registry_sha256": file_sha256(registry_path),
              "registry_fingerprint": canonical_hash(registry),
              "parser_code_sha256": registry["parser_code_sha256"],
              "inventory_sha256": registry["inventory_sha256"],
              "requested_decision": "Approve exact C300 lexical parser bindings only?",
              "rules": {"encoding": "strict UTF-8", "quoting": "literal",
                        "escaping": "literal", "types": "ALL_TEXT", "null_semantics": "UNKNOWN",
                        "daily": "five exact bound metadata records, header, 80-hyphen separator",
                        "streaming": "8 MiB physical-record cap; explicit failure; no truncation"},
              "alternatives": ["Approve PASS bindings only", "Withhold activation pending review"],
              "consequences": "Approval permits shallow mechanical inspection only; no semantic facts",
              "instances": instances, "tables": tables,
              "activation": "INACTIVE_PENDING_HUMAN_APPROVAL"}
    save_new(output / "validation-and-approval.json", packet)
    try:
        require_activation(registry)
    except PermissionError:
        pass
    else:
        raise AssertionError("Activation unexpectedly authorized")
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["gold", "c300"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--registry", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.mode == "gold":
        run_gold(root, args.output)
    else:
        validate_c300(root, args.registry.resolve(), args.output)


if __name__ == "__main__":
    main()
