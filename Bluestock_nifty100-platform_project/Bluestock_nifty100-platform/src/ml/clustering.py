"""Winsorised KMeans segmentation and portfolio distribution statistics."""

from __future__ import annotations

import logging

import matplotlib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.analytics.sector_peer import latest_ratios
from src.config.settings import Settings
from src.database.sqlite_loader import load_derived_table

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

LOGGER = logging.getLogger(__name__)
FEATURES = (
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_3y",
    "operating_profit_margin_pct",
    "fcf_conversion_pct",
)


def _prepare_features(
    settings: Settings, ratios: pd.DataFrame, sectors: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Impute and winsorise clustering features."""
    data = sectors[["company_id", "broad_sector"]].merge(
        latest_ratios(ratios), on="company_id", how="left"
    )
    prepared = pd.DataFrame(index=data.index)
    for feature in FEATURES:
        values = pd.to_numeric(data[feature], errors="coerce")
        sector_median = values.groupby(data["broad_sector"]).transform("median")
        values = values.fillna(sector_median).fillna(values.median()).fillna(0.0)
        low = values.quantile(settings.winsor_lower)
        high = values.quantile(settings.winsor_upper)
        prepared[feature] = values.clip(low, high)
    return data[["company_id", "broad_sector"]], prepared


def _centroid_labels(centroids: np.ndarray) -> dict[int, str]:
    """Create descriptive labels from each standardized centroid."""
    friendly = {
        "return_on_equity_pct": "ROE",
        "debt_to_equity": "Leverage",
        "revenue_cagr_3y": "Growth",
        "operating_profit_margin_pct": "Margin",
        "fcf_conversion_pct": "Cash Conversion",
    }
    labels: dict[int, str] = {}
    for cluster_id, centroid in enumerate(centroids):
        strongest = np.argsort(np.abs(centroid))[-2:][::-1]
        parts = [
            f"{'High' if centroid[index] >= 0 else 'Low'} {friendly[FEATURES[index]]}"
            for index in strongest
        ]
        labels[cluster_id] = f"{parts[0]} / {parts[1]}"
    return labels


def compute_clusters(
    settings: Settings, ratios: pd.DataFrame, sectors: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fit five clusters and return labels, prepared features, and centroids."""
    identity, features = _prepare_features(settings, ratios, sectors)
    scaler = StandardScaler()
    standardized = scaler.fit_transform(features)
    model = KMeans(
        n_clusters=settings.cluster_count,
        random_state=42,
        n_init=20,
    )
    cluster_ids = model.fit_predict(standardized)
    labels = _centroid_labels(model.cluster_centers_)
    output = identity[["company_id"]].copy()
    output["cluster_id"] = cluster_ids
    output["cluster_label"] = output["cluster_id"].map(labels)
    centroids = pd.DataFrame(model.cluster_centers_, columns=FEATURES)
    centroids.insert(0, "cluster_id", range(settings.cluster_count))
    centroids["cluster_label"] = centroids["cluster_id"].map(labels)
    return output, features, centroids


def portfolio_statistics(ratios: pd.DataFrame) -> pd.DataFrame:
    """Compute P10, median, and P90 for every numeric KPI."""
    latest = latest_ratios(ratios)
    rows: list[dict[str, float | str]] = []
    for metric in latest.select_dtypes(include="number").columns:
        values = latest[metric].dropna()
        if values.empty:
            continue
        rows.append(
            {
                "metric": metric,
                "p10": values.quantile(0.10),
                "median": values.median(),
                "p90": values.quantile(0.90),
                "minimum": values.min(),
                "maximum": values.max(),
            }
        )
    return pd.DataFrame(rows)


def _save_heatmap(features: pd.DataFrame, path: str) -> None:
    """Save a labelled correlation heatmap using matplotlib."""
    correlation = features.corr()
    figure, axis = plt.subplots(figsize=(8, 6))
    image = axis.imshow(correlation, cmap="RdYlBu", vmin=-1, vmax=1)
    axis.set_xticks(
        range(len(FEATURES)), [name.replace("_", "\n") for name in FEATURES]
    )
    axis.set_yticks(range(len(FEATURES)), [name.replace("_", " ") for name in FEATURES])
    for row in range(len(FEATURES)):
        for column in range(len(FEATURES)):
            axis.text(
                column,
                row,
                f"{correlation.iloc[row, column]:.2f}",
                ha="center",
                va="center",
                fontsize=8,
            )
    axis.set_title("Latest-Year KPI Correlation")
    figure.colorbar(image, ax=axis, shrink=0.8)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def run_clustering(
    settings: Settings, ratios: pd.DataFrame, frames: dict[str, pd.DataFrame]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit clusters, export artifacts, and persist labels/statistics."""
    labels, features, centroids = compute_clusters(settings, ratios, frames["sectors"])
    statistics = portfolio_statistics(ratios)
    labels.to_csv(settings.output_dir / "cluster_labels.csv", index=False)
    centroids.to_csv(settings.output_dir / "cluster_centroids.csv", index=False)
    statistics.to_csv(settings.output_dir / "portfolio_stats.csv", index=False)
    _save_heatmap(features, str(settings.output_dir / "correlation_heatmap.png"))
    load_derived_table(settings, "cluster_labels", labels)
    load_derived_table(settings, "portfolio_stats", statistics)
    LOGGER.info(
        "clusters companies=%d distribution=%s",
        len(labels),
        labels["cluster_id"].value_counts().sort_index().to_dict(),
    )
    return labels, statistics
