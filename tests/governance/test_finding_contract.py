"""Offline structural contract checks; no evidence resolution or approval engine.

The test-only evaluator covers exactly the JSON Schema keywords used by v1.
Unknown keywords fail closed; no external schema retrieval or dependency needed.
"""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "metadata/finding_schema_v1.json").read_text())
KEYWORDS = {
    "$schema", "$id", "$defs", "$ref", "title", "type", "additionalProperties",
    "required", "properties", "const", "enum", "pattern", "items", "minItems",
    "allOf", "if", "then",
}


def validate(value, schema=SCHEMA):
    """Evaluate only the local v1 keyword subset, using JSON Schema semantics."""
    assert set(schema) <= KEYWORDS
    if "$ref" in schema:
        assert schema["$ref"].startswith("#/$defs/")
        validate(value, SCHEMA["$defs"][schema["$ref"].split("/")[-1]])
    if "type" in schema:
        assert isinstance(value, {"object": dict, "array": list, "string": str}[schema["type"]])
    if "const" in schema:
        assert value == schema["const"]
    if "enum" in schema:
        assert value in schema["enum"]
    if isinstance(value, str) and "pattern" in schema:
        assert re.search(schema["pattern"], value)
    if isinstance(value, dict):
        assert set(schema.get("required", [])) <= value.keys()
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            assert value.keys() <= properties.keys()
        for key in value.keys() & properties.keys():
            validate(value[key], properties[key])
    if isinstance(value, list):
        assert len(value) >= schema.get("minItems", 0)
        for item in value:
            validate(item, schema.get("items", {}))
    for constraint in schema.get("allOf", []):
        validate(value, constraint)
    if "if" in schema:
        try:
            validate(value, schema["if"])
        except AssertionError:
            pass
        else:
            validate(value, schema["then"])


@pytest.fixture
def finding():
    # Synthetic witnesses exercise shape only; these are not source observations.
    evidence = {"path": "tests/synthetic-witness", "version": "fixture-v1", "locator": "case 1"}
    return {
        "schema_version": "1.0.0", "finding_id": "FND-fixture", "owner": "test executor",
        "claim": "Synthetic lexical observation", "finding_type": "MECHANICAL",
        "source_refs": [{"source_instance_id": "SRC999999", "raw_path": "data/raw/fixture",
                         "raw_sha256": "a" * 64, "locator": "table fixture; record 1; field x"}],
        "evidence_refs": [evidence], "state": "OBSERVED", "materiality": "P3",
        "approval_requirement": "NONE",
        "validation": {"scope": "synthetic case only", "method": "not yet checked"},
    }


def test_schema_structure():
    assert SCHEMA["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert SCHEMA["$id"] == "urn:edp-lab:finding:1.0.0"

    def check(node):
        assert set(node) <= KEYWORDS
        for name in node.get("required", []):
            assert isinstance(name, str)
        if "pattern" in node:
            re.compile(node["pattern"])
        if "$ref" in node:
            assert node["$ref"].split("/")[-1] in SCHEMA["$defs"]
        for key in ("properties", "$defs"):
            for child in node.get(key, {}).values():
                check(child)
        for key in ("items", "if", "then"):
            if key in node:
                check(node[key])
        for child in node.get("allOf", []):
            check(child)

    check(SCHEMA)


@pytest.mark.parametrize("state", ["OBSERVED", "PROPOSED", "VALIDATED", "REJECTED", "UNRESOLVED"])
def test_five_states(finding, state):
    finding["state"] = state
    finding["validation"]["evidence_refs"] = deepcopy(finding["evidence_refs"])
    finding["reason"] = "Synthetic evidence insufficient or contrary"
    finding["next_review_trigger"] = "New independently supplied evidence"
    validate(finding)


@pytest.mark.parametrize("field", sorted(SCHEMA["required"]))
def test_required_fields(finding, field):
    del finding[field]
    with pytest.raises(AssertionError):
        validate(finding)


@pytest.mark.parametrize("change", [
    {"evidence_refs": []}, {"source_refs": []}, {"schema_version": "2.0.0"},
    {"materiality": "P4"}, {"approval_requirement": "APPROVED"},
    {"claim": "  "}, {"decision_ref": "invented"},
])
def test_invalid_findings(finding, change):
    finding.update(change)
    with pytest.raises(AssertionError):
        validate(finding)


@pytest.mark.parametrize("field", ["raw_sha256", "source_instance_id", "locator", "raw_path"])
def test_source_evidence_required(finding, field):
    del finding["source_refs"][0][field]
    with pytest.raises(AssertionError):
        validate(finding)


@pytest.mark.parametrize("field", ["path", "version", "locator"])
def test_versioned_evidence_required(finding, field):
    del finding["evidence_refs"][0][field]
    with pytest.raises(AssertionError):
        validate(finding)


def test_validated_requires_validation_evidence(finding):
    finding["state"] = "VALIDATED"
    with pytest.raises(AssertionError):
        validate(finding)
    finding["validation"]["evidence_refs"] = []
    with pytest.raises(AssertionError):
        validate(finding)
    finding["validation"]["evidence_refs"] = deepcopy(finding["evidence_refs"])
    validate(finding)  # Mechanical validation does not need a decision or approval.
    assert "decision_ref" not in finding
    assert finding["approval_requirement"] == "NONE"


def test_rejected_requires_contrary_validation_evidence(finding):
    finding.update(state="REJECTED", reason="Synthetic claim refuted by contrary witness")
    finding["validation"].update(
        scope="synthetic case 2, field x only",
        method="Compare claim with contrary literal witness",
    )
    with pytest.raises(AssertionError):
        validate(finding)
    finding["validation"]["evidence_refs"] = []
    with pytest.raises(AssertionError):
        validate(finding)
    finding["validation"]["evidence_refs"] = [{
        "path": "tests/synthetic-contrary-witness", "version": "fixture-v1", "locator": "case 2",
    }]
    validate(finding)


@pytest.mark.parametrize("field", ["scope", "method"])
def test_rejected_requires_validation_scope_and_method(finding, field):
    finding.update(state="REJECTED", reason="Synthetic contrary evidence")
    finding["validation"]["evidence_refs"] = deepcopy(finding["evidence_refs"])
    del finding["validation"][field]
    with pytest.raises(AssertionError):
        validate(finding)


@pytest.fixture
def semantic_proposal(finding):
    finding.update(
        finding_type="SEMANTIC", state="PROPOSED", approval_requirement="HUMAN_REVIEW",
        claim="Should the synthetic interpretation be adopted?",
        alternatives=["Adopt the synthetic interpretation", "Defer pending new evidence"],
        consequences="Adopt: synthetic dependent work may proceed after approval; "
        "defer: dependent interpretation remains withheld.",
    )
    return finding


def test_semantic_proposal_with_alternatives_and_consequences(semantic_proposal):
    validate(semantic_proposal)


@pytest.mark.parametrize("field", ["alternatives", "consequences"])
def test_semantic_proposal_requires_decision_context(semantic_proposal, field):
    del semantic_proposal[field]
    with pytest.raises(AssertionError):
        validate(semantic_proposal)


@pytest.mark.parametrize("change", [
    {"alternatives": []}, {"alternatives": ["Only one option"]},
    {"alternatives": ["Defer", "  "]}, {"consequences": "  "},
])
def test_semantic_proposal_rejects_empty_decision_context(semantic_proposal, change):
    semantic_proposal.update(change)
    with pytest.raises(AssertionError):
        validate(semantic_proposal)


@pytest.mark.parametrize("approval", ["NONE", "HUMAN_REVIEW"])
def test_mechanical_proposal_needs_no_semantic_decision_context(finding, approval):
    finding.update(state="PROPOSED", approval_requirement=approval)
    validate(finding)


def test_unresolved_semantic_finding_needs_no_proposal_context(finding):
    finding.update(
        finding_type="SEMANTIC", state="UNRESOLVED", approval_requirement="HUMAN_REVIEW",
        reason="Synthetic evidence is insufficient", next_review_trigger="New synthetic witness",
    )
    validate(finding)


@pytest.mark.parametrize("state", ["APPROVED", "ADMITTED", "ACCEPTED", "EXACT_FULL_SCAN", "NOT_COMPUTED"])
def test_other_status_dimensions_cannot_be_finding_states(finding, state):
    finding["state"] = state
    with pytest.raises(AssertionError):
        validate(finding)


@pytest.mark.parametrize("field", ["approved", "approved_by", "decision_status", "admission_status"])
def test_no_embedded_approval_escalation(finding, field):
    finding["state"] = "VALIDATED"
    finding["validation"]["evidence_refs"] = deepcopy(finding["evidence_refs"])
    finding["decision_ref"] = "DEC-000001"  # Linking a decision grants no extra fields.
    finding[field] = "APPROVED"
    with pytest.raises(AssertionError):
        validate(finding)


@pytest.mark.parametrize("kind", ["SEMANTIC", "GOVERNANCE"])
def test_validation_cannot_remove_human_review(finding, kind):
    finding["finding_type"] = kind
    finding["state"] = "VALIDATED"
    finding["validation"]["evidence_refs"] = deepcopy(finding["evidence_refs"])
    with pytest.raises(AssertionError):
        validate(finding)
    finding["approval_requirement"] = "HUMAN_REVIEW"
    validate(finding)


def test_unresolved_incidental_question_remains_unresolved(finding):
    finding["state"] = "UNRESOLVED"
    with pytest.raises(AssertionError):
        validate(finding)
    finding["reason"] = "Footer timezone is unknown; preservation and accounting satisfied"
    with pytest.raises(AssertionError):
        validate(finding)
    finding["next_review_trigger"] = "Concrete new downstream semantic dependency"
    validate(finding)
    assert finding["state"] == "UNRESOLVED"
    assert finding["materiality"] == "P3"


def test_documentary_governance_finding_needs_no_raw_source(finding):
    finding.update(finding_type="GOVERNANCE", source_refs=[], approval_requirement="HUMAN_REVIEW")
    validate(finding)
