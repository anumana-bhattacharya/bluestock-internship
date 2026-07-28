"""Professional CSV and Excel export helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

HEADER_COLOR = "#0B3558"
ACCENT_COLOR = "#2C74B3"
LIGHT_BLUE = "#EAF2F8"


def write_formatted_workbook(
    path: Path,
    sheets: dict[str, pd.DataFrame],
    conditional_columns: dict[str, list[str]] | None = None,
) -> None:
    """Write a typed, filtered, and consistently formatted Excel workbook."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conditional_columns = conditional_columns or {}
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        workbook = writer.book
        title_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": HEADER_COLOR,
                "border": 0,
                "align": "left",
            }
        )
        integer_format = workbook.add_format({"num_format": "#,##0"})
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        percent_format = workbook.add_format({"num_format": "0.00"})
        for sheet_name, frame in sheets.items():
            safe_name = sheet_name[:31]
            export = frame.copy()
            for column in export.select_dtypes(include=["object", "string"]).columns:
                export[column] = export[column].map(
                    lambda value: (
                        " ".join(value.split()) if isinstance(value, str) else value
                    )
                )
            export.to_excel(writer, sheet_name=safe_name, index=False)
            worksheet = writer.sheets[safe_name]
            worksheet.hide_gridlines(2)
            worksheet.freeze_panes(1, 2 if len(export.columns) > 2 else 1)
            if len(export.columns):
                worksheet.autofilter(0, 0, max(len(export), 1), len(export.columns) - 1)
                worksheet.set_row(0, 24, title_format)
            for index, column in enumerate(export.columns):
                series = export[column]
                populated_lengths = series.dropna().astype(str).str.len()
                is_text = pd.api.types.is_object_dtype(
                    series
                ) or pd.api.types.is_string_dtype(series)
                target_length = (
                    populated_lengths.max()
                    if is_text and not populated_lengths.empty
                    else populated_lengths.quantile(0.95)
                )
                observed_width = (
                    int(target_length) + 2
                    if not populated_lengths.empty and pd.notna(target_length)
                    else len(str(column)) + 2
                )
                width = min(
                    max(
                        len(str(column)) + 2,
                        observed_width,
                    ),
                    76 if is_text else 24,
                )
                format_object = None
                lowered = str(column).lower()
                if pd.api.types.is_integer_dtype(series):
                    format_object = integer_format
                elif pd.api.types.is_numeric_dtype(series):
                    format_object = (
                        percent_format
                        if any(
                            token in lowered
                            for token in ("pct", "score", "percentile", "yield")
                        )
                        else number_format
                    )
                worksheet.set_column(index, index, width, format_object)
            for column in conditional_columns.get(sheet_name, []):
                if column not in export.columns or export.empty:
                    continue
                col_index = export.columns.get_loc(column)
                worksheet.conditional_format(
                    1,
                    col_index,
                    len(export),
                    col_index,
                    {
                        "type": "3_color_scale",
                        "min_color": "#F8696B",
                        "mid_color": "#FFEB84",
                        "max_color": "#63BE7B",
                    },
                )


def export_full_universe(
    path: Path,
    companies: pd.DataFrame,
    latest_ratios: pd.DataFrame,
    health_scores: pd.DataFrame,
    valuation: pd.DataFrame,
    sectors: pd.DataFrame,
    peers: pd.DataFrame,
    cashflow: pd.DataFrame,
    clusters: pd.DataFrame,
    validation_failures: pd.DataFrame,
    load_audit: pd.DataFrame,
) -> None:
    """Export the full analytical universe and audit layers to Excel."""
    universe = (
        companies[["company_id", "company_name", "website"]]
        .merge(sectors, on="company_id", how="left", suffixes=("", "_sector"))
        .merge(latest_ratios, on="company_id", how="left")
        .merge(health_scores, on=["company_id", "year"], how="left")
        .merge(
            valuation.drop(columns=["year", "broad_sector"], errors="ignore"),
            on="company_id",
            how="left",
            suffixes=("", "_valuation"),
        )
        .merge(cashflow, on="company_id", how="left", suffixes=("", "_cashflow"))
        .merge(clusters, on="company_id", how="left")
    )
    write_formatted_workbook(
        path,
        {
            "Universe": universe,
            "Ratios Latest": latest_ratios,
            "Health Scores": health_scores,
            "Valuation": valuation,
            "Sector Benchmarks": sectors,
            "Peer Percentiles": peers,
            "Cash Flow": cashflow,
            "Clusters": clusters,
            "Load Audit": load_audit,
            "DQ Failures": validation_failures,
        },
        conditional_columns={
            "Universe": ["health_score", "return_on_equity_pct", "fcf_yield_pct"],
            "Health Scores": ["health_score"],
            "Peer Percentiles": ["composite_percentile"],
        },
    )
