"""API query and route tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.api.queries import DatabaseQueries
from src.config.settings import Settings


def test_query_health(settings: Settings) -> None:
    """Database health reports the full universe and zero FK errors."""
    result = DatabaseQueries(settings.database_path).health()
    assert result == {"status": "ok", "companies": 92, "foreign_key_violations": 0}


def test_query_companies(settings: Settings) -> None:
    """Company listing and sector filter are bounded."""
    queries = DatabaseQueries(settings.database_path)
    assert len(queries.companies(limit=10)) == 10
    assert all(
        row["broad_sector"] == "Financials"
        for row in queries.companies(sector="Financials")
    )


def test_query_company_and_history(settings: Settings) -> None:
    """Profiles and statement histories are returned for a known ticker."""
    queries = DatabaseQueries(settings.database_path)
    assert queries.company("tcs")["company_id"] == "TCS"
    assert len(queries.history("ratios", "TCS")) >= 10
    assert len(queries.history("documents", "TCS")) >= 1


def test_query_unknown_kind(settings: Settings) -> None:
    """Dynamic history tables are strictly whitelisted."""
    queries = DatabaseQueries(settings.database_path)
    try:
        queries.history("companies; DROP TABLE companies", "TCS")
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported table selector was accepted")


def test_query_screener_sector_peer_stats(settings: Settings) -> None:
    """Analytical query endpoints return material results."""
    queries = DatabaseQueries(settings.database_path)
    assert queries.screener(minimum_health=50)
    assert len(queries.sectors()) == 10
    assert queries.sector("Financials")
    assert queries.peers("IT Services")
    assert len(queries.portfolio_stats()) >= 30


def test_fastapi_routes(settings: Settings) -> None:
    """All public route families respond successfully."""
    client = TestClient(create_app(settings.database_path))
    for route in (
        "/health",
        "/companies?limit=2",
        "/companies/TCS",
        "/pl/TCS",
        "/bs/TCS",
        "/cashflow/TCS",
        "/ratios/TCS",
        "/documents/TCS",
        "/screener?minimum_health=50",
        "/sectors",
        "/sectors/Financials",
        "/peers/IT%20Services",
        "/portfolio/stats",
        "/docs",
    ):
        assert client.get(route).status_code == 200, route


def test_fastapi_not_found(settings: Settings) -> None:
    """Unknown tickers return 404."""
    client = TestClient(create_app(settings.database_path))
    assert client.get("/companies/NOTREAL").status_code == 404
