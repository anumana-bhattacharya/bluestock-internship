"""Backward-compatible imports for Sprint 5 cash-flow analytics."""

from src.analytics.cashflow_kpis import (
    capex_label,
    cfo_quality_label,
    compute_cashflow_kpis,
    run_cashflow_kpis,
)


def capex_tier(
    intensity: float | None, high_threshold: float, medium_threshold: float
) -> str:
    """Preserve the legacy High/Medium/Low classifier for API callers."""
    if intensity is None:
        return "No Data"
    if intensity >= high_threshold:
        return "High"
    if intensity >= medium_threshold:
        return "Medium"
    return "Low"


run_cashflow_intelligence = run_cashflow_kpis

__all__ = [
    "capex_label",
    "capex_tier",
    "cfo_quality_label",
    "compute_cashflow_kpis",
    "run_cashflow_intelligence",
    "run_cashflow_kpis",
]
