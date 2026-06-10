"""
live_nav_fetch.py
-----------------
Day 1 — Fetch live NAV history from the AMFI-backed mfapi.in API.

Endpoint shape (https://api.mfapi.in/mf/<scheme_code>):
    {
      "meta": {"fund_house", "scheme_type", "scheme_category",
               "scheme_code", "scheme_name", "isin_growth", "isin_div_reinvestment"},
      "data": [ {"date": "DD-MM-YYYY", "nav": "1234.56"}, ... ],   # newest first
      "status": "SUCCESS"
    }

Outputs (written to ./data/raw_nav/):
    nav_<code>_<slug>.csv     one tidy file per scheme
    nav_meta.csv              one row of metadata per scheme
    nav_combined.csv          all schemes stacked (long format)

Run:
    python live_nav_fetch.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

API_BASE = "https://api.mfapi.in/mf"
OUT_DIR = Path("data/raw")
TIMEOUT = 30
RETRIES = 3
RETRY_BACKOFF = 2  # seconds, multiplied by attempt number

# Scheme codes from the task brief. The primary scheme + 5 key bluechip schemes.
SCHEMES: dict[int, str] = {
    125497: "HDFC Top 100 Direct",
    119551: "SBI Bluechip",
    120503: "ICICI Bluechip",
    118632: "Nippon Large Cap",
    119092: "Axis Bluechip",
    120841: "Kotak Bluechip",
}


def _slug(text: str) -> str:
    """Filesystem-safe slug from a scheme name."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def fetch_scheme(code: int, session: requests.Session) -> dict:
    """GET one scheme, with simple retry/backoff. Returns parsed JSON dict."""
    url = f"{API_BASE}/{code}"
    last_err: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("status") != "SUCCESS" or not payload.get("data"):
                raise ValueError(f"Unexpected payload for {code}: status={payload.get('status')}")
            return payload
        except (requests.RequestException, ValueError, json.JSONDecodeError) as err:
            last_err = err
            wait = RETRY_BACKOFF * attempt
            print(f"  [warn] {code} attempt {attempt}/{RETRIES} failed: {err} -> retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Failed to fetch scheme {code} after {RETRIES} attempts: {last_err}")


def to_frame(code: int, label: str, payload: dict) -> pd.DataFrame:
    """Convert the 'data' array into a tidy, typed DataFrame (oldest-first)."""
    df = pd.DataFrame(payload["data"])
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["date", "nav"]).sort_values("date").reset_index(drop=True)
    meta = payload["meta"]
    df.insert(0, "scheme_code", code)
    df.insert(1, "scheme_name", meta.get("scheme_name", label))
    df.insert(2, "fund_house", meta.get("fund_house"))
    df.insert(3, "scheme_category", meta.get("scheme_category"))
    return df


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "mf-analytics-day1/1.0"})

    meta_rows: list[dict] = []
    combined: list[pd.DataFrame] = []

    for code, label in SCHEMES.items():
        print(f"Fetching {code} — {label} ...")
        payload = fetch_scheme(code, session)

        # Save raw JSON untouched for auditability.
        (OUT_DIR / f"raw_{code}.json").write_text(json.dumps(payload, indent=2))

        df = to_frame(code, label, payload)
        slug = _slug(payload["meta"].get("scheme_name", label))
        csv_path = OUT_DIR / f"nav_{code}_{slug}.csv"
        df.to_csv(csv_path, index=False)
        combined.append(df)

        m = dict(payload["meta"])
        m["records"] = len(df)
        m["nav_start"] = df["date"].min().date().isoformat() if len(df) else None
        m["nav_end"] = df["date"].max().date().isoformat() if len(df) else None
        m["latest_nav"] = float(df["nav"].iloc[-1]) if len(df) else None
        meta_rows.append(m)

        print(f"  saved {len(df):>6,} rows -> {csv_path.name} "
              f"(latest NAV {m['latest_nav']} on {m['nav_end']})")

    pd.DataFrame(meta_rows).to_csv(OUT_DIR / "nav_meta.csv", index=False)
    pd.concat(combined, ignore_index=True).to_csv(OUT_DIR / "nav_combined.csv", index=False)
    print(f"\nDone. {len(SCHEMES)} schemes -> {OUT_DIR}/ "
          f"(nav_meta.csv + nav_combined.csv written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
