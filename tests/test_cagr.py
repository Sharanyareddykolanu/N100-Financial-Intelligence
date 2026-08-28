import pytest

from src.analytics.cagr import (
    calculate_cagr,
    compute_window_cagr,
    revenue_cagr,
    pat_cagr,
    eps_cagr,
)


def test_normal_cagr():
    value, flag = calculate_cagr(100, 121, 2)

    assert value == pytest.approx(10)
    assert flag is None


def test_positive_to_negative():
    value, flag = calculate_cagr(100, -20, 3)

    assert value is None
    assert flag == "DECLINE_TO_LOSS"


def test_negative_to_positive():
    value, flag = calculate_cagr(-100, 50, 3)

    assert value is None
    assert flag == "TURNAROUND"


def test_both_negative():
    value, flag = calculate_cagr(-100, -50, 3)

    assert value is None
    assert flag == "BOTH_NEGATIVE"


def test_zero_base():
    value, flag = calculate_cagr(0, 100, 3)

    assert value is None
    assert flag == "ZERO_BASE"


def test_insufficient_data():
    value, flag = compute_window_cagr([100, 110, 120], 3)

    assert value is None
    assert flag == "INSUFFICIENT"


def test_three_year_cagr():
    values = [100, 105, 110, 121]

    value, flag = compute_window_cagr(values, 3)

    assert value == pytest.approx(6.5602237)
    assert flag is None


def test_revenue_cagr_flags():
    result = revenue_cagr([100, 110, 120, 130])

    assert "revenue_cagr_3yr" in result
    assert "revenue_cagr_3yr_flag" in result
    assert result["revenue_cagr_5yr_flag"] == "INSUFFICIENT"


def test_pat_cagr():
    result = pat_cagr([50, 55, 60, 66])

    assert result["pat_cagr_3yr"] is not None
    assert result["pat_cagr_3yr_flag"] is None


def test_eps_cagr():
    result = eps_cagr([10, 11, 12, 13])

    assert result["eps_cagr_3yr"] is not None
    assert result["eps_cagr_3yr_flag"] is None