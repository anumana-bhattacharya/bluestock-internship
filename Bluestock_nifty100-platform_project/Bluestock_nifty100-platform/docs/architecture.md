# Architecture and Operational Model

## Control plane

`src/config/tables.py` is the declarative control plane. Every `TableSpec` defines
the source path, Excel header, normalized primary key, company FK, year handling,
critical fields, and warning sets. The loader and validator do not switch on file
names.

## Data plane

The ETL reads Excel into pandas, normalizes headings/tickers/periods, emits one
row-level failure per hit, quarantines critical rows, and deduplicates keep-last.
SQLite is initialized from versioned SQL and loaded with bound `executemany`
parameters. Every connection enables FKs.

## Analytical plane

Financial formulas and CAGR sign-state logic are pure functions. Company-period
alignment is performed before formulas run. The supplied ratio file is never used
as a calculation input; it is joined afterward for ROE/NPM divergence measurement.
Latest-year company features feed health, screens, sector/peer, valuation, cash
flow, and KMeans.

## Serving plane

`src/dashboard/data.py` and `src/api/queries.py` own SQL. Streamlit and FastAPI only
map user interactions and HTTP routes to those functions. Dynamic history table
selection is a fixed whitelist, and all user values are bound parameters.

## Reliability

- Idempotent replacement loads inside transactions.
- PK uniqueness after keep-last deduplication.
- `PRAGMA foreign_key_check` in the pipeline and tests.
- Row-level DQ and table-level load audit.
- Deterministic KMeans (`random_state=42`, `n_init=20`).
- Fixed report filenames and PDF signature/size checks.
- Full rebuild in the coverage-enabled test run.
