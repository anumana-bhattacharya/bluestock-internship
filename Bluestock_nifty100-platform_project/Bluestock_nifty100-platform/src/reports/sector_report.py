"""Overflow-safe broad-sector benchmark reports with complete member tables."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.config.settings import Settings

LOGGER = logging.getLogger(__name__)
PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
NAVY = colors.HexColor("#0B3558")
BLUE = colors.HexColor("#2C74B3")
LIGHT = colors.HexColor("#EAF2F8")
GREY = colors.HexColor("#61788A")


def _slug(value: str) -> str:
    """Convert a sector name into a stable PDF stem."""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _display(value: Any) -> str:
    """Format a compact sector metric."""
    return "N/A" if value is None or pd.isna(value) else f"{float(value):,.1f}"


def _page_decor(canvas: Any, document: Any) -> None:
    """Draw consistent sector report headers and footers."""
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_HEIGHT - 25 * mm, PAGE_WIDTH, 25 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(
        18 * mm,
        PAGE_HEIGHT - 15 * mm,
        str(document.title),
    )
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(
        PAGE_WIDTH - 18 * mm,
        PAGE_HEIGHT - 15 * mm,
        f"Page {document.page}",
    )
    canvas.setStrokeColor(colors.HexColor("#D6E4F0"))
    canvas.line(18 * mm, 14 * mm, PAGE_WIDTH - 18 * mm, 14 * mm)
    canvas.setFillColor(GREY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(
        18 * mm,
        9 * mm,
        "Observed sector taxonomy from sectors.xlsx · INR Crore · Analytical output, not investment advice.",
    )
    canvas.restoreState()


def generate_sector_report(
    output_path: Path,
    benchmark: pd.Series,
    members: pd.DataFrame,
) -> None:
    """Generate one sector summary plus a complete eight-metric member table."""
    sector = str(benchmark["broad_sector"])
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=31 * mm,
        bottomMargin=19 * mm,
        title=f"{sector} Sector Intelligence",
        pageCompression=1,
        invariant=1,
    )
    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "SectorHeading",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=NAVY,
        spaceAfter=6,
        wordWrap="CJK",
    )
    subheading = ParagraphStyle(
        "SectorSubheading",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=GREY,
        wordWrap="CJK",
    )
    cell_style = ParagraphStyle(
        "SectorCell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.2,
        leading=8.5,
        textColor=NAVY,
        alignment=TA_LEFT,
        wordWrap="CJK",
    )
    numeric_style = ParagraphStyle(
        "SectorNumericCell",
        parent=cell_style,
        alignment=TA_CENTER,
    )
    header_style = ParagraphStyle(
        "SectorHeaderCell",
        parent=numeric_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        wordWrap="CJK",
    )
    story: list[Any] = [
        Paragraph(f"{sector} Sector Intelligence", heading),
        Paragraph(
            f"{int(benchmark['company_count'])} companies · observed sector rank "
            f"{int(benchmark['sector_rank'])} of {int(members.attrs.get('sector_count', 0))}",
            subheading,
        ),
        Spacer(1, 12 * mm),
    ]
    metric_pairs = [
        ("Median Health Score", benchmark.get("median_health_score")),
        ("Median ROE", benchmark.get("median_roe")),
        (
            "Median ROCE",
            pd.to_numeric(
                members["return_on_capital_employed_pct"], errors="coerce"
            ).median(),
        ),
        ("Median Net Margin", benchmark.get("median_npm")),
        ("Median Operating Margin", benchmark.get("median_opm")),
        ("Median Debt / Equity", benchmark.get("median_debt_to_equity")),
        ("Median Revenue CAGR 3Y", benchmark.get("median_revenue_cagr_3y")),
        ("Median FCF Conversion", benchmark.get("median_fcf_conversion")),
    ]
    metric_cells: list[list[Paragraph]] = []
    for row_start in range(0, len(metric_pairs), 4):
        labels = [
            Paragraph(metric_pairs[index][0], cell_style)
            for index in range(row_start, row_start + 4)
        ]
        values = [
            Paragraph(
                f"<b>{_display(metric_pairs[index][1])}</b>",
                ParagraphStyle(
                    f"Metric{index}",
                    parent=numeric_style,
                    fontSize=16,
                    leading=19,
                    textColor=BLUE,
                ),
            )
            for index in range(row_start, row_start + 4)
        ]
        metric_cells.extend([labels, values])
    metric_table = Table(
        metric_cells, colWidths=[45 * mm] * 4, rowHeights=[10 * mm, 16 * mm] * 2
    )
    metric_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6E4F0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend(
        [
            metric_table,
            Spacer(1, 11 * mm),
            Paragraph(
                "Benchmark medians are based on the latest available fiscal period for each company.",
                subheading,
            ),
            PageBreak(),
            Paragraph("Company Metrics", heading),
            Paragraph(
                "All observed companies are included; cells use wrapped paragraphs to prevent overflow.",
                subheading,
            ),
            Spacer(1, 5 * mm),
        ]
    )
    columns = [
        ("Ticker", "company_id", cell_style),
        ("Health", "health_score", numeric_style),
        ("ROE %", "return_on_equity_pct", numeric_style),
        ("ROCE %", "return_on_capital_employed_pct", numeric_style),
        ("NPM %", "net_profit_margin_pct", numeric_style),
        ("OPM %", "operating_profit_margin_pct", numeric_style),
        ("D/E x", "debt_to_equity", numeric_style),
        ("Revenue CAGR 3Y %", "revenue_cagr_3y", numeric_style),
        ("FCF Conversion %", "fcf_conversion_pct", numeric_style),
    ]
    table_data: list[list[Paragraph]] = [
        [Paragraph(label, header_style) for label, _, _ in columns]
    ]
    for _, row in members.iterrows():
        table_data.append(
            [
                Paragraph(
                    (
                        str(row.get(field))
                        if field == "company_id"
                        else _display(row.get(field))
                    ),
                    style,
                )
                for _, field, style in columns
            ]
        )
    column_widths = [
        26 * mm,
        18 * mm,
        18 * mm,
        18 * mm,
        18 * mm,
        18 * mm,
        16 * mm,
        31 * mm,
        29 * mm,
    ]
    member_table = Table(
        table_data,
        colWidths=column_widths,
        repeatRows=1,
        hAlign="LEFT",
    )
    member_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D6E4F0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(member_table)
    document.build(story, onFirstPage=_page_decor, onLaterPages=_page_decor)


def generate_all_sector_reports(
    settings: Settings,
    sector_benchmarks: pd.DataFrame,
    sectors: pd.DataFrame,
    latest_ratio_frame: pd.DataFrame,
    health_scores: pd.DataFrame,
) -> list[Path]:
    """Generate one report per observed broad sector."""
    output_dir = settings.project_root / "reports" / "sector"
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_pdf in output_dir.glob("*.pdf"):
        old_pdf.unlink()
    universe = (
        sectors[["company_id", "broad_sector"]]
        .merge(latest_ratio_frame, on="company_id", how="left")
        .merge(
            health_scores[["company_id", "health_score"]], on="company_id", how="left"
        )
    )
    paths: list[Path] = []
    sector_count = int(sector_benchmarks["broad_sector"].nunique())
    for _, benchmark in sector_benchmarks.iterrows():
        sector = str(benchmark["broad_sector"])
        members = universe.loc[universe["broad_sector"].eq(sector)].sort_values(
            "health_score", ascending=False
        )
        members.attrs["sector_count"] = sector_count
        path = output_dir / f"{_slug(sector)}_report.pdf"
        generate_sector_report(path, benchmark, members)
        paths.append(path)
    LOGGER.info("sector reports generated=%d", len(paths))
    return paths
