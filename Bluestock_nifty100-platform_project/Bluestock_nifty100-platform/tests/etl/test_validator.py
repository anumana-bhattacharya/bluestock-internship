"""Data-quality validation tests."""

from __future__ import annotations

import pandas as pd

from src.config.tables import TABLE_SPEC_BY_NAME
from src.etl.validator import duplicate_mask, validate_and_clean


def test_duplicate_detection_marks_every_member() -> None:
    """Duplicate mask identifies both sides of a duplicated key."""
    frame = pd.DataFrame(
        {"company_id": ["A", "A", "B"], "year": ["2024", "2024", "2024"]}
    )
    assert duplicate_mask(frame, ("company_id", "year")).tolist() == [True, True, False]


def test_deduplicate_keep_last() -> None:
    """Validation keeps the last duplicate record."""
    frame = pd.DataFrame(
        {
            "source_id": [1, 2],
            "company_id": ["ABB", "ABB"],
            "year": ["Mar-24", "Mar-24"],
            "sales": [10, 20],
            "net_profit": [1, 2],
            "expenses": [9, 18],
            "depreciation": [0, 0],
        }
    )
    result = validate_and_clean(frame, TABLE_SPEC_BY_NAME["profit_and_loss"], {"ABB"})
    assert len(result.data) == 1
    assert result.data.iloc[0]["sales"] == 20
    assert (result.failures["rule_id"] == "DQ012").sum() == 2


def test_ttm_is_rejected() -> None:
    """TTM rows are critical and excluded from fiscal tables."""
    frame = pd.DataFrame(
        {
            "source_id": [1],
            "company_id": ["ABB"],
            "year": ["TTM"],
            "sales": [10],
            "net_profit": [1],
            "expenses": [9],
            "depreciation": [0],
        }
    )
    result = validate_and_clean(frame, TABLE_SPEC_BY_NAME["profit_and_loss"], {"ABB"})
    assert result.data.empty
    assert result.failures.iloc[0]["rule_id"] == "DQ003"


def test_orphan_policy_quarantine() -> None:
    """Quarantine policy rejects a broken company FK."""
    frame = pd.DataFrame(
        {
            "source_id": [1],
            "company_id": ["ORPHAN"],
            "year": ["2024"],
            "market_cap_crore": [100],
            "enterprise_value_crore": [120],
        }
    )
    result = validate_and_clean(
        frame,
        TABLE_SPEC_BY_NAME["market_cap"],
        {"ABB"},
        orphan_policy="quarantine",
    )
    assert result.data.empty
    assert result.failures.iloc[0]["rule_id"] == "DQ008"


def test_orphan_policy_load() -> None:
    """Load policy retains and flags a broken company FK."""
    frame = pd.DataFrame(
        {
            "source_id": [1],
            "company_id": ["ORPHAN"],
            "year": ["2024"],
            "market_cap_crore": [100],
            "enterprise_value_crore": [120],
        }
    )
    result = validate_and_clean(
        frame,
        TABLE_SPEC_BY_NAME["market_cap"],
        {"ABB"},
        orphan_policy="load",
    )
    assert len(result.data) == 1
    assert result.failures.iloc[0]["severity"] == "WARNING"


def test_negative_value_is_warning() -> None:
    """Positivity is a warning and does not reject a row."""
    frame = pd.DataFrame(
        {
            "source_id": [1],
            "company_id": ["ABB"],
            "year": ["2024"],
            "market_cap_crore": [-1],
            "enterprise_value_crore": [100],
        }
    )
    result = validate_and_clean(frame, TABLE_SPEC_BY_NAME["market_cap"], {"ABB"})
    assert len(result.data) == 1
    assert "DQ010" in set(result.failures["rule_id"])
