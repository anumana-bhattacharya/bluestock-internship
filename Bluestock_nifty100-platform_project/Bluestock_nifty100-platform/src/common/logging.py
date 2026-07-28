"""Central logging setup and platform exceptions."""

from __future__ import annotations

import logging


class DataValidationError(ValueError):
    """Represent a critical source-data validation error."""


class PipelineError(RuntimeError):
    """Represent an unrecoverable pipeline-stage error."""


def configure_logging(level: int = logging.INFO) -> None:
    """Configure concise structured process logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
