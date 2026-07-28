"""Command-line entry point for staged and full pipeline execution."""

from __future__ import annotations

import argparse
import json
import logging

from src.orchestration.pipeline import STAGES, run_pipeline

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Parse CLI options and run the requested pipeline stage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--through", choices=STAGES, default="all")
    arguments = parser.parse_args()
    metrics = run_pipeline(through=arguments.through)
    LOGGER.info("completed metrics\n%s", json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
