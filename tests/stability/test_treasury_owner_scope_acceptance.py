"""Post-closeout scoped Treasury L3 approval: pin exact population, not semantics."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "metadata/evaluations"


def read(path):
    return json.loads((ROOT / path).read_text())


def test_owner_decision_covers_exact_pinned_original_treasury_inventory():
    inventory_path = "metadata/evaluations/treasury_l3_inventory_v1.json"
    raw = (ROOT / inventory_path).read_bytes()
    inventory = json.loads(raw)
    decision = read("metadata/evaluations/treasury_l3_owner_scope_decision_v1.json")

    assert decision["original_inventory_path"] == inventory_path
    assert decision["original_inventory_sha256"] == hashlib.sha256(raw).hexdigest()
    assert decision["decision_status"] == "APPROVED_SOURCE_PRESERVING_ONLY"
    assert decision["approved_disposition"] == "PRESERVED_NOT_MODELED"
    assert len(inventory["fields"]) == len(decision["approvals"]) == 50
    assert decision["authorized_population"]["physical_sources"] == 5

    def key(row):
        return (
            row["source_instance_id"],
            row["source_identity"],
            row["raw_sha256"],
            row["property_qname"],
        )

    originals = {key(x) for x in inventory["fields"]}
    approvals = {key(x) for x in decision["approvals"]}
    assert len(originals) == len(approvals) == 50
    assert originals == approvals
    assert all(x["recommended_l3_disposition"] == "PRESERVED_NOT_MODELED"
               for x in inventory["fields"])
    assert all(x["l3_disposition"] == "PRESERVED_NOT_MODELED"
               and x["owner_decision"] == "APPROVED_SOURCE_PRESERVING_ONLY"
               for x in decision["approvals"])
    assert {x["source_instance_id"] for x in decision["approvals"]} == {
        "SRC010451", "SRC010452", "SRC010453", "SRC010454", "SRC010455",
    }
    assert decision["out_of_scope"]["treasury_economic_integration"] == "NOT_IMPLEMENTED"
    assert decision["out_of_scope"]["day4_c3_4"] == "BLOCKED"
    assert decision["out_of_scope"]["day4_result_freeze"] == "CANDIDATE_NOT_FROZEN"


def test_scoped_reconciliation_does_not_promote_full_day4_result():
    evaluation = read(
        "metadata/evaluations/c1500_m2_stability_scoped_v3_owner_acceptance.json"
    )
    decision = read(
        "metadata/evaluations/treasury_l3_owner_scope_decision_v1.json"
    )
    assert evaluation["owner_decision_ref"] == (
        "metadata/evaluations/treasury_l3_owner_scope_decision_v1.json"
    )
    assert decision["decision_status"] == "APPROVED_SOURCE_PRESERVING_ONLY"
    assert evaluation["source_scope"]["treasury_l3_fields"] == 50
    assert evaluation["scoped_results"] == {
        "B2_1_SOURCE_PRESERVING": "PASS",
        "C1_SOURCE_PRESERVING": "PASS",
    }
    limits = evaluation["preserved_limits"]
    assert limits["C3_4_DAY4"] == "BLOCKED"
    assert limits["result_freeze"] == "CANDIDATE_NOT_FROZEN"
    assert limits["day4_exit"] == "PARTIAL"
    assert limits["full_c1500_acceptance"] == "NOT_CLAIMED"
    assert limits["B2_1_FULL_ECONOMIC"] == "NOT_IMPLEMENTED"
    assert limits["C1_FULL_ECONOMIC"] == "NOT_IMPLEMENTED"
