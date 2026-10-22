"""Permanent positive and adversarial Lossless 6 suite controls without live CI SQL."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("lossless6_gate", ROOT / "scripts/validate_lossless6_suite_v3.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)
import run_treasury_lossless6_v1 as treasury


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def test_registration_and_budget_are_pinned():
    suite = gate.read(gate.SUITE)
    gate.check_registration(suite)
    assert suite["mandatory_controls"] == list(gate.CONTROLS)
    budget = gate.read(ROOT / suite["c3_4_budget_ref"])
    assert budget["status"] == "PROPOSED_PENDING_APPLICABILITY_APPROVAL"
    assert budget["day4_c3_4"] == "BLOCKED"
    for row in budget["phases"].values():
        assert round(row["observed_seconds"] * 10, 3) == row["prospective_max_seconds"]
    measurement = {"phases": {k: v["observed_seconds"] for k, v in budget["phases"].items()},
                   "method": budget["measurement_method"],
                   "run_started_at": "2026-11-01", "workload_applicability_approval": "scope-1"}
    assert gate.check_prospective_budget(measurement, budget)["status"] == "BLOCKED"
    future = copy.deepcopy(budget)
    future.update(status="APPROVED", approved_effective_date="2026-10-31",
                  approved_scope_id="scope-1")
    assert gate.check_prospective_budget(measurement, future)["status"] == "PASS"
    measurement["run_started_at"] = "2026-10-30"
    assert gate.check_prospective_budget(measurement, future)["status"] == "BLOCKED"


def test_try_negative_controls():
    fixture = treasury.read(treasury.FIXTURE)
    rows1 = []
    for row in fixture["sources"]:
        rows1.append(["TRY_001_V1", row["source_instance_id"],
                      *[str(x) for x in (row["entries"], row["entries"],
                        len(row["qnames"]), len(row["qnames"]), row["evaluations"],
                        row["evaluations"], row["valid"], row["valid"], row["missing"],
                        row["missing"], 0, 0)]])
    assert treasury.evaluate("TRY_001", rows1, fixture)["status"] == "PASS"
    for index in (3, 5, 7, 9, 11, 12, 13):
        changed = copy.deepcopy(rows1)
        changed[0][index] = str(int(changed[0][index]) + 1)
        assert treasury.evaluate("TRY_001", changed, fixture)["status"] == "FAIL"
    numeric = [["TRY_002_V1", "12793", "12793", "0", "0", "0", "0", "0"]]
    assert treasury.evaluate("TRY_002", numeric, fixture)["status"] == "PASS"
    for index in range(3, 8):  # fan-out, outcome, precision/value, locator, version
        changed = copy.deepcopy(numeric)
        changed[0][index] = "1"
        assert treasury.evaluate("TRY_002", changed, fixture)["status"] == "FAIL"
    missing = [["TRY_003_V1", "12948", "12948", "12793", "12793", "155",
                "155", "0", "0", "0", "0", "249", "0"]]
    assert treasury.evaluate("TRY_003", missing, fixture)["status"] == "PASS"
    for index in (5, 7, 8, 9, 10, 11, 12):
        changed = copy.deepcopy(missing)
        changed[0][index] = str(int(changed[0][index]) + 1)
        assert treasury.evaluate("TRY_003", changed, fixture)["status"] == "FAIL"
    isolation = [["TRY_004_V1", "34564", "0", "0", "12793", "5"]]
    assert treasury.evaluate("TRY_004", isolation, fixture)["status"] == "PASS"
    for index in range(1, 6):
        changed = copy.deepcopy(isolation)
        changed[0][index] = str(int(changed[0][index]) + 1)
        assert treasury.evaluate("TRY_004", changed, fixture)["status"] == "FAIL"


def build_packet(tmp_path: Path, monkeypatch):
    fixture = treasury.read(treasury.FIXTURE)
    roster = [{"source_instance_id": "SRC000001", "raw_sha256": "a" * 64,
               "source_identity": "native", "raw_path": "data/raw/old.dat"}]
    write(tmp_path / "roster.json", roster)
    suite = {"retained_roster_ref": "roster.json", "retained_scope_sha256": "roster-pin",
             "model_pins": {"m1": "M1", "m2": "M2"}, "historical_output_pins": {"old": 0},
             "registered_sha256": {"sql/stability/c1500_m2_v1/combined_candidate.sql": "sql-pin"},
             "approved_reused_receipts": {}, "approved_combined_response_sha256": ""}
    packet = {"sources": roster, "model_pins": suite["model_pins"],
              "historical_output_pins": suite["historical_output_pins"],
              "registered_sha256": suite["registered_sha256"],
              "new_source_classifications": {}, "control_results": {},
              "claims_economic_integration": False, "source_preserving_status": "PASS"}
    for control in gate.CONTROLS:
        name = control.removesuffix("_V1")
        if name == "TRY_001":
            rows = [[control, s["source_instance_id"], *map(str, (s["entries"], s["entries"],
                len(s["qnames"]), len(s["qnames"]), s["evaluations"], s["evaluations"],
                s["valid"], s["valid"], s["missing"], s["missing"], 0, 0))]
                for s in fixture["sources"]]
        elif name == "TRY_002":
            rows = [[control, "12793", "12793", "0", "0", "0", "0", "0"]]
        elif name == "TRY_003":
            rows = [[control, "12948", "12948", "12793", "12793", "155", "155",
                     "0", "0", "0", "0", "249", "0"]]
        elif name == "TRY_004":
            rows = [[control, "34564", "0", "0", "12793", "5"]]
        else:
            rows = [["fixed FIN fixture"]]
        ref = f"receipts/{control}.json"
        write(tmp_path / ref, {"status": {"state": "SUCCEEDED"}, "statement_id": control,
                               "result": {"data_array": rows}})
        result = {"status": "PASS", "evidence_mode": "REUSED", "response_ref": ref,
                  "response_sha256": digest(tmp_path / ref), "statement_id": control,
                  "reuse_scope_sha256": "roster-pin"}
        if name.startswith("TRY_"):
            request_ref = f"receipts/{control}-request.json"
            write(tmp_path / request_ref, {"statement": treasury.render(name, fixture)})
            result.update(request_ref=request_ref,
                          request_sha256=digest(tmp_path / request_ref))
        packet["control_results"][control] = result
        suite["approved_reused_receipts"][control] = result["response_sha256"]
    combined_ref = "receipts/combined.json"
    write(tmp_path / combined_ref, {"status": {"state": "SUCCEEDED"},
             "statement_id": "combined", "result": {"data_array": [
                 [scope, direction, "0"] for scope in ("old", "new", "xml", "m2")
                 for direction in ("candidate_minus_pinned", "pinned_minus_candidate")]}})
    suite["approved_combined_response_sha256"] = digest(tmp_path / combined_ref)
    packet["combined_candidate"] = {"status": "PASS", "evidence_mode": "REUSED",
        "full_schema_differences": 0, "fin_noninterference": "PASS", "sql_sha256": "sql-pin",
        "response_ref": combined_ref, "response_sha256": digest(tmp_path / combined_ref)}
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    return packet, suite


def test_cumulative_gate_positive_and_negative(tmp_path, monkeypatch):
    packet, suite = build_packet(tmp_path, monkeypatch)
    assert gate.check_packet(packet, suite)["status"] == "PASS"
    mutations = []
    x = copy.deepcopy(packet); x["control_results"].pop("TRY_003_V1"); mutations.append(x)
    x = copy.deepcopy(packet); x["sources"][0]["raw_sha256"] = "b" * 64; mutations.append(x)
    x = copy.deepcopy(packet); x["model_pins"]["m2"] = "M2_CHANGED"; mutations.append(x)
    x = copy.deepcopy(packet); x["registered_sha256"]["sql/stability/c1500_m2_v1/combined_candidate.sql"] = "changed"; mutations.append(x)
    x = copy.deepcopy(packet); x["control_results"]["TRY_002_V1"]["response_sha256"] = "forged"; mutations.append(x)
    x = copy.deepcopy(packet); x["claims_economic_integration"] = True; mutations.append(x)
    x = copy.deepcopy(packet); x["sources"].append({"source_instance_id": "SRCNEW", "raw_sha256": "c" * 64,
        "source_identity": "new", "raw_path": "data/raw/treasury/new.xml"}); mutations.append(x)
    for changed in mutations:
        assert gate.check_packet(changed, suite)["status"] == "BLOCKED"
    expanded = copy.deepcopy(packet)
    expanded["sources"].append({"source_instance_id": "SRCNEW", "raw_sha256": "c" * 64,
        "source_identity": "new", "raw_path": "data/raw/treasury/new.xml"})
    expanded["new_source_classifications"] = {"SRCNEW": {"source_kind": "TREASURY_XML",
        "classification_evidence_sha256": "d" * 64, "independent_fixture_ref": "new-fixture.json"}}
    assert "new_treasury_controls_missing_or_extra" in gate.check_packet(expanded, suite)["errors"]
    expanded["new_treasury_controls"] = {"SRCNEW": {"TRY_001_V1": "PASS"}}
    assert "expanded_candidate_requires_fresh_execution" in gate.check_packet(expanded, suite)["errors"]
