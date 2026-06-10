# Capstone Self-Review Checklist

## 7 daily objectives
- [x] **Day 1 — Data ingestion:** 10 CSVs profiled, live NAV fetched, AMFI codes validated (100% coverage).
- [x] **Day 2 — Cleaning + SQL:** 10 clean CSVs, 10-table SQLite warehouse, 10 tested queries, data dictionary.
- [x] **Day 3 — EDA:** 16 publication-quality charts + findings notebook & summary.
- [x] **Day 4 — Performance:** returns, CAGR, Sharpe/Sortino, alpha/beta, max-DD, composite scorecard, benchmark chart.
- [x] **Day 5 — Dashboard:** 4-page Power BI dashboard (exported PDF + PNGs) + Power BI Desktop build guide.
- [x] **Day 6 — Advanced analytics:** VaR/CVaR, cohorts, SIP continuity, recommender, sector HHI.
- [x] **Day 7 — Report + deck + docs:** Final report PDF, 12-slide deck, README, master pipeline.

## Day 7 deliverables
- [x] `reports/Final_Report.pdf` — 17 pages (exec summary → architecture → EDA → performance → risk → dashboard → recommendations → limitations → appendices).
- [x] `Bluestock_MF_Presentation.pptx` — 12 slides (title, problem, data, architecture, 2× EDA, 2× performance, 2× dashboard, findings, thank-you).
- [x] `README.md` — overview, setup, file map, how to run ETL & dashboard.
- [x] Code documented (docstrings on every script) + `run_pipeline.py` master runner.

## Quality checks
- [x] All Python scripts compile (`py_compile`) without errors.
- [x] Recommender tested across Low / Moderate / High risk appetites.
- [x] DB load verified: 0 orphan NAV rows, expected row counts.
- [x] PDF (17pp) and PPTX (12 slides) visually inspected — headers, tables, images render correctly.
- [x] Charts spot-checked for correctness.

## Honest caveats (documented throughout)
- Dataset is synthetic: NAV returns are independent / uncorrelated with benchmarks → alpha, beta, correlations are illustrative, not economically meaningful. Pipelines are correct and work on real data.
- Day-1 brief AMFI codes are mislabelled vs the live API; the 10 supplied CSVs are internally consistent and used throughout.
- AUM/SIP/folio reflect the 10-AMC sample (₹62.7L cr), not the full industry (₹81L cr in the brief).

## Not done (explicitly out of scope per request)
- [ ] Push to GitHub — skipped; repo packaged as `project_repo.bundle` (push via `setup_git.sh`).
- [ ] Deploy dashboard to Power BI Service / Tableau Public — skipped.
