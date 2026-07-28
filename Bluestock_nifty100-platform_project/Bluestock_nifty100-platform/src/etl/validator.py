"""Registry-driven data-quality validation and deduplication."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.config.tables import TableSpec
from src.etl.normalizer import (
    normalize_calendar_year,
    normalize_date,
    normalize_ticker,
    normalize_year,
)

FAILURE_COLUMNS = (
    "table",
    "rule_id",
    "severity",
    "company_id",
    "year",
    "field",
    "issue",
    "action",
)


@dataclass(frozen=True)
class ValidationResult:
    """Hold clean rows, failures, and rejected-row count."""

    data: pd.DataFrame
    failures: pd.DataFrame
    rejected_rows: int


def _failure(
    table: str,
    rule_id: str,
    severity: str,
    row: pd.Series,
    field: str,
    issue: str,
    action: str,
) -> dict[str, Any]:
    """Create a validation-failure record."""
    return {
        "table": table,
        "rule_id": rule_id,
        "severity": severity,
        "company_id": row.get("company_id"),
        "year": row.get("year", row.get("date")),
        "field": field,
        "issue": issue,
        "action": action,
    }


def duplicate_mask(frame: pd.DataFrame, key: Iterable[str]) -> pd.Series:
    """Return a mask for every row participating in a duplicate key."""
    columns = list(key)
    if not columns or any(column not in frame.columns for column in columns):
        return pd.Series(False, index=frame.index)
    return frame.duplicated(columns, keep=False)


def validate_and_clean(
    frame: pd.DataFrame,
    spec: TableSpec,
    master_tickers: set[str],
    orphan_policy: str = "quarantine",
) -> ValidationResult:
    """Normalize, validate, quarantine, and deduplicate one dataset."""
    data = frame.copy()
    failures: list[dict[str, Any]] = []
    reject = pd.Series(False, index=data.index)

    if "company_id" in data.columns:
        original = data["company_id"].copy()
        data["company_id"] = original.map(normalize_ticker)
        bad = data["company_id"].isna()
        for index in data.index[bad]:
            failures.append(
                _failure(
                    spec.name,
                    "DQ001",
                    "CRITICAL",
                    data.loc[index],
                    "company_id",
                    f"missing or invalid ticker: {original.loc[index]!r}",
                    "REJECT",
                )
            )
        reject |= bad

    if spec.year_column and spec.year_column in data.columns:
        if spec.year_kind == "fiscal":
            results = data[spec.year_column].map(normalize_year)
            data[spec.year_column] = results.map(lambda result: result.value)
            data["period_kind"] = results.map(lambda result: result.period_kind)
            invalid = data[spec.year_column].isna()
            for index in data.index[invalid]:
                result = results.loc[index]
                rule = "DQ003" if result.period_kind == "ttm" else "DQ002"
                failures.append(
                    _failure(
                        spec.name,
                        rule,
                        "CRITICAL",
                        data.loc[index],
                        spec.year_column,
                        result.note or "invalid fiscal period",
                        "REJECT",
                    )
                )
            reject |= invalid
            partial = data["period_kind"].eq("partial") & ~invalid
            for index in data.index[partial]:
                failures.append(
                    _failure(
                        spec.name,
                        "DQ004",
                        "WARNING",
                        data.loc[index],
                        spec.year_column,
                        results.loc[index].note or "partial fiscal period",
                        "KEEP_FLAGGED",
                    )
                )
            assumed = data["period_kind"].eq("assumed_march") & ~invalid
            for index in data.index[assumed]:
                failures.append(
                    _failure(
                        spec.name,
                        "DQ005",
                        "INFO",
                        data.loc[index],
                        spec.year_column,
                        "bare year assumed March end",
                        "COUNT",
                    )
                )
        elif spec.year_kind == "calendar":
            data[spec.year_column] = data[spec.year_column].map(normalize_calendar_year)
            invalid = data[spec.year_column].isna()
            for index in data.index[invalid]:
                failures.append(
                    _failure(
                        spec.name,
                        "DQ002",
                        "CRITICAL",
                        data.loc[index],
                        spec.year_column,
                        "invalid calendar year",
                        "REJECT",
                    )
                )
            reject |= invalid
        elif spec.year_kind == "date":
            data[spec.year_column] = data[spec.year_column].map(normalize_date)
            invalid = data[spec.year_column].isna()
            for index in data.index[invalid]:
                failures.append(
                    _failure(
                        spec.name,
                        "DQ002",
                        "CRITICAL",
                        data.loc[index],
                        spec.year_column,
                        "invalid date",
                        "REJECT",
                    )
                )
            reject |= invalid

    for field in spec.not_null:
        if field not in data.columns:
            continue
        missing = data[field].isna() | data[field].astype(str).str.strip().eq("")
        for index in data.index[missing & ~reject]:
            failures.append(
                _failure(
                    spec.name,
                    "DQ006",
                    "CRITICAL",
                    data.loc[index],
                    field,
                    "null critical field",
                    "REJECT",
                )
            )
        reject |= missing

    if spec.name == "companies" and "company_name" in data.columns:
        empty_name = data["company_name"].fillna("").astype(str).str.strip().eq("")
        for index in data.index[empty_name & ~reject]:
            failures.append(
                _failure(
                    spec.name,
                    "DQ007",
                    "CRITICAL",
                    data.loc[index],
                    "company_name",
                    "empty company name",
                    "REJECT",
                )
            )
        reject |= empty_name

    if spec.company_fk and "company_id" in data.columns:
        orphan = data["company_id"].notna() & ~data["company_id"].isin(master_tickers)
        action = (
            "REJECT_QUARANTINE" if orphan_policy == "quarantine" else "KEEP_FLAGGED"
        )
        severity = "CRITICAL" if orphan_policy == "quarantine" else "WARNING"
        for index in data.index[orphan]:
            failures.append(
                _failure(
                    spec.name,
                    "DQ008",
                    severity,
                    data.loc[index],
                    "company_id",
                    "company ticker absent from companies master",
                    action,
                )
            )
        if orphan_policy == "quarantine":
            reject |= orphan

    for field in spec.non_negative:
        if field not in data.columns:
            continue
        numeric = pd.to_numeric(data[field], errors="coerce")
        hit = numeric < 0
        for index in data.index[hit & ~reject]:
            failures.append(
                _failure(
                    spec.name,
                    "DQ009",
                    "WARNING",
                    data.loc[index],
                    field,
                    "negative value where non-negative expected",
                    "KEEP_FLAGGED",
                )
            )

    for field in spec.positive:
        if field not in data.columns:
            continue
        numeric = pd.to_numeric(data[field], errors="coerce")
        hit = numeric.notna() & (numeric <= 0)
        for index in data.index[hit & ~reject]:
            failures.append(
                _failure(
                    spec.name,
                    "DQ010",
                    "WARNING",
                    data.loc[index],
                    field,
                    "non-positive value where positive expected",
                    "KEEP_FLAGGED",
                )
            )

    for field in spec.url_columns:
        if field not in data.columns:
            continue
        text = data[field].fillna("").astype(str).str.strip()
        hit = ~text.str.match(r"^https?://", na=False)
        for index in data.index[hit & ~reject]:
            failures.append(
                _failure(
                    spec.name,
                    "DQ011",
                    "WARNING",
                    data.loc[index],
                    field,
                    "missing or invalid HTTP(S) URL",
                    "KEEP_FLAGGED",
                )
            )

    clean = data.loc[~reject].copy()
    duplicated = duplicate_mask(clean, spec.primary_key)
    if duplicated.any():
        drop_mask = clean.duplicated(list(spec.primary_key), keep="last")
        for index in clean.index[duplicated]:
            failures.append(
                _failure(
                    spec.name,
                    "DQ012",
                    "WARNING",
                    clean.loc[index],
                    ",".join(spec.primary_key),
                    "duplicate primary key",
                    "DEDUP_KEEP_LAST",
                )
            )
        clean = clean.loc[~drop_mask].copy()

    clean = clean.reset_index(drop=True)
    failure_frame = pd.DataFrame(failures, columns=FAILURE_COLUMNS)
    return ValidationResult(
        clean,
        failure_frame,
        int(len(frame) - len(clean)),
    )
