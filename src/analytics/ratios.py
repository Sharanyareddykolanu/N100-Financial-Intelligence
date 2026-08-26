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