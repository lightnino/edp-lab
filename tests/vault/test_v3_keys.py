"""V3 wheel keys match the unchanged approved V1 reference."""

from edp_lab.vault.v3_keys import concept_key, filing_key, key, occurrence_key
from scripts import day6_vault_contract_v1 as reference


def test_v3_key_bytes_match_approved_v1_reference():
    assert filing_key("000123-25-000004") == reference.filing_key("000123-25-000004")
    assert concept_key("Assets", "us-gaap/2025") == (
        reference.concept_key("Assets", "us-gaap/2025"))
    assert occurrence_key("SRC000005", "pre.txt", "a" * 64, 42, 12) == (
        reference.occurrence_key("SRC000005", "pre.txt", "a" * 64, 42, 12))
    assert key("V3_TEST", ("", None, "a\tb", "零")) == (
        reference.key("V3_TEST", ("", None, "a\tb", "零")))
