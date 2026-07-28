"""Pure CAGR calculation with the specified sign-state contract."""

from __future__ import annotations

from dataclasses import dataclass

from src.analytics.ratios import as_number


@dataclass(frozen=True)
class CAGRResult:
    """Hold a CAGR value and its sign/coverage flag."""

    value: float | None
    flag: str


def calculate_cagr(
    base: object, end: object, years: int, observations: int
) -> CAGRResult:
    """Calculate CAGR while preserving all required edge-case flags."""
    if observations < years + 1:
        return CAGRResult(None, "INSUFFICIENT")
    base_value = as_number(base)
    end_value = as_number(end)
    if base_value is None or end_value is None:
        return CAGRResult(None, "INSUFFICIENT")
    if base_value == 0:
        return CAGRResult(None, "ZERO_BASE")
    if base_value > 0 and end_value < 0:
        return CAGRResult(None, "DECLINE_TO_LOSS")
    if base_value < 0 and end_value > 0:
        return CAGRResult(None, "TURNAROUND")
    if base_value < 0 and end_value < 0:
        return CAGRResult(None, "BOTH_NEGATIVE")
    if base_value < 0 or end_value < 0:
        return CAGRResult(None, "BOTH_NEGATIVE")
    value = ((end_value / base_value) ** (1.0 / years) - 1.0) * 100.0
    return CAGRResult(value, "OK")
