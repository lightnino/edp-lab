"""Contract, authority, evidence and replay checks without an Agent runtime."""
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from conftest import authorized_host

from edp_lab.profiling import tools
from edp_lab.profiling.source_reader import canonical_hash, read_registered, read_synthetic
from edp_lab.tool_adapters import (
    Authorization,
    CandidateKeyParameters,
    ColumnParameters,
    DuplicateParameters,
    EmptyParameters,
    ExecutionScope,
    SourceRef,
    ToolRequest,
)


def setup(raw=b"a,b\n1,x\n1,y\n", null_tokens=()):
    table = read_synthetic(raw, delimiter=",", quote=None, null_tokens=null_tokens,
                           expected_header=("a", "b"), provenance={"fixture": "V1"})
    adapter = authorized_host({"fixture": table}, {"tester": {"fixture", "missing"}})
    return table, adapter


def request(adapter, tool="profile_table", parameters=None):
    return ToolRequest(tool, adapter.source_ref("fixture"), Authorization("tester"),
                       parameters or EmptyParameters())


@pytest.mark.parametrize("name,parameters", [
    ("profile_table", EmptyParameters()), ("profile_column", ColumnParameters("a")),
    ("find_duplicates", DuplicateParameters()),
    ("candidate_key_scan", CandidateKeyParameters()), ("schema_fingerprint", EmptyParameters()),
])
def test_independent_calls_reuse_exact_existing_outputs_and_replay(name, parameters):
    table, adapter = setup()
    req = request(adapter, name, parameters)
    response = getattr(adapter, name)(req)
    assert response.status == "SUCCESS"
    assert response.result == getattr(tools, name)(table, **asdict(parameters))
    assert response == adapter.invoke(asdict(req))
    assert response.side_effects == ()
    assert response.evidence_refs["source"] == table.source
    payload = response.to_dict()
    fingerprint = payload.pop("result_fingerprint")
    assert canonical_hash(payload) == fingerprint


@pytest.mark.parametrize("change", [
    {"unexpected": 1}, {"tool_version": "V0"}, {"tool": []},
    {"parameters": {"sample_size": True}}, {"source": {}}, {"authorization": {}},
    {"scope": {"read_only": False}}, {"scope": {"max_rows": True}},
    {"parameters": {"column": "a", "sample_size": "5"}},
])
def test_malformed_requests_are_structured_failures(change):
    _, adapter = setup()
    data = asdict(request(adapter))
    data.update(change)
    response = adapter.invoke(data)
    assert response.status == "FAILED"
    assert response.errors
    assert response.result is None


def test_authority_is_host_owned_and_unavailable_sources_fail():
    _, adapter = setup()
    req = request(adapter)
    denied = adapter.invoke(replace(req, authorization=Authorization("intruder")))
    assert denied.status == "BLOCKED" and denied.approval_required
    assert denied.evidence_refs == {}
    missing = adapter.invoke(replace(req, source=SourceRef("missing", "x", "y")))
    assert missing.status == "FAILED" and missing.errors == ["SOURCE_UNAVAILABLE"]
    changed = adapter.invoke(replace(req, source=replace(req.source,
                                                       configuration_fingerprint="wrong")))
    assert changed.status == "BLOCKED"


@pytest.mark.parametrize("scope", [ExecutionScope(max_rows=1), ExecutionScope(max_cells=1)])
def test_resource_limits_do_not_run_profiler(scope, monkeypatch):
    _, adapter = setup()
    def forbidden(*args, **kwargs):
        pytest.fail("profiling must not execute")
    monkeypatch.setattr(tools, "profile_table", forbidden)
    result = adapter.invoke(replace(request(adapter), scope=scope))
    assert result.status == "BLOCKED"
    assert result.errors == ["RESOURCE_LIMIT_EXCEEDED"]


@pytest.mark.parametrize("raw,status,scanned", [
    (b"a,b\n1,x\ninvalid\n", "PARTIAL", 1), (b"wrong\n", "FAILED", 0),
])
def test_failed_scans_preserve_evidence_without_completed_metrics(raw, status, scanned):
    table, adapter = setup(raw)
    result = adapter.profile_table(request(adapter))
    assert result.status == status
    assert result.errors == list(table.errors)
    assert result.metrics["rows_scanned"]["value"] == scanned
    assert result.result["row_count"]["computation_mode"] == "NOT_COMPUTED"


def test_unresolved_semantics_are_partial_and_evidence_is_retained():
    _, adapter = setup(null_tokens=None)
    result = adapter.profile_column(request(adapter, "profile_column", ColumnParameters("a")))
    assert result.status == "PARTIAL"
    assert result.unresolved_questions
    assert result.result["statistics"]["sample"]["value"][0]["source_record"]


def test_invalid_column_and_search_limits():
    _, adapter = setup()
    for parameters, name in [(ColumnParameters("missing"), "profile_column"),
                             (CandidateKeyParameters(max_combinations=1), "candidate_key_scan")]:
        result = adapter.invoke(request(adapter, name, parameters))
        assert result.status == "FAILED"
        assert result.errors


def test_registered_gold_binding_and_integrity_failure(tmp_path):
    root = Path(__file__).resolve().parents[2]
    table = read_registered(root, "SRC000002", "nasdaqlisted.txt", provenance={})
    if any("RAW_UNAVAILABLE" in error for error in table.errors):
        pytest.skip("ENVIRONMENT: historical GOLD RAW absent; authorization passed")
    assert not table.errors
    adapter = authorized_host({"fixture": table}, {"tester": {"fixture"}})
    result = adapter.schema_fingerprint(request(adapter, "schema_fingerprint"))
    assert result.status == "SUCCESS"
    assert result.evidence_refs["config"]["freeze_sha256"]
    failed = read_registered(tmp_path, "SRC000002", "nasdaqlisted.txt", provenance={})
    adapter = authorized_host({"fixture": failed}, {"tester": {"fixture"}})
    assert adapter.profile_table(request(adapter)).status == "FAILED"


def test_host_bindings_are_isolated_from_input_and_response_mutation():
    table, adapter = setup()
    req = request(adapter)
    baseline = adapter.invoke(req)
    table.source["raw_sha256"] = "changed by caller"
    exposed = adapter.invoke(req)
    exposed.result["source"]["raw_sha256"] = "changed through response"
    assert adapter.invoke(req) == baseline
