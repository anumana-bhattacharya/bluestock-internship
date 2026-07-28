# Nifty100 Financial Intelligence Platform

Production-grade, registry-driven financial analytics for the supplied 92-company
Nifty100 universe. The repository loads 12 Excel sources, applies an auditable data
quality contract, persists clean data to SQLite, computes 30+ company-year KPIs,
scores and screens the full universe, exposes dashboard/API layers, clusters
companies, and generates PDF/Excel deliverables.

## Fresh setup

Python 3.10 or newer and a C compiler-free wheel-capable `pip` are sufficient.
Typical setup completes in under 30 minutes:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
make all
make test
```

The source workbooks are already placed under `data/raw/` and `data/supporting/`.
To replace them, preserve the filenames and the header convention in
`src/config/tables.py`.

## Verified commands

```bash
make load        # Normalize, validate, deduplicate, and load all 12 sources
make ratios      # Sprint 1 plus the raw-derived ratio engine
make sprint3     # Health, sector, peer, valuation, and screener layers
make sprint456   # Intelligence, ML, PDFs, workbooks, API/dashboard data
make all         # Full six-sprint pipeline
make test        # 80% coverage gate plus HTML report in htmlcov/
make explore     # Execute 14 exploratory SQL statements
make dashboard   # Streamlit at its displayed local URL
make api         # FastAPI at http://127.0.0.1:8000/docs
```

`make all` is idempotent. Source and derived tables are replaced inside a single
SQLite transaction; primary keys are deduplicated keep-last and foreign keys remain
enabled.

## Architecture

The table registry is the control plane. `TableSpec` defines path, header row,
primary key, company FK behavior, period handling, critical fields, positivity
warnings, and URLs. Loader, validator, deduplicator, and database writer consume the
same registry.

```text
Excel sources
  -> normalize identifiers and periods
  -> validate and quarantine
  -> deduplicate keep-last
  -> parameterized SQLite persistence
  -> ratios and growth
  -> score / screen / sector / peer / valuation
  -> cash-flow / NLP / clustering
  -> CSV / Excel / PDF / Streamlit / FastAPI
```

Pure calculation modules do not open files or framework sessions. SQLite queries
are isolated in `src/api/queries.py` and `src/dashboard/data.py`; FastAPI and
Streamlit are thin wrappers.

## Configuration

- `.env.template`: orphan policy, winsor quantiles, and KMeans count.
- `config/analytics.yaml`: health bands, valuation thresholds, cash-flow tiers.
- `config/screener_config.yaml`: six declarative investment screens.
- `config/validation_rules.yaml`: 14-rule severity/action contract.
- `src/config/tables.py`: source-to-target registry.

The default orphan policy is `quarantine`. Set
`N100_ORPHAN_POLICY=load` only if the companies master has first been corrected;
otherwise SQLite FK enforcement will reject the affected rows.

## Main artifacts

- `nifty100.db`: 12 source tables, derived analytical tables, PK/FK constraints,
  and indexes.
- `output/load_audit.csv`, `output/validation_failures.csv`.
- `output/computed_ratios.csv`, `output/ratio_edge_cases.csv`,
  `output/ratio_crosscheck_summary.csv`.
- `output/health_scores.csv`, `output/sector_benchmarks.csv`,
  `output/peer_percentiles.csv`, six screener CSVs.
- `output/screener_output.xlsx`, `output/valuation_summary.xlsx`,
  `output/cashflow_intelligence.xlsx`, `output/nifty100_full_universe.xlsx`.
- `output/analysis_parsed.csv`, `output/parse_failures.csv`,
  `output/analysis_cross_validation.csv`, `output/pros_cons_generated.csv`.
- `output/distress_alerts.csv`, `output/pattern_changes.csv`,
  `output/capital_allocation_distribution.csv`.
- `reports/tearsheets/*_tearsheet.pdf`, `reports/sector/*_report.pdf`, and
  `reports/portfolio/portfolio_summary.pdf`.
- `output/cluster_labels.csv`, `output/correlation_heatmap.png`,
  `output/portfolio_stats.csv`.
- `output/pipeline_summary.json`: concrete exit-gate metrics from the latest run.

## API routes

The API exposes `/health`, `/companies`, `/companies/{ticker}`, `/pl/{ticker}`,
`/bs/{ticker}`, `/cashflow/{ticker}`, `/ratios/{ticker}`,
`/documents/{ticker}`, `/screener`, `/sectors`, `/sectors/{sector}`,
`/peers/{group}`, and `/portfolio/stats`. All values originating in request
parameters are bound parameters; selectable table names use a fixed whitelist.

## Important calculation conventions

- Fiscal keys are canonical `YYYY-MM`; document and market-cap years remain integer.
- TTM rows never enter fiscal-year tables.
- ROE is `None` for non-positive equity; ICR is `None` and status `Debt Free` when
  interest is zero; P/E is `None` for non-positive PAT.
- The source has no explicit CapEx or cash line. CapEx uses the absolute negative
  investing cash flow as an auditable proxy, and net debt uses investments as the
  available liquid-asset proxy. These limitations are surfaced in
  `docs/delivery_report.md`.
- Supplied market-cap multiples are simulated and remain in `market_cap`; only
  explicit joined outputs appear in `computed_ratios` and valuation summaries.
- Health and clustering inputs are winsorised P10-P90 before scaling.

## Documentation

See `docs/delivery_report.md` for the measured inventory, source-to-target map,
Mermaid ER model, DQ hit counts, verification results, and risks. See
`docs/data_dictionary.md`, `docs/architecture.md`, and the six sprint reports for
implementation details. `docs/sprint_5_report.md` contains the measured NLP,
cash-flow, dashboard, workbook, and PDF verification evidence.
