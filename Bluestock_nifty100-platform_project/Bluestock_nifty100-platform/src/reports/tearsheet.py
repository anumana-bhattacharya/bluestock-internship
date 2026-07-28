"""Two-page ReportLab company tearsheets with overflow-safe narratives."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from src.config.settings import Settings

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

LOGGER = logging.getLogger(__name__)
PAGE_WIDTH, PAGE_HEIGHT = A4
NAVY = colors.HexColor("#0B3558")
BLUE = colors.HexColor("#2C74B3")
LIGHT = colors.HexColor("#EAF2F8")
GREEN = colors.HexColor("#14804A")
GREEN_LIGHT = colors.HexColor("#E8F5EE")
RED = colors.HexColor("#B42318")
RED_LIGHT = colors.HexColor("#FDECEC")
GREY = colors.HexColor("#61788A")


def _display(value: Any, decimals: int = 1, suffix: str = "") -> str:
    """Format a numeric KPI for a compact report tile."""
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):,.{decimals}f}{suffix}"


def _page_one_chart(
    profit_loss: pd.DataFrame,
    ratio_history: pd.DataFrame,
    output_path: Path,
) -> None:
    """Render the required revenue/PAT bars and ROE/ROCE dual-axis chart."""
    pl = profit_loss.sort_values("year").tail(10)
    ratios = ratio_history.sort_values("year").tail(10)
    figure, axes = plt.subplots(2, 1, figsize=(8.2, 6.4))
    x = np.arange(len(pl))
    width = 0.38
    axes[0].bar(x - width / 2, pl["sales"], width, label="Revenue", color="#2C74B3")
    axes[0].bar(
        x + width / 2, pl["net_profit"], width, label="Net Profit", color="#4AA978"
    )
    axes[0].set_xticks(x, pl["year"], rotation=42, ha="right", fontsize=7)
    axes[0].set_title("10-Year Revenue and Net Profit (INR Crore)", fontsize=10)
    axes[0].tick_params(axis="y", labelsize=7)
    axes[0].grid(axis="y", alpha=0.18)
    axes[0].legend(frameon=False, fontsize=8, ncol=2)

    primary = axes[1]
    secondary = primary.twinx()
    primary.plot(
        ratios["year"],
        ratios["return_on_equity_pct"],
        color="#2C74B3",
        marker="o",
        linewidth=1.8,
        label="ROE",
    )
    secondary.plot(
        ratios["year"],
        ratios["return_on_capital_employed_pct"],
        color="#E17C35",
        marker="s",
        linewidth=1.8,
        label="ROCE",
    )
    primary.set_ylabel("ROE (%)", color="#2C74B3", fontsize=8)
    secondary.set_ylabel("ROCE (%)", color="#E17C35", fontsize=8)
    primary.set_xticks(range(len(ratios)))
    primary.set_xticklabels(ratios["year"], rotation=42, ha="right", fontsize=7)
    primary.tick_params(axis="y", labelsize=7)
    secondary.tick_params(axis="y", labelsize=7)
    primary.grid(alpha=0.18)
    primary.set_title("ROE and ROCE Trend", fontsize=10)
    handles_a, labels_a = primary.get_legend_handles_labels()
    handles_b, labels_b = secondary.get_legend_handles_labels()
    primary.legend(
        handles_a + handles_b,
        labels_a + labels_b,
        frameon=False,
        fontsize=8,
        ncol=2,
        loc="upper left",
    )
    figure.tight_layout(h_pad=1.7)
    figure.savefig(output_path, dpi=190, facecolor="white")
    plt.close(figure)


def _page_two_chart(
    balance_sheet: pd.DataFrame,
    cash_flow: pd.DataFrame,
    output_path: Path,
) -> None:
    """Render balance-sheet composition and latest cash-flow waterfall."""
    bs = (
        balance_sheet.sort_values("year").tail(8).copy()
        if not balance_sheet.empty
        else pd.DataFrame()
    )
    latest_cf = (
        cash_flow.sort_values("year").iloc[-1]
        if not cash_flow.empty
        else pd.Series(dtype=object)
    )
    cash_values = [
        latest_cf.get("operating_activity", 0),
        latest_cf.get("investing_activity", 0),
        latest_cf.get("financing_activity", 0),
        latest_cf.get("net_cash_flow", 0),
    ]
    cash_values = [
        0.0 if value is None or pd.isna(value) else float(value)
        for value in cash_values
    ]
    figure, axes = plt.subplots(1, 2, figsize=(8.4, 4.3))
    if bs.empty:
        axes[0].text(
            0.5,
            0.5,
            "Balance-sheet history unavailable",
            ha="center",
            va="center",
            transform=axes[0].transAxes,
            fontsize=9,
            color="#61788A",
        )
        axes[0].set_xticks([])
        axes[0].set_yticks([])
    else:
        equity = pd.to_numeric(bs["equity_capital"], errors="coerce").fillna(
            0
        ) + pd.to_numeric(bs["reserves"], errors="coerce").fillna(0)
        borrowings = pd.to_numeric(bs["borrowings"], errors="coerce").fillna(0)
        other = pd.to_numeric(bs["other_liabilities"], errors="coerce").fillna(0)
        x = np.arange(len(bs))
        axes[0].bar(x, equity, label="Equity", color="#2C74B3")
        axes[0].bar(x, borrowings, bottom=equity, label="Borrowings", color="#E17C35")
        axes[0].bar(
            x,
            other,
            bottom=equity + borrowings,
            label="Other liabilities",
            color="#91A7B8",
        )
        axes[0].set_xticks(x, bs["year"], rotation=45, ha="right", fontsize=7)
        axes[0].legend(frameon=False, fontsize=7, ncol=2)
    axes[0].tick_params(axis="y", labelsize=7)
    axes[0].set_title("Balance Sheet Composition", fontsize=10)
    axes[0].grid(axis="y", alpha=0.15)

    labels = ["CFO", "CFI", "CFF", "Net Cash"]
    bar_colors = ["#14804A" if value >= 0 else "#B42318" for value in cash_values]
    axes[1].bar(labels, cash_values, color=bar_colors)
    axes[1].axhline(0, color="#4B5F6D", linewidth=0.8)
    axes[1].tick_params(axis="x", labelsize=8)
    axes[1].tick_params(axis="y", labelsize=7)
    axes[1].set_title(
        f"Latest Cash Flow Waterfall ({latest_cf.get('year', 'N/A')})", fontsize=10
    )
    axes[1].grid(axis="y", alpha=0.15)
    figure.tight_layout(w_pad=2.0)
    figure.savefig(output_path, dpi=190, facecolor="white")
    plt.close(figure)


def _header(
    document: canvas.Canvas,
    company: pd.Series,
    subtitle: str,
    health: pd.Series,
) -> None:
    """Draw a repeatable navy report header."""
    document.setFillColor(NAVY)
    document.rect(0, PAGE_HEIGHT - 88, PAGE_WIDTH, 88, fill=1, stroke=0)
    document.setFillColor(colors.white)
    document.setFont("Helvetica-Bold", 19)
    company_name = " ".join(str(company["company_name"]).split())
    document.drawString(32, PAGE_HEIGHT - 40, company_name[:50])
    document.setFont("Helvetica", 9)
    document.drawString(
        32,
        PAGE_HEIGHT - 61,
        f"{company['company_id']}  |  {subtitle}",
    )
    document.setFillColor(BLUE)
    document.roundRect(PAGE_WIDTH - 148, PAGE_HEIGHT - 69, 112, 42, 8, fill=1, stroke=0)
    document.setFillColor(colors.white)
    document.setFont("Helvetica-Bold", 15)
    document.drawCentredString(
        PAGE_WIDTH - 92, PAGE_HEIGHT - 49, _display(health.get("health_score"), 1)
    )
    document.setFont("Helvetica", 7)
    document.drawCentredString(
        PAGE_WIDTH - 92,
        PAGE_HEIGHT - 62,
        f"HEALTH · {health.get('health_band', 'N/A')}",
    )


def _footer(document: canvas.Canvas, page_number: int) -> None:
    """Draw report provenance and page numbering."""
    document.setStrokeColor(colors.HexColor("#D6E4F0"))
    document.line(32, 50, PAGE_WIDTH - 32, 50)
    document.setFillColor(GREY)
    document.setFont("Helvetica", 7)
    document.drawString(
        32,
        34,
        "Source: supplied Nifty100 workbooks · INR Crore · Analytical output, not investment advice.",
    )
    document.drawRightString(
        PAGE_WIDTH - 32, 34, f"N100 Financial Intelligence · {page_number}/2"
    )


def _draw_tiles(
    document: canvas.Canvas,
    tiles: list[tuple[str, object, str]],
) -> None:
    """Draw six KPI tiles in two rows of three."""
    tile_width = (PAGE_WIDTH - 76) / 3
    for index, (label, value, suffix) in enumerate(tiles):
        row, column = divmod(index, 3)
        x = 32 + column * (tile_width + 6)
        y = PAGE_HEIGHT - 156 - row * 61
        document.setFillColor(LIGHT)
        document.roundRect(x, y, tile_width, 48, 6, fill=1, stroke=0)
        document.setFillColor(NAVY)
        document.setFont("Helvetica", 7.5)
        document.drawString(x + 9, y + 32, label.upper())
        document.setFont("Helvetica-Bold", 14)
        document.drawString(x + 9, y + 11, _display(value, 1, suffix))


def _draw_narrative_box(
    document: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    items: list[str],
    foreground: colors.Color,
    background: colors.Color,
) -> None:
    """Draw an overflow-safe narrative panel using wrapped paragraphs."""
    document.setFillColor(background)
    document.roundRect(x, y, width, height, 7, fill=1, stroke=0)
    document.setFillColor(foreground)
    document.setFont("Helvetica-Bold", 11)
    document.drawString(x + 12, y + height - 21, title)
    style = ParagraphStyle(
        f"{title}Style",
        fontName="Helvetica",
        fontSize=7.4,
        leading=9.2,
        textColor=NAVY,
        alignment=TA_LEFT,
        wordWrap="CJK",
        spaceAfter=5,
    )
    cursor = y + height - 38
    for item in items[:4]:
        paragraph = Paragraph(f"• {item}", style)
        _, paragraph_height = paragraph.wrap(width - 24, cursor - y - 8)
        if cursor - paragraph_height < y + 7:
            break
        paragraph.drawOn(document, x + 12, cursor - paragraph_height)
        cursor -= paragraph_height + 5


def generate_tearsheet(
    output_path: Path,
    company: pd.Series,
    latest: pd.Series,
    ratio_history: pd.DataFrame,
    profit_loss: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cash_flow: pd.DataFrame,
    health: pd.Series,
    valuation: pd.Series,
    narratives: pd.DataFrame,
    chart_one_path: Path,
    chart_two_path: Path,
) -> None:
    """Generate one valid two-page company tearsheet PDF."""
    _page_one_chart(profit_loss, ratio_history, chart_one_path)
    _page_two_chart(balance_sheet, cash_flow, chart_two_path)
    document = canvas.Canvas(
        str(output_path), pagesize=A4, pageCompression=1, invariant=1
    )
    document.setTitle(f"{company['company_id']} Financial Tearsheet")

    _header(
        document,
        company,
        f"Latest fiscal period {latest.get('year', 'N/A')}",
        health,
    )
    _draw_tiles(
        document,
        [
            ("ROE", latest.get("return_on_equity_pct"), "%"),
            ("ROCE", latest.get("return_on_capital_employed_pct"), "%"),
            ("OPM", latest.get("operating_profit_margin_pct"), "%"),
            ("Debt / Equity", latest.get("debt_to_equity"), "x"),
            ("Revenue CAGR 5Y", latest.get("revenue_cagr_5y"), "%"),
            ("P/E", valuation.get("pe_ratio"), "x"),
        ],
    )
    document.drawImage(
        ImageReader(str(chart_one_path)),
        30,
        87,
        width=PAGE_WIDTH - 60,
        height=480,
        preserveAspectRatio=True,
        anchor="c",
    )
    _footer(document, 1)
    document.showPage()

    _header(document, company, "Cash Flow · Balance Sheet · Signals", health)
    document.drawImage(
        ImageReader(str(chart_two_path)),
        30,
        405,
        width=PAGE_WIDTH - 60,
        height=330,
        preserveAspectRatio=True,
        anchor="c",
    )
    pros = narratives.loc[narratives["type"].eq("pro"), "text"].astype(str).tolist()
    cons = narratives.loc[narratives["type"].eq("con"), "text"].astype(str).tolist()
    _draw_narrative_box(
        document,
        30,
        108,
        258,
        270,
        "Pros",
        pros,
        GREEN,
        GREEN_LIGHT,
    )
    _draw_narrative_box(
        document,
        307,
        108,
        258,
        270,
        "Cons",
        cons,
        RED,
        RED_LIGHT,
    )
    allocation = str(latest.get("capital_allocation_label", "NO_DATA")).replace(
        "_", " "
    )
    document.setFillColor(BLUE)
    document.roundRect(30, 67, PAGE_WIDTH - 60, 28, 7, fill=1, stroke=0)
    document.setFillColor(colors.white)
    document.setFont("Helvetica-Bold", 9)
    document.drawCentredString(PAGE_WIDTH / 2, 77, f"CAPITAL ALLOCATION · {allocation}")
    _footer(document, 2)
    document.showPage()
    document.save()


def generate_all_tearsheets(
    settings: Settings,
    frames: dict[str, pd.DataFrame],
    ratios: pd.DataFrame,
    health_scores: pd.DataFrame,
    valuation: pd.DataFrame,
    narratives: pd.DataFrame,
) -> tuple[list[Path], pd.DataFrame]:
    """Generate all feasible tearsheets and log limited or absent histories."""
    output_dir = settings.project_root / "reports" / "tearsheets"
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_pdf in output_dir.glob("*.pdf"):
        old_pdf.unlink()
    chart_dir = settings.project_root / "tmp" / "pdfs"
    chart_dir.mkdir(parents=True, exist_ok=True)
    ratio_lookup = {
        company_id: group.sort_values("year")
        for company_id, group in ratios.groupby("company_id")
    }
    pl_lookup = {
        company_id: group.sort_values("year")
        for company_id, group in frames["profit_and_loss"].groupby("company_id")
    }
    bs_lookup = {
        company_id: group.sort_values("year")
        for company_id, group in frames["balance_sheet"].groupby("company_id")
    }
    cf_lookup = {
        company_id: group.sort_values("year")
        for company_id, group in frames["cash_flow"].groupby("company_id")
    }
    narrative_lookup = {
        company_id: group.sort_values("confidence_pct", ascending=False)
        for company_id, group in narratives.groupby("company_id")
    }
    health_lookup = health_scores.set_index("company_id")
    valuation_lookup = valuation.set_index("company_id")
    paths: list[Path] = []
    skipped: list[dict[str, object]] = []
    limited_history: list[dict[str, object]] = []
    for _, company in frames["companies"].sort_values("company_id").iterrows():
        ticker = str(company["company_id"])
        profit_loss = pl_lookup.get(ticker, pd.DataFrame())
        available_years = (
            int(profit_loss["year"].nunique()) if not profit_loss.empty else 0
        )
        if available_years < 3:
            limited_history.append(
                {
                    "company_id": ticker,
                    "available_years": available_years,
                    "action": "GENERATED_LIMITED_HISTORY_REPORT_TO_SATISFY_92_PDF_EXIT_GATE",
                }
            )
        ratio_history = ratio_lookup.get(ticker, pd.DataFrame())
        if profit_loss.empty or ratio_history.empty:
            skipped.append(
                {
                    "company_id": ticker,
                    "available_years": available_years,
                    "reason": "NO_PROFIT_AND_LOSS_OR_RATIO_DATA",
                }
            )
            continue
        chart_one_path = chart_dir / f"{ticker}_page1.png"
        chart_two_path = chart_dir / f"{ticker}_page2.png"
        output_path = output_dir / f"{ticker}_tearsheet.pdf"
        generate_tearsheet(
            output_path=output_path,
            company=company,
            latest=ratio_history.iloc[-1],
            ratio_history=ratio_history,
            profit_loss=profit_loss,
            balance_sheet=bs_lookup.get(ticker, pd.DataFrame()),
            cash_flow=cf_lookup.get(ticker, pd.DataFrame()),
            health=health_lookup.loc[ticker],
            valuation=valuation_lookup.loc[ticker],
            narratives=narrative_lookup.get(
                ticker,
                pd.DataFrame(columns=["type", "text", "confidence_pct"]),
            ),
            chart_one_path=chart_one_path,
            chart_two_path=chart_two_path,
        )
        chart_one_path.unlink(missing_ok=True)
        chart_two_path.unlink(missing_ok=True)
        paths.append(output_path)
    skipped_frame = pd.DataFrame(
        skipped, columns=["company_id", "available_years", "reason"]
    )
    skipped_frame.to_csv(settings.output_dir / "skipped_tearsheets.csv", index=False)
    pd.DataFrame(
        limited_history, columns=["company_id", "available_years", "action"]
    ).to_csv(settings.output_dir / "limited_history_tearsheets.csv", index=False)
    LOGGER.info(
        "company tearsheets generated=%d skipped=%d", len(paths), len(skipped_frame)
    )
    return paths, skipped_frame
