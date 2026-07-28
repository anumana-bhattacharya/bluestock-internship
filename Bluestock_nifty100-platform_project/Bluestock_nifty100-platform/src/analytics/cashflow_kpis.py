"""Sprint 5 cash-flow quality, intensity, distress, and allocation analytics."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.analytics.cagr import calculate_cagr
from src.analytics.ratios import safe_divide
from src.config.settings import Settings
from src.database.sqlite_loader import load_derived_table
from src.reports.exports import write_formatted_workbook

LOGGER = logging.getLogger(__name__)
REQUIRED_COLUMNS = (
    "company_id",
    "sector",
    "cfo_quality_score",
    "cfo_quality_label",
    "capex_intensity_pct",
    "capex_label",
    "fcf_cagr_5yr",
    "fcf_conversion_pct",
    "distress_flag",
    "deleveraging_flag",
    "capital_allocation_label",
)
ALLOCATION_PATTERNS = (
    "SELF_FUNDED_REINVESTMENT",
    "EXPANSION_WITH_EXTERNAL_CAPITAL",
    "ASSET_MONETISATION_AND_DELEVERAGING",
    "CASH_ACCUMULATION",
    "CASH_BURN_AND_CONTRACTION",
    "EXTERNALLY_FUNDED_INVESTMENT",
    "ASSET_SALES_FUNDING_OPERATIONS",
    "RESTRUCTURING_WITH_EXTERNAL_SUPPORT",
)


def _cashflow_config(project_root: Path) -> dict[str, Any]:
    """Read cash-flow thresholds from analytics YAML."""
    with (project_root / "config" / "analytics.yaml").open(encoding="utf-8") as file:
        return yaml.safe_load(file)["cashflow"]


def cfo_quality_label(
    score: float | None, high_quality_min: float, moderate_min: float
) -> str:
    """Classify the five-year average CFO/PAT ratio."""
    if score is None or pd.isna(score):
        return "No Data"
    if score > high_quality_min:
        return "High Quality"
    if score >= moderate_min:
        return "Moderate"
    return "Accrual Risk"


def capex_label(
    intensity: float | None, asset_light_max: float, moderate_max: float
) -> str:
    """Classify latest CapEx intensity using the required 3% and 8% bands."""
    if intensity is None or pd.isna(intensity):
        return "No Data"
    if intensity < asset_light_max:
        return "Asset Light"
    if intensity <= moderate_max:
        return "Moderate"
    return "Capital Intensive"


def _latest(frame: pd.DataFrame) -> pd.Series:
    """Return the latest row from a company history."""
    return frame.sort_values("year").iloc[-1] if not frame.empty else pd.Series()


def _fcf_cagr(history: pd.DataFrame, years: int) -> float | None:
    """Compute FCF CAGR across the requested observed-year window."""
    values = (
        history.sort_values("year")["free_cash_flow_cr"].dropna()
        if not history.empty
        else pd.Series(dtype=float)
    )
    observations = years + 1
    if len(values) < observations:
        return None
    result = calculate_cagr(
        values.iloc[-observations], values.iloc[-1], years, observations
    )
    return result.value


def _pattern_outputs(
    ratios: pd.DataFrame,
    companies: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build latest pattern distribution and year-over-year changes."""
    latest = (
        ratios.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
    )
    counts = latest["capital_allocation_label"].value_counts().to_dict()
    distribution = pd.DataFrame(
        [
            {
                "capital_allocation_label": label,
                "company_count": int(counts.get(label, 0)),
            }
            for label in ALLOCATION_PATTERNS
        ]
    )
    if counts.get("NO_DATA", 0):
        distribution.loc[len(distribution)] = {
            "capital_allocation_label": "NO_DATA",
            "company_count": int(counts["NO_DATA"]),
        }
    changes: list[dict[str, object]] = []
    for company_id in companies["company_id"].astype(str):
        history = ratios.loc[ratios["company_id"].eq(company_id)].sort_values("year")
        if len(history) < 2:
            continue
        previous, current = history.iloc[-2], history.iloc[-1]
        if previous["capital_allocation_label"] != current["capital_allocation_label"]:
            changes.append(
                {
                    "company_id": company_id,
                    "previous_year": previous["year"],
                    "previous_pattern": previous["capital_allocation_label"],
                    "latest_year": current["year"],
                    "latest_pattern": current["capital_allocation_label"],
                }
            )
    return distribution, pd.DataFrame(
        changes,
        columns=[
            "company_id",
            "previous_year",
            "previous_pattern",
            "latest_year",
            "latest_pattern",
        ],
    )


def compute_cashflow_kpis(
    settings: Settings,
    ratios: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compute full-universe cash-flow intelligence and supporting reports."""
    config = _cashflow_config(settings.project_root)
    ratio_groups = {
        company_id: group.sort_values("year")
        for company_id, group in ratios.groupby("company_id")
    }
    cf_groups = {
        company_id: group.sort_values("year")
        for company_id, group in frames["cash_flow"].groupby("company_id")
    }
    pl_groups = {
        company_id: group.sort_values("year")
        for company_id, group in frames["profit_and_loss"].groupby("company_id")
    }
    bs_groups = {
        company_id: group.sort_values("year")
        for company_id, group in frames["balance_sheet"].groupby("company_id")
    }
    sector_map = frames["sectors"].set_index("company_id")["broad_sector"].to_dict()
    rows: list[dict[str, object]] = []
    alerts: list[dict[str, object]] = []
    for company_id in frames["companies"]["company_id"].astype(str):
        ratio_history = ratio_groups.get(company_id, pd.DataFrame())
        cf_history = cf_groups.get(company_id, pd.DataFrame())
        pl_history = pl_groups.get(company_id, pd.DataFrame())
        bs_history = bs_groups.get(company_id, pd.DataFrame())
        latest_ratio = _latest(ratio_history)
        latest_cf = _latest(cf_history)
        joined = (
            cf_history[
                ["company_id", "year", "operating_activity", "investing_activity"]
            ].merge(
                pl_history[["company_id", "year", "sales", "net_profit"]],
                on=["company_id", "year"],
                how="inner",
            )
            if not cf_history.empty and not pl_history.empty
            else pd.DataFrame()
        )
        latest_common = _latest(joined)
        quality_values = pd.to_numeric(
            (
                ratio_history.sort_values("year").tail(5)["cfo_to_pat"]
                if not ratio_history.empty
                else pd.Series(dtype=float)
            ),
            errors="coerce",
        ).dropna()
        quality_score = (
            float(quality_values.mean()) if not quality_values.empty else None
        )
        intensity = (
            safe_divide(
                abs(float(latest_common["investing_activity"])),
                latest_common["sales"],
                multiplier=100.0,
            )
            if not latest_common.empty
            and pd.notna(latest_common.get("investing_activity"))
            else None
        )
        cfo = (
            None
            if latest_cf.empty
            else pd.to_numeric(
                pd.Series([latest_cf.get("operating_activity")]), errors="coerce"
            ).iloc[0]
        )
        cff = (
            None
            if latest_cf.empty
            else pd.to_numeric(
                pd.Series([latest_cf.get("financing_activity")]), errors="coerce"
            ).iloc[0]
        )
        distress = bool(pd.notna(cfo) and pd.notna(cff) and cfo < 0 and cff > 0)
        latest_bs = (
            bs_history.sort_values("year").tail(2)
            if not bs_history.empty
            else pd.DataFrame()
        )
        borrowings = pd.to_numeric(
            latest_bs["borrowings"] if not latest_bs.empty else pd.Series(dtype=float),
            errors="coerce",
        ).dropna()
        deleveraging = bool(
            pd.notna(cff)
            and cff < 0
            and len(borrowings) == 2
            and borrowings.iloc[-1] < borrowings.iloc[-2]
        )
        row = {
            "company_id": company_id,
            "sector": sector_map.get(company_id, "Unknown"),
            "cfo_quality_score": quality_score,
            "cfo_quality_label": cfo_quality_label(
                quality_score,
                float(config["cfo_high_quality_min"]),
                float(config["cfo_moderate_min"]),
            ),
            "capex_intensity_pct": intensity,
            "capex_label": capex_label(
                intensity,
                float(config["capex_asset_light_max_pct"]),
                float(config["capex_moderate_max_pct"]),
            ),
            "fcf_cagr_5yr": _fcf_cagr(ratio_history, int(config["cagr_years"])),
            "fcf_conversion_pct": latest_ratio.get("fcf_conversion_pct"),
            "distress_flag": distress,
            "deleveraging_flag": deleveraging,
            "capital_allocation_label": latest_ratio.get(
                "capital_allocation_label", "NO_DATA"
            ),
        }
        rows.append(row)
        if distress:
            matching_profit = pl_history.loc[
                pl_history["year"].eq(latest_cf.get("year")), "net_profit"
            ]
            alerts.append(
                {
                    "company_id": company_id,
                    "year": latest_cf.get("year"),
                    "cfo_value_cr": float(cfo),
                    "cff_value_cr": float(cff),
                    "latest_net_profit_cr": (
                        float(matching_profit.iloc[-1])
                        if not matching_profit.empty
                        and pd.notna(matching_profit.iloc[-1])
                        else None
                    ),
                }
            )
    intelligence = pd.DataFrame(rows, columns=REQUIRED_COLUMNS)
    distress_alerts = pd.DataFrame(
        alerts,
        columns=[
            "company_id",
            "year",
            "cfo_value_cr",
            "cff_value_cr",
            "latest_net_profit_cr",
        ],
    )
    distribution, changes = _pattern_outputs(ratios, frames["companies"])
    return intelligence, distress_alerts, distribution, changes


def run_cashflow_kpis(
    settings: Settings,
    ratios: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Compute, export, and persist every Sprint 5 cash-flow artifact."""
    intelligence, alerts, distribution, changes = compute_cashflow_kpis(
        settings, ratios, frames
    )
    write_formatted_workbook(
        settings.output_dir / "cashflow_intelligence.xlsx",
        {
            "Cash Flow Intelligence": intelligence,
            "Distress Alerts": alerts,
            "Allocation Distribution": distribution,
            "Pattern Changes": changes,
        },
        conditional_columns={
            "Cash Flow Intelligence": [
                "cfo_quality_score",
                "capex_intensity_pct",
                "fcf_cagr_5yr",
                "fcf_conversion_pct",
            ]
        },
    )
    alerts.to_csv(settings.output_dir / "distress_alerts.csv", index=False)
    distribution.to_csv(
        settings.output_dir / "capital_allocation_distribution.csv", index=False
    )
    changes.to_csv(settings.output_dir / "pattern_changes.csv", index=False)
    load_derived_table(settings, "cashflow_intelligence", intelligence)
    LOGGER.info(
        "cashflow intelligence companies=%d distress=%d pattern_changes=%d",
        len(intelligence),
        len(alerts),
        len(changes),
    )
    return intelligence
