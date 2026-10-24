"""Pure metric definitions and deterministic header-schema fingerprint primitives.

These primitives do NOT parse source files or infer business meaning.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

CONTRACT_VERSION = "parser_profiler_contract_v1"
FINGERPRINT_VERSION = "source_columns_sha256_v1"


@dataclass(frozen=True)
class FieldCounts:
    row_count: int
    null_count: int
    distinct_non_null_count: int
    count_mode: str = "EXACT"

    def as_profile(self) -> dict[str, int | float | str | None]:
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in (self.row_count, self.null_count, self.distinct_non_null_count)
        ):
            raise ValueError("Counts must be nonnegative integers")
        if self.null_count > self.row_count:
            raise ValueError("null_count cannot exceed row_count")
        non_null = self.row_count - self.null_count
        if self.count_mode != "EXACT":
            raise ValueError("APPROXIMATE counts require a separate versioned estimator")
        if self.distinct_non_null_count > non_null:
            raise ValueError("distinct_non_null_count cannot exceed non_null_count")
        return {
            "row_count": self.row_count,
            "null_count": self.null_count,
            "non_null_count": non_null,
            "null_pct": self.null_count / self.row_count if self.row_count else None,
            "distinct_non_null_count": self.distinct_non_null_count,
            "distinct_pct": self.distinct_non_null_count / non_null if non_null else None,
            "count_mode": self.count_mode,
        }


def source_schema_fingerprint(
    header_columns: list[str], *, parser_profile_sha256: str
) -> str:
    """Hash the ordered source-visible headers under a specific parser profile."""
    if not header_columns or any(not isinstance(column, str) for column in header_columns):
        raise ValueError("Source columns must be a nonempty list of strings")
    if len(parser_profile_sha256) != 64 or any(
        char not in "0123456789abcdef" for char in parser_profile_sha256
    ):
        raise ValueError("Expected lowercase SHA-256 parser-profile digest")
    envelope = {
        "algorithm": FINGERPRINT_VERSION,
        "contract": CONTRACT_VERSION,
        "parser_profile_sha256": parser_profile_sha256,
        "columns": [
            {"ordinal": ordinal, "source_header": column}
            for ordinal, column in enumerate(header_columns, start=1)
        ],
    }
    content = json.dumps(
        envelope, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(content).hexdigest()
