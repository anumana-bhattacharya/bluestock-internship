"""Execute the exploratory SQL file statement-by-statement."""

from __future__ import annotations

import logging
import sqlite3

from src.common.logging import configure_logging
from src.config.settings import get_settings

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Execute and log compact results for all exploratory statements."""
    configure_logging()
    settings = get_settings()
    sql_path = settings.output_dir / "exploratory_queries.sql"
    statements = [
        statement.strip()
        for statement in sql_path.read_text(encoding="utf-8").split(";")
        if statement.strip()
    ]
    with sqlite3.connect(settings.database_path) as connection:
        for index, statement in enumerate(statements, start=1):
            cursor = connection.execute(statement)
            rows = cursor.fetchmany(10) if cursor.description else []
            LOGGER.info("query=%02d sample_rows=%s", index, rows)


if __name__ == "__main__":
    main()
