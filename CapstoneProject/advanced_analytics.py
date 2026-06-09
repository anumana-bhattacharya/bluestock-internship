"""
advanced_analytics.py
---------------------
Day 6 — Advanced analytics & risk metrics.

Outputs (data/processed/ unless noted):
    var_cvar_report.csv   Historical VaR(95%) + CVaR per fund (daily returns)
    cohort_analysis.csv   Investors grouped by first-transaction year
    sip_continuity.csv    Per-investor SIP gap analysis + at-risk flag
    sector_hhi.csv        Herfindahl-Hirschman Index of sector weights / equity fund
    charts/rolling_sharpe_chart.png   Rolling 90-day Sharpe for 5 funds
    charts/sector_hhi_chart.png       HHI by equity fund (concentration)

Run:  python advanced_analytics.py
"""
from __future__ import annotations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

P = Path("data/processed")
CHARTS = Path("charts")
CHARTS.mkdir(exist_ok=True)

RF = 0.065
TD = 252
WIN = 90                      # rolling window (trading days)
AT_RISK_GAP = 35             # days
EQUITY = {"Large Cap", "Mid Cap", "Small Cap", "Flexi Cap", "ELSS",
          "Large & Mid Cap", "Value", "Index", "Index/ETF"}


def load():
    nav = pd.read_csv(P/"clean_nav.csv", parse_dates=["date"])
    nav["amfi_code"] = nav["amfi_code"].astype(str)
    nav = nav.sort_values(["amfi_code", "date"])
    fm = pd.read_csv(P/"clean_fund_master.csv"); fm["amfi_code"] = fm["amfi_code"].astype(str)
    tx = pd.read_csv(P/"clean_transactions.csv", parse_dates=["transaction_date"])
    tx["amfi_code"] = tx["amfi_code"].astype(str)
    hold = pd.read_csv(P/"clean_portfolio_holdings.csv"); hold["amfi_code"] = hold["amfi_code"].astype(str)
    return nav, fm, tx, hold


# ---------------------------------------------------------------------------
# 1. Historical VaR & CVaR (95%)
# ---------------------------------------------------------------------------
def var_cvar(nav, fm) -> pd.DataFrame:
    nav = nav.copy()
    nav["ret"] = nav.groupby("amfi_code")["nav"].pct_change()
    rows = []
    name = dict(zip(fm.amfi_code, fm.scheme_name))
    cat = dict(zip(fm.amfi_code, fm.sub_category))
    for code, g in nav.groupby("amfi_code"):
        r = g["ret"].dropna()
        var95 = np.percentile(r, 5)                  # 5th percentile (loss threshold)
        cvar95 = r[r <= var95].mean()                # mean of tail beyond VaR
        rows.append({"amfi_code": code, "scheme_name": name.get(code),
                     "sub_category": cat.get(code),
                     "var_95_daily": round(var95, 5),
                     "cvar_95_daily": round(cvar95, 5),
                     "var_95_daily_pct": round(var95*100, 3),
                     "cvar_95_daily_pct": round(cvar95*100, 3)})
    df = pd.DataFrame(rows).sort_values("var_95_daily")
    df.to_csv(P/"var_cvar_report.csv", index=False)
    return df


# ---------------------------------------------------------------------------
# 2. Rolling 90-day Sharpe for 5 funds
# ---------------------------------------------------------------------------
def rolling_sharpe(nav, fm):
    # pick 5 representative funds (one per major equity category if possible)
    picks = []
    for sub in ["Large Cap", "Mid Cap", "Small Cap", "Flexi Cap", "ELSS"]:
        c = fm[fm.sub_category == sub]["amfi_code"]
        if len(c): picks.append(c.iloc[0])
    picks = picks[:5]
    name = dict(zip(fm.amfi_code, fm.scheme_name))
    rf_daily = RF / TD
    fig, ax = plt.subplots(figsize=(13, 6.5))
    for code in picks:
        g = nav[nav.amfi_code == code].copy()
        g["ret"] = g["nav"].pct_change()
        roll = (g["ret"].rolling(WIN).mean() - rf_daily) / g["ret"].rolling(WIN).std() * np.sqrt(TD)
        ax.plot(g["date"], roll, lw=1.4, label=name.get(code, code)[:30])
    ax.axhline(0, color="grey", lw=0.8, ls="--")
    ax.set(title="Rolling 90-day annualised Sharpe ratio — 5 funds",
           xlabel="Date", ylabel="Rolling Sharpe")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.savefig(CHARTS/"rolling_sharpe_chart.png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    return picks


# ---------------------------------------------------------------------------
# 3. Investor cohort analysis (by first transaction year)
# ---------------------------------------------------------------------------
def cohort_analysis(tx, fm) -> pd.DataFrame:
    first_year = tx.groupby("investor_id")["transaction_date"].min().dt.year.rename("cohort_year")
    t = tx.merge(first_year, on="investor_id")
    sub = dict(zip(fm.amfi_code, fm.sub_category))
    t["sub_category"] = t["amfi_code"].map(sub)
    rows = []
    for year, g in t.groupby("cohort_year"):
        sips = g[g.transaction_type == "SIP"]
        invested = g[g.transaction_type.isin(["SIP", "Lumpsum"])]["amount_inr"].sum()
        top_cat = g["sub_category"].mode().iloc[0] if not g["sub_category"].mode().empty else None
        rows.append({"cohort_year": int(year),
                     "n_investors": g.investor_id.nunique(),
                     "n_transactions": len(g),
                     "avg_sip_amount": round(sips.amount_inr.mean(), 0) if len(sips) else None,
                     "total_invested_cr": round(invested/1e7, 2),
                     "preferred_category": top_cat})
    df = pd.DataFrame(rows).sort_values("cohort_year")
    df.to_csv(P/"cohort_analysis.csv", index=False)
    return df


# ---------------------------------------------------------------------------
# 4. SIP continuity analysis
# ---------------------------------------------------------------------------
def sip_continuity(tx) -> pd.DataFrame:
    sips = tx[tx.transaction_type == "SIP"].sort_values(["investor_id", "transaction_date"])
    rows = []
    for inv, g in sips.groupby("investor_id"):
        if len(g) < 6:                                # need 6+ SIP transactions
            continue
        gaps = g["transaction_date"].diff().dt.days.dropna()
        avg_gap = gaps.mean()
        rows.append({"investor_id": inv,
                     "n_sip_txns": len(g),
                     "avg_gap_days": round(avg_gap, 1),
                     "max_gap_days": int(gaps.max()),
                     "at_risk": avg_gap > AT_RISK_GAP})
    df = pd.DataFrame(rows).sort_values("avg_gap_days", ascending=False)
    df.to_csv(P/"sip_continuity.csv", index=False)
    return df


# ---------------------------------------------------------------------------
# 6. Sector concentration HHI per equity fund
# ---------------------------------------------------------------------------
def sector_hhi(hold, fm) -> pd.DataFrame:
    sub = dict(zip(fm.amfi_code, fm.sub_category))
    name = dict(zip(fm.amfi_code, fm.scheme_name))
    rows = []
    for code, g in hold.groupby("amfi_code"):
        if sub.get(code) not in EQUITY:
            continue
        w = g.groupby("sector")["weight_pct"].sum()
        w = w / w.sum()                               # normalise to shares
        hhi = (w ** 2).sum()                          # 0..1 (×10000 for index form)
        rows.append({"amfi_code": code, "scheme_name": name.get(code),
                     "sub_category": sub.get(code),
                     "n_sectors": int((w > 0).sum()),
                     "hhi": round(hhi, 4),
                     "hhi_index": round(hhi*10000, 0),
                     "top_sector": w.idxmax(),
                     "top_sector_weight_pct": round(w.max()*100, 1)})
    df = pd.DataFrame(rows).sort_values("hhi", ascending=False)
    # flag: HHI > 0.18 (≈1800) considered concentrated (DOJ merger guideline analogue)
    df["concentrated"] = df["hhi"] > 0.18
    df.to_csv(P/"sector_hhi.csv", index=False)

    fig, ax = plt.subplots(figsize=(12, 7))
    d = df.sort_values("hhi")
    colors = ["#c1121f" if c else "#1b998b" for c in d["concentrated"]]
    ax.barh(d.scheme_name.str.replace(" - Regular - Growth","").str.replace(" - Direct - Growth","").str[:34],
            d.hhi, color=colors)
    ax.axvline(0.18, color="black", ls="--", lw=1, label="Concentration threshold (0.18)")
    ax.set(title="Sector concentration (HHI) by equity fund", xlabel="HHI (0–1)")
    ax.legend(); ax.grid(alpha=0.3, axis="x")
    fig.savefig(CHARTS/"sector_hhi_chart.png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    return df


def main():
    nav, fm, tx, hold = load()
    vc = var_cvar(nav, fm)
    picks = rolling_sharpe(nav, fm)
    co = cohort_analysis(tx, fm)
    sc = sip_continuity(tx)
    hhi = sector_hhi(hold, fm)

    print("VaR/CVaR — 5 worst (most negative daily VaR):")
    print(vc.head()[["scheme_name", "var_95_daily_pct", "cvar_95_daily_pct"]].to_string(index=False))
    print("\nCohorts:\n", co.to_string(index=False))
    print(f"\nSIP continuity: {len(sc)} investors with 6+ SIPs, "
          f"{int(sc.at_risk.sum())} flagged at-risk ({sc.at_risk.mean()*100:.1f}%)")
    print("\nSector HHI — most concentrated:")
    print(hhi.head()[["scheme_name", "hhi", "top_sector", "top_sector_weight_pct", "concentrated"]].to_string(index=False))
    print("\nDay 6 advanced analytics complete.")


if __name__ == "__main__":
    main()
