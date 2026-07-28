"""Evidence-based 12-pro/12-con narrative engine with confidence scoring."""

from __future__ import annotations

import logging
from collections.abc import Iterable

import pandas as pd

from src.config.settings import Settings
from src.database.sqlite_loader import load_derived_table
from src.nlp.parser import (
    cross_validate_parsed_cagrs,
    parse_analysis_with_failures,
)

LOGGER = logging.getLogger(__name__)
MIN_CONFIDENCE_EXCLUSIVE = 60.0
FALLBACK_CONFIDENCE = 61.0
FINANCIAL_SECTOR = "Financials"


def _number(value: object) -> float | None:
    """Convert a scalar to float or return None."""
    converted = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(converted) else float(converted)


def _last_values(frame: pd.DataFrame, column: str, count: int) -> list[float]:
    """Return the last numeric values from a chronologically sorted frame."""
    if frame.empty or column not in frame:
        return []
    values = pd.to_numeric(frame.sort_values("year")[column], errors="coerce").dropna()
    return [float(value) for value in values.tail(count)]


def _all_above(values: Iterable[float], threshold: float, count: int) -> bool:
    """Return whether the last required observations all exceed a threshold."""
    observations = list(values)
    return len(observations) == count and all(
        value > threshold for value in observations
    )


def _all_below(values: Iterable[float], threshold: float, count: int) -> bool:
    """Return whether the last required observations all fall below a threshold."""
    observations = list(values)
    return len(observations) == count and all(
        value < threshold for value in observations
    )


def _strict_trend(values: Iterable[float], increasing: bool) -> bool:
    """Return whether values form a strict monotonic trend."""
    observations = list(values)
    if len(observations) < 2:
        return False
    comparisons = zip(observations, observations[1:], strict=False)
    return all(
        right > left if increasing else right < left for left, right in comparisons
    )


def _confidence(base: float, strength: float, cap: float = 99.0) -> float:
    """Translate a positive rule margin into a bounded confidence score."""
    return round(min(cap, max(FALLBACK_CONFIDENCE, base + strength)), 1)


def _append(
    rows: list[dict[str, object]],
    company_id: str,
    kind: str,
    rule_id: str,
    text: str,
    confidence: float,
) -> None:
    """Append one narrative only when its confidence clears the contract."""
    if confidence > MIN_CONFIDENCE_EXCLUSIVE:
        rows.append(
            {
                "company_id": company_id,
                "type": kind,
                "rule_id": rule_id,
                "text": text,
                "confidence_pct": round(confidence, 1),
            }
        )


def _evaluate_company(
    company_id: str,
    sector: str,
    history: pd.DataFrame,
    profit_loss: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    valuation: pd.Series,
) -> list[dict[str, object]]:
    """Evaluate all prescribed pro and con rules for one company."""
    rows: list[dict[str, object]] = []
    latest = history.sort_values("year").iloc[-1] if not history.empty else pd.Series()
    latest_pl = (
        profit_loss.sort_values("year").iloc[-1]
        if not profit_loss.empty
        else pd.Series()
    )
    opm = _number(latest.get("operating_profit_margin_pct"))
    debt_equity = _number(latest.get("debt_to_equity"))
    revenue_cagr = _number(latest.get("revenue_cagr_5y"))
    pat_cagr = _number(latest.get("pat_cagr_5y"))
    eps_cagr = _number(latest.get("eps_cagr_5y"))
    interest_coverage = _number(latest.get("interest_coverage"))
    dividend_yield = _number(valuation.get("dividend_yield_pct"))
    fcf = _number(latest.get("free_cash_flow_cr"))
    payout = _number(latest.get("dividend_payout_ratio_pct"))
    roce = _number(latest.get("return_on_capital_employed_pct"))
    net_debt_ebitda = _number(latest.get("net_debt_to_ebitda"))
    net_profit = _number(latest_pl.get("net_profit"))

    roe_three = _last_values(history, "return_on_equity_pct", 3)
    fcf_five = _last_values(history, "free_cash_flow_cr", 5)
    fcf_three = _last_values(history, "free_cash_flow_cr", 3)
    opm_three = _last_values(history, "operating_profit_margin_pct", 3)
    debt_three = _last_values(history, "debt_to_equity", 3)
    eps_three = _last_values(history, "earnings_per_share", 3)
    revenue_three = _last_values(profit_loss, "sales", 3)
    balance_two = (
        balance_sheet.sort_values("year").tail(2)
        if not balance_sheet.empty
        else pd.DataFrame()
    )

    if _all_above(roe_three, 20.0, 3):
        _append(
            rows,
            company_id,
            "pro",
            "P001",
            "Consistently high return on equity above 20% demonstrates exceptional capital efficiency",
            _confidence(75.0, min(roe_three) - 20.0),
        )
    if _all_above(fcf_five, 0.0, 5):
        _append(
            rows,
            company_id,
            "pro",
            "P002",
            "Strong free cash flow generation over 5 years signals healthy business fundamentals",
            _confidence(78.0, min(20.0, sum(fcf_five) / max(abs(sum(fcf_five)), 1.0))),
        )
    if debt_equity is not None and abs(debt_equity) < 1e-9:
        _append(
            rows,
            company_id,
            "pro",
            "P003",
            "Debt-free balance sheet provides financial flexibility and eliminates interest burden",
            98.0,
        )
    if revenue_cagr is not None and revenue_cagr > 15.0:
        _append(
            rows,
            company_id,
            "pro",
            "P004",
            "Revenue growing at above 15% CAGR over 5 years reflects strong business momentum",
            _confidence(70.0, revenue_cagr - 15.0),
        )
    if opm is not None and opm > 25.0:
        _append(
            rows,
            company_id,
            "pro",
            "P005",
            "Operating profit margin above 25% indicates strong pricing power and cost discipline",
            _confidence(70.0, opm - 25.0),
        )
    if pat_cagr is not None and pat_cagr > 20.0:
        _append(
            rows,
            company_id,
            "pro",
            "P006",
            "Net profit compounding at above 20% over 5 years creates significant shareholder value",
            _confidence(70.0, pat_cagr - 20.0),
        )
    if (
        interest_coverage is not None
        and interest_coverage > 10.0
        or latest.get("interest_coverage_status") == "Debt Free"
    ):
        _append(
            rows,
            company_id,
            "pro",
            "P007",
            "Very high interest coverage ratio reflects negligible financial stress from debt servicing",
            _confidence(76.0, min(23.0, (interest_coverage or 20.0) - 10.0)),
        )
    if (
        dividend_yield is not None
        and dividend_yield > 2.0
        and fcf is not None
        and fcf > 0.0
    ):
        _append(
            rows,
            company_id,
            "pro",
            "P008",
            "Consistent dividend yield above 2% backed by positive free cash flow",
            _confidence(72.0, (dividend_yield - 2.0) * 4.0),
        )
    if eps_cagr is not None and eps_cagr > 15.0:
        _append(
            rows,
            company_id,
            "pro",
            "P009",
            "Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding",
            _confidence(70.0, eps_cagr - 15.0),
        )
    if len(roe_three) == 3 and _strict_trend(roe_three, increasing=True):
        _append(
            rows,
            company_id,
            "pro",
            "P010",
            "Return on equity improving for 3 consecutive years shows strengthening business quality",
            _confidence(74.0, roe_three[-1] - roe_three[0]),
        )
    if revenue_cagr is not None and pat_cagr is not None and pat_cagr > revenue_cagr:
        _append(
            rows,
            company_id,
            "pro",
            "P011",
            "Revenue growing slower than profits shows improving operating leverage and scale benefits",
            _confidence(70.0, pat_cagr - revenue_cagr),
        )
    if len(balance_two) == 2:
        assets = _last_values(balance_two, "total_assets", 2)
        debt = _last_values(balance_two, "borrowings", 2)
        if (
            len(assets) == 2
            and len(debt) == 2
            and assets[1] > assets[0]
            and debt[1] < debt[0]
        ):
            _append(
                rows,
                company_id,
                "pro",
                "P012",
                "Growing asset base funded by internal accruals reflects self-sustaining growth",
                _confidence(
                    74.0,
                    min(
                        15.0, 100.0 * (assets[1] - assets[0]) / max(abs(assets[0]), 1.0)
                    ),
                ),
            )

    if debt_equity is not None and debt_equity > 2.0 and sector != FINANCIAL_SECTOR:
        _append(
            rows,
            company_id,
            "con",
            "C001",
            f"Debt-to-equity ratio of {debt_equity:.2f} is elevated for a non-financial company and warrants monitoring",
            _confidence(70.0, min(29.0, (debt_equity - 2.0) * 8.0)),
        )
    if _all_below(fcf_three, 0.0, 3):
        _append(
            rows,
            company_id,
            "con",
            "C002",
            "Free cash flow negative for 3 consecutive years raises concern about cash generation quality",
            88.0,
        )
    if len(opm_three) == 3 and _strict_trend(opm_three, increasing=False):
        _append(
            rows,
            company_id,
            "con",
            "C003",
            "Operating margins declining for 3 consecutive years suggest pricing or cost pressure",
            _confidence(74.0, opm_three[0] - opm_three[-1]),
        )
    if net_profit is not None and net_profit < 0.0:
        _append(
            rows,
            company_id,
            "con",
            "C004",
            "Company reported a net loss in the most recent financial year",
            96.0,
        )
    if len(revenue_three) == 3 and _strict_trend(revenue_three, increasing=False):
        _append(
            rows,
            company_id,
            "con",
            "C005",
            "Revenue contraction over 2 consecutive years indicates demand weakness or market share loss",
            86.0,
        )
    if interest_coverage is not None and interest_coverage < 1.5:
        _append(
            rows,
            company_id,
            "con",
            "C006",
            "Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations",
            _confidence(78.0, (1.5 - interest_coverage) * 10.0),
        )
    if payout is not None and payout > 100.0:
        _append(
            rows,
            company_id,
            "con",
            "C007",
            "Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable",
            _confidence(75.0, min(24.0, (payout - 100.0) / 5.0)),
        )
    if len(debt_three) == 3 and _strict_trend(debt_three, increasing=True):
        _append(
            rows,
            company_id,
            "con",
            "C008",
            "Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk",
            _confidence(73.0, min(26.0, (debt_three[-1] - debt_three[0]) * 10.0)),
        )
    if len(eps_three) == 3 and _strict_trend(eps_three, increasing=False):
        _append(
            rows,
            company_id,
            "con",
            "C009",
            "Earnings per share declining for 3 consecutive years reflects deteriorating profitability",
            _confidence(74.0, min(25.0, abs(eps_three[-1] - eps_three[0]))),
        )
    if roce is not None and roce < 10.0:
        _append(
            rows,
            company_id,
            "con",
            "C010",
            "Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital",
            _confidence(72.0, 10.0 - roce),
        )
    if net_debt_ebitda is not None and net_debt_ebitda > 3.0:
        _append(
            rows,
            company_id,
            "con",
            "C011",
            "Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility",
            _confidence(75.0, min(24.0, (net_debt_ebitda - 3.0) * 5.0)),
        )
    if revenue_cagr is not None and revenue_cagr < 5.0:
        _append(
            rows,
            company_id,
            "con",
            "C012",
            "Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum",
            _confidence(72.0, 5.0 - revenue_cagr),
        )
    return rows


def generate_pros_cons(
    companies: pd.DataFrame,
    ratios: pd.DataFrame,
    profit_loss: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    sectors: pd.DataFrame,
    valuation: pd.DataFrame,
) -> pd.DataFrame:
    """Generate full-universe narratives using the exact Sprint 5 rules."""
    ratio_groups = {
        company_id: group.sort_values("year")
        for company_id, group in ratios.groupby("company_id")
    }
    pl_groups = {
        company_id: group.sort_values("year")
        for company_id, group in profit_loss.groupby("company_id")
    }
    bs_groups = {
        company_id: group.sort_values("year")
        for company_id, group in balance_sheet.groupby("company_id")
    }
    sector_map = sectors.set_index("company_id")["broad_sector"].to_dict()
    valuation_map = valuation.set_index("company_id").to_dict("index")
    rows: list[dict[str, object]] = []
    for company_id in companies["company_id"].astype(str):
        company_rows = _evaluate_company(
            company_id=company_id,
            sector=str(sector_map.get(company_id, "Unknown")),
            history=ratio_groups.get(company_id, pd.DataFrame()),
            profit_loss=pl_groups.get(company_id, pd.DataFrame()),
            balance_sheet=bs_groups.get(company_id, pd.DataFrame()),
            valuation=pd.Series(valuation_map.get(company_id, {}), dtype=object),
        )
        present = {str(row["type"]) for row in company_rows}
        if "pro" not in present:
            _append(
                company_rows,
                company_id,
                "pro",
                "P000",
                "The latest available evidence includes at least one stable operating or balance-sheet characteristic",
                FALLBACK_CONFIDENCE,
            )
        if "con" not in present:
            _append(
                company_rows,
                company_id,
                "con",
                "C000",
                "No prescribed risk threshold fired; valuation assumptions and primary filings still require monitoring",
                FALLBACK_CONFIDENCE,
            )
        rows.extend(company_rows)
    return pd.DataFrame(
        rows, columns=["company_id", "type", "rule_id", "text", "confidence_pct"]
    ).sort_values(
        ["company_id", "type", "confidence_pct"], ascending=[True, True, False]
    )


def run_text_intelligence(
    settings: Settings,
    frames: dict[str, pd.DataFrame],
    ratios: pd.DataFrame,
    health_scores: pd.DataFrame,
    valuation: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse source narratives and generate full-universe pros/cons."""
    del health_scores, cashflow
    parse_result = parse_analysis_with_failures(frames["analysis"])
    cross_validation = cross_validate_parsed_cagrs(parse_result.parsed, ratios)
    generated = generate_pros_cons(
        companies=frames["companies"],
        ratios=ratios,
        profit_loss=frames["profit_and_loss"],
        balance_sheet=frames["balance_sheet"],
        sectors=frames["sectors"],
        valuation=valuation,
    )
    parse_result.parsed.to_csv(settings.output_dir / "analysis_parsed.csv", index=False)
    parse_result.failures.to_csv(
        settings.output_dir / "parse_failures.csv", index=False
    )
    cross_validation.to_csv(
        settings.output_dir / "analysis_cross_validation.csv", index=False
    )
    generated.to_csv(settings.output_dir / "pros_cons_generated.csv", index=False)
    load_derived_table(settings, "analysis_parsed", parse_result.parsed)
    load_derived_table(settings, "pros_cons_generated", generated)
    LOGGER.info(
        "text intelligence parsed=%d failures=%d manual_reviews=%d narratives=%d companies=%d",
        len(parse_result.parsed),
        len(parse_result.failures),
        (
            int(cross_validation["manual_review_flag"].sum())
            if not cross_validation.empty
            else 0
        ),
        len(generated),
        generated["company_id"].nunique(),
    )
    return parse_result.parsed, generated
