import sqlite3

import pandas as pd
import pytest

from src.analytics.peer import (
    calculate_percent_rank,
    build_peer_percentiles,
)


def test_percent_rank_basic():
    values = pd.Series([10, 20, 30, 40, 50])

    result = calculate_percent_rank(values)

    assert result.iloc[0] == 0.0
    assert result.iloc[-1] == 1.0
    assert result.iloc[2] == 0.5


def test_percent_rank_with_missing_values():
    values = pd.Series([10, None, 30, None, 50])

    result = calculate_percent_rank(values)

    assert result.notna().sum() == 3
    assert pd.isna(result.iloc[1])
    assert pd.isna(result.iloc[3])
    assert result.iloc[0] == 0.0
    assert result.iloc[2] == 0.5
    assert result.iloc[4] == 1.0


def test_percent_rank_single_value():
    values = pd.Series([100])

    result = calculate_percent_rank(values)

    assert result.iloc[0] == 0.0


def test_peer_percentiles_contains_all_metrics():
    financial_data = pd.DataFrame(
        {
            "company_id": ["AAA", "BBB", "CCC"],
            "year": [2024, 2024, 2024],
            "return_on_equity_pct": [10, 20, 30],
            "roce_pct": [10, 20, 30],
            "net_profit_margin_pct": [5, 10, 15],
            "debt_to_equity": [3, 2, 1],
            "free_cash_flow_cr": [100, 200, 300],
            "pat_cagr_5yr": [5, 10, 15],
            "revenue_cagr_5yr": [5, 10, 15],
            "eps_cagr_5yr": [5, 10, 15],
            "interest_coverage": [2, 4, 6],
            "asset_turnover": [0.5, 1.0, 1.5],
        }
    )

    peer_groups = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "peer_group_name": ["Test Group"] * 3,
            "company_id": ["AAA", "BBB", "CCC"],
            "is_benchmark": [True, False, False],
        }
    )

    result = build_peer_percentiles(financial_data, peer_groups)

    assert set(result["metric"].unique()) == {
        "ROE",
        "ROCE",
        "Net Profit Margin",
        "D/E",
        "FCF",
        "PAT CAGR 5yr",
        "Revenue CAGR 5yr",
        "EPS CAGR 5yr",
        "Interest Coverage",
        "Asset Turnover",
    }


def test_de_inversion():
    financial_data = pd.DataFrame(
        {
            "company_id": ["AAA", "BBB", "CCC"],
            "year": [2024, 2024, 2024],
            "return_on_equity_pct": [10, 10, 10],
            "roce_pct": [10, 10, 10],
            "net_profit_margin_pct": [10, 10, 10],
            "debt_to_equity": [1, 2, 3],
            "free_cash_flow_cr": [100, 100, 100],
            "pat_cagr_5yr": [10, 10, 10],
            "revenue_cagr_5yr": [10, 10, 10],
            "eps_cagr_5yr": [10, 10, 10],
            "interest_coverage": [3, 3, 3],
            "asset_turnover": [1, 1, 1],
        }
    )

    peer_groups = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "peer_group_name": ["Test Group"] * 3,
            "company_id": ["AAA", "BBB", "CCC"],
            "is_benchmark": [True, False, False],
        }
    )

    result = build_peer_percentiles(financial_data, peer_groups)

    de = result[result["metric"] == "D/E"].sort_values("value")

    assert de.iloc[0]["percentile_rank"] == 1.0
    assert de.iloc[-1]["percentile_rank"] == 0.0


def test_unassigned_company_does_not_raise():
    financial_data = pd.DataFrame(
        {
            "company_id": ["AAA", "BBB"],
            "year": [2024, 2024],
            "return_on_equity_pct": [10, 20],
            "roce_pct": [10, 20],
            "net_profit_margin_pct": [10, 20],
            "debt_to_equity": [1, 2],
            "free_cash_flow_cr": [100, 200],
            "pat_cagr_5yr": [10, 20],
            "revenue_cagr_5yr": [10, 20],
            "eps_cagr_5yr": [10, 20],
            "interest_coverage": [3, 4],
            "asset_turnover": [1, 2],
        }
    )

    peer_groups = pd.DataFrame(
        {
            "id": [1],
            "peer_group_name": ["Test Group"],
            "company_id": ["AAA"],
            "is_benchmark": [True],
        }
    )

    result = build_peer_percentiles(financial_data, peer_groups)

    assert "BBB" not in result["company_id"].unique()
    assert "AAA" in result["company_id"].unique()


def test_percentiles_are_between_zero_and_one():
    financial_data = pd.DataFrame(
        {
            "company_id": ["AAA", "BBB", "CCC"],
            "year": [2024, 2024, 2024],
            "return_on_equity_pct": [10, 20, 30],
            "roce_pct": [10, 20, 30],
            "net_profit_margin_pct": [5, 10, 15],
            "debt_to_equity": [1, 2, 3],
            "free_cash_flow_cr": [100, 200, 300],
            "pat_cagr_5yr": [5, 10, 15],
            "revenue_cagr_5yr": [5, 10, 15],
            "eps_cagr_5yr": [5, 10, 15],
            "interest_coverage": [2, 4, 6],
            "asset_turnover": [0.5, 1.0, 1.5],
        }
    )

    peer_groups = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "peer_group_name": ["Test Group"] * 3,
            "company_id": ["AAA", "BBB", "CCC"],
            "is_benchmark": [True, False, False],
        }
    )

    result = build_peer_percentiles(financial_data, peer_groups)

    valid = result["percentile_rank"].dropna()

    assert (valid >= 0).all()
    assert (valid <= 1).all()


def test_database_peer_percentiles_table():
    conn = sqlite3.connect("nifty100.db")

    columns = pd.read_sql_query(
        "PRAGMA table_info(peer_percentiles)",
        conn,
    )

    conn.close()

    actual_columns = columns["name"].tolist()

    expected_columns = [
        "company_id",
        "peer_group_name",
        "metric",
        "value",
        "percentile_rank",
        "year",
    ]

    assert actual_columns == expected_columns