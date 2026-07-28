"""End-to-end database and artifact gate tests."""

from __future__ import annotations

import json
import sqlite3

import pandas as pd
from pypdf import PdfReader

from src.config.settings import Settings


def _scalar(connection: sqlite3.Connection, sql: str) -> int:
    """Return one integer query result."""
    return int(connection.execute(sql).fetchone()[0])


def test_database_gates(settings: Settings) -> None:
    """SQLite contains the expected clean, derived universe."""
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert _scalar(connection, "SELECT COUNT(*) FROM companies") == 92
        assert _scalar(connection, "SELECT COUNT(*) FROM computed_ratios") >= 1000
        assert _scalar(connection, "SELECT COUNT(*) FROM health_scores") == 92
        assert _scalar(connection, "SELECT COUNT(*) FROM cluster_labels") == 92
        assert _scalar(connection, "SELECT COUNT(*) FROM sector_benchmarks") == 10


def test_no_duplicate_post_load_keys(settings: Settings) -> None:
    """Post-load primary keys are unique in statement and ratio tables."""
    with sqlite3.connect(settings.database_path) as connection:
        for table in (
            "profit_and_loss",
            "balance_sheet",
            "cash_flow",
            "financial_ratios_reference",
            "computed_ratios",
        ):
            count = _scalar(
                connection,
                f"""
                SELECT COUNT(*) FROM (
                    SELECT company_id, year, COUNT(*) AS n
                    FROM {table} GROUP BY company_id, year HAVING n > 1
                )
                """,
            )
            assert count == 0, table


def test_crosscheck_and_summary(settings: Settings) -> None:
    """Ratio divergence and pipeline summary meet their gates."""
    crosscheck = pd.read_csv(settings.output_dir / "ratio_crosscheck_summary.csv")
    assert crosscheck.iloc[0]["combined_mean_absolute_divergence"] < 0.5
    summary = json.loads(
        (settings.output_dir / "pipeline_summary.json").read_text(encoding="utf-8")
    )
    assert summary["foreign_key_violations"] == 0
    assert summary["computed_ratio_companies"] == 92


def test_pdf_and_excel_artifacts(settings: Settings) -> None:
    """All PDF and required workbook artifacts are non-empty."""
    company_pdfs = list(
        (settings.project_root / "reports" / "tearsheets").glob("*.pdf")
    )
    sector_pdfs = list((settings.project_root / "reports" / "sector").glob("*.pdf"))
    assert len(company_pdfs) == 92
    assert len(sector_pdfs) == 10
    assert all(
        path.stat().st_size >= 30_000
        and path.read_bytes()[:4] == b"%PDF"
        and len(PdfReader(path).pages) == 2
        for path in company_pdfs
    )
    assert all(
        path.stat().st_size >= 1000
        and path.read_bytes()[:4] == b"%PDF"
        and len(PdfReader(path).pages) >= 2
        for path in sector_pdfs
    )
    portfolio = (
        settings.project_root / "reports" / "portfolio" / "portfolio_summary.pdf"
    )
    assert portfolio.stat().st_size >= 1000
    assert len(PdfReader(portfolio).pages) == 92
    for name in (
        "screener_output.xlsx",
        "valuation_summary.xlsx",
        "cashflow_intelligence.xlsx",
        "nifty100_full_universe.xlsx",
    ):
        assert (settings.output_dir / name).stat().st_size > 1000


def test_nlp_and_percentile_coverage(settings: Settings) -> None:
    """Every company has pro/con coverage and peer directions are bounded."""
    narratives = pd.read_csv(settings.output_dir / "pros_cons_generated.csv")
    assert list(narratives.columns) == [
        "company_id",
        "type",
        "rule_id",
        "text",
        "confidence_pct",
    ]
    assert narratives["confidence_pct"].gt(60).all()
    coverage = narratives.groupby(["company_id", "type"]).size().unstack(fill_value=0)
    assert len(coverage) == 92
    assert (coverage[["pro", "con"]] >= 1).all().all()
    peers = pd.read_csv(settings.output_dir / "peer_percentiles.csv")
    percentile_columns = [column for column in peers if column.endswith("percentile")]
    assert peers[percentile_columns].stack().dropna().between(0, 1).all()


def test_sprint5_tabular_contracts(settings: Settings) -> None:
    """Sprint 5 parser and cash-flow artifacts have exact required schemas."""
    parsed = pd.read_csv(settings.output_dir / "analysis_parsed.csv")
    assert list(parsed.columns) == [
        "company_id",
        "metric_type",
        "period_years",
        "value_pct",
    ]
    assert (settings.output_dir / "parse_failures.csv").exists()
    validation = pd.read_csv(settings.output_dir / "analysis_cross_validation.csv")
    assert "manual_review_flag" in validation
    cashflow = pd.read_excel(
        settings.output_dir / "cashflow_intelligence.xlsx",
        sheet_name="Cash Flow Intelligence",
    )
    assert len(cashflow) == 92
    assert list(cashflow.columns) == [
        "company_id",
        "sector",
        "cfo_quality_score",
        "cfo_quality_label",
        "capex_intensity_pct",
        "capex_label",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
        "distress_flag",
        "deleveraging_flag",
        "capital_allocation_label",
    ]
    assert (settings.output_dir / "pattern_changes.csv").exists()
    assert (settings.output_dir / "capital_allocation_distribution.csv").exists()
