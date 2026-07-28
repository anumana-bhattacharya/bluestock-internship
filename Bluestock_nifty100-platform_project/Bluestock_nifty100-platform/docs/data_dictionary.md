# Data Dictionary

All monetary statement values are INR Crore unless a column name states otherwise.
Fiscal periods use `YYYY-MM`; calendar years are integers and market dates are ISO
`YYYY-MM-DD`.

## Source entities

- `companies`: governed company master and descriptive links. `company_id` is the
  normalized NSE-style identifier.
- `profit_and_loss`: sales, expenses, operating profit, other income, interest,
  depreciation, PBT, tax, PAT, EPS, and payout.
- `balance_sheet`: equity capital, reserves, borrowings, liabilities, fixed assets,
  CWIP, investments, other assets, and totals.
- `cash_flow`: operating, investing, financing, and net cash flow.
- `analysis`: source growth/ROE narratives.
- `documents`: calendar-year annual-report URLs.
- `pros_and_cons`: sparse source narratives.
- `sectors`: broad and sub-sector classification, index weight, and cap category.
- `market_cap`: simulated calendar-year market cap, enterprise value, P/E, P/B,
  EV/EBITDA, and dividend yield.
- `stock_prices`: monthly OHLCV and adjusted close.
- `financial_ratios_reference`: supplied ratio cross-check only.
- `peer_groups`: 11 named peer groups and benchmark flags.

## Derived entities

- `computed_ratios`: 30+ profitability, return, leverage, coverage, cash-flow,
  per-share, CAGR, valuation-join, and capital-allocation features.
- `health_scores`: four component scores, weighted score, and band.
- `sector_benchmarks`: observed-sector medians and rank.
- `peer_percentiles`: direction-aware intra-group percentiles.
- `valuation_summary`: latest simulated multiples, FCF yield, sector P/E median,
  and valuation flag.
- `cashflow_intelligence`: full-universe 5-year CFO quality score/label, exact
  3%/8% CapEx classification, FCF CAGR/conversion, distress and deleveraging
  flags, sector, and capital-allocation pattern.
- `cluster_labels`: KMeans ID and centroid-derived label.
- `portfolio_stats`: P10, median, P90, minimum, and maximum by KPI.
- `analysis_parsed`: normalized regex extractions keyed by company, metric type,
  and period years.
- `pros_cons_generated`: pro/con type, rule ID, evidence narrative, and
  confidence percentage for every company.

The authoritative column types and constraints are in `src/database/schema.sql`.
