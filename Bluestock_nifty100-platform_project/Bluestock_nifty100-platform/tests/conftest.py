"""Shared test fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.config.settings import Settings, get_settings
from src.orchestration.pipeline import run_pipeline


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the repository root."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def settings(project_root: Path) -> Settings:
    """Return test settings and ensure a verified database exists."""
    configured = get_settings(project_root)
    if os.getenv("N100_TEST_REBUILD") == "1" or not configured.database_path.exists():
        run_pipeline(project_root, through="all")
    return configured
