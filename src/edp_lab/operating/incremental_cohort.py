"""Reusable, read-only incremental cohort planning; never a data-plane grant.

This module validates physical disjointness, pinned history and source eligibility.
The protected admission actor must independently verify the actual RAW handoff
receipts before publishing or executing any plan.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

from edp_lab.operating.authority import Denied, canonical


def _sha(value: object) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise Denied("INVALID_SOURCE_SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise Denied("INVALID_SOURCE_SHA256") from exc
    return value.lower()


def _identity(row: Mapping) -> tuple[str, str]:
    physical = row.get("source_identity")
    delivery = row.get("source_instance_id")
    if not isinstance(physical, str) or not physical:
        raise Denied("MISSING_PHYSICAL_IDENTITY")
    if not isinstance(delivery, str) or not delivery:
        raise Denied("MISSING_DELIVERY_IDENTITY")
    return physical, delivery


def plan_increment(
    previous: Sequence[Mapping],
    incoming: Sequence[Mapping],
    approved_members: Sequence[Mapping],
    *,
    previous_cohort: str,
    new_cohort: str,
    expected_increment: int,
    pinned_universe_sha256: str,
) -> dict:
    """Validate C_old + N -> C_new, without opening RAW or modifying history.

    Exactly one canonical Universe snapshot is passed by the trusted caller.
    The executor separately verifies source hash/path and signed U10 RAW handoff.
    """
    import re

    if (not isinstance(previous_cohort, str)
            or re.fullmatch(r"C[1-9][0-9]*", previous_cohort) is None
            or not isinstance(new_cohort, str)
            or re.fullmatch(r"C[1-9][0-9]*", new_cohort) is None
            or previous_cohort == new_cohort
            or type(expected_increment) is not int or expected_increment <= 0):
        raise Denied("INVALID_INCREMENT_SCOPE")
    universe_pin = _sha(pinned_universe_sha256)
    if (not previous or len(incoming) != expected_increment
            or len(previous) != int(previous_cohort[1:])
            or len(previous) + expected_increment != int(new_cohort[1:])):
        raise Denied("INCREMENT_COUNT_MISMATCH")

    eligible: dict[str, Mapping] = {}
    for member in approved_members:
        identity = member.get("identity")
        if not isinstance(identity, str) or not identity or identity in eligible:
            raise Denied("INVALID_UNIVERSE_MEMBERSHIP")
        eligible[identity] = member

    old_physical: set[str] = set()
    all_names: set[str] = set()
    for item in previous:
        physical, delivery = _identity(item)
        if physical in old_physical or delivery in all_names:
            raise Denied("PRIOR_COHORT_NOT_UNIQUE")
        old_physical.add(physical)
        all_names.add(delivery)

    additions: set[str] = set()
    for item in incoming:
        physical, delivery = _identity(item)
        if physical in old_physical or physical in additions or delivery in all_names:
            raise Denied("INCREMENT_OVERLAP")
        additions.add(physical)
        all_names.add(delivery)
        member = eligible.get(physical)
        if member is None or member.get("holdout") is not False:
            raise Denied("INCREMENT_NOT_APPROVED_OR_HOLDOUT")
        if (_sha(item.get("raw_sha256")) != _sha(member.get("raw_sha256"))
                or item.get("raw_path") != member.get("raw_path")):
            raise Denied("INCREMENT_RAW_IDENTITY_MISMATCH")
        # New cohort consumes existing remotely verified RAW, never stages it.
        if not isinstance(item.get("remote_raw_path"), str) or not item["remote_raw_path"]:
            raise Denied("RAW_HANDOFF_MISSING")
        _sha(item.get("raw_handoff_receipt_sha256"))

    old_names = {row["source_instance_id"] for row in previous}
    return {
        "schema": "EDP_INCREMENTAL_COHORT_PLAN_V1",
        "status": "PREPARED_NOT_ADMITTED",
        "previous_cohort": previous_cohort,
        "cohort": new_cohort,
        "universe_sha256": universe_pin,
        "old_count": len(previous),
        "new_count": len(incoming),
        "combined_count": len(previous) + len(incoming),
        "old_members_sha256": hashlib.sha256(canonical(sorted(old_physical))).hexdigest(),
        "new_members_sha256": hashlib.sha256(canonical(sorted(additions))).hexdigest(),
        "new_delivery_sha256": hashlib.sha256(
            canonical(sorted(all_names - old_names))).hexdigest(),
        "raw_write_operations": 0,
        "historical_result_rewrite": False,
    }
