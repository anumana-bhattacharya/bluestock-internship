"""Latest-year valuation analytics and sector-relative flags."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.analytics.ratios import safe_divide
from src.analytics.sector_peer import latest_ratios
from src.config.settings import Settings
from src.database.sqlite_loader import load_derived_table
from src.reports.exports import write_formatted_workbook

LOGGER = logging.getLogger(__name__)


def _valuation_config(project_root: Path) -> dict[str, Any]:
    """Read valuation thresholds from analytics YAML."""
    with (project_root / "config" / "analytics.yaml").open(encoding="utf-8") as file:
        return yaml.safe_load(file)["valuation"]


def valuation_flag(
    pe_ratio: float | None,
    sector_median: float | None,
    caution_multiple: float,
    discount_multiple: float,
) -> str:
    """Classify P/E relative to sector median."""
    if (
        pe_ratio is None
        or sector_median is None
        or pd.isna(pe_ratio)
        or pd.isna(sector_median)
    ):
        return "Unavailable"
    if pe_ratio > sector_median * caution_multiple:
        return "Caution"
    if pe_ratio < sector_median * discount_multiple:
        return "Discount"
    return "Fair"


def compute_valuation(
    settings: Settings,
    ratios: pd.DataFrame,
    market_cap: pd.DataFrame,
    sectors: pd.DataFrame,
) -> pd.DataFrame:
    """Compute valuation summary for all companies using latest simulated values."""
    market = (
        market_cap.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
    )
    latest = latest_ratios(ratios)[["company_id", "free_cash_flow_cr"]]
    data = market.merge(latest, on="company_id", how="left").merge(
        sectors[["company_id", "broad_sector"]], on="company_id", how="left"
    )
    data["fcf_yield_pct"] = data.apply(
        lambda row: safe_divide(
            row["free_cash_flow_cr"], row["market_cap_crore"], multiplier=100.0
        ),
        axis=1,
    )
    data["sector_median_pe"] = data.groupby("broad_sector")["pe_ratio"].transform(
        "median"
    )
    config = _valuation_config(settings.project_root)
    data["valuation_flag"] = data.apply(
        lambda row: valuation_flag(
            row["pe_ratio"],
            row["sector_median_pe"],
            float(config["caution_multiple"]),
            float(config["discount_multiple"]),
        ),
        axis=1,
    )
    return data[
        [
            "company_id",
            "year",
            "broad_sector",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield_pct",
            "fcf_yield_pct",
            "sector_median_pe",
            "valuation_flag",
        ]
    ].sort_values(["broad_sector", "pe_ratio"])


def run_valuation(
    settings: Settings,
    ratios: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Compute, export, and persist valuation analytics."""
    valuation = compute_valuation(
        settings, ratios, frames["market_cap"], frames["sectors"]
    )
    valuation.to_csv(settings.output_dir / "valuation_flags.csv", index=False)
    write_formatted_workbook(
        settings.output_dir / "valuation_summary.xlsx",
        {"Valuation Summary": valuation},
        conditional_columns={"Valuation Summary": ["pe_ratio", "fcf_yield_pct"]},
    )
    load_derived_table(settings, "valuation_summary", valuation)
    LOGGER.info(
        "valuation companies=%d flags=%s",
        len(valuation),
        valuation["valuation_flag"].value_counts().to_dict(),
    )
    return valuation
