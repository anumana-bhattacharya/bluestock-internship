"""Idempotent, parameterized SQLite persistence."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

from src.config.settings import Settings
from src.config.tables import TABLE_SPECS


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection with foreign keys enabled."""
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(settings: Settings) -> None:
    """Create all declared source and derived tables."""
    with connect(settings.database_path) as connection:
        connection.executescript(settings.schema_path.read_text(encoding="utf-8"))


def _python_value(value: object) -> object:
    """Convert pandas and NumPy scalars into SQLite-safe values."""
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, bool):
        return int(value)
    return value


def replace_rows(
    connection: sqlite3.Connection, table: str, frame: pd.DataFrame
) -> None:
    """Replace all rows in one existing table using bound parameters."""
    columns = list(frame.columns)
    existing = {
        row["name"]
        for row in connection.execute(f'PRAGMA table_info("{table}")').fetchall()
    }
    columns = [column for column in columns if column in existing]
    connection.execute(f'DELETE FROM "{table}"')
    if not columns or frame.empty:
        return
    placeholders = ", ".join("?" for _ in columns)
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    sql = f'INSERT INTO "{table}" ({quoted_columns}) VALUES ({placeholders})'
    rows = [
        tuple(_python_value(value) for value in row)
        for row in frame[columns].itertuples(index=False, name=None)
    ]
    connection.executemany(sql, rows)


def load_source_tables(settings: Settings, frames: dict[str, pd.DataFrame]) -> None:
    """Load the twelve cleaned source tables idempotently."""
    initialize_database(settings)
    with connect(settings.database_path) as connection:
        connection.execute("PRAGMA defer_foreign_keys = ON")
        derived_tables = (
            "pros_cons_generated",
            "analysis_parsed",
            "cluster_labels",
            "portfolio_stats",
            "cashflow_intelligence",
            "valuation_summary",
            "peer_percentiles",
            "sector_benchmarks",
            "health_scores",
            "computed_ratios",
            "load_audit",
            "validation_failures",
        )
        for table in derived_tables:
            connection.execute(f'DELETE FROM "{table}"')
        for spec in reversed(TABLE_SPECS):
            connection.execute(f'DELETE FROM "{spec.name}"')
        for spec in TABLE_SPECS:
            replace_rows(connection, spec.name, frames[spec.name])


def load_derived_table(settings: Settings, table: str, frame: pd.DataFrame) -> None:
    """Replace a derived table with the supplied rows."""
    with connect(settings.database_path) as connection:
        replace_rows(connection, table, frame)


def foreign_key_violations(settings: Settings) -> list[sqlite3.Row]:
    """Return every SQLite foreign-key violation."""
    with connect(settings.database_path) as connection:
        return connection.execute("PRAGMA foreign_key_check").fetchall()
