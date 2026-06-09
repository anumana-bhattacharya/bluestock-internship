"""
recommender.py
--------------
Day 6 — Simple rule-based fund recommendation model.

Logic
  Input : investor risk appetite in {Low, Moderate, High}
  Match : map appetite -> acceptable risk grades (fund_master.risk_category)
  Rank  : within matching funds, take the Top 3 by Sharpe ratio (Day-4 output)
  Output: printed recommendation table (and returned DataFrame)

Usage
    python recommender.py                # interactive prompt
    python recommender.py --risk High    # one-shot
    from recommender import recommend; recommend("Moderate")
"""
from __future__ import annotations
import argparse
from pathlib import Path

import pandas as pd

P = Path("data/processed")

# Risk appetite -> acceptable fund risk grades (riskometer bands)
RISK_MAP = {
    "Low":      ["Low", "Moderately Low", "Moderate"],
    "Moderate": ["Moderate", "Moderately High"],
    "High":     ["High", "Very High"],
}


def _load() -> pd.DataFrame:
    fm = pd.read_csv(P / "clean_fund_master.csv")
    fm["amfi_code"] = fm["amfi_code"].astype(str)
    sharpe = pd.read_csv(P / "sharpe_values.csv")
    sharpe["amfi_code"] = sharpe["amfi_code"].astype(str)
    df = fm.merge(sharpe[["amfi_code", "sharpe_ratio"]], on="amfi_code", how="left")
    return df


def recommend(risk_appetite: str, top_n: int = 3) -> pd.DataFrame:
    """Return the Top-N funds by Sharpe matching the investor's risk appetite."""
    appetite = risk_appetite.strip().title()
    if appetite not in RISK_MAP:
        raise ValueError(f"risk_appetite must be one of {list(RISK_MAP)}; got {risk_appetite!r}")
    df = _load()
    grades = RISK_MAP[appetite]
    match = df[df["risk_category"].isin(grades)].copy()
    match = match.sort_values("sharpe_ratio", ascending=False).head(top_n)
    return match[["scheme_name", "fund_house", "sub_category",
                  "risk_category", "expense_ratio_pct", "sharpe_ratio"]].reset_index(drop=True)


def _print_table(appetite: str, recs: pd.DataFrame) -> None:
    print(f"\nTop {len(recs)} fund recommendations for a '{appetite}' risk appetite")
    print(f"(matching risk grades: {', '.join(RISK_MAP[appetite.title()])})\n")
    show = recs.copy()
    show["sharpe_ratio"] = show["sharpe_ratio"].round(2)
    show.index = range(1, len(show) + 1)
    print(show.to_string())


def main() -> int:
    ap = argparse.ArgumentParser(description="Fund recommender by risk appetite")
    ap.add_argument("--risk", choices=["Low", "Moderate", "High"])
    ap.add_argument("--top", type=int, default=3)
    args = ap.parse_args()

    appetite = args.risk
    if not appetite:
        appetite = input("Enter risk appetite [Low / Moderate / High]: ").strip().title()

    recs = recommend(appetite, args.top)
    _print_table(appetite, recs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
