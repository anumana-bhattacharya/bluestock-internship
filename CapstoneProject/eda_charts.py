"""
eda_charts.py
-------------
Day 3 — Exploratory Data Analysis. Generates 16 publication-quality charts
from the cleaned datasets (data/processed/) and saves them as PNGs to charts/.

Charts:
   01 NAV trend lines (all schemes, 2022-2026)
   02 NAV trend — 6 representative large-cap schemes (highlighted)
   03 AUM growth — grouped bar by fund house per year
   04 SIP inflow monthly time-series (Dec-2025 milestone marked)
   05 Category-wise net inflow heatmap (month x category)
   06 Investor age-group distribution (pie)
   07 SIP amount distribution by age group (box plot)
   08 SIP amount by state (horizontal bar)
   09 T30 vs B30 split (pie)
   10 Industry folio count growth (line)
   11 Correlation matrix of daily NAV returns across 10 funds (heatmap)
   12 Top holdings — sector allocation (donut)
   13 Distribution of scheme 1-yr returns (histogram)
   14 Transaction type mix (bar)
   15 Payment mode usage (bar)
   16 Average NAV across all schemes per month (line)

Run:  python eda_charts.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "axes.titleweight": "bold"})

PROC = Path("data/processed")
OUT = Path("charts")
OUT.mkdir(exist_ok=True)


def load():
    d = {}
    d["nav"] = pd.read_csv(PROC / "clean_nav.csv", parse_dates=["date"])
    d["fm"] = pd.read_csv(PROC / "clean_fund_master.csv")
    d["aum"] = pd.read_csv(PROC / "clean_aum_by_fund_house.csv", parse_dates=["date"])
    d["sip"] = pd.read_csv(PROC / "clean_monthly_sip_inflows.csv", parse_dates=["month"])
    d["cat"] = pd.read_csv(PROC / "clean_category_inflows.csv", parse_dates=["month"])
    d["folio"] = pd.read_csv(PROC / "clean_industry_folio_count.csv", parse_dates=["month"])
    d["tx"] = pd.read_csv(PROC / "clean_transactions.csv", parse_dates=["transaction_date"])
    d["perf"] = pd.read_csv(PROC / "clean_performance.csv")
    d["hold"] = pd.read_csv(PROC / "clean_portfolio_holdings.csv")
    return d


def save(fig, name):
    fig.savefig(OUT / name)
    plt.close(fig)
    print("  saved", name)


def main():
    d = load()
    nav, fm = d["nav"], d["fm"]
    nav["amfi_code"] = nav["amfi_code"].astype(str)
    fm["amfi_code"] = fm["amfi_code"].astype(str)
    name_of = dict(zip(fm["amfi_code"], fm["scheme_name"]))

    # 01 — all schemes NAV trend
    fig, ax = plt.subplots(figsize=(12, 6))
    for code, g in nav.groupby("amfi_code"):
        ax.plot(g["date"], g["nav"], lw=0.7, alpha=0.5)
    ax.set(title="01 · Daily NAV — all 40 schemes (2022–2026)",
           xlabel="Date", ylabel="NAV (₹)")
    save(fig, "01_nav_trend_all.png")

    # 02 — representative large-cap schemes
    lc = fm[fm["sub_category"] == "Large Cap"]["amfi_code"].tolist()[:6]
    fig, ax = plt.subplots(figsize=(12, 6))
    for code in lc:
        g = nav[nav["amfi_code"] == code]
        ax.plot(g["date"], g["nav"], lw=1.6, label=name_of.get(code, code)[:34])
    ax.set(title="02 · NAV trend — representative Large-Cap schemes",
           xlabel="Date", ylabel="NAV (₹)")
    ax.legend(fontsize=7, loc="upper left")
    save(fig, "02_nav_trend_largecap.png")

    # 03 — AUM grouped bar by fund house per year (year-end)
    aum = d["aum"].copy()
    aum["year"] = aum["date"].dt.year
    ye = aum.sort_values("date").groupby(["year", "fund_house"]).tail(1)
    piv = ye.pivot_table(index="fund_house", columns="year", values="aum_crore") / 1e5  # lakh cr
    fig, ax = plt.subplots(figsize=(13, 6.5))
    piv.plot(kind="bar", ax=ax)
    ax.set(title="03 · AUM growth by fund house (₹ lakh crore, year-end)",
           xlabel="Fund house", ylabel="AUM (₹ lakh crore)")
    ax.legend(title="Year")
    ax.tick_params(axis="x", rotation=35)
    for lbl in ax.get_xticklabels():
        lbl.set_ha("right")
    save(fig, "03_aum_growth_by_amc.png")

    # 04 — SIP inflow time-series with Dec-2025 milestone
    sip = d["sip"].sort_values("month")
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(sip["month"], sip["sip_inflow_crore"], color="#1f77b4", lw=2)
    ax.fill_between(sip["month"], sip["sip_inflow_crore"], alpha=0.15)
    peak = sip.loc[sip["sip_inflow_crore"].idxmax()]
    ax.annotate(f"₹{peak['sip_inflow_crore']:,.0f} Cr\n{peak['month']:%b %Y}",
                xy=(peak["month"], peak["sip_inflow_crore"]),
                xytext=(-90, -30), textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color="crimson"), color="crimson")
    ax.set(title="04 · Monthly SIP inflow trend (₹ crore)", xlabel="Month",
           ylabel="SIP inflow (₹ crore)")
    save(fig, "04_sip_inflow_trend.png")

    # 05 — category inflow heatmap
    cat = d["cat"].copy()
    cat["m"] = cat["month"].dt.strftime("%Y-%m")
    piv = cat.pivot_table(index="category", columns="m", values="net_inflow_crore")
    fig, ax = plt.subplots(figsize=(14, 6))
    sns.heatmap(piv, cmap="RdYlGn", center=0, ax=ax, cbar_kws={"label": "Net inflow (₹ Cr)"})
    ax.set(title="05 · Category-wise net inflow heatmap", xlabel="Month", ylabel="Category")
    save(fig, "05_category_heatmap.png")

    # 06 — age group pie
    tx = d["tx"]
    ag = tx["age_group"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(ag.values, labels=ag.index, autopct="%1.1f%%", startangle=90,
           wedgeprops=dict(width=0.55))
    ax.set(title="06 · Investor age-group distribution")
    save(fig, "06_age_group_pie.png")

    # 07 — SIP amount box plot by age group (SIP only)
    sips = tx[tx["transaction_type"] == "SIP"]
    fig, ax = plt.subplots(figsize=(11, 6))
    order = sorted(sips["age_group"].unique())
    sns.boxplot(data=sips, x="age_group", y="amount_inr", order=order, ax=ax, showfliers=False)
    ax.set(title="07 · SIP amount distribution by age group", xlabel="Age group",
           ylabel="SIP amount (₹)")
    save(fig, "07_sip_amount_by_age_box.png")

    # 08 — SIP amount by state (horizontal bar)
    by_state = (sips.groupby("state")["amount_inr"].sum() / 1e7).sort_values()
    fig, ax = plt.subplots(figsize=(10, 9))
    by_state.plot(kind="barh", ax=ax, color=sns.color_palette("viridis", len(by_state)))
    ax.set(title="08 · Total SIP amount by state (₹ crore)", xlabel="SIP amount (₹ crore)",
           ylabel="State")
    save(fig, "08_sip_by_state.png")

    # 09 — T30 vs B30 pie
    tier = tx.groupby("city_tier")["amount_inr"].sum()
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(tier.values, labels=tier.index, autopct="%1.1f%%", startangle=90,
           colors=["#4c72b0", "#dd8452"])
    ax.set(title="09 · Transaction value — T30 vs B30 cities")
    save(fig, "09_t30_b30_pie.png")

    # 10 — folio count growth
    fl = d["folio"].sort_values("month")
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(fl["month"], fl["total_folios_crore"], lw=2, marker="o", ms=3)
    ax.set(title="10 · Industry folio count growth (crore)", xlabel="Month",
           ylabel="Total folios (crore)")
    ax.annotate(f"{fl['total_folios_crore'].iloc[-1]:.2f} cr",
                xy=(fl["month"].iloc[-1], fl["total_folios_crore"].iloc[-1]),
                xytext=(-70, 10), textcoords="offset points", color="crimson")
    save(fig, "10_folio_growth.png")

    # 11 — correlation matrix of daily NAV returns across 10 funds
    codes10 = fm["amfi_code"].head(10).tolist()
    rets = (nav[nav["amfi_code"].isin(codes10)]
            .pivot_table(index="date", columns="amfi_code", values="daily_return"))
    rets.columns = [name_of.get(c, c)[:18] for c in rets.columns]
    corr = rets.corr()
    fig, ax = plt.subplots(figsize=(10, 8.5))
    sns.heatmap(corr, cmap="coolwarm", center=0, annot=True, fmt=".2f",
                annot_kws={"size": 7}, ax=ax)
    ax.set(title="11 · Correlation of daily NAV returns (10 funds)")
    save(fig, "11_return_correlation.png")

    # 12 — sector allocation donut
    sec = d["hold"].groupby("sector")["market_value_cr"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8.5, 8.5))
    ax.pie(sec.values, labels=sec.index, autopct="%1.0f%%", startangle=90,
           wedgeprops=dict(width=0.45), textprops={"fontsize": 8})
    ax.set(title="12 · Aggregate portfolio sector allocation")
    save(fig, "12_sector_allocation_donut.png")

    # 13 — distribution of 1-yr returns
    fig, ax = plt.subplots(figsize=(10, 5.5))
    sns.histplot(d["perf"]["return_1yr_pct"], bins=15, kde=True, ax=ax, color="#55a868")
    ax.set(title="13 · Distribution of scheme 1-year returns (%)",
           xlabel="1-year return (%)", ylabel="Number of schemes")
    save(fig, "13_return_distribution.png")

    # 14 — transaction type mix
    fig, ax = plt.subplots(figsize=(8, 5.5))
    tt = tx["transaction_type"].value_counts()
    sns.barplot(x=tt.index, y=tt.values, ax=ax)
    for i, v in enumerate(tt.values):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=9)
    ax.set(title="14 · Transaction type mix", xlabel="Type", ylabel="Count")
    save(fig, "14_transaction_type_mix.png")

    # 15 — payment mode usage
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    pm = tx["payment_mode"].value_counts()
    sns.barplot(x=pm.values, y=pm.index, ax=ax, palette="mako")
    ax.set(title="15 · Payment mode usage", xlabel="Count", ylabel="Payment mode")
    save(fig, "15_payment_mode.png")

    # 16 — average NAV per month
    nav["ym"] = nav["date"].dt.to_period("M").dt.to_timestamp()
    avg = nav.groupby("ym")["nav"].mean()
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(avg.index, avg.values, lw=2, color="#8172b3")
    ax.set(title="16 · Average NAV across all schemes per month",
           xlabel="Month", ylabel="Average NAV (₹)")
    save(fig, "16_avg_nav_monthly.png")

    print(f"\nGenerated {len(list(OUT.glob('*.png')))} charts -> {OUT}/")


if __name__ == "__main__":
    main()
