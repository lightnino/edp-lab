"""Bounded Day 4 write-task and freeze-gate integrity checks."""

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def rows(path: str) -> list[dict]:
    with (ROOT / path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def test_cohort_copy_is_exact_and_nested() -> None:
    frozen = ROOT / "metadata/freezes/C1500_v1/C1500.csv"
    assert (ROOT / "metadata/cohorts/C1500.csv").read_bytes() == frozen.read_bytes()
    c300 = {x["source_instance_id"] for x in rows("metadata/cohorts/C300.csv")}
    c750 = {x["source_instance_id"] for x in rows("metadata/freezes/C1500_v1/C750.original.csv")}
    c1500 = {x["source_instance_id"] for x in rows("metadata/cohorts/C1500.csv")}
    assert (len(c300), len(c750), len(c1500)) == (300, 750, 1500)
    assert c300 < c750 < c1500


def test_candidate_artifacts_keep_approval_boundary() -> None:
    sttm = rows("metadata/sttm.csv")
    crosswalk = rows("metadata/entity_crosswalk.csv")
    controlled = rows("metadata/ground_truth/controlled_variants.csv")
    assert len(sttm) == 61  # 11 benchmark cases + 50 source/QName dispositions
    assert len(crosswalk) == 12
    assert len(controlled) == 23
    assert all(x["human_approval"] != "APPROVED" for x in sttm + crosswalk)
    assert all(x["promotion_eligible"] == "False" for x in crosswalk)
    assert sum(x["human_approval"] == "PENDING_FIELD_LEVEL_L3" for x in sttm) == 50
    truth = ROOT / "metadata/evaluations/agent_v2/ground_truth_v1.json"
    truth_sha = hashlib.sha256(truth.read_bytes()).hexdigest()
    assert {x["truth_sha256"] for x in controlled} == {truth_sha}
    assert {x["case_id"] for x in controlled} == {
        x["id"] for x in json.loads(truth.read_text())["cases"]
    }


def test_freeze_assessment_cannot_claim_frozen() -> None:
    packet = read_json("metadata/evaluations/o_c1500_m2_freeze_assessment_v1.json")
    assert packet["status"] == "CANDIDATE"
    assert packet["result_frozen"] is False
    assert packet["main_merge_eligible"] is False
    assert packet["scoped"]["C3_4"] == "BLOCKED"
    assert packet["scoped"]["economic_integration"] == "NOT_IMPLEMENTED"
    for path, expected in packet["file_pins_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
