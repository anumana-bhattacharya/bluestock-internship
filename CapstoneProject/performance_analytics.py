"""
performance_analytics.py
------------------------
Day 4 — Fund performance & risk analytics computed from NAV history.

Outputs (data/processed/ unless noted):
    returns_computed.csv   daily + annualised return per scheme
    cagr_report.csv        CAGR over 1y / 3y / 5y(avail) periods
    sharpe_values.csv      Sharpe ratio (Rf = 6.5%, annualised √252)
    sortino_values.csv     Sortino ratio (downside deviation)
    alpha_beta.csv         OLS alpha (annualised) & beta vs NIFTY100
    max_drawdown.csv       max drawdown + peak/trough dates
    fund_scorecard.csv     composite 0–100 score + rank + best/worst flags
    charts/benchmark_chart.png   top-5 funds vs NIFTY50 / NIFTY100 (3y)

Notes
  * Risk-free rate Rf = 6.5% (RBI repo proxy).
  * Trading days per year = 252.
  * scipy is unavailable in some environments, so the OLS regression for
    alpha/beta is implemented directly with numpy (identical to
    scipy.stats.linregress slope/intercept).
  * Data spans ~4.4 years, so the "5y" CAGR uses the full available history
    and is flagged in the `years` column.

Run:  python performance_analytics.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROC = Path("data/processed")
CHARTS = Path("charts")
CHARTS.mkdir(exist_ok=True)

RF = 0.065          # risk-free rate
TD = 252            # trading days / year
BENCH = "NIFTY100"  # regression benchmark


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
def load():
    nav = pd.read_csv(PROC / "clean_nav.csv", parse_dates=["date"])
    nav["amfi_code"] = nav["amfi_code"].astype(str)
    nav = nav.sort_values(["amfi_code", "date"])
    fm = pd.read_csv(PROC / "clean_fund_master.csv")
    fm["amfi_code"] = fm["amfi_code"].astype(str)
    bench = pd.read_csv(PROC / "clean_benchmark_indices.csv", parse_dates=["date"])
    return nav, fm, bench


# ---------------------------------------------------------------------------
# 1. Daily & annualised returns
# ---------------------------------------------------------------------------
def returns_table(nav: pd.DataFrame) -> pd.DataFrame:
    nav = nav.copy()
    nav["daily_return"] = nav.groupby("amfi_code")["nav"].pct_change()
    rows = []
    for code, g in nav.groupby("amfi_code"):
        r = g["daily_return"].dropna()
        ann = (1 + r).prod() ** (TD / len(r)) - 1
        rows.append({"amfi_code": code,
                     "n_days": len(r),
                     "mean_daily_return": r.mean(),
                     "ann_volatility": r.std() * np.sqrt(TD),
                     "annualised_return": ann})
    nav.to_csv(PROC / "returns_computed.csv", index=False)
    return nav, pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. CAGR over fixed look-back windows
# ---------------------------------------------------------------------------
def cagr_report(nav: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for code, g in nav.groupby("amfi_code"):
        g = g.sort_values("date")
        end_date, end_nav = g["date"].iloc[-1], g["nav"].iloc[-1]
        rec = {"amfi_code": code}
        for label, yrs in [("cagr_1yr", 1), ("cagr_3yr", 3), ("cagr_5yr", 5)]:
            start_cut = end_date - pd.DateOffset(years=yrs)
            sub = g[g["date"] <= start_cut]
            if sub.empty:                       # not enough history -> use earliest
                start_nav = g["nav"].iloc[0]
                yrs_act = (end_date - g["date"].iloc[0]).days / 365.25
            else:
                start_nav = sub["nav"].iloc[-1]
                yrs_act = yrs
            rec[label] = (end_nav / start_nav) ** (1 / yrs_act) - 1
        rec["years_available"] = round((end_date - g["date"].iloc[0]).days / 365.25, 2)
        rows.append(rec)
    df = pd.DataFrame(rows)
    df.to_csv(PROC / "cagr_report.csv", index=False)
    return df


# ---------------------------------------------------------------------------
# 3 & 4. Sharpe and Sortino
# ---------------------------------------------------------------------------
def sharpe_sortino(nav: pd.DataFrame):
    sh, so = [], []
    for code, g in nav.groupby("amfi_code"):
        r = g["daily_return"].dropna()
        ann_ret = (1 + r.mean()) ** TD - 1
        ann_vol = r.std() * np.sqrt(TD)
        sharpe = (ann_ret - RF) / ann_vol if ann_vol else np.nan
        downside = r[r < 0]
        dd = downside.std() * np.sqrt(TD)
        sortino = (ann_ret - RF) / dd if dd else np.nan
        sh.append({"amfi_code": code, "ann_return": ann_ret,
                   "ann_volatility": ann_vol, "sharpe_ratio": sharpe})
        so.append({"amfi_code": code, "ann_return": ann_ret,
                   "downside_deviation": dd, "sortino_ratio": sortino})
    sh = pd.DataFrame(sh); so = pd.DataFrame(so)
    sh.to_csv(PROC / "sharpe_values.csv", index=False)
    so.to_csv(PROC / "sortino_values.csv", index=False)
    return sh, so


# ---------------------------------------------------------------------------
# 5. Alpha & Beta vs benchmark (numpy OLS == scipy.stats.linregress)
# ---------------------------------------------------------------------------
def ols(y: np.ndarray, x: np.ndarray):
    """Return slope, intercept, r for y ~ x (least squares)."""
    x = np.asarray(x); y = np.asarray(y)
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    sxy = ((x - xm) * (y - ym)).sum()
    slope = sxy / sxx
    intercept = ym - slope * xm
    syy = ((y - ym) ** 2).sum()
    r = sxy / np.sqrt(sxx * syy) if sxx and syy else np.nan
    return slope, intercept, r


def alpha_beta(nav: pd.DataFrame, bench: pd.DataFrame) -> pd.DataFrame:
    b = (bench[bench["index_name"] == BENCH]
         .sort_values("date").set_index("date")["close_value"])
    b_ret = b.pct_change().dropna()
    rows = []
    for code, g in nav.groupby("amfi_code"):
        s = g.set_index("date")["daily_return"].dropna()
        joined = pd.concat([s.rename("f"), b_ret.rename("m")], axis=1).dropna()
        if len(joined) < 30:
            continue
        beta, intercept, r = ols(joined["f"].values, joined["m"].values)
        rows.append({"amfi_code": code,
                     "benchmark": BENCH,
                     "beta": beta,
                     "alpha_annualised": intercept * TD,
                     "r_squared": r ** 2,
                     "n_obs": len(joined)})
    df = pd.DataFrame(rows)
    df.to_csv(PROC / "alpha_beta.csv", index=False)
    return df


# ---------------------------------------------------------------------------
# 6. Maximum drawdown
# ---------------------------------------------------------------------------
def max_drawdown(nav: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for code, g in nav.groupby("amfi_code"):
        g = g.sort_values("date")
        run_max = g["nav"].cummax()
        dd = g["nav"] / run_max - 1
        trough_i = dd.idxmin()
        trough_date = g.loc[trough_i, "date"]
        peak_date = g.loc[g["date"] <= trough_date, "nav"].idxmax()
        rows.append({"amfi_code": code,
                     "max_drawdown": dd.min(),
                     "peak_date": g.loc[peak_date, "date"].date(),
                     "trough_date": trough_date.date()})
    df = pd.DataFrame(rows)
    df.to_csv(PROC / "max_drawdown.csv", index=False)
    return df


# ---------------------------------------------------------------------------
# 7. Composite fund scorecard
# ---------------------------------------------------------------------------
def scorecard(fm, cagr, sharpe, ab, mdd) -> pd.DataFrame:
    df = (fm[["amfi_code", "scheme_name", "fund_house", "category",
              "sub_category", "expense_ratio_pct"]]
          .merge(cagr[["amfi_code", "cagr_3yr"]], on="amfi_code")
          .merge(sharpe[["amfi_code", "sharpe_ratio"]], on="amfi_code")
          .merge(ab[["amfi_code", "alpha_annualised"]], on="amfi_code", how="left")
          .merge(mdd[["amfi_code", "max_drawdown"]], on="amfi_code"))

    def pct_rank(s, inverse=False):
        r = s.rank(pct=True)
        return (1 - r if inverse else r) * 100

    df["r_return"] = pct_rank(df["cagr_3yr"])
    df["r_sharpe"] = pct_rank(df["sharpe_ratio"])
    df["r_alpha"] = pct_rank(df["alpha_annualised"])
    df["r_expense"] = pct_rank(df["expense_ratio_pct"], inverse=True)   # lower is better
    df["r_maxdd"] = pct_rank(df["max_drawdown"])  # max_dd is negative; higher (closer to 0) better
    df["score"] = (0.30 * df["r_return"] + 0.25 * df["r_sharpe"] +
                   0.20 * df["r_alpha"] + 0.15 * df["r_expense"] +
                   0.10 * df["r_maxdd"]).round(1)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    # best / worst per category
    df["category_best"] = df.groupby("sub_category")["score"].transform("max").eq(df["score"])
    df["category_worst"] = df.groupby("sub_category")["score"].transform("min").eq(df["score"])
    df.to_csv(PROC / "fund_scorecard.csv", index=False)
    return df


# ---------------------------------------------------------------------------
# 8. Benchmark comparison chart + tracking error
# ---------------------------------------------------------------------------
def benchmark_chart(nav, fm, bench, cagr) -> pd.DataFrame:
    end = nav["date"].max()
    start = end - pd.DateOffset(years=3)
    top5 = cagr.sort_values("cagr_3yr", ascending=False).head(5)["amfi_code"].tolist()
    name_of = dict(zip(fm["amfi_code"], fm["scheme_name"]))

    fig, ax = plt.subplots(figsize=(13, 7))

    def norm(series):
        series = series[series.index >= start]
        return series / series.iloc[0] * 100

    te_rows = []
    n100 = (bench[bench.index_name == "NIFTY100"].set_index("date")["close_value"])
    for code in top5:
        s = nav[nav.amfi_code == code].set_index("date")["nav"]
        ns = norm(s)
        ax.plot(ns.index, ns.values, lw=1.8, label=name_of.get(code, code)[:30])
        # tracking error vs NIFTY100
        fr = s.pct_change(); mr = n100.pct_change()
        j = pd.concat([fr, mr], axis=1).dropna()
        j = j[j.index >= start]
        te = (j.iloc[:, 0] - j.iloc[:, 1]).std() * np.sqrt(TD)
        te_rows.append({"amfi_code": code, "scheme_name": name_of.get(code, code),
                        "tracking_error_vs_nifty100": round(te, 4)})

    for idx, style in [("NIFTY50", "--"), ("NIFTY100", ":")]:
        s = bench[bench.index_name == idx].set_index("date")["close_value"]
        ns = norm(s)
        ax.plot(ns.index, ns.values, style, color="black", lw=2, label=idx)

    ax.set(title="Top-5 funds (by 3-yr CAGR) vs NIFTY50 / NIFTY100 — rebased to 100",
           xlabel="Date", ylabel="Growth of ₹100")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.savefig(CHARTS / "benchmark_chart.png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    te = pd.DataFrame(te_rows)
    te.to_csv(PROC / "tracking_error.csv", index=False)
    return te


def main() -> int:
    nav, fm, bench = load()
    nav, _ = returns_table(nav)
    cagr = cagr_report(nav)
    sharpe, sortino = sharpe_sortino(nav)
    ab = alpha_beta(nav, bench)
    mdd = max_drawdown(nav)
    sc = scorecard(fm, cagr, sharpe, ab, mdd)
    te = benchmark_chart(nav, fm, bench, cagr)

    print("Top 5 by composite score:")
    print(sc[["rank", "scheme_name", "sub_category", "score"]].head().to_string(index=False))
    print("\nTracking error (top-5 vs NIFTY100):")
    print(te.to_string(index=False))
    print("\nDay 4 analytics complete -> data/processed/ + charts/benchmark_chart.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
