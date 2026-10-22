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


def operational_acceptance_failures(
    *,
    expected_bindings: int,
    completed_binding_ids: list[str],
    reprocessed_completed_bindings: int,
    historical_replays: int,
    publication_exact_readback: bool,
    stage_wall_seconds: dict[str, float],
    approved_stage_budgets_seconds: dict[str, float] | None,
) -> list[str]:
    """Evaluate C3.1–C3.4 from actual receipts; missing budgets cannot PASS."""
    failed: list[str] = []
    if len(completed_binding_ids) != expected_bindings:
        failed.append("C3.1: binding completion count mismatch")
    if len(set(completed_binding_ids)) != expected_bindings:
        failed.append("C3.1: duplicate or missing COMPLETE binding identity")
    if historical_replays != 0:
        failed.append("C3.2: historical replay occurred")
    if reprocessed_completed_bindings != 0 or not publication_exact_readback:
        failed.append("C3.3: checkpoint replay or output readback mismatch")
    required_stages = {"processing", "clean_publication", "queryable_validation"}
    if set(stage_wall_seconds) != required_stages:
        failed.append("C3.4: measured stage inventory incomplete")
    elif any(not (0 < value < float("inf")) for value in stage_wall_seconds.values()):
        failed.append("C3.4: invalid measured wall time")
    if approved_stage_budgets_seconds is None:
        failed.append("C3.4: no prior configured or owner-accepted budgets")
    elif set(approved_stage_budgets_seconds) != required_stages:
        failed.append("C3.4: phase budget inventory incomplete")
    else:
        for name in required_stages & stage_wall_seconds.keys():
            limit = approved_stage_budgets_seconds[name]
            if not (0 < limit < float("inf")) or stage_wall_seconds[name] > limit:
                failed.append(f"C3.4: {name} elapsed outside approved budget")
    return failed
