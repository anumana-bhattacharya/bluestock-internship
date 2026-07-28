"""Normalizer unit tests."""

from __future__ import annotations

import pytest

from src.etl.normalizer import (
    normalize_calendar_year,
    normalize_column_name,
    normalize_date,
    normalize_ticker,
    normalize_year,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (" abb ", "ABB"),
        ("M&M", "M&M"),
        ("BAJAJ-AUTO", "BAJAJ-AUTO"),
        ("ABC.DEF", "ABC.DEF"),
        ("nse123", "NSE123"),
        ("", None),
        ("A/B", None),
        (None, None),
    ],
)
def test_normalize_ticker(source: object, expected: str | None) -> None:
    """Ticker rules preserve valid NSE punctuation."""
    assert normalize_ticker(source) == expected


@pytest.mark.parametrize(
    ("source", "expected", "kind"),
    [
        ("Mar-23", "2023-03", "fiscal"),
        ("Dec 2012", "2012-12", "fiscal"),
        ("Jun 2013", "2013-06", "fiscal"),
        ("Sep-99", "1999-09", "fiscal"),
        ("FY24", "2024-03", "fiscal"),
        (2015.0, "2015-03", "assumed_march"),
        ("2015", "2015-03", "assumed_march"),
        ("Mar 2016 9m", "2016-03", "partial"),
        ("2024.5", "2024-09", "partial"),
        ("TTM", None, "ttm"),
        ("", None, "invalid"),
        ("not-a-year", None, "invalid"),
    ],
)
def test_normalize_year(source: object, expected: str | None, kind: str) -> None:
    """Fiscal year normalization handles all observed formats."""
    result = normalize_year(source)
    assert result.value == expected
    assert result.period_kind == kind


@pytest.mark.parametrize(
    ("source", "expected"),
    [(2024, 2024), ("2023", 2023), (2024.0, 2024), ("bad", None), (None, None)],
)
def test_calendar_year(source: object, expected: int | None) -> None:
    """Calendar years remain integers."""
    assert normalize_calendar_year(source) == expected


def test_column_name_and_date() -> None:
    """Column and date normalization are deterministic."""
    assert normalize_column_name("Annual Report (%)") == "annual_report"
    assert normalize_date("2024-05-01") == "2024-05-01"
    assert normalize_date("bad") is None
