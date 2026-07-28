"""Pure, unit-testable SQLite query layer for the REST API."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any

HISTORY_TABLES = {
    "pl": "profit_and_loss",
    "bs": "balance_sheet",
    "cashflow": "cash_flow",
    "ratios": "computed_ratios",
    "documents": "documents",
}


class DatabaseQueries:
    """Expose read-only API queries over a configured SQLite database."""

    def __init__(self, database_path: Path) -> None:
        """Store the database path."""
        self.database_path = database_path

    def _fetch(self, sql: str, parameters: Sequence[Any] = ()) -> list[dict[str, Any]]:
        """Execute one parameterized read query and return dictionaries."""
        with sqlite3.connect(
            f"file:{self.database_path}?mode=ro", uri=True
        ) as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute(sql, parameters).fetchall()]

    def health(self) -> dict[str, Any]:
        """Return database health and integrity metadata."""
        companies = self._fetch("SELECT COUNT(*) AS count FROM companies")[0]["count"]
        violations = self._fetch("PRAGMA foreign_key_check")
        return {
            "status": "ok" if not violations else "degraded",
            "companies": companies,
            "foreign_key_violations": len(violations),
        }

    def companies(
        self, sector: str | None = None, limit: int = 200, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List companies with sector and health metadata."""
        sql = """
            SELECT c.company_id, c.company_name, s.broad_sector, s.sub_sector,
                   h.health_score, h.health_band
            FROM companies c
            LEFT JOIN sectors s USING (company_id)
            LEFT JOIN health_scores h USING (company_id)
        """
        parameters: list[Any] = []
        if sector:
            sql += " WHERE s.broad_sector = ?"
            parameters.append(sector)
        sql += " ORDER BY c.company_id LIMIT ? OFFSET ?"
        parameters.extend([limit, offset])
        return self._fetch(sql, parameters)

    def company(self, ticker: str) -> dict[str, Any] | None:
        """Return one company profile with latest scores and valuation."""
        rows = self._fetch(
            """
            SELECT c.*, s.broad_sector, s.sub_sector, h.health_score, h.health_band,
                   v.pe_ratio, v.pb_ratio, v.ev_ebitda, v.dividend_yield_pct,
                   v.fcf_yield_pct, v.valuation_flag, cl.cluster_label
            FROM companies c
            LEFT JOIN sectors s USING (company_id)
            LEFT JOIN health_scores h USING (company_id)
            LEFT JOIN valuation_summary v USING (company_id)
            LEFT JOIN cluster_labels cl USING (company_id)
            WHERE c.company_id = ?
            """,
            (ticker.strip().upper(),),
        )
        return rows[0] if rows else None

    def history(self, kind: str, ticker: str) -> list[dict[str, Any]]:
        """Return a whitelisted company history table."""
        if kind not in HISTORY_TABLES:
            raise ValueError(f"unsupported history kind: {kind}")
        table = HISTORY_TABLES[kind]
        order_column = "year"
        return self._fetch(
            f'SELECT * FROM "{table}" WHERE company_id = ? ORDER BY "{order_column}"',
            (ticker.strip().upper(),),
        )

    def screener(
        self,
        minimum_health: float = 0.0,
        maximum_pe: float | None = None,
        sector: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Screen latest ratios using bound query parameters."""
        sql = """
            WITH latest AS (
                SELECT r.*
                FROM computed_ratios r
                JOIN (
                    SELECT company_id, MAX(year) AS year
                    FROM computed_ratios GROUP BY company_id
                ) x USING (company_id, year)
            )
            SELECT l.company_id, l.year, h.health_score, h.health_band,
                   s.broad_sector, l.return_on_equity_pct,
                   l.operating_profit_margin_pct, l.debt_to_equity,
                   l.revenue_cagr_3y, v.pe_ratio, v.valuation_flag
            FROM latest l
            JOIN health_scores h USING (company_id)
            JOIN sectors s USING (company_id)
            LEFT JOIN valuation_summary v USING (company_id)
            WHERE h.health_score >= ?
        """
        parameters: list[Any] = [minimum_health]
        if maximum_pe is not None:
            sql += " AND v.pe_ratio <= ?"
            parameters.append(maximum_pe)
        if sector:
            sql += " AND s.broad_sector = ?"
            parameters.append(sector)
        sql += " ORDER BY h.health_score DESC LIMIT ?"
        parameters.append(limit)
        return self._fetch(sql, parameters)

    def sectors(self) -> list[dict[str, Any]]:
        """Return sector benchmarks."""
        return self._fetch(
            "SELECT * FROM sector_benchmarks ORDER BY sector_rank, broad_sector"
        )

    def sector(self, name: str) -> list[dict[str, Any]]:
        """Return member rankings for one broad sector."""
        return self._fetch(
            """
            SELECT c.company_id, c.company_name, h.health_score, h.health_band,
                   v.pe_ratio, v.valuation_flag
            FROM companies c
            JOIN sectors s USING (company_id)
            LEFT JOIN health_scores h USING (company_id)
            LEFT JOIN valuation_summary v USING (company_id)
            WHERE s.broad_sector = ?
            ORDER BY h.health_score DESC
            """,
            (name,),
        )

    def peers(self, group: str) -> list[dict[str, Any]]:
        """Return percentile ranks for one peer group."""
        return self._fetch(
            """
            SELECT * FROM peer_percentiles
            WHERE peer_group_name = ?
            ORDER BY composite_percentile DESC
            """,
            (group,),
        )

    def portfolio_stats(self) -> list[dict[str, Any]]:
        """Return portfolio P10-median-P90 statistics."""
        return self._fetch("SELECT * FROM portfolio_stats ORDER BY metric")
