-- ============================================================================
-- Bluestock Mutual Fund Analytics — SQLite schema (Day 2)
-- Star-style design: dim_fund is the central dimension; fact_* tables hold
-- measurements keyed by amfi_code and/or date.
-- ============================================================================
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fact_nav;
DROP TABLE IF EXISTS fact_transactions;
DROP TABLE IF EXISTS fact_performance;
DROP TABLE IF EXISTS fact_holdings;
DROP TABLE IF EXISTS fact_aum;
DROP TABLE IF EXISTS fact_sip_inflows;
DROP TABLE IF EXISTS fact_category_inflows;
DROP TABLE IF EXISTS fact_folio_count;
DROP TABLE IF EXISTS fact_benchmark;
DROP TABLE IF EXISTS dim_fund;

-- ---------------------------------------------------------------------------
-- Dimension: one row per scheme
-- ---------------------------------------------------------------------------
CREATE TABLE dim_fund (
    amfi_code           TEXT PRIMARY KEY,
    fund_house          TEXT,
    scheme_name         TEXT,
    category            TEXT,
    sub_category        TEXT,
    plan                TEXT,
    launch_date         DATE,
    benchmark           TEXT,
    expense_ratio_pct   REAL,
    exit_load_pct       REAL,
    min_sip_amount      REAL,
    min_lumpsum_amount  REAL,
    fund_manager        TEXT,
    risk_category       TEXT,
    sebi_category_code  TEXT
);

-- ---------------------------------------------------------------------------
-- Fact: daily NAV history
-- ---------------------------------------------------------------------------
CREATE TABLE fact_nav (
    amfi_code     TEXT NOT NULL,
    nav_date      DATE NOT NULL,
    nav           REAL NOT NULL CHECK (nav > 0),
    daily_return  REAL,
    PRIMARY KEY (amfi_code, nav_date),
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);
CREATE INDEX idx_nav_date ON fact_nav(nav_date);

-- ---------------------------------------------------------------------------
-- Fact: investor transactions
-- ---------------------------------------------------------------------------
CREATE TABLE fact_transactions (
    investor_id        TEXT,
    transaction_date   DATE,
    amfi_code          TEXT,
    transaction_type   TEXT CHECK (transaction_type IN ('SIP','Lumpsum','Redemption')),
    amount_inr         REAL CHECK (amount_inr > 0),
    state              TEXT,
    city               TEXT,
    city_tier          TEXT,
    age_group          TEXT,
    gender             TEXT,
    annual_income_lakh REAL,
    payment_mode       TEXT,
    kyc_status         TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);
CREATE INDEX idx_txn_code  ON fact_transactions(amfi_code);
CREATE INDEX idx_txn_state ON fact_transactions(state);

-- ---------------------------------------------------------------------------
-- Fact: scheme performance snapshot
-- ---------------------------------------------------------------------------
CREATE TABLE fact_performance (
    amfi_code                   TEXT PRIMARY KEY,
    scheme_name                 TEXT,
    fund_house                  TEXT,
    category                    TEXT,
    plan                        TEXT,
    return_1yr_pct              REAL,
    return_3yr_pct              REAL,
    return_5yr_pct              REAL,
    benchmark_3yr_pct           REAL,
    alpha                       REAL,
    beta                        REAL,
    sharpe_ratio                REAL,
    sortino_ratio               REAL,
    std_dev_ann_pct             REAL,
    max_drawdown_pct            REAL,
    aum_crore                   REAL,
    expense_ratio_pct           REAL,
    morningstar_rating          INTEGER,
    risk_grade                  TEXT,
    neg_sharpe_flag             INTEGER,
    expense_ratio_out_of_range  INTEGER,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- ---------------------------------------------------------------------------
-- Fact: portfolio holdings
-- ---------------------------------------------------------------------------
CREATE TABLE fact_holdings (
    amfi_code         TEXT,
    stock_symbol      TEXT,
    stock_name        TEXT,
    sector            TEXT,
    weight_pct        REAL,
    market_value_cr   REAL,
    current_price_inr REAL,
    portfolio_date    DATE,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- ---------------------------------------------------------------------------
-- Industry-level facts (not keyed to a single scheme)
-- ---------------------------------------------------------------------------
CREATE TABLE fact_aum (
    date            DATE,
    fund_house      TEXT,
    aum_lakh_crore  REAL,
    aum_crore       REAL,
    num_schemes     INTEGER
);

CREATE TABLE fact_sip_inflows (
    month                    DATE,
    sip_inflow_crore         REAL,
    active_sip_accounts_crore REAL,
    new_sip_accounts_lakh    REAL,
    sip_aum_lakh_crore       REAL,
    yoy_growth_pct           REAL
);

CREATE TABLE fact_category_inflows (
    month            DATE,
    category         TEXT,
    net_inflow_crore REAL
);

CREATE TABLE fact_folio_count (
    month                DATE,
    total_folios_crore   REAL,
    equity_folios_crore  REAL,
    debt_folios_crore    REAL,
    hybrid_folios_crore  REAL,
    others_folios_crore  REAL
);

CREATE TABLE fact_benchmark (
    date        DATE,
    index_name  TEXT,
    close_value REAL
);
