"""Winsorised, weighted financial health scoring for all companies."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.config.settings import Settings
from src.database.sqlite_loader import load_derived_table

LOGGER = logging.getLogger(__name__)
COMPONENT_METRICS = {
    "profitability": (
        ("return_on_equity_pct", False),
        ("return_on_capital_employed_pct", False),
        ("net_profit_margin_pct", False),
        ("operating_profit_margin_pct", False),
    ),
    "cash_quality": (
        ("cfo_to_pat", False),
        ("fcf_conversion_pct", False),
    ),
    "growth": (
        ("revenue_cagr_3y", False),
        ("pat_cagr_3y", False),
        ("eps_cagr_3y", False),
    ),
    "leverage": (
        ("debt_to_equity", True),
        ("net_debt_to_ebitda", True),
        ("interest_coverage", False),
    ),
}


def _read_analytics_config(project_root: Path) -> dict[str, Any]:
    """Read analytics thresholds from YAML."""
    with (project_root / "config" / "analytics.yaml").open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def winsorised_scale(
    series: pd.Series, lower: float, upper: float, invert: bool = False
) -> pd.Series:
    """Winsorise a series then min-max scale it to 0-100."""
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() == 0:
        scaled = pd.Series(50.0, index=series.index)
    else:
        filled = numeric.fillna(numeric.median())
        low = filled.quantile(lower)
        high = filled.quantile(upper)
        clipped = filled.clip(low, high)
        if np.isclose(high, low):
            scaled = pd.Series(50.0, index=series.index)
        else:
            scaled = (clipped - low) / (high - low) * 100.0
    return 100.0 - scaled if invert else scaled


def health_band(score: float, bands: list[dict[str, Any]]) -> str:
    """Map a score to the configured health band."""
    for band in bands:
        if score >= float(band["minimum"]):
            return str(band["label"])
    return "Poor"


def compute_health_scores(
    settings: Settings,
    ratios: pd.DataFrame,
    companies: pd.DataFrame,
    sectors: pd.DataFrame,
) -> pd.DataFrame:
    """Compute latest-year health scores for the complete master universe."""
    config = _read_analytics_config(settings.project_root)
    latest = (
        ratios.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
    )
    data = companies[["company_id"]].merge(
        sectors[["company_id", "broad_sector"]], on="company_id", how="left"
    )
    data = data.merge(latest, on="company_id", how="left")
    data["year"] = data["year"].fillna("N/A")
    lower = float(config["winsor"]["lower_quantile"])
    upper = float(config["winsor"]["upper_quantile"])

    component_scores: dict[str, pd.Series] = {}
    for component, metrics in COMPONENT_METRICS.items():
        scaled_metrics: list[pd.Series] = []
        for metric, invert in metrics:
            values = pd.to_numeric(data[metric], errors="coerce")
            sector_median = values.groupby(data["broad_sector"]).transform("median")
            values = values.fillna(sector_median).fillna(values.median()).fillna(0.0)
            scaled_metrics.append(winsorised_scale(values, lower, upper, invert=invert))
        component_scores[component] = pd.concat(scaled_metrics, axis=1).mean(axis=1)
        data[f"{component}_score"] = component_scores[component]

    total_weight = sum(settings.health_weights.values())
    data["health_score"] = (
        sum(
            data[f"{component}_score"] * weight
            for component, weight in settings.health_weights.items()
        )
        / total_weight
    )
    data["health_score"] = data["health_score"].clip(0.0, 100.0).round(2)
    data["health_band"] = data["health_score"].map(
        lambda score: health_band(score, config["health_bands"])
    )
    output = data[
        [
            "company_id",
            "year",
            "profitability_score",
            "cash_quality_score",
            "growth_score",
            "leverage_score",
            "health_score",
            "health_band",
        ]
    ].copy()
    score_columns = [column for column in output.columns if column.endswith("_score")]
    output[score_columns] = output[score_columns].round(2)
    return output.sort_values("health_score", ascending=False).reset_index(drop=True)


def run_health_scores(
    settings: Settings,
    ratios: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Compute, export, and persist financial health scores."""
    scores = compute_health_scores(
        settings, ratios, frames["companies"], frames["sectors"]
    )
    scores.to_csv(settings.output_dir / "health_scores.csv", index=False)
    load_derived_table(settings, "health_scores", scores)
    LOGGER.info(
        "health scores companies=%d bands=%s",
        len(scores),
        scores["health_band"].value_counts().to_dict(),
    )
    return scores
