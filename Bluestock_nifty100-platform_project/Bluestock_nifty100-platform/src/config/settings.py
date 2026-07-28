"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Hold paths and configurable pipeline thresholds."""

    project_root: Path
    orphan_policy: str
    winsor_lower: float
    winsor_upper: float
    cluster_count: int
    health_weights: dict[str, float]

    @property
    def raw_dir(self) -> Path:
        """Return the core source directory."""
        return self.project_root / "data" / "raw"

    @property
    def supporting_dir(self) -> Path:
        """Return the supporting source directory."""
        return self.project_root / "data" / "supporting"

    @property
    def processed_dir(self) -> Path:
        """Return the processed data directory."""
        return self.project_root / "data" / "processed"

    @property
    def output_dir(self) -> Path:
        """Return the generated output directory."""
        return self.project_root / "output"

    @property
    def database_path(self) -> Path:
        """Return the SQLite database path."""
        return self.project_root / "nifty100.db"

    @property
    def schema_path(self) -> Path:
        """Return the SQL schema path."""
        return self.project_root / "src" / "database" / "schema.sql"


def get_settings(project_root: Path | None = None) -> Settings:
    """Build settings with environment overrides."""
    root = project_root or Path(__file__).resolve().parents[2]
    policy = os.getenv("N100_ORPHAN_POLICY", "quarantine").strip().lower()
    if policy not in {"quarantine", "load"}:
        raise ValueError("N100_ORPHAN_POLICY must be 'quarantine' or 'load'")
    return Settings(
        project_root=root,
        orphan_policy=policy,
        winsor_lower=float(os.getenv("N100_WINSOR_LOWER", "0.10")),
        winsor_upper=float(os.getenv("N100_WINSOR_UPPER", "0.90")),
        cluster_count=int(os.getenv("N100_CLUSTER_COUNT", "5")),
        health_weights={
            "profitability": 35.0,
            "cash_quality": 30.0,
            "growth": 20.0,
            "leverage": 15.0,
        },
    )
