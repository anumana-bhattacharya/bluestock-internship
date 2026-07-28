"""End-to-end, idempotent six-sprint pipeline orchestration."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.common.logging import PipelineError, configure_logging
from src.config.settings import Settings, get_settings
from src.database.sqlite_loader import (
    foreign_key_violations,
    load_derived_table,
    load_source_tables,
)
from src.etl.loader import load_sources

LOGGER = logging.getLogger(__name__)
STAGES = ("load", "ratios", "sprint3", "all")


def _ensure_directories(settings: Settings) -> None:
    """Create every generated-artifact directory."""
    for path in (
        settings.processed_dir,
        settings.output_dir,
        settings.project_root / "reports" / "tearsheets",
        settings.project_root / "reports" / "sector",
        settings.project_root / "reports" / "portfolio",
        settings.project_root / "tmp" / "pdfs",
    ):
        path.mkdir(parents=True, exist_ok=True)


def _pdf_is_valid(path: Path, minimum_bytes: int = 1000) -> bool:
    """Check the PDF signature and minimum non-trivial size."""
    return path.stat().st_size >= minimum_bytes and path.read_bytes()[:4] == b"%PDF"


def run_pipeline(
    project_root: Path | None = None, through: str = "all"
) -> dict[str, Any]:
    """Execute the requested pipeline stage and all prerequisites."""
    if through not in STAGES:
        raise ValueError(f"through must be one of {STAGES}")
    configure_logging()
    settings = get_settings(project_root)
    _ensure_directories(settings)
    frames, audit, failures = load_sources(settings)
    load_source_tables(settings, frames)
    load_derived_table(settings, "load_audit", audit)
    load_derived_table(
        settings,
        "validation_failures",
        failures.rename(columns={"table": "table_name"}),
    )
    metrics: dict[str, Any] = {
        "source_rows_in": int(audit["rows_in"].sum()),
        "source_rows_loaded": int(audit["rows_out"].sum()),
        "source_rows_rejected": int(audit["rejected_rows"].sum()),
        "orphan_rows_quarantined": int(
            failures.loc[
                failures["rule_id"].eq("DQ008")
                & failures["action"].eq("REJECT_QUARANTINE")
            ].shape[0]
        ),
        "ttm_rows_rejected": int(failures["rule_id"].eq("DQ003").sum()),
        "foreign_key_violations": len(foreign_key_violations(settings)),
    }
    if through == "load":
        _save_summary(settings, metrics)
        return metrics

    from src.analytics.ratio_engine import run_ratio_engine

    ratios, crosscheck = run_ratio_engine(settings, frames)
    metrics.update(
        {
            "computed_ratio_rows": len(ratios),
            "computed_ratio_companies": int(ratios["company_id"].nunique()),
            "ratio_crosscheck_matched_rows": int(crosscheck.at[0, "matched_rows"]),
            "ratio_mean_absolute_divergence": float(
                crosscheck.at[0, "combined_mean_absolute_divergence"]
            ),
        }
    )
    if through == "ratios":
        metrics["foreign_key_violations"] = len(foreign_key_violations(settings))
        _save_summary(settings, metrics)
        return metrics

    from src.analytics.health_score import run_health_scores
    from src.analytics.screener import run_screener
    from src.analytics.sector_peer import run_sector_peer
    from src.analytics.valuation import run_valuation

    health = run_health_scores(settings, ratios, frames)
    sectors, peers = run_sector_peer(settings, ratios, health, frames)
    valuation = run_valuation(settings, ratios, frames)
    _, screens = run_screener(settings, ratios, health, valuation, frames["sectors"])
    metrics.update(
        {
            "health_band_distribution": health["health_band"].value_counts().to_dict(),
            "sector_count": len(sectors),
            "peer_group_count": int(peers["peer_group_name"].nunique()),
            "screener_counts": {name: len(frame) for name, frame in screens.items()},
            "valuation_companies": len(valuation),
        }
    )
    if through == "sprint3":
        metrics["foreign_key_violations"] = len(foreign_key_violations(settings))
        _save_summary(settings, metrics)
        return metrics

    from src.analytics.cashflow_kpis import run_cashflow_kpis
    from src.analytics.sector_peer import latest_ratios
    from src.ml.clustering import run_clustering
    from src.nlp.pros_cons_generator import run_text_intelligence
    from src.reports.exports import export_full_universe
    from src.reports.portfolio_report import generate_portfolio_summary
    from src.reports.sector_report import generate_all_sector_reports
    from src.reports.tearsheet import generate_all_tearsheets

    cashflow = run_cashflow_kpis(settings, ratios, frames)
    _, narratives = run_text_intelligence(
        settings, frames, ratios, health, valuation, cashflow
    )
    clusters, statistics = run_clustering(settings, ratios, frames)
    company_pdfs, skipped_tearsheets = generate_all_tearsheets(
        settings, frames, ratios, health, valuation, narratives
    )
    sector_pdfs = generate_all_sector_reports(
        settings,
        sectors,
        frames["sectors"],
        latest_ratios(ratios),
        health,
    )
    portfolio_pdf = generate_portfolio_summary(
        settings,
        frames["companies"],
        frames["sectors"],
        ratios,
        health,
    )
    export_full_universe(
        settings.output_dir / "nifty100_full_universe.xlsx",
        frames["companies"],
        latest_ratios(ratios),
        health,
        valuation,
        frames["sectors"],
        peers,
        cashflow,
        clusters,
        failures,
        audit,
    )
    invalid_pdfs = [
        str(path) for path in company_pdfs if not _pdf_is_valid(path, 30_000)
    ]
    invalid_pdfs.extend(
        str(path) for path in [*sector_pdfs, portfolio_pdf] if not _pdf_is_valid(path)
    )
    if invalid_pdfs:
        raise PipelineError(f"invalid generated PDFs: {invalid_pdfs[:3]}")
    metrics.update(
        {
            "cashflow_companies": len(cashflow),
            "distress_alerts": int(cashflow["distress_flag"].sum()),
            "narrative_companies": int(narratives["company_id"].nunique()),
            "generated_narratives": len(narratives),
            "narrative_pro_coverage": int(
                narratives.loc[narratives["type"].eq("pro"), "company_id"].nunique()
            ),
            "narrative_con_coverage": int(
                narratives.loc[narratives["type"].eq("con"), "company_id"].nunique()
            ),
            "parse_failures": len(
                pd.read_csv(settings.output_dir / "parse_failures.csv")
            ),
            "analysis_manual_reviews": int(
                pd.read_csv(settings.output_dir / "analysis_cross_validation.csv")[
                    "manual_review_flag"
                ].sum()
            ),
            "cluster_distribution": clusters["cluster_id"]
            .value_counts()
            .sort_index()
            .to_dict(),
            "portfolio_stat_metrics": len(statistics),
            "company_pdf_count": len(company_pdfs),
            "skipped_tearsheet_count": len(skipped_tearsheets),
            "minimum_company_pdf_bytes": min(
                path.stat().st_size for path in company_pdfs
            ),
            "sector_pdf_count": len(sector_pdfs),
            "portfolio_pdf_count": 1,
            "xlsx_artifact_count": len(list(settings.output_dir.glob("*.xlsx"))),
            "foreign_key_violations": len(foreign_key_violations(settings)),
        }
    )
    _save_summary(settings, metrics)
    return metrics


def _save_summary(settings: Settings, metrics: dict[str, Any]) -> None:
    """Persist and log the concrete pipeline metrics."""
    path = settings.output_dir / "pipeline_summary.json"
    path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    LOGGER.info("pipeline summary\n%s", json.dumps(metrics, indent=2, sort_keys=True))
