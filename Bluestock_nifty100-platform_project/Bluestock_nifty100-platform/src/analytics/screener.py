"""Config-driven investment screener with six presets."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.analytics.sector_peer import latest_ratios
from src.config.settings import Settings
from src.reports.exports import write_formatted_workbook

LOGGER = logging.getLogger(__name__)


def load_screener_config(path: Path) -> dict[str, Any]:
    """Load screener presets from YAML."""
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def _condition_mask(data: pd.DataFrame, condition: dict[str, Any]) -> pd.Series:
    """Evaluate one declarative screener condition."""
    field = condition["field"]
    operation = condition["op"]
    value = condition["value"]
    if field not in data.columns:
        return pd.Series(False, index=data.index)
    series = data[field]
    operations = {
        "gte": lambda: series >= value,
        "gt": lambda: series > value,
        "lte": lambda: series <= value,
        "lt": lambda: series < value,
        "eq": lambda: series == value,
        "in": lambda: series.isin(value),
    }
    if operation not in operations:
        raise ValueError(f"unsupported screener operation: {operation}")
    return operations[operation]().fillna(False)


def apply_preset(data: pd.DataFrame, conditions: list[dict[str, Any]]) -> pd.DataFrame:
    """Return rows satisfying every condition in one preset."""
    mask = pd.Series(True, index=data.index)
    for condition in conditions:
        mask &= _condition_mask(data, condition)
    return data.loc[mask].sort_values("composite_ranking_score", ascending=False)


def build_screener_universe(
    ratios: pd.DataFrame,
    health_scores: pd.DataFrame,
    valuation: pd.DataFrame,
    sectors: pd.DataFrame,
) -> pd.DataFrame:
    """Assemble the latest company-level screener universe."""
    latest = latest_ratios(ratios)
    data = latest.merge(health_scores, on=["company_id", "year"], how="left")
    data = data.merge(
        valuation[
            [
                "company_id",
                "pe_ratio",
                "pb_ratio",
                "ev_ebitda",
                "dividend_yield_pct",
                "valuation_flag",
            ]
        ],
        on="company_id",
        how="left",
    ).merge(
        sectors[["company_id", "broad_sector", "sub_sector"]],
        on="company_id",
        how="left",
    )
    quality = data[
        [
            "return_on_equity_pct",
            "operating_profit_margin_pct",
            "revenue_cagr_3y",
            "fcf_conversion_pct",
        ]
    ].rank(pct=True)
    leverage = data["debt_to_equity"].rank(pct=True, ascending=False)
    data["composite_ranking_score"] = (
        data["health_score"] * 0.50
        + quality.mean(axis=1).fillna(0.50) * 40.0
        + leverage.fillna(0.50) * 10.0
    ).round(2)
    return data.sort_values("composite_ranking_score", ascending=False)


def _slug(value: str) -> str:
    """Convert a preset label into a safe file stem."""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def run_screener(
    settings: Settings,
    ratios: pd.DataFrame,
    health_scores: pd.DataFrame,
    valuation: pd.DataFrame,
    sectors: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Run all six presets and export CSV and Excel deliverables."""
    universe = build_screener_universe(ratios, health_scores, valuation, sectors)
    config = load_screener_config(
        settings.project_root / "config" / "screener_config.yaml"
    )
    results: dict[str, pd.DataFrame] = {}
    summary_rows: list[dict[str, Any]] = []
    for name, conditions in config["presets"].items():
        result = apply_preset(universe, conditions)
        results[name] = result
        result.to_csv(settings.output_dir / f"screener_{_slug(name)}.csv", index=False)
        summary_rows.append(
            {
                "preset": name,
                "company_count": len(result),
                "conditions": len(conditions),
            }
        )
    summary = pd.DataFrame(summary_rows)
    sheets = {"Summary": summary, "Universe": universe, **results}
    write_formatted_workbook(
        settings.output_dir / "screener_output.xlsx",
        sheets,
        conditional_columns={
            "Universe": ["health_score", "composite_ranking_score"],
            **{name: ["health_score", "composite_ranking_score"] for name in results},
        },
    )
    universe.to_csv(settings.output_dir / "screener_universe.csv", index=False)
    LOGGER.info(
        "screener counts=%s", summary.set_index("preset")["company_count"].to_dict()
    )
    return universe, results
