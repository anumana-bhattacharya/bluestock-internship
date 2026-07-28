"""Framework-independent, parameterized dashboard SQL data layer."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd


def query_frame(
    database_path: Path, sql: str, parameters: Sequence[Any] = ()
) -> pd.DataFrame:
    """Execute a read-only query and return a DataFrame."""
    with sqlite3.connect(f"file:{database_path}?mode=ro", uri=True) as connection:
        return pd.read_sql_query(sql, connection, params=tuple(parameters))


def overview(database_path: Path) -> dict[str, Any]:
    """Return overview KPIs and health-band distribution."""
    counts = (
        query_frame(
            database_path,
            """
        SELECT
            (SELECT COUNT(*) FROM companies) AS companies,
            (SELECT COUNT(DISTINCT broad_sector) FROM sectors) AS sectors,
            (SELECT COUNT(*) FROM computed_ratios) AS ratio_rows,
            (SELECT COUNT(*) FROM documents) AS documents
        """,
        )
        .iloc[0]
        .to_dict()
    )
    counts["health_bands"] = query_frame(
        database_path,
        """
        SELECT health_band, COUNT(*) AS companies
        FROM health_scores GROUP BY health_band ORDER BY companies DESC
        """,
    )
    return counts


def company_tickers(database_path: Path) -> list[str]:
    """Return available tickers."""
    return query_frame(
        database_path, "SELECT company_id FROM companies ORDER BY company_id"
    )["company_id"].tolist()


def company_profile(database_path: Path, ticker: str) -> dict[str, pd.DataFrame]:
    """Return company metadata, ratios, and document links."""
    profile = query_frame(
        database_path,
        """
        SELECT c.company_id, c.company_name, c.about_company, c.website,
               s.broad_sector, s.sub_sector, h.health_score, h.health_band,
               v.pe_ratio, v.pb_ratio, v.ev_ebitda, v.valuation_flag
        FROM companies c
        LEFT JOIN sectors s USING (company_id)
        LEFT JOIN health_scores h USING (company_id)
        LEFT JOIN valuation_summary v USING (company_id)
        WHERE c.company_id = ?
        """,
        (ticker,),
    )
    ratios = query_frame(
        database_path,
        """
        SELECT * FROM computed_ratios
        WHERE company_id = ? ORDER BY year
        """,
        (ticker,),
    )
    documents = query_frame(
        database_path,
        """
        SELECT year, annual_report FROM documents
        WHERE company_id = ? ORDER BY year DESC
        """,
        (ticker,),
    )
    return {"profile": profile, "ratios": ratios, "documents": documents}


def screener_data(
    database_path: Path, minimum_health: float, maximum_debt_to_equity: float
) -> pd.DataFrame:
    """Return latest companies satisfying dashboard screen parameters."""
    return query_frame(
        database_path,
        """
        WITH latest AS (
            SELECT r.* FROM computed_ratios r
            JOIN (
                SELECT company_id, MAX(year) AS year
                FROM computed_ratios GROUP BY company_id
            ) x USING (company_id, year)
        )
        SELECT l.company_id, h.health_score, h.health_band, s.broad_sector,
               l.return_on_equity_pct, l.operating_profit_margin_pct,
               l.debt_to_equity, l.revenue_cagr_3y
        FROM latest l
        JOIN health_scores h USING (company_id)
        JOIN sectors s USING (company_id)
        WHERE h.health_score >= ?
          AND COALESCE(l.debt_to_equity, 0) <= ?
        ORDER BY h.health_score DESC
        """,
        (minimum_health, maximum_debt_to_equity),
    )


def sector_data(database_path: Path) -> pd.DataFrame:
    """Return sector benchmarks."""
    return query_frame(
        database_path,
        "SELECT * FROM sector_benchmarks ORDER BY sector_rank, broad_sector",
    )


def peer_groups(database_path: Path) -> list[str]:
    """Return configured peer group names."""
    return query_frame(
        database_path,
        "SELECT DISTINCT peer_group_name FROM peer_groups ORDER BY peer_group_name",
    )["peer_group_name"].tolist()


def peer_data(database_path: Path, group: str) -> pd.DataFrame:
    """Return peer percentiles for one group."""
    return query_frame(
        database_path,
        """
        SELECT * FROM peer_percentiles
        WHERE peer_group_name = ?
        ORDER BY composite_percentile DESC
        """,
        (group,),
    )
