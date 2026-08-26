import pytest

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    check_opm_difference,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
    sector_relative_roce,
)


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