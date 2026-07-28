"""Thin five-screen Streamlit view over the dashboard data layer."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.dashboard import data

DATABASE_PATH = Path(__file__).resolve().parents[2] / "nifty100.db"

st.set_page_config(
    page_title="N100 Financial Intelligence",
    page_icon="📈",
    layout="wide",
)
st.title("N100 · Financial Intelligence")
screen = st.sidebar.radio(
    "Screen",
    ["Overview", "Company Profile", "Screener", "Sector", "Peer"],
)

if screen == "Overview":
    overview = data.overview(DATABASE_PATH)
    columns = st.columns(4)
    columns[0].metric("Companies", overview["companies"])
    columns[1].metric("Broad sectors", overview["sectors"])
    columns[2].metric("Ratio rows", overview["ratio_rows"])
    columns[3].metric("Annual reports", overview["documents"])
    st.subheader("Health score bands")
    st.bar_chart(overview["health_bands"].set_index("health_band"))
elif screen == "Company Profile":
    ticker = st.selectbox("Ticker", data.company_tickers(DATABASE_PATH))
    result = data.company_profile(DATABASE_PATH, ticker)
    st.dataframe(result["profile"], width="stretch", hide_index=True)
    if not result["ratios"].empty:
        st.line_chart(
            result["ratios"].set_index("year")[
                ["return_on_equity_pct", "operating_profit_margin_pct"]
            ]
        )
    st.dataframe(result["documents"], width="stretch", hide_index=True)
elif screen == "Screener":
    minimum_health = st.slider("Minimum health score", 0, 100, 50)
    maximum_debt = st.slider("Maximum debt-to-equity", 0.0, 5.0, 1.0)
    st.dataframe(
        data.screener_data(DATABASE_PATH, minimum_health, maximum_debt),
        width="stretch",
        hide_index=True,
    )
elif screen == "Sector":
    sectors = data.sector_data(DATABASE_PATH)
    st.dataframe(sectors, width="stretch", hide_index=True)
    st.bar_chart(sectors.set_index("broad_sector")["median_health_score"])
else:
    group = st.selectbox("Peer group", data.peer_groups(DATABASE_PATH))
    st.dataframe(
        data.peer_data(DATABASE_PATH, group),
        width="stretch",
        hide_index=True,
    )
