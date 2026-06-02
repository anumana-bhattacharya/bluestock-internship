from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_DIR = Path("data/raw")
REPORT_PATH = Path("reports/day1_data_quality.md")

# Logical name -> expected filename(s). First match wins. Adjust to taste.
FILES: dict[str, list[str]] = {
    "fund_master":     ["01_fund_master.csv", "fund_master.csv"],
    "nav_history":     ["02_nav_history.csv", "nav_history.csv"],
    "aum_by_house":    ["03_aum_by_fund_house.csv"],
    "monthly_sip":     ["04_monthly_sip_inflows.csv"],
    "category_inflows":["05_category_inflows.csv"],
    "folio_count":     ["06_industry_folio_count.csv"],
    "performance":     ["07_scheme_performance.csv"],
    "transactions":    ["08_investor_transactions.csv"],
    "holdings":        ["09_portfolio_holdings.csv"],
    "benchmark":       ["10_benchmark_indices.csv"],
}

# Candidate column names for the AMFI scheme code, by dataset.
CODE_ALIASES = ["amfi_code", "scheme_code", "scheme_id", "code", "amfi_scheme_code"]

pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 160)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def discover(data_dir: Path) -> dict[str, Path]:
    """Resolve logical dataset names to actual files that exist on disk.

    Falls back to loading every *.csv in the directory under its own stem
    when none of the configured aliases match, so nothing is silently missed.
    """
    found: dict[str, Path] = {}
    for name, candidates in FILES.items():
        for cand in candidates:
            p = data_dir / cand
            if p.exists():
                found[name] = p
                break
    # Catch any extra CSVs not covered by FILES.
    known = {p.name for p in found.values()}
    for p in sorted(data_dir.glob("*.csv")):
        if p.name not in known and p.stem not in found:
            found[p.stem] = p
    return found


def load_all(paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for name, path in paths.items():
        try:
            df = pd.read_csv(path)
            frames[name] = df
            print(f"[ok]   loaded {name:<14} <- {path.name}  ({len(df):,} rows)")
        except Exception as err:  # noqa: BLE001 - report and continue
            print(f"[fail] {name:<14} <- {path.name}: {err}")
    return frames


# ---------------------------------------------------------------------------
# Profiling
# ---------------------------------------------------------------------------
def profile(name: str, df: pd.DataFrame) -> list[str]:
    """Print shape/dtypes/head and return a list of anomaly strings."""
    print("\n" + "=" * 78)
    print(f"DATASET: {name}")
    print("=" * 78)
    print(f"shape: {df.shape}")
    print("\ndtypes:")
    print(df.dtypes)
    print("\nhead():")
    print(df.head())

    anomalies: list[str] = []

    # Nulls
    nulls = df.isna().sum()
    for col, n in nulls[nulls > 0].items():
        anomalies.append(f"`{col}` has {n:,} nulls ({n / len(df):.1%})")

    # Full-row duplicates
    dupes = df.duplicated().sum()
    if dupes:
        anomalies.append(f"{dupes:,} fully duplicated rows")

    # Constant columns
    for col in df.columns:
        if df[col].nunique(dropna=True) <= 1:
            anomalies.append(f"`{col}` is constant / single-valued")

    # Leading/trailing whitespace in object columns
    for col in df.select_dtypes(include="object").columns:
        s = df[col].dropna().astype(str)
        if (s != s.str.strip()).any():
            anomalies.append(f"`{col}` has leading/trailing whitespace")

    # Negative values in numeric columns that usually shouldn't be negative
    for col in df.select_dtypes(include=[np.number]).columns:
        if (df[col] < 0).any() and any(k in col.lower() for k in ("nav", "aum", "price", "amount", "ratio")):
            anomalies.append(f"`{col}` contains negative values")

    if anomalies:
        print("\nanomalies:")
        for a in anomalies:
            print(f"  - {a}")
    else:
        print("\nanomalies: none detected")
    return anomalies


def find_code_col(df: pd.DataFrame) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for alias in CODE_ALIASES:
        if alias in lower:
            return lower[alias]
    return None


def profile_fund_master(df: pd.DataFrame) -> list[str]:
    """Print categorical structure of the fund master and AMFI code shape."""
    print("\n" + "#" * 78)
    print("FUND MASTER EXPLORATION")
    print("#" * 78)
    lines: list[str] = []

    def show(label: str, candidates: list[str]) -> None:
        col = next((c for c in df.columns if c.lower() in candidates), None)
        if col is None:
            print(f"\n{label}: (column not found)")
            return
        vals = sorted(df[col].dropna().astype(str).unique())
        print(f"\n{label} ({len(vals)} unique) — column `{col}`:")
        print("  " + ", ".join(vals[:40]) + (" ..." if len(vals) > 40 else ""))
        lines.append(f"- **{label}**: {len(vals)} unique (`{col}`)")

    show("Fund houses", ["fund_house", "amc", "amc_name", "fund_house_name"])
    show("Categories", ["category", "scheme_category"])
    show("Sub-categories", ["sub_category", "subcategory", "scheme_sub_category"])
    show("Risk grades", ["risk_category", "risk_grade", "risk", "riskometer", "risk_level"])
    show("SEBI category codes", ["sebi_category_code", "sebi_code"])

    code_col = find_code_col(df)
    if code_col:
        codes = df[code_col].dropna().astype(str)
        lengths = codes.str.len().value_counts().sort_index()
        numeric = codes.str.fullmatch(r"\d+").mean()
        print(f"\nAMFI code column `{code_col}`:")
        print(f"  length distribution: {dict(lengths)}")
        print(f"  fully numeric: {numeric:.1%}")
        print(f"  range: {codes.min()} .. {codes.max()}")
        lines.append(
            f"- **AMFI code** (`{code_col}`): {numeric:.0%} numeric, "
            f"lengths {dict(lengths)}, range {codes.min()}–{codes.max()}"
        )
    return lines


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_codes(frames: dict[str, pd.DataFrame]) -> list[str]:
    """Confirm every fund_master AMFI code exists in nav_history."""
    print("\n" + "#" * 78)
    print("AMFI CODE VALIDATION (fund_master vs nav_history)")
    print("#" * 78)
    lines: list[str] = []

    fm = frames.get("fund_master")
    nav = frames.get("nav_history")
    if fm is None or nav is None:
        msg = "Skipped: fund_master and/or nav_history not loaded."
        print(msg)
        return [msg]

    fm_col, nav_col = find_code_col(fm), find_code_col(nav)
    if not fm_col or not nav_col:
        msg = f"Skipped: code column not found (fund_master={fm_col}, nav_history={nav_col})."
        print(msg)
        return [msg]

    fm_codes = set(fm[fm_col].dropna().astype(str))
    nav_codes = set(nav[nav_col].dropna().astype(str))

    missing_in_nav = fm_codes - nav_codes
    orphan_in_nav = nav_codes - fm_codes
    coverage = 1 - len(missing_in_nav) / max(len(fm_codes), 1)

    print(f"fund_master codes : {len(fm_codes):,}")
    print(f"nav_history codes : {len(nav_codes):,}")
    print(f"coverage          : {coverage:.1%}")
    print(f"missing in nav    : {len(missing_in_nav):,}")
    print(f"orphans in nav    : {len(orphan_in_nav):,}")
    if missing_in_nav:
        print(f"  sample missing: {sorted(missing_in_nav)[:10]}")

    lines += [
        f"- fund_master codes: **{len(fm_codes):,}**, nav_history codes: **{len(nav_codes):,}**",
        f"- NAV coverage of master: **{coverage:.1%}**",
        f"- Codes in master but missing from NAV: **{len(missing_in_nav):,}**"
        + (f" (e.g. {sorted(missing_in_nav)[:10]})" if missing_in_nav else ""),
        f"- Orphan codes in NAV not in master: **{len(orphan_in_nav):,}**",
    ]
    return lines


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def write_report(frames: dict[str, pd.DataFrame],
                 anomalies: dict[str, list[str]],
                 master_lines: list[str],
                 validation_lines: list[str]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = ["# Day 1 — Data Quality Summary\n",
           f"Datasets loaded: **{len(frames)}**\n",
           "## Dataset overview\n",
           "| Dataset | Rows | Cols | Anomalies |",
           "|---|---:|---:|---:|"]
    for name, df in frames.items():
        out.append(f"| {name} | {len(df):,} | {df.shape[1]} | {len(anomalies.get(name, []))} |")

    out.append("\n## Anomalies by dataset\n")
    for name in frames:
        items = anomalies.get(name, [])
        out.append(f"### {name}")
        out.extend([f"- {a}" for a in items] if items else ["- none detected"])
        out.append("")

    out.append("## Fund master structure\n")
    out.extend(master_lines or ["- fund_master not available"])
    out.append("\n## AMFI code validation\n")
    out.extend(validation_lines)
    REPORT_PATH.write_text("\n".join(out) + "\n")
    print(f"\nReport written -> {REPORT_PATH}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Day 1 MF data ingestion & profiling")
    ap.add_argument("--data-dir", default=str(DATA_DIR), type=Path)
    args = ap.parse_args()

    if not args.data_dir.exists():
        print(f"ERROR: data dir not found: {args.data_dir}")
        return 1

    paths = discover(args.data_dir)
    if not paths:
        print(f"ERROR: no CSV files found in {args.data_dir}")
        return 1

    print(f"Discovered {len(paths)} CSV dataset(s) in {args.data_dir}\n")
    frames = load_all(paths)

    anomalies = {name: profile(name, df) for name, df in frames.items()}

    master_lines = profile_fund_master(frames["fund_master"]) if "fund_master" in frames else []
    validation_lines = validate_codes(frames)

    write_report(frames, anomalies, master_lines, validation_lines)
    print("\nDay 1 ingestion complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
