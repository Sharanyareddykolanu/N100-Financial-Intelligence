"""
Day 08 - Profitability Ratios

Calculates:
- Net Profit Margin (NPM)
- Operating Profit Margin (OPM)
- Return on Equity (ROE)
- Return on Capital Employed (ROCE)
- Return on Assets (ROA)
"""


def net_profit_margin(net_profit, sales):
    """
    Net Profit Margin = (Net Profit / Sales) * 100

    Returns None when sales is zero or unavailable.
    """
    if sales is None or sales == 0:
        return None

    if net_profit is None:
        return None

    return (net_profit / sales) * 100


def operating_profit_margin(operating_profit, sales):
    """
    Operating Profit Margin = (Operating Profit / Sales) * 100

    Returns None when sales is zero or unavailable.
    """
    if sales is None or sales == 0:
        return None

    if operating_profit is None:
        return None

    return (operating_profit / sales) * 100


def check_opm_difference(computed_opm, reported_opm):
    """
    Cross-check computed OPM against the reported opm_percentage.

    Returns:
        difference percentage points
        mismatch flag

    A mismatch is logged when the absolute difference is > 1%.
    """
    if computed_opm is None or reported_opm is None:
        return None, False

    difference = abs(computed_opm - reported_opm)
    mismatch = difference > 1

    if mismatch:
        print(
            f"OPM mismatch: computed={computed_opm:.2f}%, "
            f"reported={reported_opm:.2f}%, "
            f"difference={difference:.2f}%"
        )

    return difference, mismatch


def return_on_equity(net_profit, equity_capital, reserves):
    """
    ROE = Net Profit / (Equity Capital + Reserves) * 100

    Returns None when total equity is zero or negative.
    """
    if net_profit is None:
        return None

    if equity_capital is None:
        equity_capital = 0

    if reserves is None:
        reserves = 0

    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return (net_profit / equity) * 100


def return_on_capital_employed(
    ebit,
    equity_capital,
    reserves,
    borrowings
):
    """
    ROCE = EBIT / (Equity + Reserves + Borrowings) * 100

    Returns None when capital employed is zero or negative.
    """
    if ebit is None:
        return None

    if equity_capital is None:
        equity_capital = 0

    if reserves is None:
        reserves = 0

    if borrowings is None:
        borrowings = 0

    capital_employed = (
        equity_capital +
        reserves +
        borrowings
    )

    if capital_employed <= 0:
        return None

    return (ebit / capital_employed) * 100


def return_on_assets(net_profit, total_assets):
    """
    ROA = Net Profit / Total Assets * 100

    Returns None when total assets is zero or unavailable.
    """
    if net_profit is None:
        return None

    if total_assets is None or total_assets == 0:
        return None

    return (net_profit / total_assets) * 100


def sector_relative_roce(roce, sector_benchmark):
    """
    Compare ROCE with the sector benchmark.

    Returns the difference between company ROCE
    and the sector benchmark.
    """
    if roce is None or sector_benchmark is None:
        return None

    return roce - sector_benchmark


def evaluate_roce(roce, broad_sector, sector_benchmark=None):
    """
    Evaluate ROCE using a sector-relative benchmark for Financials.

    Financials:
        Returns ROCE relative to the sector benchmark.

    Other sectors:
        Returns absolute ROCE.
    """
    if roce is None:
        return None

    if (
        broad_sector is not None
        and str(broad_sector).strip().lower() == "financials"
    ):
        return sector_relative_roce(
            roce,
            sector_benchmark
        )

    return roce
# ============================================================
# Day 09 - Leverage & Efficiency Ratios
# ============================================================


def debt_to_equity(borrowings, equity_capital, reserves):
    """
    Debt-to-Equity = Borrowings / (Equity Capital + Reserves)

    Returns 0 when borrowings is zero.
    Returns None when equity is zero or negative.
    """
    if borrowings is None:
        borrowings = 0

    if equity_capital is None:
        equity_capital = 0

    if reserves is None:
        reserves = 0

    equity = equity_capital + reserves

    if borrowings == 0:
        return 0

    if equity <= 0:
        return None

    return borrowings / equity


def high_leverage_flag(
    debt_to_equity_ratio,
    broad_sector
):
    """
    Flag companies with D/E > 5.

    Financials companies are excluded because
    higher leverage is normal in the sector.
    """
    if debt_to_equity_ratio is None:
        return False

    if (
        broad_sector is not None
        and str(broad_sector).strip().lower() == "financials"
    ):
        return False

    return debt_to_equity_ratio > 5


def interest_coverage_ratio(
    operating_profit,
    other_income,
    interest
):
    """
    Interest Coverage Ratio (ICR)

    ICR = (Operating Profit + Other Income) / Interest

    Returns None when interest is zero or unavailable.
    """
    if interest is None or interest == 0:
        return None

    if operating_profit is None:
        operating_profit = 0

    if other_income is None:
        other_income = 0

    return (operating_profit + other_income) / interest


def icr_label(icr):
    """
    Returns 'Debt Free' when ICR is None.

    Otherwise returns None.
    """
    if icr is None:
        return "Debt Free"

    return None


def icr_warning_flag(icr):
    """
    Flag companies where ICR < 1.5.

    Such companies may have difficulty covering
    their interest payments.
    """
    if icr is None:
        return False

    return icr < 1.5


def net_debt(borrowings, investments):
    """
    Net Debt = Borrowings - Investments

    Investments are treated as a liquid asset proxy.
    """
    if borrowings is None:
        borrowings = 0

    if investments is None:
        investments = 0

    return borrowings - investments


def asset_turnover(sales, total_assets):
    """
    Asset Turnover = Sales / Total Assets

    Returns None when total assets is zero or unavailable.
    """
    if total_assets is None or total_assets == 0:
        return None

    if sales is None:
        return None

    return sales / total_assets
# ============================================================
# Day 09 - Leverage & Efficiency Ratio Tests
# ============================================================

from src.analytics.ratios import (
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    icr_label,
    icr_warning_flag,
    net_debt,
    asset_turnover,
)


def test_debt_to_equity_normal():
    assert debt_to_equity(50, 100, 50) == 1 / 3


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
# ============================================================
# Day 09 - Leverage & Efficiency Ratio Tests
# ============================================================

from src.analytics.ratios import (
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    icr_label,
    icr_warning_flag,
    net_debt,
    asset_turnover,
)


def test_debt_to_equity_normal():
    assert debt_to_equity(50, 100, 50) == 1 / 3


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