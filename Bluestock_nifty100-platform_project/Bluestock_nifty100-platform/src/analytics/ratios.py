"""Pure financial-ratio formulas with explicit edge handling."""

from __future__ import annotations

import math
from typing import Any


def as_number(value: Any) -> float | None:
    """Return a finite float or None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def safe_divide(
    numerator: Any, denominator: Any, *, multiplier: float = 1.0
) -> float | None:
    """Divide finite inputs, returning None for a zero denominator."""
    num = as_number(numerator)
    den = as_number(denominator)
    if num is None or den is None or den == 0:
        return None
    return num / den * multiplier


def margin(profit: Any, sales: Any) -> float | None:
    """Compute a percentage margin, returning None when sales is zero."""
    return safe_divide(profit, sales, multiplier=100.0)


def return_on_equity(net_profit: Any, equity: Any) -> float | None:
    """Compute ROE; non-positive equity produces None."""
    equity_value = as_number(equity)
    if equity_value is None or equity_value <= 0:
        return None
    return safe_divide(net_profit, equity_value, multiplier=100.0)


def interest_coverage(ebit: Any, interest: Any) -> tuple[float | None, str]:
    """Compute ICR; zero interest is classified as Debt Free."""
    interest_value = as_number(interest)
    if interest_value is None:
        return None, "Missing Interest"
    if interest_value == 0:
        return None, "Debt Free"
    if interest_value < 0:
        return None, "Invalid Interest"
    return safe_divide(ebit, interest_value), "Levered"


def price_to_earnings(market_cap: Any, net_profit: Any) -> float | None:
    """Compute P/E; non-positive PAT produces None."""
    profit = as_number(net_profit)
    if profit is None or profit <= 0:
        return None
    return safe_divide(market_cap, profit)


def capital_allocation_label(cfo: Any, cfi: Any, cff: Any) -> str:
    """Classify the eight possible CFO/CFI/CFF sign combinations."""
    values = [as_number(value) for value in (cfo, cfi, cff)]
    if any(value is None for value in values):
        return "NO_DATA"
    signs = tuple("+" if value >= 0 else "-" for value in values)
    labels = {
        ("+", "-", "-"): "SELF_FUNDED_REINVESTMENT",
        ("+", "-", "+"): "EXPANSION_WITH_EXTERNAL_CAPITAL",
        ("+", "+", "-"): "ASSET_MONETISATION_AND_DELEVERAGING",
        ("+", "+", "+"): "CASH_ACCUMULATION",
        ("-", "-", "-"): "CASH_BURN_AND_CONTRACTION",
        ("-", "-", "+"): "EXTERNALLY_FUNDED_INVESTMENT",
        ("-", "+", "-"): "ASSET_SALES_FUNDING_OPERATIONS",
        ("-", "+", "+"): "RESTRUCTURING_WITH_EXTERNAL_SUPPORT",
    }
    return labels[signs]
