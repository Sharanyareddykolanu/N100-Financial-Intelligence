import pytest

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    check_opm_difference,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
    sector_relative_roce,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    icr_label,
    icr_warning_flag,
    net_debt,
    asset_turnover,
)


# ============================================================
# Day 08 - Profitability Ratio Tests
# ============================================================

def test_net_profit_margin_normal():
    assert net_profit_margin(20, 100) == 20


def test_net_profit_margin_zero_sales():
    assert net_profit_margin(20, 0) is None


def test_operating_profit_margin_normal():
    assert operating_profit_margin(30, 100) == 30


def test_opm_cross_check_match():
    difference, mismatch = check_opm_difference(30, 30.5)

    assert difference == pytest.approx(0.5)
    assert mismatch is False


def test_opm_cross_check_mismatch():
    difference, mismatch = check_opm_difference(30, 32)

    assert difference == pytest.approx(2)
    assert mismatch is True


def test_roe_negative_equity():
    assert return_on_equity(20, 50, -60) is None


def test_roce_normal():
    assert return_on_capital_employed(
        30,
        100,
        50,
        50
    ) == pytest.approx(15)


def test_roa_zero_assets():
    assert return_on_assets(20, 0) is None


# ============================================================
# Day 09 - Leverage & Efficiency Ratio Tests
# ============================================================

def test_debt_to_equity_normal():
    assert debt_to_equity(50, 100, 50) == pytest.approx(1 / 3)


def test_debt_to_equity_debt_free_returns_zero():
    assert debt_to_equity(0, 100, 50) == 0


def test_debt_to_equity_negative_equity_returns_none():
    assert debt_to_equity(50, -100, 20) is None


def test_high_debt_equity_flag():
    assert high_leverage_flag(6, "Information Technology") is True


def test_financials_high_debt_equity_not_flagged():
    assert high_leverage_flag(6, "Financials") is False


def test_icr_interest_zero_returns_none():
    assert interest_coverage_ratio(100, 20, 0) is None


def test_icr_label_debt_free():
    assert icr_label(None) == "Debt Free"


def test_icr_warning_flag():
    assert icr_warning_flag(1.2) is True