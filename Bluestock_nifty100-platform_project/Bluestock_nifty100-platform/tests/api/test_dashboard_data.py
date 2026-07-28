"""Framework-independent dashboard data tests."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

from src.config.settings import Settings
from src.dashboard.data import (
    company_profile,
    company_tickers,
    overview,
    peer_data,
    peer_groups,
    screener_data,
    sector_data,
)


def test_streamlit_five_screen_smoke() -> None:
    """Every declared Streamlit screen executes without an exception."""
    app = AppTest.from_file("src/dashboard/app.py", default_timeout=20).run()
    for screen in ("Overview", "Company Profile", "Screener", "Sector", "Peer"):
        app.sidebar.radio[0].set_value(screen).run()
        assert not app.exception, screen


def test_dashboard_overview(settings: Settings) -> None:
    """Overview counts match the verified database."""
    result = overview(settings.database_path)
    assert result["companies"] == 92
    assert result["sectors"] == 10
    assert result["health_bands"]["companies"].sum() == 92


def test_dashboard_company_profile(settings: Settings) -> None:
    """Company profile data contains ratios and documents."""
    assert "TCS" in company_tickers(settings.database_path)
    result = company_profile(settings.database_path, "TCS")
    assert not result["profile"].empty
    assert not result["ratios"].empty
    assert not result["documents"].empty


def test_dashboard_analytical_views(settings: Settings) -> None:
    """Screener, sector, and peer data layers execute independently."""
    assert not screener_data(settings.database_path, 50, 1).empty
    assert len(sector_data(settings.database_path)) == 10
    groups = peer_groups(settings.database_path)
    assert len(groups) == 11
    assert not peer_data(settings.database_path, groups[0]).empty
