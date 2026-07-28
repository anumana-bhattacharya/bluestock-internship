"""Registry-driven Excel ingestion and validation orchestration."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.config.settings import Settings
from src.config.tables import TABLE_SPECS, TableSpec
from src.etl.normalizer import normalize_column_name
from src.etl.validator import FAILURE_COLUMNS, validate_and_clean

LOGGER = logging.getLogger(__name__)
AUDIT_COLUMNS = (
    "table_name",
    "rows_in",
    "rows_out",
    "rejected_rows",
    "runtime_seconds",
    "load_timestamp",
)


def read_source(path: Path, header: int) -> pd.DataFrame:
    """Read one Excel source with the configured header row."""
    return pd.read_excel(path, header=header)


def prepare_columns(frame: pd.DataFrame, spec: TableSpec) -> pd.DataFrame:
    """Normalize headings and apply the registry rename map."""
    data = frame.copy()
    data.columns = [normalize_column_name(column) for column in data.columns]
    normalized_renames = {
        normalize_column_name(source): target for source, target in spec.rename.items()
    }
    return data.rename(columns=normalized_renames)


def load_sources(
    settings: Settings,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    """Load and validate all twelve sources in dependency order."""
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, pd.DataFrame] = {}
    audits: list[dict[str, object]] = []
    failures: list[pd.DataFrame] = []
    master_tickers: set[str] = set()

    for spec in TABLE_SPECS:
        started = time.perf_counter()
        source_path = settings.project_root / spec.relative_path
        raw = read_source(source_path, spec.header)
        prepared = prepare_columns(raw, spec)
        result = validate_and_clean(
            prepared,
            spec,
            master_tickers,
            orphan_policy=settings.orphan_policy,
        )
        outputs[spec.name] = result.data
        if spec.name == "companies":
            master_tickers = set(result.data["company_id"].dropna().astype(str))
        elapsed = time.perf_counter() - started
        audits.append(
            {
                "table_name": spec.name,
                "rows_in": len(raw),
                "rows_out": len(result.data),
                "rejected_rows": result.rejected_rows,
                "runtime_seconds": round(elapsed, 6),
                "load_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        if not result.failures.empty:
            failures.append(result.failures)
        result.data.to_csv(settings.processed_dir / f"{spec.name}.csv", index=False)
        LOGGER.info(
            "loaded table=%s rows_in=%d rows_out=%d rejected=%d",
            spec.name,
            len(raw),
            len(result.data),
            result.rejected_rows,
        )

    audit_frame = pd.DataFrame(audits, columns=AUDIT_COLUMNS)
    completeness_rows: list[dict[str, object]] = []
    for table_name in ("profit_and_loss", "balance_sheet", "cash_flow"):
        covered = set(outputs[table_name]["company_id"].dropna().astype(str))
        for company_id in sorted(master_tickers - covered):
            completeness_rows.append(
                {
                    "table": table_name,
                    "rule_id": "DQ014",
                    "severity": "WARNING",
                    "company_id": company_id,
                    "year": None,
                    "field": "company_id",
                    "issue": "master company has no retained rows in statement table",
                    "action": "KEEP_FLAGGED",
                }
            )
    failure_frame = (
        pd.concat(failures, ignore_index=True)
        if failures
        else pd.DataFrame(columns=FAILURE_COLUMNS)
    )
    if completeness_rows:
        failure_frame = pd.concat(
            [
                failure_frame,
                pd.DataFrame(completeness_rows, columns=FAILURE_COLUMNS),
            ],
            ignore_index=True,
        )
    audit_frame.to_csv(settings.output_dir / "load_audit.csv", index=False)
    failure_frame.to_csv(settings.output_dir / "validation_failures.csv", index=False)
    return outputs, audit_frame, failure_frame
