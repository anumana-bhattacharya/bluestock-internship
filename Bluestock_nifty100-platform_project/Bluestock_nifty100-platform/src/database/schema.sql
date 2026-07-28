PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY NOT NULL,
    company_logo TEXT,
    company_name TEXT NOT NULL,
    chart_link TEXT,
    about_company TEXT,
    website TEXT,
    nse_profile TEXT,
    bse_profile TEXT,
    face_value REAL,
    book_value REAL,
    roce_percentage REAL,
    roe_percentage REAL
);

CREATE TABLE IF NOT EXISTS profit_and_loss (
    source_id INTEGER,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    period_kind TEXT,
    sales REAL NOT NULL,
    expenses REAL,
    operating_profit REAL,
    opm_percentage REAL,
    other_income REAL,
    interest REAL,
    depreciation REAL,
    profit_before_tax REAL,
    tax_percentage REAL,
    net_profit REAL NOT NULL,
    eps REAL,
    dividend_payout REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS balance_sheet (
    source_id INTEGER,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    period_kind TEXT,
    equity_capital REAL,
    reserves REAL,
    borrowings REAL,
    other_liabilities REAL,
    total_liabilities REAL NOT NULL,
    fixed_assets REAL,
    cwip REAL,
    investments REAL,
    other_asset REAL,
    total_assets REAL NOT NULL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS cash_flow (
    source_id INTEGER,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    period_kind TEXT,
    operating_activity REAL,
    investing_activity REAL,
    financing_activity REAL,
    net_cash_flow REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS analysis (
    source_id INTEGER PRIMARY KEY NOT NULL,
    company_id TEXT NOT NULL,
    compounded_sales_growth TEXT,
    compounded_profit_growth TEXT,
    stock_price_cagr TEXT,
    roe TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS documents (
    source_id INTEGER,
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    annual_report TEXT,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS pros_and_cons (
    source_id INTEGER PRIMARY KEY NOT NULL,
    company_id TEXT NOT NULL,
    pros TEXT,
    cons TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS sectors (
    source_id INTEGER,
    company_id TEXT PRIMARY KEY NOT NULL,
    broad_sector TEXT NOT NULL,
    sub_sector TEXT NOT NULL,
    index_weight_pct REAL,
    market_cap_category TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS market_cap (
    source_id INTEGER,
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    market_cap_crore REAL NOT NULL,
    enterprise_value_crore REAL,
    pe_ratio REAL,
    pb_ratio REAL,
    ev_ebitda REAL,
    dividend_yield_pct REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS stock_prices (
    source_id INTEGER,
    company_id TEXT NOT NULL,
    date TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL NOT NULL,
    volume REAL,
    adjusted_close REAL,
    PRIMARY KEY (company_id, date),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS financial_ratios_reference (
    source_id INTEGER,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    period_kind TEXT,
    net_profit_margin_pct REAL,
    operating_profit_margin_pct REAL,
    return_on_equity_pct REAL,
    debt_to_equity REAL,
    interest_coverage REAL,
    asset_turnover REAL,
    free_cash_flow_cr REAL,
    capex_cr REAL,
    earnings_per_share REAL,
    book_value_per_share REAL,
    dividend_payout_ratio_pct REAL,
    total_debt_cr REAL,
    cash_from_operations_cr REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS peer_groups (
    source_id INTEGER,
    peer_group_name TEXT NOT NULL,
    company_id TEXT NOT NULL,
    is_benchmark INTEGER NOT NULL,
    PRIMARY KEY (peer_group_name, company_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS computed_ratios (
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    net_profit_margin_pct REAL,
    operating_profit_margin_pct REAL,
    ebit_margin_pct REAL,
    return_on_equity_pct REAL,
    return_on_capital_employed_pct REAL,
    return_on_assets_pct REAL,
    debt_to_equity REAL,
    interest_coverage REAL,
    interest_coverage_status TEXT,
    net_debt_cr REAL,
    net_debt_to_ebitda REAL,
    asset_turnover REAL,
    fixed_asset_turnover REAL,
    free_cash_flow_cr REAL,
    cfo_to_pat REAL,
    capex_intensity_pct REAL,
    fcf_conversion_pct REAL,
    book_value_per_share REAL,
    earnings_per_share REAL,
    dividend_payout_ratio_pct REAL,
    revenue_cagr_3y REAL,
    revenue_cagr_5y REAL,
    revenue_cagr_10y REAL,
    pat_cagr_3y REAL,
    pat_cagr_5y REAL,
    pat_cagr_10y REAL,
    eps_cagr_3y REAL,
    eps_cagr_5y REAL,
    eps_cagr_10y REAL,
    revenue_cagr_3y_flag TEXT,
    revenue_cagr_5y_flag TEXT,
    revenue_cagr_10y_flag TEXT,
    pat_cagr_3y_flag TEXT,
    pat_cagr_5y_flag TEXT,
    pat_cagr_10y_flag TEXT,
    eps_cagr_3y_flag TEXT,
    eps_cagr_5y_flag TEXT,
    eps_cagr_10y_flag TEXT,
    price_to_earnings REAL,
    price_to_book REAL,
    ev_to_ebitda REAL,
    fcf_yield_pct REAL,
    capital_allocation_label TEXT,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS health_scores (
    company_id TEXT PRIMARY KEY NOT NULL,
    year TEXT NOT NULL,
    profitability_score REAL NOT NULL,
    cash_quality_score REAL NOT NULL,
    growth_score REAL NOT NULL,
    leverage_score REAL NOT NULL,
    health_score REAL NOT NULL CHECK (health_score BETWEEN 0 AND 100),
    health_band TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS sector_benchmarks (
    broad_sector TEXT PRIMARY KEY NOT NULL,
    company_count INTEGER NOT NULL,
    median_roe REAL,
    median_npm REAL,
    median_opm REAL,
    median_debt_to_equity REAL,
    median_revenue_cagr_3y REAL,
    median_fcf_conversion REAL,
    median_health_score REAL,
    sector_rank INTEGER
);

CREATE TABLE IF NOT EXISTS peer_percentiles (
    peer_group_name TEXT NOT NULL,
    company_id TEXT NOT NULL,
    roe_percentile REAL,
    opm_percentile REAL,
    revenue_growth_percentile REAL,
    fcf_conversion_percentile REAL,
    debt_to_equity_percentile REAL,
    composite_percentile REAL,
    PRIMARY KEY (peer_group_name, company_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS valuation_summary (
    company_id TEXT PRIMARY KEY NOT NULL,
    year INTEGER NOT NULL,
    broad_sector TEXT NOT NULL,
    pe_ratio REAL,
    pb_ratio REAL,
    ev_ebitda REAL,
    dividend_yield_pct REAL,
    fcf_yield_pct REAL,
    sector_median_pe REAL,
    valuation_flag TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

DROP TABLE IF EXISTS cashflow_intelligence;
CREATE TABLE cashflow_intelligence (
    company_id TEXT PRIMARY KEY NOT NULL,
    sector TEXT NOT NULL,
    cfo_quality_score REAL,
    cfo_quality_label TEXT NOT NULL,
    capex_intensity_pct REAL,
    capex_label TEXT NOT NULL,
    fcf_cagr_5yr REAL,
    fcf_conversion_pct REAL,
    distress_flag INTEGER NOT NULL,
    deleveraging_flag INTEGER NOT NULL,
    capital_allocation_label TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS cluster_labels (
    company_id TEXT PRIMARY KEY NOT NULL,
    cluster_id INTEGER NOT NULL,
    cluster_label TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS portfolio_stats (
    metric TEXT PRIMARY KEY NOT NULL,
    p10 REAL,
    median REAL,
    p90 REAL,
    minimum REAL,
    maximum REAL
);

DROP TABLE IF EXISTS analysis_parsed;
CREATE TABLE analysis_parsed (
    company_id TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    period_years INTEGER NOT NULL,
    value_pct REAL NOT NULL,
    PRIMARY KEY (company_id, metric_type, period_years),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

DROP TABLE IF EXISTS pros_cons_generated;
CREATE TABLE pros_cons_generated (
    company_id TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('pro', 'con')),
    rule_id TEXT NOT NULL,
    text TEXT NOT NULL,
    confidence_pct REAL NOT NULL CHECK (confidence_pct > 60 AND confidence_pct <= 100),
    PRIMARY KEY (company_id, type, rule_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS load_audit (
    table_name TEXT NOT NULL,
    rows_in INTEGER NOT NULL,
    rows_out INTEGER NOT NULL,
    rejected_rows INTEGER NOT NULL,
    runtime_seconds REAL NOT NULL,
    load_timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS validation_failures (
    table_name TEXT,
    rule_id TEXT,
    severity TEXT,
    company_id TEXT,
    year TEXT,
    field TEXT,
    issue TEXT,
    action TEXT
);

CREATE INDEX IF NOT EXISTS idx_pl_year ON profit_and_loss(year);
CREATE INDEX IF NOT EXISTS idx_bs_year ON balance_sheet(year);
CREATE INDEX IF NOT EXISTS idx_cf_year ON cash_flow(year);
CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year);
CREATE INDEX IF NOT EXISTS idx_market_cap_year ON market_cap(year);
CREATE INDEX IF NOT EXISTS idx_prices_date ON stock_prices(date);
CREATE INDEX IF NOT EXISTS idx_ratio_year ON computed_ratios(year);
CREATE INDEX IF NOT EXISTS idx_sector_broad ON sectors(broad_sector);
CREATE INDEX IF NOT EXISTS idx_peer_group ON peer_groups(peer_group_name);
