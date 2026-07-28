"""Declarative registry for all twelve source datasets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

YearKind = Literal["none", "fiscal", "calendar", "date"]


@dataclass(frozen=True)
class TableSpec:
    """Describe how one source dataset is loaded and validated."""

    name: str
    relative_path: str
    header: int
    primary_key: tuple[str, ...]
    company_fk: bool
    year_column: str | None
    year_kind: YearKind
    rename: dict[str, str]
    not_null: tuple[str, ...]
    non_negative: tuple[str, ...] = ()
    positive: tuple[str, ...] = ()
    url_columns: tuple[str, ...] = ()


TABLE_SPECS: tuple[TableSpec, ...] = (
    TableSpec(
        name="companies",
        relative_path="data/raw/companies.xlsx",
        header=1,
        primary_key=("company_id",),
        company_fk=False,
        year_column=None,
        year_kind="none",
        rename={"id": "company_id"},
        not_null=("company_id", "company_name"),
        positive=("face_value",),
        url_columns=("website", "nse_profile", "bse_profile"),
    ),
    TableSpec(
        name="profit_and_loss",
        relative_path="data/raw/profitandloss.xlsx",
        header=1,
        primary_key=("company_id", "year"),
        company_fk=True,
        year_column="year",
        year_kind="fiscal",
        rename={"id": "source_id"},
        not_null=("company_id", "year", "sales", "net_profit"),
        non_negative=("sales", "expenses", "depreciation"),
    ),
    TableSpec(
        name="balance_sheet",
        relative_path="data/raw/balancesheet.xlsx",
        header=1,
        primary_key=("company_id", "year"),
        company_fk=True,
        year_column="year",
        year_kind="fiscal",
        rename={"id": "source_id"},
        not_null=("company_id", "year", "total_assets", "total_liabilities"),
        non_negative=("equity_capital", "borrowings", "total_assets"),
        positive=("total_assets",),
    ),
    TableSpec(
        name="cash_flow",
        relative_path="data/raw/cashflow.xlsx",
        header=1,
        primary_key=("company_id", "year"),
        company_fk=True,
        year_column="year",
        year_kind="fiscal",
        rename={"id": "source_id"},
        not_null=("company_id", "year"),
    ),
    TableSpec(
        name="analysis",
        relative_path="data/raw/analysis.xlsx",
        header=1,
        primary_key=("source_id",),
        company_fk=True,
        year_column=None,
        year_kind="none",
        rename={"id": "source_id"},
        not_null=("source_id", "company_id"),
    ),
    TableSpec(
        name="documents",
        relative_path="data/raw/documents.xlsx",
        header=1,
        primary_key=("company_id", "year"),
        company_fk=True,
        year_column="year",
        year_kind="calendar",
        rename={"id": "source_id", "Year": "year", "Annual_Report": "annual_report"},
        not_null=("company_id", "year"),
        url_columns=("annual_report",),
    ),
    TableSpec(
        name="pros_and_cons",
        relative_path="data/raw/prosandcons.xlsx",
        header=1,
        primary_key=("source_id",),
        company_fk=True,
        year_column=None,
        year_kind="none",
        rename={"id": "source_id"},
        not_null=("source_id", "company_id"),
    ),
    TableSpec(
        name="sectors",
        relative_path="data/supporting/sectors.xlsx",
        header=0,
        primary_key=("company_id",),
        company_fk=True,
        year_column=None,
        year_kind="none",
        rename={"id": "source_id"},
        not_null=("company_id", "broad_sector", "sub_sector"),
        non_negative=("index_weight_pct",),
    ),
    TableSpec(
        name="market_cap",
        relative_path="data/supporting/market_cap.xlsx",
        header=0,
        primary_key=("company_id", "year"),
        company_fk=True,
        year_column="year",
        year_kind="calendar",
        rename={"id": "source_id"},
        not_null=("company_id", "year", "market_cap_crore"),
        positive=("market_cap_crore", "enterprise_value_crore"),
    ),
    TableSpec(
        name="stock_prices",
        relative_path="data/supporting/stock_prices.xlsx",
        header=0,
        primary_key=("company_id", "date"),
        company_fk=True,
        year_column="date",
        year_kind="date",
        rename={"id": "source_id"},
        not_null=("company_id", "date", "close_price"),
        positive=("open_price", "high_price", "low_price", "close_price", "volume"),
    ),
    TableSpec(
        name="financial_ratios_reference",
        relative_path="data/supporting/financial_ratios.xlsx",
        header=0,
        primary_key=("company_id", "year"),
        company_fk=True,
        year_column="year",
        year_kind="fiscal",
        rename={"id": "source_id"},
        not_null=("company_id", "year"),
    ),
    TableSpec(
        name="peer_groups",
        relative_path="data/supporting/peer_groups.xlsx",
        header=0,
        primary_key=("peer_group_name", "company_id"),
        company_fk=True,
        year_column=None,
        year_kind="none",
        rename={"id": "source_id"},
        not_null=("peer_group_name", "company_id", "is_benchmark"),
    ),
)

TABLE_SPEC_BY_NAME = {spec.name: spec for spec in TABLE_SPECS}
