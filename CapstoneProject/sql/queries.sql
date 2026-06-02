-- ============================================================================
-- Bluestock MF Analytics — Day 2 analytics queries (SQLite)
-- Run:  sqlite3 bluestock_mf.db < sql/queries.sql
-- ============================================================================

-- 1. Top 5 funds by AUM (from performance snapshot)
SELECT scheme_name, fund_house, aum_crore
FROM fact_performance
ORDER BY aum_crore DESC
LIMIT 5;

-- 2. Average NAV per month (across all schemes)
SELECT strftime('%Y-%m', nav_date) AS month,
       ROUND(AVG(nav), 2) AS avg_nav,
       COUNT(*) AS observations
FROM fact_nav
GROUP BY month
ORDER BY month
LIMIT 12;

-- 3. SIP inflow YoY growth (latest 12 months reported)
SELECT strftime('%Y-%m', month) AS month,
       sip_inflow_crore,
       yoy_growth_pct
FROM fact_sip_inflows
ORDER BY month DESC
LIMIT 12;

-- 4. Transactions by state (count + total value)
SELECT state,
       COUNT(*) AS num_txns,
       ROUND(SUM(amount_inr)/1e7, 2) AS total_cr
FROM fact_transactions
GROUP BY state
ORDER BY total_cr DESC
LIMIT 10;

-- 5. Funds with expense ratio < 1%
SELECT scheme_name, fund_house, expense_ratio_pct
FROM dim_fund
WHERE expense_ratio_pct < 1.0
ORDER BY expense_ratio_pct;

-- 6. Best risk-adjusted performers: top 10 by Sharpe ratio
SELECT scheme_name, category, sharpe_ratio, return_3yr_pct
FROM fact_performance
ORDER BY sharpe_ratio DESC
LIMIT 10;

-- 7. AUM by fund house (latest reported date)
SELECT fund_house, aum_crore, num_schemes
FROM fact_aum
WHERE date = (SELECT MAX(date) FROM fact_aum)
ORDER BY aum_crore DESC;

-- 8. Net category inflows — total over the full period
SELECT category, ROUND(SUM(net_inflow_crore), 0) AS total_net_inflow_crore
FROM fact_category_inflows
GROUP BY category
ORDER BY total_net_inflow_crore DESC;

-- 9. Latest NAV per scheme (most recent observation)
SELECT d.scheme_name, n.nav_date, n.nav
FROM fact_nav n
JOIN dim_fund d ON d.amfi_code = n.amfi_code
JOIN (SELECT amfi_code, MAX(nav_date) AS mx FROM fact_nav GROUP BY amfi_code) m
  ON m.amfi_code = n.amfi_code AND m.mx = n.nav_date
ORDER BY d.scheme_name
LIMIT 10;

-- 10. Top portfolio sectors by aggregate market value
SELECT sector,
       ROUND(SUM(market_value_cr), 1) AS total_market_value_cr,
       COUNT(DISTINCT amfi_code) AS held_by_funds
FROM fact_holdings
GROUP BY sector
ORDER BY total_market_value_cr DESC
LIMIT 10;

-- ============================================================================
-- SAMPLE RESULTS (generated 2026-06-02 against bluestock_mf.db)
-- ============================================================================
-- ### 1. Top 5 funds by AUM (from performance snapshot)
-- scheme_name | fund_house | aum_crore
-- Mirae Asset Emerging Bluechip Fund - Regular - Growth | Mirae Asset MF | 49046.0
-- Kotak Emerging Equity Fund - Regular - Growth | Kotak Mahindra MF | 47469.0
-- Nippon India Small Cap Fund - Regular - Growth | Nippon India MF | 43630.0
-- DSP Top 100 Equity Fund - Regular - Growth | DSP Mutual Fund | 41828.0
-- UTI Mid Cap Fund - Regular - Growth | UTI Mutual Fund | 41728.0
-- 
-- ### 2. Average NAV per month (across all schemes)
-- month | avg_nav | observations
-- 2022-01 | 207.06 | 840
-- 2022-02 | 207.72 | 800
-- 2022-03 | 209.69 | 920
-- 2022-04 | 211.83 | 840
-- 2022-05 | 212.73 | 880
-- 2022-06 | 213.86 | 880
-- 2022-07 | 213.96 | 840
-- 2022-08 | 215.68 | 920
-- 2022-09 | 218.49 | 880
-- 2022-10 | 219.53 | 840
-- 
-- ### 3. SIP inflow YoY growth (latest 12 months reported)
-- month | sip_inflow_crore | yoy_growth_pct
-- 2025-12 | 31002.0 | 17.17
-- 2025-11 | 30200.0 | 19.27
-- 2025-10 | 29529.0 | 16.61
-- 2025-09 | 29361.0 | 19.8
-- 2025-08 | 28265.0 | 20.04
-- 2025-07 | 28464.0 | 22.0
-- 2025-06 | 27274.0 | 28.28
-- 2025-05 | 26688.0 | 25.52
-- 2025-04 | 26632.0 | 30.73
-- 2025-03 | 25926.0 | 27.27
-- 
-- ### 4. Transactions by state (count + total value)
-- state | num_txns | total_cr
-- Punjab | 2965 | 31.58
-- Tamil Nadu | 2806 | 31.52
-- Madhya Pradesh | 2931 | 30.83
-- Rajasthan | 2577 | 29.86
-- Gujarat | 2780 | 29.84
-- West Bengal | 2748 | 29.72
-- Telangana | 2718 | 29.02
-- Delhi | 2677 | 28.96
-- Uttar Pradesh | 2695 | 28.54
-- Haryana | 2736 | 27.96
-- 
-- ### 5. Funds with expense ratio < 1%
-- scheme_name | fund_house | expense_ratio_pct
-- Nippon India Gilt Securities Fund - Regular - Growth | Nippon India MF | 0.55
-- HDFC Short Term Debt Fund - Regular - Growth | HDFC Mutual Fund | 0.56
-- Kotak Liquid Fund - Regular - Growth | Kotak Mahindra MF | 0.6
-- SBI Bluechip Fund - Direct Plan - Growth | SBI Mutual Fund | 0.66
-- SBI Small Cap Fund - Direct Plan - Growth | SBI Mutual Fund | 0.72
-- Nippon India Large Cap Fund - Direct - Growth | Nippon India MF | 0.72
-- ICICI Pru Liquid Fund - Regular - Growth | ICICI Prudential MF | 0.74
-- Axis Bluechip Fund - Direct - Growth | Axis Mutual Fund | 0.75
-- SBI Magnum Gilt Fund - Regular Plan - Growth | SBI Mutual Fund | 0.77
-- HDFC Mid-Cap Opportunities Fund - Direct - Growth | HDFC Mutual Fund | 0.78
-- 
-- ### 6. Best risk-adjusted performers: top 10 by Sharpe ratio
-- scheme_name | category | sharpe_ratio | return_3yr_pct
-- ICICI Pru Liquid Fund - Regular - Growth | Liquid | 7.68 | 7.68
-- Kotak Liquid Fund - Regular - Growth | Liquid | 6.18 | 6.18
-- ABSL Liquid Fund - Regular - Growth | Liquid | 5.14 | 5.14
-- HDFC Short Term Debt Fund - Regular - Growth | Short Duration | 1.84 | 7.37
-- SBI Magnum Gilt Fund - Regular Plan - Growth | Gilt | 1.52 | 6.07
-- Nippon India Gilt Securities Fund - Regular - Growth | Gilt | 1.33 | 5.31
-- HDFC Top 100 Fund - Regular Plan - Growth | Large Cap | 1.06 | 14.84
-- Mirae Asset Large Cap Fund - Regular - Growth | Large Cap | 1.06 | 14.81
-- ICICI Pru Bluechip Fund - Direct - Growth | Large Cap | 1.03 | 14.41
-- Nippon India Large Cap Fund - Regular - Growth | Large Cap | 1.0 | 14.0
-- 
-- ### 7. AUM by fund house (latest reported date)
-- fund_house | aum_crore | num_schemes
-- SBI Mutual Fund | 1250000.0 | 186
-- ICICI Prudential MF | 1074000.0 | 216
-- HDFC Mutual Fund | 930000.0 | 195
-- Nippon India MF | 700000.0 | 177
-- Kotak Mahindra MF | 580000.0 | 168
-- Aditya Birla Sun Life MF | 460000.0 | 199
-- UTI Mutual Fund | 410000.0 | 142
-- Axis Mutual Fund | 350000.0 | 95
-- Mirae Asset MF | 290000.0 | 56
-- DSP Mutual Fund | 230000.0 | 88
-- 
-- ### 8. Net category inflows — total over the full period
-- category | total_net_inflow_crore
-- Liquid | 451275.0
-- Sectoral/Thematic | 103829.0
-- Flexi Cap | 63989.0
-- Large & Mid Cap | 57752.0
-- Short Duration | 55530.0
-- Mid Cap | 55312.0
-- Small Cap | 46596.0
-- Hybrid | 38868.0
-- Large Cap | 25633.0
-- Value/Contra | 16980.0
-- 
-- ### 9. Latest NAV per scheme (most recent observation)
-- scheme_name | nav_date | nav
-- ABSL Frontline Equity Fund - Regular - Growth | 2026-05-29 | 773.2939
-- ABSL Liquid Fund - Regular - Growth | 2026-05-29 | 410.1021
-- ABSL Small Cap Fund - Regular - Growth | 2026-05-29 | 53.9836
-- Axis Bluechip Fund - Direct - Growth | 2026-05-29 | 58.4203
-- Axis Bluechip Fund - Regular - Growth | 2026-05-29 | 50.8387
-- Axis Midcap Fund - Regular - Growth | 2026-05-29 | 203.8581
-- Axis Small Cap Fund - Regular - Growth | 2026-05-29 | 56.1319
-- DSP Midcap Fund - Regular - Growth | 2026-05-29 | 245.3651
-- DSP Small Cap Fund - Regular - Growth | 2026-05-29 | 279.7511
-- DSP Top 100 Equity Fund - Regular - Growth | 2026-05-29 | 606.2349
-- 
-- ### 10. Top portfolio sectors by aggregate market value
-- sector | total_market_value_cr | held_by_funds
-- Banking | 62840.3 | 30
-- IT | 38477.1 | 27
-- Pharma | 34606.1 | 22
-- Automobile | 34297.0 | 26
-- Utilities | 25108.6 | 19
-- Infrastructure | 22433.4 | 18
-- FMCG | 21151.2 | 19
-- Telecom | 16051.5 | 15
-- Energy | 15286.5 | 13
-- Diversified | 13897.8 | 14
