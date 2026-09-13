import pytest

from src.analytics.ratios import (
    operating_profit_margin,
    check_opm_difference,
    return_on_equity,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
)

from src.analytics.cagr import calculate_cagr
from src.analytics.cashflow import cfo_quality_score


def test_roe_positive_equity():
    assert return_on_equity(20, 100, 100) == 10


def test_roe_negative_equity_returns_none():
    assert return_on_equity(20, -100, 20) is None


def test_debt_to_equity_normal():
    assert debt_to_equity(50, 100, 50) == pytest.approx(1 / 3)


def test_debt_free_company_returns_zero():
    assert debt_to_equity(0, 100, 50) == 0


def test_high_debt_non_financial_flag():
    assert high_leverage_flag(6, "Information Technology") is True


def test_high_debt_financial_company_not_flagged():
    assert high_leverage_flag(6, "Financials") is False


def test_icr_interest_zero_returns_none():
    assert interest_coverage_ratio(100, 20, 0) is None


def test_icr_normal_calculation():
    assert interest_coverage_ratio(100, 20, 10) == 12


def test_cagr_normal_calculation():
    result, flag = calculate_cagr(100, 121, 2)
    assert result == pytest.approx(10.0, abs=0.01)
    assert flag is None


def test_cagr_turnaround_flag():
    result, flag = calculate_cagr(-100, 150, 5)
    assert result is None
    assert flag == "TURNAROUND"


def test_cagr_decline_to_loss_flag():
    result, flag = calculate_cagr(100, -50, 5)
    assert result is None
    assert flag == "DECLINE_TO_LOSS"


def test_cagr_both_negative_flag():
    result, flag = calculate_cagr(-100, -50, 5)
    assert result is None
    assert flag == "BOTH_NEGATIVE"


def test_opm_calculation():
    assert operating_profit_margin(20, 100) == 20


def test_opm_cross_check_no_divergence():
    difference, mismatch = check_opm_difference(20, 20.5)
    assert difference == pytest.approx(0.5)
    assert mismatch is False


def test_opm_cross_check_divergence_flag():
    difference, mismatch = check_opm_difference(20, 22)
    assert difference == pytest.approx(2)
    assert mismatch is True


def test_cfo_quality_high():
    score, label = cfo_quality_score(
        [120, 130, 140],
        [100, 100, 100]
    )
    assert score == pytest.approx(1.3)
    assert label == "High Quality"


def test_cfo_quality_moderate():
    score, label = cfo_quality_score(
        [60, 70, 80],
        [100, 100, 100]
    )
    assert score == pytest.approx(0.7)
    assert label == "Moderate"


def test_cfo_quality_zero_pat_is_ignored():
    score, label = cfo_quality_score(
        [100, 120, 140],
        [100, 0, 100]
    )
    assert score == pytest.approx(1.2)
    assert label == "High Quality"


def test_cfo_quality_insufficient_data():
    score, label = cfo_quality_score(
        [None, None],
        [100, 100]
    )
    assert score is None
    assert label is None

def test_cagr_insufficient_years_returns_flag():
    result, flag = calculate_cagr(100, 120, 0)
    assert result is None
    assert flag == "INSUFFICIENT"
