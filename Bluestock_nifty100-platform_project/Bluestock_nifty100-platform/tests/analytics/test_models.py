"""Scoring, valuation, cash-flow, peer, NLP, and clustering tests."""

from __future__ import annotations

import pandas as pd
import pytest

from src.analytics.cashflow_intel import capex_tier
from src.analytics.cashflow_kpis import capex_label, cfo_quality_label
from src.analytics.health_score import health_band, winsorised_scale
from src.analytics.sector_peer import compute_peer_percentiles
from src.analytics.valuation import valuation_flag
from src.nlp.parser import (
    cross_validate_parsed_cagrs,
    parse_analysis_with_failures,
    parse_metric_text,
)
from src.reports.portfolio_report import _trend


def test_winsorised_scale_bounds() -> None:
    """Winsorised scores remain in the 0-100 range."""
    score = winsorised_scale(pd.Series([-100, 1, 2, 3, 1000]), 0.1, 0.9)
    assert score.between(0, 100).all()
    assert winsorised_scale(pd.Series([1, 2, 3]), 0.1, 0.9, invert=True).iloc[0] > 50


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100, "Excellent"),
        (80, "Excellent"),
        (79.99, "Good"),
        (65, "Good"),
        (50, "Average"),
        (35, "Weak"),
        (0, "Poor"),
    ],
)
def test_health_bands(score: float, expected: str) -> None:
    """Band boundaries follow the user contract."""
    bands = [
        {"minimum": 80, "label": "Excellent"},
        {"minimum": 65, "label": "Good"},
        {"minimum": 50, "label": "Average"},
        {"minimum": 35, "label": "Weak"},
        {"minimum": 0, "label": "Poor"},
    ]
    assert health_band(score, bands) == expected


@pytest.mark.parametrize(
    ("pe", "median", "expected"),
    [
        (31, 20, "Caution"),
        (13, 20, "Discount"),
        (20, 20, "Fair"),
        (None, 20, "Unavailable"),
    ],
)
def test_valuation_flags(pe: float | None, median: float | None, expected: str) -> None:
    """Sector-relative P/E flags use exact configured multipliers."""
    assert valuation_flag(pe, median, 1.5, 0.7) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (25, "High"),
        (20, "High"),
        (15, "Medium"),
        (10, "Medium"),
        (5, "Low"),
        (None, "No Data"),
    ],
)
def test_capex_tiers(value: float | None, expected: str) -> None:
    """CapEx intensity tier thresholds are stable."""
    assert capex_tier(value, 20, 10) == expected


def test_peer_percentile_direction() -> None:
    """Highest ROE and lowest leverage receive percentile 1.0."""
    ratios = pd.DataFrame(
        {
            "company_id": ["A", "B", "C"],
            "year": ["2024-03"] * 3,
            "return_on_equity_pct": [10, 20, 30],
            "operating_profit_margin_pct": [10, 20, 30],
            "revenue_cagr_3y": [10, 20, 30],
            "fcf_conversion_pct": [10, 20, 30],
            "debt_to_equity": [3, 2, 1],
        }
    )
    groups = pd.DataFrame({"peer_group_name": ["G"] * 3, "company_id": ["A", "B", "C"]})
    result = compute_peer_percentiles(ratios, groups).set_index("company_id")
    assert result.loc["C", "roe_percentile"] == 1.0
    assert result.loc["C", "debt_to_equity_percentile"] == 1.0


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("10 Years: 21%", [(10, 21.0)]),
        ("5 Years          14%", [(5, 14.0)]),
        ("3 Year: 7.5%", [(3, 7.5)]),
        (None, []),
    ],
)
def test_analysis_parser(text: str | None, expected: list[tuple[int, float]]) -> None:
    """The requested regex parses observed narrative variants."""
    assert parse_metric_text(text) == expected


def test_analysis_parser_outputs_and_failures() -> None:
    """Parsed and failed cells use the exact Sprint 5 contracts."""
    source = pd.DataFrame(
        {
            "company_id": ["ABC"],
            "compounded_sales_growth": ["5 Years: 12.5%"],
            "compounded_profit_growth": ["not available"],
            "stock_price_cagr": [None],
            "roe": ["3 Years 20%"],
        }
    )
    result = parse_analysis_with_failures(source)
    assert list(result.parsed.columns) == [
        "company_id",
        "metric_type",
        "period_years",
        "value_pct",
    ]
    assert len(result.parsed) == 2
    assert result.failures.iloc[0]["metric_type"] == "compounded_profit_growth"


def test_analysis_cross_validation_flags_divergence() -> None:
    """Parsed-versus-computed growth differences above five points are flagged."""
    parsed = pd.DataFrame(
        {
            "company_id": ["ABC"],
            "metric_type": ["compounded_sales_growth"],
            "period_years": [5],
            "value_pct": [20.0],
        }
    )
    ratios = pd.DataFrame(
        {
            "company_id": ["ABC"],
            "year": ["2024-03"],
            "revenue_cagr_5y": [10.0],
        }
    )
    result = cross_validate_parsed_cagrs(parsed, ratios)
    assert bool(result.iloc[0]["manual_review_flag"])
    assert result.iloc[0]["divergence_pct"] == 10.0


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (1.01, "High Quality"),
        (1.0, "Moderate"),
        (0.5, "Moderate"),
        (0.49, "Accrual Risk"),
        (None, "No Data"),
    ],
)
def test_cfo_quality_labels(score: float | None, expected: str) -> None:
    """CFO/PAT quality labels use the exact Sprint 5 boundaries."""
    assert cfo_quality_label(score, 1.0, 0.5) == expected


@pytest.mark.parametrize(
    ("intensity", "expected"),
    [
        (2.99, "Asset Light"),
        (3.0, "Moderate"),
        (8.0, "Moderate"),
        (8.01, "Capital Intensive"),
        (None, "No Data"),
    ],
)
def test_sprint5_capex_labels(intensity: float | None, expected: str) -> None:
    """CapEx intensity labels use the exact 3% and 8% bands."""
    assert capex_label(intensity, 3.0, 8.0) == expected


@pytest.mark.parametrize(
    ("previous", "latest", "higher_is_better", "expected"),
    [
        (10.0, 12.0, True, "up"),
        (10.0, 8.0, True, "down"),
        (1.0, 0.8, False, "up"),
        (100.0, 101.0, True, "flat"),
        (None, 1.0, True, "unavailable"),
    ],
)
def test_portfolio_trend_arrows(
    previous: float | None,
    latest: float,
    higher_is_better: bool,
    expected: str,
) -> None:
    """Portfolio arrows distinguish improvement, decline, and 2% flat moves."""
    assert _trend(previous, latest, higher_is_better) == expected
