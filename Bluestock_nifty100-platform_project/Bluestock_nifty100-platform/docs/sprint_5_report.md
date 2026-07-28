# Sprint 5 — Intelligence, NLP, Dashboard and Reports

Status: **implemented and verified** on 2026-07-27.

## Measured outputs

| Area | Result |
|---|---:|
| Analysis observations parsed | 51 |
| Non-matching source cells logged | 13 |
| Parsed/computed CAGR manual-review flags (>5 points) | 1 |
| Generated narratives | 545 |
| Pro narratives / covered companies | 390 / 92 |
| Con narratives / covered companies | 155 / 92 |
| Narrative confidence range | 61.0–99.0 |
| Cash-flow intelligence rows | 92 |
| Distress signals | 13 |
| Deleveraging flags | 18 |
| Year-over-year allocation pattern changes | 36 |
| Company tearsheets | 92, exactly 2 pages each |
| Minimum company tearsheet size | 155,022 bytes |
| Sector reports | 10 observed broad sectors |
| Portfolio summary | 92 pages |
| Streamlit navigation states exercised | 5 |
| Pytest | 111 passed |
| Source coverage | 94.38% |

## Day 29 — Analysis parser

- `src/nlp/parser.py` uses
  `(\d+)\s*Years?:?\s*([\d.]+)%`.
- `output/analysis_parsed.csv` has exactly `company_id`, `metric_type`,
  `period_years`, and `value_pct`.
- `output/parse_failures.csv` retains non-matching source text and its issue code.
- `output/analysis_cross_validation.csv` compares 3/5/10-year sales and profit
  observations with the latest raw-derived Ratio Engine values; differences over
  five percentage points receive `manual_review_flag=True`.

## Day 30 — Pros and cons

- `src/nlp/pros_cons_generator.py` implements the prescribed P001–P012 and
  C001–C012 rules.
- Only rows with `confidence_pct > 60` are exported.
- Deterministic P000/C000 monitoring narratives close genuine no-signal gaps
  without claiming that a prescribed financial threshold fired.
- The output contract is exactly `company_id`, `type`, `rule_id`, `text`,
  `confidence_pct`, and both types cover all 92 master companies.

## Days 31–32 — Cash-flow intelligence

- `src/analytics/cashflow_kpis.py` implements five-year CFO/PAT quality, exact
  3%/8% CapEx tiers, five-year FCF CAGR, FCF conversion, distress, deleveraging,
  and latest capital-allocation pattern.
- `output/cashflow_intelligence.xlsx` has 92 rows and four inspected sheets:
  Cash Flow Intelligence, Distress Alerts, Allocation Distribution, and Pattern
  Changes.
- Supporting CSVs are `distress_alerts.csv`,
  `capital_allocation_distribution.csv`, and `pattern_changes.csv`.
- Classification distribution:
  - CFO quality: 62 High Quality, 12 Moderate, 17 Accrual Risk, 1 No Data.
  - CapEx: 21 Asset Light, 24 Moderate, 46 Capital Intensive, 1 No Data.

## Days 33–34 — Company and sector PDFs

- Every company tearsheet contains exactly two pages. Page 1 has the navy header,
  six KPI tiles, revenue/PAT bars, and ROE/ROCE dual-axis trends. Page 2 has
  balance-sheet composition, latest cash-flow bars, wrapped pro/con panels, and
  the capital-allocation badge.
- Structural inspection across every generated page found zero blank pages, zero
  text blocks outside the page bounds, and zero page-count failures.
- TCS, HDFCBANK, RELIANCE, SUNPHARMA, and TATASTEEL were rendered and visually
  reviewed. Company names are whitespace-normalized to avoid unsupported control
  glyphs.
- JIOFIN has only two source fiscal years. The stricter 92-PDF exit gate is
  honored by generating a limited-history report; the exception is recorded in
  `output/limited_history_tearsheets.csv`. No company was skipped.
- The real supporting data contains 10 broad sectors, so 10 sector PDFs are
  generated. Hard-coding the project document’s claimed 11 sectors would create
  a fictional empty report.

## Day 35 — Portfolio, dashboard and Excel

- `reports/portfolio/portfolio_summary.pdf` contains one page for each of the 92
  companies in ticker order. Six KPI cards include improvement/decline/flat
  arrows, with flat defined as movement within 2%.
- The Streamlit process started successfully, returned `ok` from its health
  endpoint, and all five states—Overview, Company Profile, Screener, Sector, and
  Peer—were exercised without browser console errors.
- All 23 sheets across the four generated workbooks were imported, inspected for
  formula-error tokens, and rendered for visual review.

The team-lead review/sign-off remains an external organizational action; all
technical evidence required for that review is included in this repository.
