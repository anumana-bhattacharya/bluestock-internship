"""Raw-statement financial ratio engine and cross-validation."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from src.analytics.cagr import calculate_cagr
from src.analytics.ratios import (
    as_number,
    capital_allocation_label,
    interest_coverage,
    margin,
    price_to_earnings,
    return_on_equity,
    safe_divide,
)
from src.config.settings import Settings
from src.database.sqlite_loader import load_derived_table

LOGGER = logging.getLogger(__name__)
CAGR_HORIZONS = (3, 5, 10)
CAGR_INPUTS = {
    "revenue": "sales",
    "pat": "net_profit",
    "eps": "eps",
}


def _sum_values(*values: Any) -> float | None:
    """Sum finite values, returning None if every input is missing."""
    numeric = [as_number(value) for value in values]
    present = [value for value in numeric if value is not None]
    return sum(present) if present else None


def _row_ratios(row: pd.Series) -> dict[str, Any]:
    """Compute non-growth KPIs for one aligned company-period row."""
    sales = as_number(row.get("sales"))
    net_profit = as_number(row.get("net_profit"))
    operating_profit = as_number(row.get("operating_profit"))
    interest = as_number(row.get("interest"))
    depreciation = as_number(row.get("depreciation"))
    pbt = as_number(row.get("profit_before_tax"))
    equity = _sum_values(row.get("equity_capital"), row.get("reserves"))
    borrowings = as_number(row.get("borrowings"))
    investments = as_number(row.get("investments"))
    total_assets = as_number(row.get("total_assets"))
    fixed_assets = as_number(row.get("fixed_assets"))
    cfo = as_number(row.get("operating_activity"))
    cfi = as_number(row.get("investing_activity"))
    cff = as_number(row.get("financing_activity"))
    ebit = _sum_values(pbt, interest)
    ebitda = _sum_values(ebit, depreciation)
    capital_employed = _sum_values(equity, borrowings)
    capex = abs(min(cfi, 0.0)) if cfi is not None else None
    fcf = cfo - capex if cfo is not None and capex is not None else None
    net_debt = (
        borrowings - investments
        if borrowings is not None and investments is not None
        else borrowings
    )
    icr, icr_status = interest_coverage(ebit, interest)
    shares_crore = safe_divide(row.get("equity_capital"), row.get("face_value"))
    book_value_per_share = (
        safe_divide(equity, shares_crore) if shares_crore is not None else None
    )
    market_cap = as_number(row.get("market_cap_crore"))
    enterprise_value = as_number(row.get("enterprise_value_crore"))

    return {
        "net_profit_margin_pct": margin(net_profit, sales),
        "operating_profit_margin_pct": margin(operating_profit, sales),
        "ebit_margin_pct": margin(ebit, sales),
        "return_on_equity_pct": return_on_equity(net_profit, equity),
        "return_on_capital_employed_pct": (
            safe_divide(ebit, capital_employed, multiplier=100.0)
            if capital_employed is not None and capital_employed > 0
            else None
        ),
        "return_on_assets_pct": (
            safe_divide(net_profit, total_assets, multiplier=100.0)
            if total_assets is not None and total_assets > 0
            else None
        ),
        "debt_to_equity": (
            safe_divide(borrowings, equity)
            if equity is not None and equity > 0
            else None
        ),
        "interest_coverage": icr,
        "interest_coverage_status": icr_status,
        "net_debt_cr": net_debt,
        "net_debt_to_ebitda": (
            safe_divide(net_debt, ebitda) if ebitda is not None and ebitda > 0 else None
        ),
        "asset_turnover": (
            safe_divide(sales, total_assets)
            if total_assets is not None and total_assets > 0
            else None
        ),
        "fixed_asset_turnover": (
            safe_divide(sales, fixed_assets)
            if fixed_assets is not None and fixed_assets > 0
            else None
        ),
        "free_cash_flow_cr": fcf,
        "cfo_to_pat": safe_divide(cfo, net_profit),
        "capex_intensity_pct": margin(capex, sales),
        "fcf_conversion_pct": safe_divide(fcf, net_profit, multiplier=100.0),
        "book_value_per_share": book_value_per_share,
        "earnings_per_share": as_number(row.get("eps")),
        "dividend_payout_ratio_pct": as_number(row.get("dividend_payout")),
        "price_to_earnings": price_to_earnings(market_cap, net_profit),
        "price_to_book": (
            safe_divide(market_cap, equity)
            if equity is not None and equity > 0
            else None
        ),
        "ev_to_ebitda": (
            safe_divide(enterprise_value, ebitda)
            if ebitda is not None and ebitda > 0
            else None
        ),
        "fcf_yield_pct": safe_divide(fcf, market_cap, multiplier=100.0),
        "capital_allocation_label": capital_allocation_label(cfo, cfi, cff),
    }


def _add_cagrs(frame: pd.DataFrame) -> pd.DataFrame:
    """Add 3/5/10-year revenue, PAT, and EPS CAGR values and flags."""
    data = frame.sort_values(["company_id", "year"]).copy()
    for metric in CAGR_INPUTS:
        for horizon in CAGR_HORIZONS:
            data[f"{metric}_cagr_{horizon}y"] = np.nan
            data[f"{metric}_cagr_{horizon}y_flag"] = "INSUFFICIENT"
    for _, group in data.groupby("company_id", sort=False):
        indices = list(group.index)
        for position, index in enumerate(indices):
            for metric, source in CAGR_INPUTS.items():
                for horizon in CAGR_HORIZONS:
                    observations = position + 1
                    base = (
                        data.at[indices[position - horizon], source]
                        if position >= horizon
                        else None
                    )
                    result = calculate_cagr(
                        base,
                        data.at[index, source],
                        horizon,
                        observations,
                    )
                    data.at[index, f"{metric}_cagr_{horizon}y"] = result.value
                    data.at[index, f"{metric}_cagr_{horizon}y_flag"] = result.flag
    return data


def _edge_cases(frame: pd.DataFrame) -> pd.DataFrame:
    """Materialize formula and CAGR edge cases for audit."""
    rows: list[dict[str, Any]] = []
    for row in frame.itertuples(index=False):
        record = row._asdict()
        if record["return_on_equity_pct"] is None or pd.isna(
            record["return_on_equity_pct"]
        ):
            rows.append(
                {
                    "company_id": record["company_id"],
                    "year": record["year"],
                    "metric": "return_on_equity_pct",
                    "flag": "NON_POSITIVE_OR_MISSING_EQUITY",
                }
            )
        if record["interest_coverage_status"] != "Levered":
            rows.append(
                {
                    "company_id": record["company_id"],
                    "year": record["year"],
                    "metric": "interest_coverage",
                    "flag": record["interest_coverage_status"],
                }
            )
        for metric in CAGR_INPUTS:
            for horizon in CAGR_HORIZONS:
                flag = record[f"{metric}_cagr_{horizon}y_flag"]
                if flag != "OK":
                    rows.append(
                        {
                            "company_id": record["company_id"],
                            "year": record["year"],
                            "metric": f"{metric}_cagr_{horizon}y",
                            "flag": flag,
                        }
                    )
    return pd.DataFrame(rows, columns=["company_id", "year", "metric", "flag"])


def compute_ratios(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute 30+ raw-derived and market-cap-joined KPIs."""
    pl = frames["profit_and_loss"].copy()
    bs_columns = [
        "company_id",
        "year",
        "equity_capital",
        "reserves",
        "borrowings",
        "fixed_assets",
        "investments",
        "total_assets",
    ]
    cf_columns = [
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
    ]
    data = pl.merge(
        frames["balance_sheet"][bs_columns],
        on=["company_id", "year"],
        how="left",
        validate="one_to_one",
    ).merge(
        frames["cash_flow"][cf_columns],
        on=["company_id", "year"],
        how="left",
        validate="one_to_one",
    )
    data = data.merge(
        frames["companies"][["company_id", "face_value"]],
        on="company_id",
        how="left",
        validate="many_to_one",
    )
    data["calendar_year"] = data["year"].str.slice(0, 4).astype(int)
    market_columns = [
        "company_id",
        "year",
        "market_cap_crore",
        "enterprise_value_crore",
    ]
    market = frames["market_cap"][market_columns].rename(
        columns={"year": "calendar_year"}
    )
    data = data.merge(
        market,
        on=["company_id", "calendar_year"],
        how="left",
        validate="many_to_one",
    )
    data = _add_cagrs(data)
    calculated = pd.DataFrame(
        [_row_ratios(row) for _, row in data.iterrows()], index=data.index
    )
    output = pd.concat([data[["company_id", "year"]], calculated], axis=1)
    for metric in CAGR_INPUTS:
        for horizon in CAGR_HORIZONS:
            output[f"{metric}_cagr_{horizon}y"] = data[f"{metric}_cagr_{horizon}y"]
            output[f"{metric}_cagr_{horizon}y_flag"] = data[
                f"{metric}_cagr_{horizon}y_flag"
            ]
    ordered = [
        "company_id",
        "year",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "ebit_margin_pct",
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "return_on_assets_pct",
        "debt_to_equity",
        "interest_coverage",
        "interest_coverage_status",
        "net_debt_cr",
        "net_debt_to_ebitda",
        "asset_turnover",
        "fixed_asset_turnover",
        "free_cash_flow_cr",
        "cfo_to_pat",
        "capex_intensity_pct",
        "fcf_conversion_pct",
        "book_value_per_share",
        "earnings_per_share",
        "dividend_payout_ratio_pct",
    ]
    for metric in CAGR_INPUTS:
        for horizon in CAGR_HORIZONS:
            ordered.extend(
                [f"{metric}_cagr_{horizon}y", f"{metric}_cagr_{horizon}y_flag"]
            )
    ordered.extend(
        [
            "price_to_earnings",
            "price_to_book",
            "ev_to_ebitda",
            "fcf_yield_pct",
            "capital_allocation_label",
        ]
    )
    return output[ordered].sort_values(["company_id", "year"]).reset_index(drop=True)


def cross_validate(
    computed: pd.DataFrame, reference: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cross-check computed NPM and ROE against the supplied reference."""
    joined = computed.merge(
        reference[
            [
                "company_id",
                "year",
                "net_profit_margin_pct",
                "return_on_equity_pct",
            ]
        ],
        on=["company_id", "year"],
        suffixes=("_computed", "_reference"),
        how="inner",
    )
    joined["npm_abs_divergence"] = (
        joined["net_profit_margin_pct_computed"]
        - joined["net_profit_margin_pct_reference"]
    ).abs()
    joined["roe_abs_divergence"] = (
        joined["return_on_equity_pct_computed"]
        - joined["return_on_equity_pct_reference"]
    ).abs()
    summary = pd.DataFrame(
        [
            {
                "matched_rows": len(joined),
                "npm_mean_absolute_divergence": joined["npm_abs_divergence"].mean(),
                "roe_mean_absolute_divergence": joined["roe_abs_divergence"].mean(),
                "combined_mean_absolute_divergence": joined[
                    ["npm_abs_divergence", "roe_abs_divergence"]
                ]
                .stack()
                .mean(),
            }
        ]
    )
    return joined, summary


def run_ratio_engine(
    settings: Settings, frames: dict[str, pd.DataFrame]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run KPI computation, persistence, cross-check, and audit exports."""
    ratios = compute_ratios(frames)
    crosscheck, summary = cross_validate(ratios, frames["financial_ratios_reference"])
    edges = _edge_cases(ratios)
    capital = ratios[["company_id", "year", "capital_allocation_label"]].copy()
    ratios.to_csv(settings.output_dir / "computed_ratios.csv", index=False)
    capital.to_csv(settings.output_dir / "capital_allocation.csv", index=False)
    edges.to_csv(settings.output_dir / "ratio_edge_cases.csv", index=False)
    crosscheck.to_csv(settings.output_dir / "ratio_crosscheck.csv", index=False)
    summary.to_csv(settings.output_dir / "ratio_crosscheck_summary.csv", index=False)
    load_derived_table(settings, "computed_ratios", ratios)
    LOGGER.info(
        "computed ratios rows=%d companies=%d divergence=%.6f",
        len(ratios),
        ratios["company_id"].nunique(),
        summary.at[0, "combined_mean_absolute_divergence"],
    )
    return ratios, summary
