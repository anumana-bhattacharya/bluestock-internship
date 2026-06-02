from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

DB_PATH = Path("bluestock_mf.db")
SCHEMA = Path("sql/schema.sql")
PROC = Path("data/processed")

# cleaned CSV  ->  target table
LOAD_MAP = {
    "clean_fund_master.csv":          "dim_fund",
    "clean_nav.csv":                  "fact_nav",
    "clean_transactions.csv":         "fact_transactions",
    "clean_performance.csv":          "fact_performance",
    "clean_portfolio_holdings.csv":   "fact_holdings",
    "clean_aum_by_fund_house.csv":    "fact_aum",
    "clean_monthly_sip_inflows.csv":  "fact_sip_inflows",
    "clean_category_inflows.csv":     "fact_category_inflows",
    "clean_industry_folio_count.csv": "fact_folio_count",
    "clean_benchmark_indices.csv":    "fact_benchmark",
}

# rename cleaned columns -> schema column names where they differ
RENAMES = {
    "fact_nav": {"date": "nav_date"},
}


def apply_schema() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA.read_text())
    conn.commit()
    conn.close()
    print(f"schema applied -> {DB_PATH}")


def load() -> None:
    engine = create_engine(f"sqlite:///{DB_PATH}")
    for csv, table in LOAD_MAP.items():
        df = pd.read_csv(PROC / csv)
        df = df.rename(columns=RENAMES.get(table, {}))
        # keep only columns that exist in the target table
        cols = pd.read_sql(f"SELECT * FROM {table} LIMIT 0", engine).columns
        df = df[[c for c in df.columns if c in cols]]
        df.to_sql(table, engine, if_exists="append", index=False)
        print(f"  loaded {len(df):>7,} rows -> {table}")
    return engine


def sanity_checks(engine) -> None:
    print("\nrow counts:")
    with engine.connect() as cx:
        tables = [r[0] for r in cx.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))]
        for t in tables:
            n = cx.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(f"  {t:<22} {n:>8,}")
        orphans = cx.execute(text(
            "SELECT COUNT(*) FROM fact_nav f LEFT JOIN dim_fund d "
            "ON f.amfi_code=d.amfi_code WHERE d.amfi_code IS NULL")).scalar()
        print(f"\nfact_nav rows with no dim_fund match: {orphans}")


def main() -> int:
    apply_schema()
    engine = load()
    sanity_checks(engine)
    print("\nDay 2 DB load complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
