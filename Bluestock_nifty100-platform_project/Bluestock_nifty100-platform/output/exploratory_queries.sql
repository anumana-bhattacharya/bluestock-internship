-- 01. Row counts for all twelve source tables.
SELECT 'companies' AS table_name, COUNT(*) AS row_count FROM companies
UNION ALL SELECT 'profit_and_loss', COUNT(*) FROM profit_and_loss
UNION ALL SELECT 'balance_sheet', COUNT(*) FROM balance_sheet
UNION ALL SELECT 'cash_flow', COUNT(*) FROM cash_flow
UNION ALL SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'pros_and_cons', COUNT(*) FROM pros_and_cons
UNION ALL SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL SELECT 'market_cap', COUNT(*) FROM market_cap
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL SELECT 'financial_ratios_reference', COUNT(*) FROM financial_ratios_reference
UNION ALL SELECT 'peer_groups', COUNT(*) FROM peer_groups;

-- 02. Null analysis for critical P&L fields.
SELECT
    SUM(company_id IS NULL) AS null_company,
    SUM(year IS NULL) AS null_year,
    SUM(sales IS NULL) AS null_sales,
    SUM(net_profit IS NULL) AS null_net_profit
FROM profit_and_loss;

-- 03. Fiscal-year coverage per company.
SELECT company_id, MIN(year) AS first_year, MAX(year) AS latest_year,
       COUNT(*) AS periods
FROM computed_ratios
GROUP BY company_id
ORDER BY periods, company_id;

-- 04. Master companies absent from each statement table.
SELECT c.company_id, 'profit_and_loss' AS missing_from
FROM companies c LEFT JOIN profit_and_loss p USING (company_id)
WHERE p.company_id IS NULL
UNION ALL
SELECT c.company_id, 'balance_sheet'
FROM companies c LEFT JOIN balance_sheet b USING (company_id)
WHERE b.company_id IS NULL
UNION ALL
SELECT c.company_id, 'cash_flow'
FROM companies c LEFT JOIN cash_flow f USING (company_id)
WHERE f.company_id IS NULL;

-- 05. Duplicate detection after load (must return zero rows).
SELECT company_id, year, COUNT(*) AS duplicates
FROM computed_ratios
GROUP BY company_id, year
HAVING COUNT(*) > 1;

-- 06. Referential-integrity audit for P&L.
SELECT p.company_id
FROM profit_and_loss p LEFT JOIN companies c USING (company_id)
WHERE c.company_id IS NULL;

-- 07. Statement completeness by matched company-period.
SELECT p.company_id, p.year,
       b.company_id IS NOT NULL AS has_balance_sheet,
       f.company_id IS NOT NULL AS has_cash_flow
FROM profit_and_loss p
LEFT JOIN balance_sheet b USING (company_id, year)
LEFT JOIN cash_flow f USING (company_id, year)
ORDER BY p.company_id, p.year;

-- 08. Broad-sector company counts (observed taxonomy).
SELECT broad_sector, COUNT(*) AS companies
FROM sectors
GROUP BY broad_sector
ORDER BY companies DESC, broad_sector;

-- 09. Health-band distribution.
SELECT health_band, COUNT(*) AS companies,
       ROUND(AVG(health_score), 2) AS average_score
FROM health_scores
GROUP BY health_band
ORDER BY average_score DESC;

-- 10. Companies whose latest P/E is far above their sector median.
SELECT company_id, broad_sector, pe_ratio, sector_median_pe, valuation_flag
FROM valuation_summary
WHERE valuation_flag = 'Caution'
ORDER BY pe_ratio DESC;

-- 11. Peer direction check: highest-ROE percentile in each group.
SELECT peer_group_name, company_id, roe_percentile
FROM peer_percentiles p
WHERE roe_percentile = (
    SELECT MAX(p2.roe_percentile)
    FROM peer_percentiles p2
    WHERE p2.peer_group_name = p.peer_group_name
)
ORDER BY peer_group_name;

-- 12. Cash-flow distress alerts.
SELECT company_id, year, cfo_quality_5y, fcf_conversion_pct
FROM cashflow_intelligence
WHERE distress_flag = 1
ORDER BY company_id;

-- 13. Ratio cross-sectional outliers after scoring input winsorisation.
SELECT company_id, year, return_on_equity_pct, debt_to_equity,
       operating_profit_margin_pct
FROM computed_ratios r
WHERE year = (SELECT MAX(r2.year) FROM computed_ratios r2 WHERE r2.company_id = r.company_id)
ORDER BY ABS(return_on_equity_pct) DESC
LIMIT 20;

-- 14. Direct SQLite foreign-key check (must return zero rows).
PRAGMA foreign_key_check;
