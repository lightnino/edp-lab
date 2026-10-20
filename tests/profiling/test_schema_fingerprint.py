"""Contract oracle independent of the production canonicalizer."""

import hashlib

import pytest

from edp_lab.profiling.conventions import schema_fingerprint


def test_exact_utf8_canonical_json():
    expected = hashlib.sha256(
        '{"columns":[{"name":" Å ","type":"TEXT"},{"name":"id","type":"TEXT"}],'
        '"version":"SCHEMA_SHA256_V1"}'.encode()).hexdigest()
    assert schema_fingerprint([(" Å ", "TEXT"), ("id", "TEXT")]) == expected


@pytest.mark.parametrize("columns", [
    [("Å", "TEXT"), ("id", "TEXT")],
    [(" å ", "TEXT"), ("id", "TEXT")],
    [(" A\u030a ", "TEXT"), ("id", "TEXT")],
    [("id", "TEXT"), (" Å ", "TEXT")],
    [(" Å ", "TEXT")],
    [(" Å ", "TEXT"), ("id", "TEXT"), ("new", "TEXT")],
    [(" Å ", "TEXT"), ("id", "INTEGER")],
])
def test_structural_changes_are_not_normalized(columns):
    assert schema_fingerprint(columns) != schema_fingerprint([(" Å ", "TEXT"), ("id", "TEXT")])
