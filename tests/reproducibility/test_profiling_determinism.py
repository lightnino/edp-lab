"""Independent sample oracle and narrowly scoped provenance comparison."""

import hashlib
import json
from dataclasses import replace

import pytest

from edp_lab.profiling import tools
from edp_lab.profiling.source_reader import read_synthetic


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def table():
    return read_synthetic(b"a,b\nz,1\na,2\nz,1\na,2\nb,3\n", delimiter=",", quote=None,
                          null_tokens=None, expected_header=("a", "b"), provenance={"run": 1})


@pytest.mark.parametrize("call", [tools.profile_table, tools.find_duplicates,
                                  tools.candidate_key_scan, tools.schema_fingerprint,
                                  lambda t: tools.profile_column(t, "a", sample_seed=17)])
def test_replay_and_provenance_sensitive_envelope(call):
    first = table()
    a, b = call(first), call(table())
    assert a == b
    changed = call(replace(first, provenance={"run": 2}))
    for output in (a, changed):
        payload = {k: v for k, v in output.items() if k != "result_sha256"}
        assert output["result_sha256"] == sha(payload)
    assert a["provenance"] != changed["provenance"]
    assert a["run_id"] != changed["run_id"]
    assert a["result_sha256"] != changed["result_sha256"]
    # Only these envelope fields depend on execution provenance. All inputs,
    # parameters, errors, locators and substantive results must still match.
    excluded = {"provenance", "run_id", "result_sha256"}
    assert {k: v for k, v in a.items() if k not in excluded} == {
        k: v for k, v in changed.items() if k not in excluded}


@pytest.mark.parametrize("seed,size", [(0, 0), (17, 3), (42, 99)])
def test_sample_selection_matches_declared_hash_ranking(seed, size):
    source = table()
    result = tools.profile_column(source, "a", sample_seed=seed, sample_size=size)
    ranked = sorted(range(5), key=lambda i: (sha({"seed": seed, "source": source.source,
                                                "locator": source.locators[i]}), i))[:size]
    assert result["statistics"]["sample"] == {
        "computation_mode": "EXACT_SAMPLE", "value": [
            {"literal_value": source.rows[i][0], "source_record": source.locators[i],
             "column": "a"} for i in ranked]}
    assert result["sample_selection"] == {
        "method": "LOWEST_SHA256_SEED_SOURCE_LOCATOR", "seed": seed,
        "actual_size": min(size, 5), "population_size": 5}
    assert result["literal_statistics"]["top_text_values"]["value"] == [
        {"value": "a", "count": 2}, {"value": "z", "count": 2}, {"value": "b", "count": 1}]
    groups = tools.find_duplicates(source)["groups"]
    assert [g["values"] for g in groups] == [["a", "2"], ["z", "1"]]
    assert groups[0]["source_record_witnesses"] == [source.locators[i] for i in (1, 3)]
