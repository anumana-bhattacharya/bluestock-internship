"""Regex parsing and ratio-engine cross-validation for analysis narratives."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

ANALYSIS_PATTERN = re.compile(r"(\d+)\s*Years?:?\s*([\d.]+)%", re.IGNORECASE)
METRIC_COLUMNS = (
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
)
PARSED_COLUMNS = ("company_id", "metric_type", "period_years", "value_pct")
FAILURE_COLUMNS = ("company_id", "metric_type", "source_text", "issue")


@dataclass(frozen=True)
class AnalysisParseResult:
    """Hold tidy observations and non-matching source cells."""

    parsed: pd.DataFrame
    failures: pd.DataFrame


def parse_metric_text(value: object) -> list[tuple[int, float]]:
    """Extract every (years, percentage) pair from a narrative cell."""
    if value is None or pd.isna(value):
        return []
    compact = " ".join(str(value).split())
    return [
        (int(years), float(percent))
        for years, percent in ANALYSIS_PATTERN.findall(compact)
    ]


def parse_analysis_with_failures(frame: pd.DataFrame) -> AnalysisParseResult:
    """Convert wide analysis narratives and retain every non-matching cell."""
    rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for row in frame.itertuples(index=False):
        values = row._asdict()
        company_id = str(values["company_id"])
        for metric in METRIC_COLUMNS:
            source = values.get(metric)
            if source is None or pd.isna(source) or not str(source).strip():
                continue
            matches = parse_metric_text(source)
            if not matches:
                failures.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric,
                        "source_text": " ".join(str(source).split()),
                        "issue": "NO_REGEX_MATCH",
                    }
                )
                continue
            rows.extend(
                {
                    "company_id": company_id,
                    "metric_type": metric,
                    "period_years": years,
                    "value_pct": percentage,
                }
                for years, percentage in matches
            )
    parsed = pd.DataFrame(rows, columns=PARSED_COLUMNS).drop_duplicates(
        ["company_id", "metric_type", "period_years"], keep="last"
    )
    return AnalysisParseResult(
        parsed=parsed.reset_index(drop=True),
        failures=pd.DataFrame(failures, columns=FAILURE_COLUMNS),
    )


def parse_analysis(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert wide analysis narratives into tidy parsed observations."""
    return parse_analysis_with_failures(frame).parsed


def cross_validate_parsed_cagrs(
    parsed: pd.DataFrame,
    ratios: pd.DataFrame,
    divergence_threshold_pct: float = 5.0,
) -> pd.DataFrame:
    """Compare parsed growth CAGRs with computed latest-period ratios."""
    columns = (
        "company_id",
        "metric_type",
        "period_years",
        "parsed_value_pct",
        "computed_value_pct",
        "divergence_pct",
        "manual_review_flag",
        "validation_status",
    )
    if parsed.empty:
        return pd.DataFrame(columns=columns)
    latest = (
        ratios.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
        .set_index("company_id")
    )
    metric_prefix = {
        "compounded_sales_growth": "revenue",
        "compounded_profit_growth": "pat",
    }
    rows: list[dict[str, object]] = []
    for record in parsed.to_dict("records"):
        prefix = metric_prefix.get(str(record["metric_type"]))
        horizon = int(record["period_years"])
        computed: float | None = None
        status = "NOT_COMPARABLE"
        if prefix is not None and horizon in {3, 5, 10}:
            column = f"{prefix}_cagr_{horizon}y"
            if record["company_id"] in latest.index and column in latest:
                value = pd.to_numeric(
                    pd.Series([latest.at[record["company_id"], column]]),
                    errors="coerce",
                ).iloc[0]
                if pd.notna(value):
                    computed = float(value)
                    status = "COMPARED"
                else:
                    status = "COMPUTED_VALUE_UNAVAILABLE"
        divergence = (
            abs(float(record["value_pct"]) - computed) if computed is not None else None
        )
        rows.append(
            {
                "company_id": record["company_id"],
                "metric_type": record["metric_type"],
                "period_years": horizon,
                "parsed_value_pct": record["value_pct"],
                "computed_value_pct": computed,
                "divergence_pct": divergence,
                "manual_review_flag": bool(
                    divergence is not None
                    and divergence > float(divergence_threshold_pct)
                ),
                "validation_status": status,
            }
        )
    return pd.DataFrame(rows, columns=columns)
