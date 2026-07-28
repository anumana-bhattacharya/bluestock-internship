"""FastAPI application exposing the financial intelligence query layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from src.api.queries import DatabaseQueries


def create_app(database_path: Path | None = None) -> FastAPI:
    """Create the FastAPI app for a selected database."""
    path = database_path or Path(__file__).resolve().parents[2] / "nifty100.db"
    queries = DatabaseQueries(path)
    app = FastAPI(
        title="Nifty100 Financial Intelligence API",
        version="1.0.0",
        description="Auditable financial statements, ratios, screens, sectors, and peers.",
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        """Return service and database health."""
        return queries.health()

    @app.get("/companies")
    def companies(
        sector: str | None = None,
        limit: int = Query(200, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ) -> list[dict[str, Any]]:
        """List companies."""
        return queries.companies(sector, limit, offset)

    @app.get("/companies/{ticker}")
    def company(ticker: str) -> dict[str, Any]:
        """Return one company profile."""
        result = queries.company(ticker)
        if result is None:
            raise HTTPException(status_code=404, detail="company not found")
        return result

    def history(kind: str, ticker: str) -> list[dict[str, Any]]:
        """Return a statement or analytical history."""
        result = queries.history(kind, ticker)
        if not result:
            raise HTTPException(status_code=404, detail="company history not found")
        return result

    @app.get("/pl/{ticker}")
    def profit_and_loss(ticker: str) -> list[dict[str, Any]]:
        """Return P&L history."""
        return history("pl", ticker)

    @app.get("/bs/{ticker}")
    def balance_sheet(ticker: str) -> list[dict[str, Any]]:
        """Return balance-sheet history."""
        return history("bs", ticker)

    @app.get("/cashflow/{ticker}")
    def cashflow(ticker: str) -> list[dict[str, Any]]:
        """Return cash-flow history."""
        return history("cashflow", ticker)

    @app.get("/ratios/{ticker}")
    def ratios(ticker: str) -> list[dict[str, Any]]:
        """Return computed-ratio history."""
        return history("ratios", ticker)

    @app.get("/documents/{ticker}")
    def documents(ticker: str) -> list[dict[str, Any]]:
        """Return annual-report links."""
        return history("documents", ticker)

    @app.get("/screener")
    def screener(
        minimum_health: float = Query(0.0, ge=0.0, le=100.0),
        maximum_pe: float | None = Query(None, gt=0.0),
        sector: str | None = None,
        limit: int = Query(200, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        """Run a query-parameter screen."""
        return queries.screener(minimum_health, maximum_pe, sector, limit)

    @app.get("/sectors")
    def sectors() -> list[dict[str, Any]]:
        """Return sector benchmarks."""
        return queries.sectors()

    @app.get("/sectors/{sector_name}")
    def sector(sector_name: str) -> list[dict[str, Any]]:
        """Return members of one broad sector."""
        return queries.sector(sector_name)

    @app.get("/peers/{group}")
    def peers(group: str) -> list[dict[str, Any]]:
        """Return peer percentiles."""
        return queries.peers(group)

    @app.get("/portfolio/stats")
    def portfolio_stats() -> list[dict[str, Any]]:
        """Return portfolio distribution statistics."""
        return queries.portfolio_stats()

    return app


app = create_app()
