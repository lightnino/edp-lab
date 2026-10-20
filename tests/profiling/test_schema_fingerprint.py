"""Contract oracle independent of the production canonicalizer."""

import hashlib

import pytest

from edp_lab.profiling.conventions import schema_fingerprint


def test_exact_utf8_canonical_json():
    expected = hashlib.sha256(
        '{"columns":[{"name":" Å ","type":"TEXT"},{"name":"id","type":"TEXT"}],'
        '"version":"SCHEMA_SHA256_V1"}'.encode()).hexdigest()
    assert schema_fingerprint([(" Å ", "TEXT"), ("id", "TEXT")]) == expected


def test_nested_json_field_addition_changes_metadata_fingerprint():
    # Hand-declared synthetic JSON structure metadata, not inferred from records.
    # V1 hashes exact declared type text; these descriptors are opaque fixture
    # strings, not a new type grammar, JSON parser or registered source profile.
    before = [("payload", "STRUCT(id TEXT, nested STRUCT(code TEXT))")]
    after = [("payload", "STRUCT(id TEXT, nested STRUCT(code TEXT, label TEXT))")]
    original = schema_fingerprint(before)
    changed = schema_fingerprint(after)
    assert original != changed
    assert schema_fingerprint(before) == original
    expected = hashlib.sha256(
        b'{"columns":[{"name":"payload","type":'
        b'"STRUCT(id TEXT, nested STRUCT(code TEXT, label TEXT))"}],'
        b'"version":"SCHEMA_SHA256_V1"}').hexdigest()
    assert changed == expected


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
