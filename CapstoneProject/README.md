# Mutual Fund Analytics

# Day 1: Data Ingestion

Ingestion and validation layer for an AMFI mutual-fund analytics project.

## Setup

```bash
python -m venv .venv \&\& source .venv/bin/activate
pip install -r requirements.txt
```

## Scripts

### `data_ingestion.py`

Loads the 10 project CSVs, profiles each (`.shape`, `.dtypes`, `.head()`,
anomalies), explores the fund master (fund houses, categories, sub-categories,
risk grades, AMFI code structure), cross-validates AMFI codes between
`fund_master` and `nav_history`, and writes `reports/day1_data_quality.md`.

```bash
python data_ingestion.py --data-dir data
```

Place the 10 CSVs in `./data/`. Edit the `FILES` and `\*\_ALIASES` maps at the
top of the script if your filenames or column names differ.

### `live_nav_fetch.py`

Fetches live NAV history from the AMFI-backed `mfapi.in` API for 6 schemes
(HDFC Top 100 Direct `125497`, SBI Bluechip `119551`, ICICI Bluechip `120503`,
Nippon Large Cap `118632`, Axis Bluechip `119092`, Kotak Bluechip `120841`).


```bash
python live\_nav\_fetch.py
```

## Project layout

```
.
├── data/
│   ├── raw/               # 10 provided CSVs + fetched NAV CSVs (tracked)
│   └── processed/         # cleaned/derived data (generated)
├── notebooks/
│   └── day1_eda.ipynb     # exploratory data analysis
├── sql/                   # SQL scripts (later days)
├── dashboard/             # dashboard assets (later days)
├── reports/
│   └── day1_data_quality.md
├── data_ingestion.py
├── live_nav_fetch.py
└── requirements.txt
```

> Note: `sqlite3` is part of the Python standard library, so it is not in
> `requirements.txt` (it cannot be pip-installed).

## Day 1 deliverables

* \[x] `requirements.txt`
* \[x] `data_ingestion.py`
* \[x] `live_nav_fetch.py`
* \[x] Git repo with `Day 1: Data ingestion complete` commit

## Day 2 deliverables

* \[x] `10 clean CSVs`
* \[x] `bluestock_mf.db`
* \[x] `schema.sql`
* \[x] `queries.sql`
* \[x] `data_dictionary.md`
* \[x] `Update repo with latest code and data`

## Day 3 deliverables

* \[x] `EDA_Analysis.ipynb with 15+ charts`
* \[x] `EDA_Findings summary`
* \[x] `exported PNG charts`

