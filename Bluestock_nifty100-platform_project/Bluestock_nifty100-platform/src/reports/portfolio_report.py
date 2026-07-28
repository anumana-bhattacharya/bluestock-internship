"""One-page-per-company portfolio summary PDF with directional KPI arrows."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from src.config.settings import Settings

LOGGER = logging.getLogger(__name__)
PAGE_WIDTH, PAGE_HEIGHT = A4
NAVY = colors.HexColor("#0B3558")
BLUE = colors.HexColor("#2C74B3")
LIGHT = colors.HexColor("#EAF2F8")
GREEN = colors.HexColor("#14804A")
RED = colors.HexColor("#B42318")
GREY = colors.HexColor("#61788A")
FLAT_TOLERANCE = 0.02


def _display(value: Any, suffix: str) -> str:
    """Format a portfolio KPI."""
    return "N/A" if value is None or pd.isna(value) else f"{float(value):,.1f}{suffix}"


def _trend(
    previous: object,
    latest: object,
    higher_is_better: bool,
    flat_tolerance: float = FLAT_TOLERANCE,
) -> str:
    """Classify KPI movement as improved, declined, flat, or unavailable."""
    values = pd.to_numeric(pd.Series([previous, latest]), errors="coerce")
    if values.isna().any():
        return "unavailable"
    prior, current = float(values.iloc[0]), float(values.iloc[1])
    relative_change = abs(current - prior) / max(abs(prior), 1.0)
    if relative_change <= flat_tolerance:
        return "flat"
    improved = current > prior if higher_is_better else current < prior
    return "up" if improved else "down"


def _draw_arrow(document: canvas.Canvas, x: float, y: float, direction: str) -> None:
    """Draw an up, down, or right arrow without relying on glyph support."""
    if direction == "unavailable":
        document.setFillColor(GREY)
        document.setFont("Helvetica", 7)
        document.drawString(x, y - 2, "N/A")
        return
    color = GREEN if direction == "up" else RED if direction == "down" else GREY
    document.setStrokeColor(color)
    document.setFillColor(color)
    document.setLineWidth(2.2)
    if direction == "up":
        document.line(x + 7, y - 5, x + 7, y + 7)
        path = document.beginPath()
        path.moveTo(x + 2, y + 3)
        path.lineTo(x + 7, y + 10)
        path.lineTo(x + 12, y + 3)
        path.close()
    elif direction == "down":
        document.line(x + 7, y + 7, x + 7, y - 5)
        path = document.beginPath()
        path.moveTo(x + 2, y - 1)
        path.lineTo(x + 7, y - 8)
        path.lineTo(x + 12, y - 1)
        path.close()
    else:
        document.line(x + 1, y, x + 13, y)
        path = document.beginPath()
        path.moveTo(x + 9, y + 5)
        path.lineTo(x + 16, y)
        path.lineTo(x + 9, y - 5)
        path.close()
    document.drawPath(path, fill=1, stroke=0)


def generate_portfolio_summary(
    settings: Settings,
    companies: pd.DataFrame,
    sectors: pd.DataFrame,
    ratios: pd.DataFrame,
    health_scores: pd.DataFrame,
) -> Path:
    """Generate the alphabetical 92-page portfolio summary."""
    output_dir = settings.project_root / "reports" / "portfolio"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "portfolio_summary.pdf"
    sector_map = sectors.set_index("company_id")["broad_sector"].to_dict()
    health_map = health_scores.set_index("company_id").to_dict("index")
    ratio_groups = {
        company_id: group.sort_values("year")
        for company_id, group in ratios.groupby("company_id")
    }
    document = canvas.Canvas(
        str(output_path), pagesize=A4, pageCompression=1, invariant=1
    )
    document.setTitle("Nifty100 Portfolio Summary")
    ordered = companies.sort_values("company_id").reset_index(drop=True)
    metric_specs = [
        ("ROE", "return_on_equity_pct", "%", True),
        ("ROCE", "return_on_capital_employed_pct", "%", True),
        ("Operating Margin", "operating_profit_margin_pct", "%", True),
        ("Debt / Equity", "debt_to_equity", "x", False),
        ("Revenue CAGR 3Y", "revenue_cagr_3y", "%", True),
        ("FCF Conversion", "fcf_conversion_pct", "%", True),
    ]
    for page_index, company in ordered.iterrows():
        ticker = str(company["company_id"])
        history = ratio_groups.get(ticker, pd.DataFrame()).sort_values("year")
        latest = history.iloc[-1] if not history.empty else pd.Series()
        previous = history.iloc[-2] if len(history) >= 2 else pd.Series()
        health = health_map.get(ticker, {})
        document.setFillColor(NAVY)
        document.rect(0, PAGE_HEIGHT - 112, PAGE_WIDTH, 112, fill=1, stroke=0)
        document.setFillColor(colors.white)
        document.setFont("Helvetica-Bold", 22)
        company_name = " ".join(str(company["company_name"]).split())
        document.drawString(36, PAGE_HEIGHT - 48, company_name[:48])
        document.setFont("Helvetica", 10)
        document.drawString(
            36,
            PAGE_HEIGHT - 71,
            f"{ticker} · {sector_map.get(ticker, 'Unknown')} · latest {latest.get('year', 'N/A')}",
        )
        document.setFillColor(BLUE)
        document.roundRect(
            PAGE_WIDTH - 158, PAGE_HEIGHT - 84, 120, 50, 8, fill=1, stroke=0
        )
        document.setFillColor(colors.white)
        document.setFont("Helvetica-Bold", 18)
        document.drawCentredString(
            PAGE_WIDTH - 98,
            PAGE_HEIGHT - 58,
            _display(health.get("health_score"), ""),
        )
        document.setFont("Helvetica", 8)
        document.drawCentredString(
            PAGE_WIDTH - 98,
            PAGE_HEIGHT - 73,
            f"HEALTH · {health.get('health_band', 'N/A')}",
        )
        document.setFillColor(NAVY)
        document.setFont("Helvetica-Bold", 13)
        document.drawString(36, PAGE_HEIGHT - 150, "Latest KPIs and Direction")
        document.setFont("Helvetica", 8)
        document.setFillColor(GREY)
        document.drawString(
            36,
            PAGE_HEIGHT - 166,
            "Arrow shows improvement versus the preceding fiscal period; flat means movement within 2%.",
        )
        tile_width = (PAGE_WIDTH - 90) / 2
        for metric_index, (label, field, suffix, higher_is_better) in enumerate(
            metric_specs
        ):
            row, column = divmod(metric_index, 2)
            x = 36 + column * (tile_width + 18)
            y = PAGE_HEIGHT - 265 - row * 128
            document.setFillColor(LIGHT)
            document.roundRect(x, y, tile_width, 100, 8, fill=1, stroke=0)
            document.setFillColor(NAVY)
            document.setFont("Helvetica", 9)
            document.drawString(x + 15, y + 72, label.upper())
            document.setFont("Helvetica-Bold", 22)
            document.drawString(x + 15, y + 36, _display(latest.get(field), suffix))
            direction = _trend(previous.get(field), latest.get(field), higher_is_better)
            _draw_arrow(document, x + tile_width - 43, y + 48, direction)
            document.setFont("Helvetica-Bold", 7)
            document.setFillColor(
                GREEN if direction == "up" else RED if direction == "down" else GREY
            )
            document.drawString(
                x + tile_width - 56, y + 19, direction.upper().replace("_", " ")
            )
        document.setStrokeColor(colors.HexColor("#D6E4F0"))
        document.line(36, 58, PAGE_WIDTH - 36, 58)
        document.setFillColor(GREY)
        document.setFont("Helvetica", 7.5)
        document.drawString(
            36,
            41,
            "Source: supplied Nifty100 workbooks · INR Crore · Analytical output, not investment advice.",
        )
        document.drawRightString(
            PAGE_WIDTH - 36,
            41,
            f"{page_index + 1} / {len(ordered)}",
        )
        document.showPage()
    document.save()
    LOGGER.info("portfolio summary generated pages=%d", len(ordered))
    return output_path


__all__ = ["generate_portfolio_summary"]
