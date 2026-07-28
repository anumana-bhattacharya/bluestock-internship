# Bluestock Fintech — Mutual Fund Analytics Capstone

End-to-end analytics on Indian mutual funds: ingestion of 10 datasets + live AMFI
NAV, cleaning, a SQLite warehouse, exploratory analysis, fund performance & risk
modelling, a Power BI dashboard, and advanced risk analytics (VaR, cohorts,
recommender, sector concentration).

**Scope of data:** 40 schemes across 10 AMCs, 46,000 daily NAVs (2022–2026),
~32,800 investor transactions, plus AUM / SIP / folio / category / benchmark series.

---

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_pipeline.py        # runs the full ETL + analytics pipeline end-to-end
```
`run_pipeline.py` executes, in order: data ingestion → cleaning → SQLite load →
EDA charts → performance analytics → advanced analytics. Outputs land in
`data/processed/`, `charts/`, and `bluestock_mf.db`.

To fetch fresh live NAV: `python live_nav_fetch.py`.

---

## Repository layout
```
.
├── data/
│   ├── raw/            10 source CSVs + fetched live NAV
│   └── processed/      cleaned CSVs + all computed metric tables
├── notebooks/          day1_eda, EDA_Analysis, Performance_Analytics, Advanced_Analytics
├── sql/                schema.sql (10-table star), queries.sql (10 analytics queries)
├── charts/             18 EDA + analytics PNG charts
├── dashboard/          Power BI exports — Dashboard PDF + 4 page PNGs
├── reports/            data-quality, EDA findings, query results, Final_Report.pdf
├── data_ingestion.py   Day 1 — load & profile
├── live_nav_fetch.py   Day 1 — live NAV from mfapi.in
├── clean_data.py        Day 2 — clean & validate
├── load_db.py           Day 2 — build SQLite warehouse
├── eda_charts.py        Day 3 — 16 EDA charts
├── performance_analytics.py  Day 4 — returns, CAGR, Sharpe/Sortino, alpha/beta, scorecard
├── build_dashboard.py   Day 5 — dashboard page renders
├── advanced_analytics.py Day 6 — VaR/CVaR, cohorts, SIP continuity, sector HHI
├── recommender.py       Day 6 — rule-based fund recommender
├── run_pipeline.py      master runner
├── bluestock_mf.db      SQLite warehouse (10 tables)
├── POWERBI_BUILD_GUIDE.md  step-by-step Power BI Desktop build
├── data_dictionary.md   every column documented
└── requirements.txt
```

---

## Pipeline stages

| Day | Script | Produces |
|---|---|---|
| 1 | `data_ingestion.py`, `live_nav_fetch.py` | profiled raw data, live NAV CSVs |
| 2 | `clean_data.py`, `load_db.py` | 10 clean CSVs, `bluestock_mf.db` |
| 3 | `eda_charts.py` | 16 charts + `reports/EDA_Findings.md` |
| 4 | `performance_analytics.py` | returns, CAGR, Sharpe, Sortino, alpha/beta, max DD, `fund_scorecard.csv` |
| 5 | `build_dashboard.py` + Power BI | dashboard pages, `Dashboard.pdf` |
| 6 | `advanced_analytics.py`, `recommender.py` | VaR/CVaR, cohorts, SIP continuity, sector HHI |
| 7 | — | `Final_Report.pdf`, `Bluestock_MF_Presentation.pptx`, this README |

---

## The database
`bluestock_mf.db` is a star schema (`dim_fund` hub + 9 fact tables). Build it with
`python load_db.py`; query it with `sqlite3 bluestock_mf.db < sql/queries.sql`.
See `data_dictionary.md` for the full column reference and `sql/schema.sql` for DDL.

## The dashboard
4 Power BI pages — Industry Overview, Fund Performance, Investor Analytics,
SIP & Market Trends. Exports are in `dashboard/`. To rebuild the `.pbix` yourself,
follow `POWERBI_BUILD_GUIDE.md` (import the cleaned CSVs, no ODBC needed).

---

## Key results
- **SBI leads AUM** at ₹12.5L cr (Dec 2025); SIP inflows hit a record **₹31,002 cr**.
- **Top composite fund:** Mirae Asset Large Cap (scorecard 85.9/100).
- **Tail risk:** small-cap funds carry the deepest daily VaR₉₅ (≈ −2.7%).
- **Concentration:** most equity funds are sector-concentrated (HHI > 0.18).

## Known limitations
The provided NAV/transaction data is **synthetic**: daily NAV returns are mutually
independent and uncorrelated with benchmarks, so market-relative factors (alpha,
beta, return correlations) are not economically meaningful — the pipelines are
correct and produce valid factors on real data. The Day-1 brief's AMFI codes are
also mislabelled vs the live API; the 10 supplied CSVs are internally consistent
and used throughout. Details in `reports/EDA_Findings.md` and `Final_Report.pdf`.

## Tech stack
Python (pandas, numpy, matplotlib, seaborn), SQLite + SQLAlchemy, Power BI, Jupyter.
