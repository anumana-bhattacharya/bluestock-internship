# Day 1 — Data Quality Summary

Datasets loaded: **10**

## Dataset overview

| Dataset | Rows | Cols | Anomalies |
|---|---:|---:|---:|
| fund_master | 40 | 15 | 1 |
| nav_history | 46,000 | 3 | 0 |
| aum_by_house | 90 | 5 | 0 |
| monthly_sip | 48 | 6 | 1 |
| category_inflows | 144 | 3 | 0 |
| folio_count | 21 | 6 | 0 |
| performance | 40 | 19 | 0 |
| transactions | 32,778 | 13 | 0 |
| holdings | 322 | 8 | 1 |
| benchmark | 8,050 | 3 | 0 |

## Anomalies by dataset

### fund_master
- `min_sip_amount` is constant / single-valued

### nav_history
- none detected

### aum_by_house
- none detected

### monthly_sip
- `yoy_growth_pct` has 12 nulls (25.0%)

### category_inflows
- none detected

### folio_count
- none detected

### performance
- none detected

### transactions
- none detected

### holdings
- `portfolio_date` is constant / single-valued

### benchmark
- none detected

## Fund master structure

- **Fund houses**: 10 unique (`fund_house`)
- **Categories**: 2 unique (`category`)
- **Sub-categories**: 12 unique (`sub_category`)
- **Risk grades**: 5 unique (`risk_category`)
- **SEBI category codes**: 9 unique (`sebi_category_code`)
- **AMFI code** (`amfi_code`): 100% numeric, lengths {6: np.int64(40)}, range 100016–149324

## AMFI code validation

- fund_master codes: **40**, nav_history codes: **40**
- NAV coverage of master: **100.0%**
- Codes in master but missing from NAV: **0**
- Orphan codes in NAV not in master: **0**

## Live NAV fetch (mfapi.in)

Fetched via the AMFI-backed mfapi.in API. **Important: the human labels in the
task brief do not match the actual schemes behind these AMFI codes.**

| Code | Brief label | Actual scheme (API) | Rows | Range |
|---|---|---|---:|---|
| 125497 | HDFC Top 100 Direct | SBI Small Cap Fund – Direct – Growth | 1745 | 2019-05→2026-05 |
| 119551 | SBI Bluechip | Aditya Birla SL Banking & PSU Debt | 1757 | 2019-02→2026-06 |
| 120503 | ICICI Bluechip | Axis ELSS Tax Saver – Direct | 1753 | 2019-04→2026-06 |
| 118632 | Nippon Large Cap | Nippon India Large Cap – Direct | 1* | latest only |
| 119092 | Axis Bluechip | HDFC Money Market – Direct | 1* | latest only |
| 120841 | Kotak Bluechip | quant Mid Cap – Direct | 1743 | 2019-04→2026-05 |

\* 118632 and 119092 returned only the latest NAV in this environment (API
intermittency); running `live_nav_fetch.py` locally retrieves full history.

Action: reconcile the code→scheme mapping with the analytics requirements
before downstream work — the codes are valid AMFI codes but mislabelled.
