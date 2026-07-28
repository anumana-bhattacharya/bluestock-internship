"""Pure normalization functions for identifiers, columns, and periods."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import pandas as pd

TICKER_PATTERN = re.compile(r"^[A-Z0-9&.\-]+$")
MONTHS = {"MAR": 3, "JUN": 6, "SEP": 9, "DEC": 12}


@dataclass(frozen=True)
class YearResult:
    """Return a normalized fiscal period and its interpretation."""

    value: str | None
    period_kind: str
    note: str | None = None


def normalize_column_name(value: Any) -> str:
    """Convert a source heading into snake_case."""
    text = re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip()).strip("_")
    return text.lower()


def normalize_ticker(value: Any) -> str | None:
    """Normalize an NSE ticker while preserving ampersand, dash, and dot."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    ticker = str(value).strip().upper()
    if not ticker or ticker in {"NAN", "NONE"} or not TICKER_PATTERN.fullmatch(ticker):
        return None
    return ticker


def _four_digit_year(token: str) -> int | None:
    """Convert two- or four-digit year text into a plausible year."""
    try:
        value = int(token)
    except ValueError:
        return None
    if value < 50:
        value += 2000
    elif value < 100:
        value += 1900
    return value if 1900 <= value <= 2100 else None


def normalize_year(value: Any) -> YearResult:
    """Normalize mixed fiscal labels to YYYY-MM with audit metadata."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return YearResult(None, "invalid", "missing fiscal period")
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return YearResult(f"{value.year:04d}-{value.month:02d}", "fiscal")
    text = str(value).strip()
    if not text:
        return YearResult(None, "invalid", "blank fiscal period")
    if re.search(r"\bTTM\b", text, flags=re.IGNORECASE):
        return YearResult(None, "ttm", "trailing-twelve-month row")

    month_match = re.search(
        r"\b(Mar|Jun|Sep|Dec)[\s\-]*(\d{2,4})\b", text, flags=re.IGNORECASE
    )
    if month_match:
        year = _four_digit_year(month_match.group(2))
        if year is None:
            return YearResult(None, "invalid", f"unparseable fiscal period: {text}")
        month = MONTHS[month_match.group(1).upper()]
        partial = bool(re.search(r"\b(?:3|6|9)\s*m\b", text, flags=re.IGNORECASE))
        return YearResult(
            f"{year:04d}-{month:02d}",
            "partial" if partial else "fiscal",
            "partial-period source label" if partial else None,
        )

    fy_match = re.fullmatch(r"FY[\s\-]*(\d{2,4})", text, flags=re.IGNORECASE)
    if fy_match:
        year = _four_digit_year(fy_match.group(1))
        return (
            YearResult(f"{year:04d}-03", "fiscal", "FY label assumed March end")
            if year
            else YearResult(None, "invalid", f"unparseable fiscal period: {text}")
        )

    number_match = re.fullmatch(r"(\d{4})(?:\.([0-9]+))?", text)
    if number_match:
        year = _four_digit_year(number_match.group(1))
        fraction = number_match.group(2)
        if year is None:
            return YearResult(None, "invalid", f"unparseable fiscal period: {text}")
        if fraction and int(fraction) != 0:
            month = 9 if fraction.startswith("5") else 3
            return YearResult(
                f"{year:04d}-{month:02d}",
                "partial",
                "fractional bare year interpreted as partial period",
            )
        return YearResult(
            f"{year:04d}-03", "assumed_march", "bare year assumed March end"
        )
    return YearResult(None, "invalid", f"unparseable fiscal period: {text}")


def normalize_calendar_year(value: Any) -> int | None:
    """Normalize a calendar year to an integer."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        year = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
    return year if 1900 <= year <= 2100 else None


def normalize_date(value: Any) -> str | None:
    """Normalize a source date to ISO YYYY-MM-DD."""
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.strftime("%Y-%m-%d")
