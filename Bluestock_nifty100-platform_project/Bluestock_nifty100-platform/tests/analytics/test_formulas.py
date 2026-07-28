"""Financial formula and CAGR unit tests."""

from __future__ import annotations

import pytest

from src.analytics.cagr import calculate_cagr
from src.analytics.ratios import (
    capital_allocation_label,
    interest_coverage,
    margin,
    price_to_earnings,
    return_on_equity,
    safe_divide,
)


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected"),
    [(10, 2, 5), (0, 2, 0), (10, 0, None), (None, 2, None)],
)
def test_safe_divide(
    numerator: object, denominator: object, expected: float | None
) -> None:
    """Safe divide has a zero-denominator contract."""
    assert safe_divide(numerator, denominator) == expected


def test_margin_and_roe_edges() -> None:
    """Margins and ROE implement the specified edge cases."""
    assert margin(25, 100) == 25
    assert margin(10, 0) is None
    assert return_on_equity(20, 100) == 20
    assert return_on_equity(20, 0) is None
    assert return_on_equity(20, -5) is None


def test_interest_coverage_contract() -> None:
    """Zero interest maps to Debt Free and no numeric ICR."""
    assert interest_coverage(50, 10) == (5, "Levered")
    assert interest_coverage(50, 0) == (None, "Debt Free")
    assert interest_coverage(50, -1) == (None, "Invalid Interest")


def test_pe_contract() -> None:
    """Non-positive PAT cannot produce P/E."""
    assert price_to_earnings(1000, 100) == 10
    assert price_to_earnings(1000, 0) is None
    assert price_to_earnings(1000, -10) is None


@pytest.mark.parametrize(
    ("base", "end", "years", "observations", "flag"),
    [
        (100, 133.1, 3, 4, "OK"),
        (100, -1, 3, 4, "DECLINE_TO_LOSS"),
        (-100, 1, 3, 4, "TURNAROUND"),
        (-100, -50, 3, 4, "BOTH_NEGATIVE"),
        (0, 100, 3, 4, "ZERO_BASE"),
        (100, 120, 3, 3, "INSUFFICIENT"),
        (None, 120, 3, 4, "INSUFFICIENT"),
    ],
)
def test_cagr_flags(
    base: object, end: object, years: int, observations: int, flag: str
) -> None:
    """Every specified CAGR sign-state is preserved."""
    result = calculate_cagr(base, end, years, observations)
    assert result.flag == flag
    assert (result.value is not None) == (flag == "OK")


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((1, -1, -1), "SELF_FUNDED_REINVESTMENT"),
        ((1, -1, 1), "EXPANSION_WITH_EXTERNAL_CAPITAL"),
        ((1, 1, -1), "ASSET_MONETISATION_AND_DELEVERAGING"),
        ((1, 1, 1), "CASH_ACCUMULATION"),
        ((-1, -1, -1), "CASH_BURN_AND_CONTRACTION"),
        ((-1, -1, 1), "EXTERNALLY_FUNDED_INVESTMENT"),
        ((-1, 1, -1), "ASSET_SALES_FUNDING_OPERATIONS"),
        ((-1, 1, 1), "RESTRUCTURING_WITH_EXTERNAL_SUPPORT"),
    ],
)
def test_capital_allocation_classes(
    values: tuple[int, int, int], expected: str
) -> None:
    """All eight sign classes have stable labels."""
    assert capital_allocation_label(*values) == expected
