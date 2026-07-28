"""Sector benchmarks and intra-peer percentile analytics."""

from __future__ import annotations

import logging

import pandas as pd

from src.config.settings import Settings
from src.database.sqlite_loader import load_derived_table

LOGGER = logging.getLogger(__name__)


def latest_ratios(ratios: pd.DataFrame) -> pd.DataFrame:
    """Return the latest available ratio row per company."""
    return (
        ratios.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )


def compute_sector_benchmarks(
    ratios: pd.DataFrame, health_scores: pd.DataFrame, sectors: pd.DataFrame
) -> pd.DataFrame:
    """Compute median KPI benchmarks for the observed broad sectors."""
    latest = latest_ratios(ratios).merge(
        health_scores[["company_id", "health_score"]],
        on="company_id",
        how="left",
    )
    data = sectors[["company_id", "broad_sector"]].merge(
        latest, on="company_id", how="left"
    )
    grouped = (
        data.groupby("broad_sector", as_index=False)
        .agg(
            company_count=("company_id", "nunique"),
            median_roe=("return_on_equity_pct", "median"),
            median_npm=("net_profit_margin_pct", "median"),
            median_opm=("operating_profit_margin_pct", "median"),
            median_debt_to_equity=("debt_to_equity", "median"),
            median_revenue_cagr_3y=("revenue_cagr_3y", "median"),
            median_fcf_conversion=("fcf_conversion_pct", "median"),
            median_health_score=("health_score", "median"),
        )
        .sort_values("median_health_score", ascending=False)
        .reset_index(drop=True)
    )
    grouped["sector_rank"] = (
        grouped["median_health_score"].rank(method="dense", ascending=False).astype(int)
    )
    return grouped


def compute_peer_percentiles(
    ratios: pd.DataFrame, peer_groups: pd.DataFrame
) -> pd.DataFrame:
    """Rank each peer-group member with the correct metric direction."""
    latest = latest_ratios(ratios)
    data = peer_groups[["peer_group_name", "company_id"]].merge(
        latest,
        on="company_id",
        how="left",
        validate="many_to_one",
    )
    directions = {
        "return_on_equity_pct": ("roe_percentile", True),
        "operating_profit_margin_pct": ("opm_percentile", True),
        "revenue_cagr_3y": ("revenue_growth_percentile", True),
        "fcf_conversion_pct": ("fcf_conversion_percentile", True),
        "debt_to_equity": ("debt_to_equity_percentile", False),
    }
    for source, (target, higher_is_better) in directions.items():
        data[target] = data.groupby("peer_group_name")[source].rank(
            pct=True, method="average", ascending=higher_is_better
        )
    percentile_columns = [target for target, _ in directions.values()]
    data["composite_percentile"] = data[percentile_columns].mean(axis=1)
    return data[
        ["peer_group_name", "company_id", *percentile_columns, "composite_percentile"]
    ].sort_values(["peer_group_name", "composite_percentile"], ascending=[True, False])


def run_sector_peer(
    settings: Settings,
    ratios: pd.DataFrame,
    health_scores: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute, export, and persist sector and peer outputs."""
    sectors = compute_sector_benchmarks(ratios, health_scores, frames["sectors"])
    peers = compute_peer_percentiles(ratios, frames["peer_groups"])
    sectors.to_csv(settings.output_dir / "sector_benchmarks.csv", index=False)
    peers.to_csv(settings.output_dir / "peer_percentiles.csv", index=False)
    load_derived_table(settings, "sector_benchmarks", sectors)
    load_derived_table(settings, "peer_percentiles", peers)
    LOGGER.info(
        "sector benchmarks=%d peer_groups=%d peer_rows=%d",
        len(sectors),
        peers["peer_group_name"].nunique(),
        len(peers),
    )
    return sectors, peers
