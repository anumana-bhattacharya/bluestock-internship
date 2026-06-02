# Data Dictionary — Bluestock Mutual Fund Analytics

Documents every column across the cleaned datasets (`data/processed/`) and the
SQLite tables in `bluestock_mf.db`. Source files are the 10 raw CSVs in
`data/raw/`; live NAV columns come from the mfapi.in API.

## Conventions
- **Dates** are stored ISO-8601 (`YYYY-MM-DD`).
- **amfi_code** is the AMFI scheme code (6-digit), the join key across tables.
- Monetary values are in INR; `_crore` = ₹10M, `_lakh_crore` = ₹10^12.

---

## dim_fund  ← `clean_fund_master.csv` (01_fund_master.csv)
One row per scheme. Primary key: `amfi_code`.

| Column | Type | Description |
|---|---|---|
| amfi_code | TEXT (PK) | AMFI 6-digit scheme code |
| fund_house | TEXT | Asset management company |
| scheme_name | TEXT | Full scheme name |
| category | TEXT | Top-level class (Equity / Debt) |
| sub_category | TEXT | SEBI sub-category (Large Cap, ELSS, Liquid, …) |
| plan | TEXT | Direct / Regular |
| launch_date | DATE | Scheme inception date |
| benchmark | TEXT | Benchmark index name |
| expense_ratio_pct | REAL | Annual expense ratio (%) |
| exit_load_pct | REAL | Exit load (%) |
| min_sip_amount | REAL | Minimum SIP amount (INR) |
| min_lumpsum_amount | REAL | Minimum lump-sum amount (INR) |
| fund_manager | TEXT | Fund manager name |
| risk_category | TEXT | Riskometer band (Low … Very High) |
| sebi_category_code | TEXT | SEBI category code (e.g. EC01, DC02) |

## fact_nav  ← `clean_nav.csv` (02_nav_history.csv)
Daily NAV per scheme. PK: (`amfi_code`, `nav_date`).

| Column | Type | Description |
|---|---|---|
| amfi_code | TEXT (FK→dim_fund) | Scheme code |
| nav_date | DATE | NAV date (renamed from `date`) |
| nav | REAL | Net asset value; validated > 0; holiday gaps forward-filled |
| daily_return | REAL | Day-over-day % change in NAV (derived) |

## fact_transactions  ← `clean_transactions.csv` (08_investor_transactions.csv)
One row per investor transaction.

| Column | Type | Description |
|---|---|---|
| investor_id | TEXT | Pseudonymous investor id |
| transaction_date | DATE | Transaction date |
| amfi_code | TEXT (FK) | Scheme code |
| transaction_type | TEXT | SIP / Lumpsum / Redemption (standardised) |
| amount_inr | REAL | Amount in INR; validated > 0 |
| state | TEXT | Investor state |
| city | TEXT | Investor city |
| city_tier | TEXT | T30 / B30 |
| age_group | TEXT | Age bucket |
| gender | TEXT | Gender |
| annual_income_lakh | REAL | Annual income (₹ lakh) |
| payment_mode | TEXT | UPI / Cheque / Mandate / Net Banking |
| kyc_status | TEXT | Verified / Pending (title-cased) |

## fact_performance  ← `clean_performance.csv` (07_scheme_performance.csv)
Performance snapshot per scheme. PK: `amfi_code`.

| Column | Type | Description |
|---|---|---|
| amfi_code | TEXT (PK/FK) | Scheme code |
| scheme_name, fund_house, category, plan | TEXT | Descriptors |
| return_1yr_pct / _3yr_pct / _5yr_pct | REAL | Trailing returns (%) |
| benchmark_3yr_pct | REAL | Benchmark 3-yr return (%) |
| alpha, beta | REAL | Risk factors vs benchmark |
| sharpe_ratio, sortino_ratio | REAL | Risk-adjusted return ratios |
| std_dev_ann_pct | REAL | Annualised volatility (%) |
| max_drawdown_pct | REAL | Maximum drawdown (%) |
| aum_crore | REAL | AUM (₹ crore) |
| expense_ratio_pct | REAL | Expense ratio (%) |
| morningstar_rating | INTEGER | Star rating (1–5) |
| risk_grade | TEXT | Risk grade label |
| neg_sharpe_flag | INTEGER | 1 if Sharpe < 0 (QC flag, derived) |
| expense_ratio_out_of_range | INTEGER | 1 if expense ratio ∉ [0.1, 2.5] (derived) |

## fact_holdings  ← `clean_portfolio_holdings.csv` (09_portfolio_holdings.csv)

| Column | Type | Description |
|---|---|---|
| amfi_code | TEXT (FK) | Scheme code |
| stock_symbol | TEXT | Ticker |
| stock_name | TEXT | Company name |
| sector | TEXT | Sector classification |
| weight_pct | REAL | Holding weight in portfolio (%) |
| market_value_cr | REAL | Holding market value (₹ crore) |
| current_price_inr | REAL | Current stock price (INR) |
| portfolio_date | DATE | Portfolio disclosure date |

## fact_aum  ← `clean_aum_by_fund_house.csv` (03_aum_by_fund_house.csv)

| Column | Type | Description |
|---|---|---|
| date | DATE | Reporting month-end |
| fund_house | TEXT | AMC |
| aum_lakh_crore | REAL | AUM (₹ lakh crore) |
| aum_crore | REAL | AUM (₹ crore) |
| num_schemes | INTEGER | Number of schemes |

## fact_sip_inflows  ← `clean_monthly_sip_inflows.csv` (04_monthly_sip_inflows.csv)

| Column | Type | Description |
|---|---|---|
| month | DATE | Month |
| sip_inflow_crore | REAL | Monthly SIP inflow (₹ crore) |
| active_sip_accounts_crore | REAL | Active SIP accounts (crore) |
| new_sip_accounts_lakh | REAL | New SIP accounts (lakh) |
| sip_aum_lakh_crore | REAL | SIP AUM (₹ lakh crore) |
| yoy_growth_pct | REAL | Year-over-year inflow growth (%) |

## fact_category_inflows  ← `clean_category_inflows.csv` (05_category_inflows.csv)

| Column | Type | Description |
|---|---|---|
| month | DATE | Month |
| category | TEXT | Fund category |
| net_inflow_crore | REAL | Net inflow (₹ crore) |

## fact_folio_count  ← `clean_industry_folio_count.csv` (06_industry_folio_count.csv)

| Column | Type | Description |
|---|---|---|
| month | DATE | Month |
| total_folios_crore | REAL | Total folios (crore) |
| equity_folios_crore | REAL | Equity folios (crore) |
| debt_folios_crore | REAL | Debt folios (crore) |
| hybrid_folios_crore | REAL | Hybrid folios (crore) |
| others_folios_crore | REAL | Other folios (crore) |

## fact_benchmark  ← `clean_benchmark_indices.csv` (10_benchmark_indices.csv)

| Column | Type | Description |
|---|---|---|
| date | DATE | Trading date |
| index_name | TEXT | Index (e.g. NIFTY50) |
| close_value | REAL | Index close |

---

## Cleaning rules applied (Day 2)
- **fact_nav**: dates parsed; sorted by (amfi_code, date); NAV forward-filled
  within scheme; duplicates dropped; NAV ≤ 0 removed; `daily_return` derived.
- **fact_transactions**: `transaction_type` mapped to {SIP, Lumpsum, Redemption};
  `amount_inr` ≤ 0 removed; `kyc_status` title-cased; dates parsed; dups dropped.
- **fact_performance**: numeric coercion of returns/ratios; `neg_sharpe_flag`
  and `expense_ratio_out_of_range` QC flags added.
- **all datasets**: string trim, date parsing, duplicate removal.

## Known data-quality note
The AMFI codes given in the Day 1 brief are mislabelled relative to the live
mfapi.in API (e.g. 125497 = SBI Small Cap, not "HDFC Top 100"). The 10 provided
CSVs are internally consistent (40 schemes, 100% NAV coverage); the mismatch
only affects the live-fetch scheme labels. See `reports/day1_data_quality.md`.
