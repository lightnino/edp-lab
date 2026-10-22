"""Reusable source-aware multiset oracle for M1 cross-cohort C2 checks.

This small pure-Python comparator tests bounded witnesses and negative controls.
The real C750 assessment must ALSO compare full native Delta data and receipts.
"""

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceOccurrence:
    source_instance_id: str
    binding_sha256: str
    run_id: str
    locator: str
    lexical_value: str


def multiset_differences(
    expected_old: list[SourceOccurrence],
    expected_new: list[SourceOccurrence],
    actual_combined: list[SourceOccurrence],
) -> tuple[Counter[SourceOccurrence], Counter[SourceOccurrence]]:
    """Return missing and extra occurrences; never de-duplicate by visible value."""
    expected = Counter(expected_old) + Counter(expected_new)
    actual = Counter(actual_combined)
    return expected - actual, actual - expected


def old_projection_differences(
    original: list[SourceOccurrence],
    combined: list[SourceOccurrence],
) -> tuple[Counter[SourceOccurrence], Counter[SourceOccurrence]]:
    """Require the old source/binding/run/locator projection to be unchanged."""
    original_keys = {(x.source_instance_id, x.binding_sha256, x.run_id) for x in original}
    projected = [
        x
        for x in combined
        if (x.source_instance_id, x.binding_sha256, x.run_id) in original_keys
    ]
    return Counter(original) - Counter(projected), Counter(projected) - Counter(original)


def check_disjoint_source_ids(
    old_ids: set[str], new_ids: set[str]
) -> set[str]:
    """Source identity collisions cannot be promoted under source-preserving M1."""
    return old_ids & new_ids
