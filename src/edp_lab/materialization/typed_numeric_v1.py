"""Approved exact TEXT projection; no source selection, I/O or financial inference.

Authority/scope: DEC-000013, docs/m2_additive_typed_numeric_v1.md.
Callers retain source context and apply the exact approved field/occurrence scope.
"""
import re
from dataclasses import dataclass
from decimal import Decimal

MODEL = "M2_ADDITIVE_TYPED_NUMERIC_V1"
RULE = "EXACT_DECIMAL_38_4_V1"
_NUMBER = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?", re.ASCII)
_SPACE = frozenset(" \t\r\n\f\v")


@dataclass(frozen=True)
class Projection:
    lexical_value: str | None
    value_decimal: Decimal | None
    conversion_outcome: str
    conversion_reason: str
    model_version: str = MODEL
    conversion_rule_version: str = RULE


def convert(text: str | None, *, present: bool = True,
            null_marker: bool = False) -> Projection:
    """Convert one explicitly selected occurrence without changing its TEXT.

    ``None`` alone cannot establish missing/null semantics: callers must supply
    structural absence or an explicit source null marker. Incoherent adapter
    states fail rather than yielding a fabricated source outcome.
    """
    if text is not None and not isinstance(text, str):
        raise TypeError("original lexical TEXT required; numeric inputs forbidden")
    if type(present) is not bool or type(null_marker) is not bool:
        raise TypeError("explicit boolean source-state flags required")

    def result(outcome, reason, value=None):
        return Projection(text, value, outcome, reason)

    if not present:
        if text is not None or null_marker:
            raise ValueError("conflicting absent-source state")
        return result("MISSING", "SOURCE_FIELD_ABSENT")
    blank = text is not None and all(c in _SPACE for c in text)
    if null_marker:
        if text is None or blank:
            return result("NULL_UNRESOLVED", "SOURCE_NULL_MARKER_UNINTERPRETED")
        return result("INVALID", "CONFLICTING_NULL_MARKER")
    if text is None:
        raise ValueError("unexplained adapter NULL")
    if blank:
        return result("BLANK", "EMPTY_TEXT" if text == "" else "WHITESPACE_ONLY")
    if _NUMBER.fullmatch(text) is None:
        return result("INVALID", "LEXICAL_GRAMMAR")
    integer, _, fraction = text.lstrip("+-").partition(".")
    if len(fraction) > 4:
        return result("SCALE_EXCEEDED", "FRACTIONAL_DIGITS_GT_4")
    if len(integer.lstrip("0")) > 34:
        return result("OVERFLOW", "INTEGER_DIGITS_GT_34")
    # Decimal(string) is exact and independent of context precision. No Decimal
    # arithmetic/quantize, binary float, trimming, or removal of fractional digits.
    padded = text + ("" if "." in text else ".") + "0" * (4 - len(fraction))
    return result("VALID", "EXACT_PROJECTION", Decimal(padded))
