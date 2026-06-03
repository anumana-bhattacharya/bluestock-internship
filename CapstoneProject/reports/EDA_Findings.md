# Day 3 — EDA Findings Summary

Exploratory analysis of the Bluestock mutual-fund datasets (40 schemes, 46K NAV
observations, ~33K investor transactions, 2022–2026). All figures below are
computed from `data/processed/`; the 16 supporting charts are in `charts/`.

## 10 key findings

1. **SBI leads the industry on AUM.** Year-end 2025 AUM reaches **₹12.5 lakh crore**
   for SBI Mutual Fund, ahead of ICICI Prudential (₹10.7L cr) and HDFC (₹9.3L cr).
   All ten AMCs roughly doubled AUM over 2022→2025. *(chart 03)*

2. **SIP inflows hit a record ₹31,002 crore in Dec 2025**, up from ₹11,517 crore in
   Jan 2022 — a ~2.7× rise in four years, averaging **31.5% YoY growth**. *(chart 04)*

3. **Retail participation is broadening fast.** Industry folio count grew from
   **13.26 crore to 26.12 crore** (≈97% growth) over the period. *(chart 10)*

4. **Liquid/debt funds dominate net category inflows.** The Liquid category drew
   the largest cumulative net inflow (₹4.5 lakh crore), with equity sub-categories
   (Flexi Cap, Large & Mid Cap, Mid/Small Cap) consistently positive. *(charts 05, 08)*

5. **NAV growth tracks the broad market.** Average NAV across schemes rose steadily
   2022→2026 with visible drawdowns in 2022 and a strong 2023–2024 rally; equity
   schemes show far higher dispersion than debt/liquid. *(charts 01, 02, 16)*

6. **Returns cluster in the mid-teens.** Mean 1-year return is **14.4%** (range
   4.3%–24.9%); the top performer is ABSL Small Cap (**24.9%**). Distribution is
   right-skewed by small/mid-cap outperformers. *(chart 13)*

7. **Risk-adjusted leadership sits with liquid funds.** Highest Sharpe ratios belong
   to liquid funds (ICICI Pru Liquid 7.68) — expected, as they carry minimal
   volatility; among equity, large caps lead (~1.06 Sharpe). *(Day-2 query 6)*

8. **T30 cities drive two-thirds of flows.** T30 contributes **65.9%** of transaction
   value vs **34.1%** for B30 — but B30's share signals meaningful small-town growth.
   *(chart 09)*

9. **Young investors are the core SIP base.** The **26–35 age group** is the largest
   cohort (≈41% of transactions), followed by 36–45; SIP ticket sizes rise with age.
   *(charts 06, 07)*

10. **Banking dominates portfolio allocation.** Banking is the single largest sector
    holding (₹62,840 cr, **19.3%** of aggregate market value), ahead of IT (₹38,477 cr)
    and Pharma (₹34,606 cr) — typical of Indian equity portfolios. *(chart 12)*

## Secondary observations
- **Payment modes are evenly split** across Net Banking, Cheque, UPI and Mandate
  (~25% each) — surprising given the broader UPI shift; worth validating. *(chart 15)*
- **KYC completeness is 92% Verified, 8% Pending** — a small onboarding-friction tail.
- **Transaction mix:** SIP 60% / Lumpsum 25% / Redemption 15%, confirming a
  systematic-investing-led book. *(chart 14)*
- **Return correlations are near-zero across all funds** (|r| < 0.1 on daily
  returns). In real markets equity schemes co-move strongly (~0.7–0.9), so this
  flat correlation structure indicates the NAV series were **generated
  independently** — a synthetic-data artifact to flag before any portfolio /
  diversification modelling. *(chart 11)*

## Data-quality / anomaly notes
- The live mfapi.in AMFI codes from Day 1 are mislabelled vs the provided CSVs
  (see `reports/day1_data_quality.md`); the 10 CSVs themselves are internally
  consistent and were used for all EDA here.
- Even payment-mode split and clean categorical values suggest the dataset is
  synthetically generated — patterns are realistic but unusually smooth.

## Chart index
`01` NAV trend (all) · `02` NAV large-cap · `03` AUM by AMC · `04` SIP trend ·
`05` Category heatmap · `06` Age pie · `07` SIP by age box · `08` SIP by state ·
`09` T30/B30 · `10` Folio growth · `11` Return correlation · `12` Sector donut ·
`13` Return distribution · `14` Txn mix · `15` Payment mode · `16` Avg NAV monthly.
